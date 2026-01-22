import logging
import os
from datetime import timedelta

import redis
from celery import shared_task
from django.utils import timezone

from .models import AnalysisResult, GithubEvent, GithubUser
from .services import GeminiClient, GitHubClient, GithubEventParser

logger = logging.getLogger(__name__)

# Redis Client 설정
REDIS_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
redis_client = redis.StrictRedis.from_url(REDIS_URL)


@shared_task(bind=True)
def analyze_user_task(self, username):
    logger.info(f"Task started for {username}")

    lock_key = f"lock:analyze:{username}"

    try:
        # Redis Lock 시도 (Non-blocking, Timeout 60s)
        with redis_client.lock(lock_key, timeout=60, blocking=False):
            logger.info(f"Lock acquired for {username}")

            user, created = GithubUser.objects.get_or_create(
                username=username,
            )

            # 1. GitHub Event 증분 수집
            github_client = GitHubClient()
            events_data = github_client.get_user_events(username)

            # DB에 저장된 가장 최신 이벤트 ID 확인 (증분 수집 중단점)
            latest_event_id = None
            if not created:
                last_event = GithubEvent.objects.filter(user=user).order_by("-created_at").first()
                if last_event:
                    latest_event_id = last_event.event_id

            parsed_events = GithubEventParser.parse(events_data, github_client, latest_event_id)

            new_events_count = 0
            for parsed in parsed_events:
                # 이벤트 저장
                GithubEvent.objects.create(
                    event_id=parsed.id,
                    user=user,
                    event_type=parsed.type,
                    repo_name=parsed.repo_name,
                    message=parsed.message,
                    created_at=parsed.created_at,
                )
                new_events_count += 1

            logger.info(f"Collected {new_events_count} new events for {username}")

            # 2. 최근 24시간 이벤트 조회
            yesterday = timezone.now() - timedelta(days=1)
            recent_events = GithubEvent.objects.filter(user=user, created_at__gte=yesterday).order_by("created_at")

            # 3. Gemini 분석 요청
            analysis_input = []
            for event in recent_events:
                analysis_input.append(
                    {
                        "event_type": event.event_type,
                        "repo_name": event.repo_name,
                        "event_time": event.created_at.isoformat(),
                        "message": event.message,
                    }
                )

            gemini_client = GeminiClient()
            analysis_data = gemini_client.analyze_events(analysis_input)

            # 4. 결과 저장
            AnalysisResult.objects.create(
                user=user,
                persona_title=analysis_data.get("persona_title", "Unknown"),
                comment=analysis_data.get("comment", "No comment"),
                status_enum=analysis_data.get("status_enum", AnalysisResult.Status.NEUTRAL),
                reason=analysis_data.get("reason", ""),
                analysis_metadata={
                    "event_count": recent_events.count(),
                    "new_events": new_events_count,
                    "model": "gemini-2.5-flash-lite",
                },
            )

            user.last_analyzed_at = timezone.now()
            user.save()

            logger.info(f"Analysis completed for {username}")
            return "SUCCESS"

    except redis.exceptions.LockError:
        logger.info(f"Skipping task for {username} - Lock is held")
        return "SKIPPED_LOCKED"

    except Exception as e:
        logger.error(f"Task failed for {username}: {e}")
        raise e
