import logging

from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from .models import AnalysisResult, GithubUser
from .tasks import analyze_user_task

logger = logging.getLogger(__name__)


@require_GET
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def svg(request):
    username = request.GET.get("username")

    # 1. Username 유효성 검사 (간단히)
    if not username:
        return render(request, "card/error.svg", content_type="image/svg+xml", status=400)

    try:
        user = GithubUser.objects.filter(username=username).first()

        # 2. Cold Miss 확인 (사용자가 없거나, 분석 기록이 없음)
        if not user or not user.last_analyzed_at:
            # Task 트리거
            analyze_user_task.delay(username)
            logger.info(f"Triggered analysis task for {username} (Cold Miss)")

            # Placeholder 반환
            return render(request, "card/placeholder.svg", content_type="image/svg+xml")

        # 3. Hit (Fresh/Stale)
        latest_result = AnalysisResult.objects.filter(user=user).first()
        if latest_result:
            # Stale Check (1시간)
            # last_analyzed_at이 없거나 1시간이 지났으면 재분석 트리거
            if not user.last_analyzed_at or (timezone.now() - user.last_analyzed_at > timezone.timedelta(hours=1)):
                analyze_user_task.delay(username)
                logger.info(f"Triggered re-analysis for {username} (Stale)")

            return render(request, "card/card.svg", {"result": latest_result}, content_type="image/svg+xml")

        # 분석 기록이 없으면 (Task가 아직 안 끝났거나 실패) 다시 Placeholder
        return render(request, "card/placeholder.svg", content_type="image/svg+xml")

    except Exception as e:
        logger.error(f"View error: {e}")
        return render(request, "card/error.svg", content_type="image/svg+xml", status=500)
