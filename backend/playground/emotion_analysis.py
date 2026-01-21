import datetime
import json
import logging
import os
from dataclasses import dataclass
from enum import StrEnum
from pprint import pprint
from typing import Any

import requests
from dotenv import load_dotenv
from google import genai
from transformers import pipeline

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class GitHubEventType(StrEnum):
    """
    GitHub 이벤트 타입을 정의하는 Enum 클래스입니다.
    StrEnum을 상속받아 문자열 비교가 가능합니다.
    """

    ISSUE_COMMENT = "IssueCommentEvent"
    PR_REVIEW_COMMENT = "PullRequestReviewCommentEvent"
    COMMIT_COMMENT = "CommitCommentEvent"
    DISCUSSION_COMMENT = "DiscussionCommentEvent"
    PR_REVIEW = "PullRequestReviewEvent"
    ISSUES = "IssuesEvent"
    PULL_REQUEST = "PullRequestEvent"
    GOLLUM = "GollumEvent"
    PUSH = "PushEvent"


class StandardEmotion(StrEnum):
    """
    프로젝트에서 사용하는 표준 감정 분류 (Enum)
    """

    JOY = "JOY"  # 기쁨/성취
    ANGER = "ANGER"  # 분노/짜증
    ANXIETY = "ANXIETY"  # 불안/다급
    SADNESS = "SADNESS"  # 피로/우울
    CONFUSION = "CONFUSION"  # 당황/놀람
    NEUTRAL = "NEUTRAL"  # 평온/중립


@dataclass
class ParsedEvent:
    """
    분석을 위해 GitHub 이벤트에서 추출한 데이터 모델 (DTO)
    """

    id: str
    created_at: str
    type: str | None
    repo_name: str
    message: str
    emotion: list[dict] | None = None


@dataclass(frozen=True)
class EmotionResult:
    """
    감정 분석 결과 모델 (Value Object)
    불변 객체로 관리합니다.
    """

    emotion: StandardEmotion
    score: float


class GitHubClient:
    """
    GitHub API와의 통신을 담당하는 클라이언트 클래스입니다.
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None):
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"token {token}"})

    def get_user_events(self, username: str, per_page: int | None = None) -> list[dict[str, Any]]:
        """특정 유저의 최근 이벤트를 가져옵니다."""
        url = f"{self.BASE_URL}/users/{username}/events"
        params = {"per_page": per_page} if per_page else {}

        try:
            logger.info(f"Fetching events for user: {username}")
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch events: {e}")
            return []

    def fetch_commit_message(self, url: str) -> str | None:
        """PushEvent의 커밋 메시지를 별도로 조회합니다."""
        try:
            response = self.session.get(url)
            if response.status_code == 200:
                return response.json().get("commit", {}).get("message")
        except requests.exceptions.RequestException:
            pass
        return None


class EventParser:
    """
    GitHub 이벤트 데이터에서 분석 가능한 텍스트를 추출하는 파서 클래스입니다.
    """

    @staticmethod
    def parse(events: list[dict[str, Any]], client: GitHubClient) -> list[ParsedEvent]:
        extracted_data = []

        for event in events:
            id = event.get("id")
            etype = event.get("type")
            payload = event.get("payload", {})
            created_at = event.get("created_at", "")
            repo_name = event.get("repo", {}).get("name", "")

            message = ""

            # 1. 댓글/리뷰 계열
            if etype in [
                GitHubEventType.ISSUE_COMMENT,
                GitHubEventType.PR_REVIEW_COMMENT,
                GitHubEventType.COMMIT_COMMENT,
                GitHubEventType.DISCUSSION_COMMENT,
            ]:
                message = payload.get("comment", {}).get("body")

            elif etype == GitHubEventType.PR_REVIEW:
                message = payload.get("review", {}).get("body")

            # 2. 글 작성 계열 (Issues, PR)
            elif etype in [GitHubEventType.ISSUES, GitHubEventType.PULL_REQUEST]:
                if payload.get("action") in ["opened", "edited"]:
                    obj = payload.get("issue") or payload.get("pull_request")
                    if obj:
                        title = obj.get("title", "")
                        body = obj.get("body", "")
                        message = f"{title}\n{body}"

            # 3. 위키 수정
            elif etype == GitHubEventType.GOLLUM:
                for page in payload.get("pages", []):
                    summary = page.get("summary", "")
                    title = page.get("title", "")
                    if summary:
                        message = f"{title}\n{summary}"

            # 4. PushEvent (추가 API 호출 필요)
            elif etype == GitHubEventType.PUSH:
                head_commit_sha = payload.get("head")
                repo_url = event.get("repo", {}).get("url")

                # 1. 테스트용 데이터 확인
                if event.get("message"):
                    message = event.get("message")
                elif head_commit_sha and repo_url:
                    logger.info("Fetching commit message...")
                    commit_url = f"{repo_url}/commits/{head_commit_sha}"
                    msg = client.fetch_commit_message(commit_url)
                    if msg:
                        message = msg

            if message:
                extracted_data.append(
                    ParsedEvent(
                        id=id,
                        created_at=created_at,
                        type=etype,
                        repo_name=repo_name,
                        message=message,
                    )
                )

        return extracted_data


class EmotionAnalyzer:
    """
    텍스트의 감정을 분석하는 클래스입니다.
    ML 모델의 결과를 사용하여 표준 감정(StandardEmotion)을 반환합니다.
    """

    # MODEL_ID = "blue2959/xlm-roberta-base-finetuned-kor-8-emotions_v1.2"
    # MODEL_ID = "Seonghaa/korean-emotion-classifier-roberta"
    # MODEL_ID = "Jinuuuu/KoELECTRA_fine_tunning_emotion"
    MODEL_ID = "noridorimari/emotion_classifier"

    # 1. ML 모델의 Raw Label -> 모델의 의미적 Label
    # blue2959/xlm-roberta-base-finetuned-kor-8-emotions_v1.2
    # MODEL_LABELS = {
    #     "LABEL_0": "joy",
    #     "LABEL_1": "surprise",
    #     "LABEL_2": "anger",
    #     "LABEL_3": "fear",
    #     "LABEL_4": "hurt",
    #     "LABEL_5": "sadness",
    #     "LABEL_6": "neutral",
    # }

    # noridorimari/emotion_classifier
    MODEL_LABELS = {
        "LABEL_0": "기쁨",  # happy
        "LABEL_1": "당황",  # embarrass
        "LABEL_2": "분노",  # anger
        "LABEL_3": "불안",  # unrest
        "LABEL_4": "상처",  # damaged
        "LABEL_5": "슬픔",  # sadness
    }

    def __init__(self, device: int = -1):
        logger.info(f"Loading emotion model: {self.MODEL_ID}")

        self.classifier = pipeline(
            "text-classification",
            model=self.MODEL_ID,
            top_k=None,
            device=device,
            truncation=True,
            max_length=512,
        )

    def analyze(self, text: str) -> dict:
        # ML Inference
        results = self.classifier(text)
        # results 예시: [[{'label': 'LABEL_0', 'score': 0.99...}]]
        results = results[0]

        # Mapping (Raw Label -> Model Emotion -> Standard Emotion)
        for result in results:
            result["label"] = self.MODEL_LABELS.get(result["label"], "")
            result["score"] = round(result["score"], 4)

        return results


def main():
    # .env 파일 로드 (환경 변수 설정)
    # 프로젝트 구조상 backend/.env 위치를 명시적으로 지정하여 실행 위치에 관계없이 로드
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(base_path, ".env")
    load_dotenv(dotenv_path=env_path)

    # 설정
    target_user = "torvalds"  # torvalds, joshua1988
    github_token = os.getenv("GITHUB_TOKEN")  # 환경 변수에서 토큰 로드 권장

    # # # 1. 클라이언트 초기화 및 데이터 수집
    client = GitHubClient(token=github_token)
    # events = client.get_user_events(target_user)
    # print(events)
    #
    with open("data.json", encoding="UTF8") as f:
        events = json.load(f)

    # # 2. 데이터 파싱
    parsed_events = EventParser.parse(events, client)
    logger.info(f"Extracted {len(parsed_events)} messages for analysis.")
    # print(events)

    if not parsed_events:
        logger.warning("No messages found to analyze.")
        return

    # # 3. 감정 분석
    # analyzer = EmotionAnalyzer(device=-1)  # CPU 사용
    #
    # for event in parsed_events:
    #     result = analyzer.analyze(event.message)
    #     event.emotion = result
    #     print(f"{event.id} [{event.created_at}] {event.repo_name} - {event.type}: {event.emotion}")

    # 4. Gemini 로 분석
    gemini_api_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_api_key:
        logger.warning("GEMINI_API_KEY is not set. Skipping Gemini analysis.")
        return

    gemini_client = genai.Client(api_key=gemini_api_key)

    # 프롬프트 파일 읽기
    prompt_file_path = os.path.join(os.path.dirname(__file__), "prompt.md")
    if not os.path.exists(prompt_file_path):
        logger.error(f"Prompt file not found: {prompt_file_path}")
        return

    with open(prompt_file_path, encoding="utf-8") as f:
        system_prompt = f.read()

    system_prompt = system_prompt.replace("{current_time}", str(datetime.datetime.now().isoformat()))

    # 분석 데이터 구성
    analysis_input = []
    for event in parsed_events:
        analysis_input.append(
            {
                "event_time": event.created_at,
                "event_type": event.type,
                "repo_name": event.repo_name,
                "message": event.message,
            }
        )

    # Gemini 호출
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=json.dumps(analysis_input),
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                # response_json_schema=context.response_schema,
            ),
        )

        logger.info("Gemini Analysis Result:")
        print(response.text)

    except Exception as e:
        logger.error(f"Failed to analyze with Gemini: {e}")


if __name__ == "__main__":
    main()


"""
[2026-01-19T00:05:27Z] torvalds/HunspellColorize - PushEvent: NEUTRAL (0.9965)
[2026-01-18T23:49:50Z] torvalds/linux - PushEvent: NEUTRAL (0.9959)
[2026-01-18T21:58:01Z] torvalds/HunspellColorize - PushEvent: NEUTRAL (0.9854)
[2026-01-18T03:32:52Z] torvalds/linux - PushEvent: NEUTRAL (0.9321)
[2026-01-18T03:24:10Z] torvalds/AudioNoise - IssueCommentEvent: NEUTRAL (0.9971)
[2026-01-18T03:21:13Z] torvalds/AudioNoise - PushEvent: NEUTRAL (0.9911)
[2026-01-17T23:55:08Z] torvalds/AudioNoise - PushEvent: NEUTRAL (0.9983)
[2026-01-17T21:14:04Z] torvalds/AudioNoise - PushEvent: NEUTRAL (0.9963)
[2026-01-17T18:39:39Z] torvalds/AudioNoise - PushEvent: NEUTRAL (0.9975)
[2026-01-17T18:22:27Z] torvalds/AudioNoise - IssueCommentEvent: NEUTRAL (0.9973)
[2026-01-17T18:18:09Z] torvalds/linux - PushEvent: NEUTRAL (0.9980)
[2026-01-17T05:02:08Z] torvalds/linux - PushEvent: NEUTRAL (0.6108)
[2026-01-16T23:45:38Z] torvalds/linux - PushEvent: NEUTRAL (0.9946)
[2026-01-16T20:24:05Z] torvalds/linux - PushEvent: NEUTRAL (0.7748)
[2026-01-16T17:46:36Z] torvalds/AudioNoise - IssueCommentEvent: NEUTRAL (0.9903)
[2026-01-16T17:42:50Z] torvalds/AudioNoise - PushEvent: NEUTRAL (0.9935)
[2026-01-16T17:42:16Z] torvalds/AudioNoise - IssueCommentEvent: NEUTRAL (0.9944)
[2026-01-16T01:00:15Z] torvalds/linux - PushEvent: NEUTRAL (0.9966)
[2026-01-15T23:12:55Z] torvalds/AudioNoise - PushEvent: NEUTRAL (0.9982)
[2026-01-15T20:12:06Z] torvalds/linux - PushEvent: ANGER (0.6500)
[2026-01-15T01:22:57Z] torvalds/AudioNoise - PushEvent: NEUTRAL (0.9986)
[2026-01-14T21:08:52Z] torvalds/linux - PushEvent: NEUTRAL (0.9959)
[2026-01-14T21:08:20Z] torvalds/AudioNoise - IssueCommentEvent: NEUTRAL (0.9976)

{
  "status_enum": "NEUTRAL",
  "persona_title": "침착한 코드 흐름",
  "comment": "시스템 부하 없음. 현재 상태는 안정 모드 진입으로 추정됨."
}
"""

"""blue2959/xlm-roberta-base-finetuned-kor-8-emotions_v1.2

7621489697 [2026-01-19T19:32:53Z] torvalds/uemacs - PushEvent: [{'label': 'neutral', 'score': 0.9938}, {'label': 'sadness', 'score': 0.0038}, {'label': 'anger', 'score': 0.0017}, {'label': 'surprise', 'score': 0.0003}, {'label': 'joy', 'score': 0.0002}, {'label': 'fear', 'score': 0.0002}, {'label': 'hurt', 'score': 0.0}]
7620741436 [2026-01-19T18:58:10Z] torvalds/uemacs - PushEvent: [{'label': 'neutral', 'score': 0.9936}, {'label': 'surprise', 'score': 0.0028}, {'label': 'sadness', 'score': 0.0017}, {'label': 'anger', 'score': 0.0008}, {'label': 'fear', 'score': 0.0005}, {'label': 'joy', 'score': 0.0005}, {'label': 'hurt', 'score': 0.0001}]
7618585211 [2026-01-19T17:25:41Z] torvalds/HunspellColorize - PushEvent: [{'label': 'neutral', 'score': 0.9981}, {'label': 'joy', 'score': 0.0007}, {'label': 'anger', 'score': 0.0005}, {'label': 'sadness', 'score': 0.0003}, {'label': 'surprise', 'score': 0.0003}, {'label': 'fear', 'score': 0.0001}, {'label': 'hurt', 'score': 0.0}]
7593945715 [2026-01-19T00:05:27Z] torvalds/HunspellColorize - PushEvent: [{'label': 'neutral', 'score': 0.9965}, {'label': 'sadness', 'score': 0.0018}, {'label': 'anger', 'score': 0.0006}, {'label': 'surprise', 'score': 0.0005}, {'label': 'joy', 'score': 0.0005}, {'label': 'fear', 'score': 0.0001}, {'label': 'hurt', 'score': 0.0}]
7593731760 [2026-01-18T23:49:50Z] torvalds/linux - PushEvent: [{'label': 'neutral', 'score': 0.9959}, {'label': 'sadness', 'score': 0.0018}, {'label': 'surprise', 'score': 0.0008}, {'label': 'joy', 'score': 0.0006}, {'label': 'anger', 'score': 0.0005}, {'label': 'fear', 'score': 0.0003}, {'label': 'hurt', 'score': 0.0001}]
7592196583 [2026-01-18T21:58:01Z] torvalds/HunspellColorize - PushEvent: [{'label': 'neutral', 'score': 0.9854}, {'label': 'sadness', 'score': 0.0118}, {'label': 'anger', 'score': 0.0015}, {'label': 'fear', 'score': 0.0005}, {'label': 'surprise', 'score': 0.0004}, {'label': 'joy', 'score': 0.0004}, {'label': 'hurt', 'score': 0.0}]
7576394206 [2026-01-18T03:32:52Z] torvalds/linux - PushEvent: [{'label': 'neutral', 'score': 0.9321}, {'label': 'anger', 'score': 0.0518}, {'label': 'fear', 'score': 0.0061}, {'label': 'surprise', 'score': 0.0046}, {'label': 'sadness', 'score': 0.003}, {'label': 'hurt', 'score': 0.0016}, {'label': 'joy', 'score': 0.0008}]
5884121095 [2026-01-18T03:24:10Z] torvalds/AudioNoise - IssueCommentEvent: [{'label': 'neutral', 'score': 0.9971}, {'label': 'joy', 'score': 0.0009}, {'label': 'surprise', 'score': 0.0008}, {'label': 'anger', 'score': 0.0005}, {'label': 'sadness', 'score': 0.0004}, {'label': 'fear', 'score': 0.0002}, {'label': 'hurt', 'score': 0.0001}]
7576261026 [2026-01-18T03:21:13Z] torvalds/AudioNoise - PushEvent: [{'label': 'neutral', 'score': 0.9911}, {'label': 'surprise', 'score': 0.0037}, {'label': 'sadness', 'score': 0.0019}, {'label': 'anger', 'score': 0.0012}, {'label': 'joy', 'score': 0.001}, {'label': 'fear', 'score': 0.0008}, {'label': 'hurt', 'score': 0.0003}]
7573768000 [2026-01-17T23:55:08Z] torvalds/AudioNoise - PushEvent: [{'label': 'neutral', 'score': 0.9983}, {'label': 'sadness', 'score': 0.0004}, {'label': 'anger', 'score': 0.0004}, {'label': 'joy', 'score': 0.0004}, {'label': 'surprise', 'score': 0.0004}, {'label': 'fear', 'score': 0.0001}, {'label': 'hurt', 'score': 0.0}]
7571750643 [2026-01-17T21:14:04Z] torvalds/AudioNoise - PushEvent: [{'label': 'neutral', 'score': 0.9963}, {'label': 'joy', 'score': 0.0013}, {'label': 'anger', 'score': 0.0011}, {'label': 'sadness', 'score': 0.0008}, {'label': 'surprise', 'score': 0.0003}, {'label': 'fear', 'score': 0.0002}, {'label': 'hurt', 'score': 0.0001}]
7569650640 [2026-01-17T18:39:39Z] torvalds/AudioNoise - PushEvent: [{'label': 'neutral', 'score': 0.9975}, {'label': 'sadness', 'score': 0.0007}, {'label': 'joy', 'score': 0.0007}, {'label': 'surprise', 'score': 0.0005}, {'label': 'anger', 'score': 0.0004}, {'label': 'fear', 'score': 0.0002}, {'label': 'hurt', 'score': 0.0}]

{
  "status_enum": "NEUTRAL",
  "persona_title": "만성 코드 굴리기",
  "comment": "정신없이 코드를 굴리는 중. 집중력이 흐트러질 틈이 없습니다."
}
"""

"""Seonghaa/korean-emotion-classifier-roberta

7621489697 [2026-01-19T19:32:53Z] torvalds/uemacs - PushEvent: [{'label': '평온', 'score': 0.9628}, {'label': '분노', 'score': 0.0098}, {'label': '불안', 'score': 0.0074}, {'label': '슬픔', 'score': 0.007}, {'label': '당황', 'score': 0.0065}, {'label': '기쁨', 'score': 0.0064}]
7620741436 [2026-01-19T18:58:10Z] torvalds/uemacs - PushEvent: [{'label': '평온', 'score': 0.9645}, {'label': '분노', 'score': 0.0083}, {'label': '슬픔', 'score': 0.0072}, {'label': '당황', 'score': 0.0067}, {'label': '불안', 'score': 0.0067}, {'label': '기쁨', 'score': 0.0066}]
7618585211 [2026-01-19T17:25:41Z] torvalds/HunspellColorize - PushEvent: [{'label': '평온', 'score': 0.9643}, {'label': '분노', 'score': 0.009}, {'label': '불안', 'score': 0.0069}, {'label': '슬픔', 'score': 0.0068}, {'label': '기쁨', 'score': 0.0067}, {'label': '당황', 'score': 0.0063}]
7593945715 [2026-01-19T00:05:27Z] torvalds/HunspellColorize - PushEvent: [{'label': '평온', 'score': 0.9565}, {'label': '불안', 'score': 0.0152}, {'label': '분노', 'score': 0.01}, {'label': '슬픔', 'score': 0.0066}, {'label': '당황', 'score': 0.0059}, {'label': '기쁨', 'score': 0.0058}]
7593731760 [2026-01-18T23:49:50Z] torvalds/linux - PushEvent: [{'label': '평온', 'score': 0.9644}, {'label': '슬픔', 'score': 0.0079}, {'label': '불안', 'score': 0.0073}, {'label': '당황', 'score': 0.0072}, {'label': '분노', 'score': 0.0067}, {'label': '기쁨', 'score': 0.0066}]
7592196583 [2026-01-18T21:58:01Z] torvalds/HunspellColorize - PushEvent: [{'label': '평온', 'score': 0.9617}, {'label': '불안', 'score': 0.0106}, {'label': '분노', 'score': 0.009}, {'label': '슬픔', 'score': 0.0067}, {'label': '당황', 'score': 0.0061}, {'label': '기쁨', 'score': 0.0059}]
7576394206 [2026-01-18T03:32:52Z] torvalds/linux - PushEvent: [{'label': '평온', 'score': 0.9592}, {'label': '불안', 'score': 0.0145}, {'label': '분노', 'score': 0.0081}, {'label': '슬픔', 'score': 0.0067}, {'label': '당황', 'score': 0.0059}, {'label': '기쁨', 'score': 0.0057}]
5884121095 [2026-01-18T03:24:10Z] torvalds/AudioNoise - IssueCommentEvent: [{'label': '평온', 'score': 0.965}, {'label': '분노', 'score': 0.0075}, {'label': '당황', 'score': 0.0071}, {'label': '슬픔', 'score': 0.0071}, {'label': '기쁨', 'score': 0.0067}, {'label': '불안', 'score': 0.0066}]
7576261026 [2026-01-18T03:21:13Z] torvalds/AudioNoise - PushEvent: [{'label': '평온', 'score': 0.9647}, {'label': '분노', 'score': 0.0082}, {'label': '불안', 'score': 0.0071}, {'label': '슬픔', 'score': 0.007}, {'label': '당황', 'score': 0.0066}, {'label': '기쁨', 'score': 0.0065}]
7573768000 [2026-01-17T23:55:08Z] torvalds/AudioNoise - PushEvent: [{'label': '평온', 'score': 0.9638}, {'label': '분노', 'score': 0.009}, {'label': '불안', 'score': 0.0072}, {'label': '슬픔', 'score': 0.0069}, {'label': '기쁨', 'score': 0.0065}, {'label': '당황', 'score': 0.0065}]
7571750643 [2026-01-17T21:14:04Z] torvalds/AudioNoise - PushEvent: [{'label': '평온', 'score': 0.9651}, {'label': '분노', 'score': 0.0076}, {'label': '슬픔', 'score': 0.007}, {'label': '불안', 'score': 0.007}, {'label': '기쁨', 'score': 0.0067}, {'label': '당황', 'score': 0.0066}]
7569650640 [2026-01-17T18:39:39Z] torvalds/AudioNoise - PushEvent: [{'label': '평온', 'score': 0.9651}, {'label': '분노', 'score': 0.0078}, {'label': '기쁨', 'score': 0.0071}, {'label': '슬픔', 'score': 0.007}, {'label': '당황', 'score': 0.0066}, {'label': '불안', 'score': 0.0065}]

{
  "status_enum": "NEUTRAL",
  "persona_title": "깊은 코딩의 늪",
  "comment": "영혼 없이 기계적으로 타자만 치는 중. Ctrl+C, Ctrl+V 반복 수행 중"
}
"""

"""Jinuuuu/KoELECTRA_fine_tunning_emotion

7621489697 [2026-01-19T19:32:53Z] torvalds/uemacs - PushEvent: [{'label': 'happy', 'score': 0.4253}, {'label': 'embarrassed', 'score': 0.1853}, {'label': 'angry', 'score': 0.1276}, {'label': 'anxious', 'score': 0.1226}, {'label': 'heartache', 'score': 0.0745}, {'label': 'sad', 'score': 0.0647}]
7620741436 [2026-01-19T18:58:10Z] torvalds/uemacs - PushEvent: [{'label': 'happy', 'score': 0.6016}, {'label': 'embarrassed', 'score': 0.1355}, {'label': 'anxious', 'score': 0.0861}, {'label': 'angry', 'score': 0.0848}, {'label': 'sad', 'score': 0.048}, {'label': 'heartache', 'score': 0.0441}]
7618585211 [2026-01-19T17:25:41Z] torvalds/HunspellColorize - PushEvent: [{'label': 'embarrassed', 'score': 0.3213}, {'label': 'angry', 'score': 0.2154}, {'label': 'heartache', 'score': 0.1408}, {'label': 'sad', 'score': 0.1283}, {'label': 'anxious', 'score': 0.1087}, {'label': 'happy', 'score': 0.0854}]
7593945715 [2026-01-19T00:05:27Z] torvalds/HunspellColorize - PushEvent: [{'label': 'happy', 'score': 0.658}, {'label': 'embarrassed', 'score': 0.1053}, {'label': 'anxious', 'score': 0.0782}, {'label': 'angry', 'score': 0.0748}, {'label': 'sad', 'score': 0.0447}, {'label': 'heartache', 'score': 0.0389}]
7593731760 [2026-01-18T23:49:50Z] torvalds/linux - PushEvent: [{'label': 'anxious', 'score': 0.2723}, {'label': 'angry', 'score': 0.2556}, {'label': 'embarrassed', 'score': 0.1916}, {'label': 'heartache', 'score': 0.14}, {'label': 'sad', 'score': 0.0956}, {'label': 'happy', 'score': 0.045}]
7592196583 [2026-01-18T21:58:01Z] torvalds/HunspellColorize - PushEvent: [{'label': 'happy', 'score': 0.4586}, {'label': 'embarrassed', 'score': 0.1617}, {'label': 'angry', 'score': 0.1195}, {'label': 'anxious', 'score': 0.0928}, {'label': 'heartache', 'score': 0.0858}, {'label': 'sad', 'score': 0.0815}]
7576394206 [2026-01-18T03:32:52Z] torvalds/linux - PushEvent: [{'label': 'happy', 'score': 0.5556}, {'label': 'embarrassed', 'score': 0.1397}, {'label': 'anxious', 'score': 0.1143}, {'label': 'angry', 'score': 0.0919}, {'label': 'heartache', 'score': 0.0496}, {'label': 'sad', 'score': 0.0489}]
5884121095 [2026-01-18T03:24:10Z] torvalds/AudioNoise - IssueCommentEvent: [{'label': 'happy', 'score': 0.5836}, {'label': 'embarrassed', 'score': 0.1281}, {'label': 'anxious', 'score': 0.1011}, {'label': 'angry', 'score': 0.0992}, {'label': 'heartache', 'score': 0.0497}, {'label': 'sad', 'score': 0.0385}]
7576261026 [2026-01-18T03:21:13Z] torvalds/AudioNoise - PushEvent: [{'label': 'happy', 'score': 0.6565}, {'label': 'embarrassed', 'score': 0.1145}, {'label': 'anxious', 'score': 0.0812}, {'label': 'heartache', 'score': 0.0525}, {'label': 'angry', 'score': 0.0506}, {'label': 'sad', 'score': 0.0447}]
7573768000 [2026-01-17T23:55:08Z] torvalds/AudioNoise - PushEvent: [{'label': 'happy', 'score': 0.7757}, {'label': 'embarrassed', 'score': 0.0658}, {'label': 'angry', 'score': 0.0503}, {'label': 'anxious', 'score': 0.0475}, {'label': 'sad', 'score': 0.0315}, {'label': 'heartache', 'score': 0.0292}]
7571750643 [2026-01-17T21:14:04Z] torvalds/AudioNoise - PushEvent: [{'label': 'happy', 'score': 0.4938}, {'label': 'embarrassed', 'score': 0.1657}, {'label': 'anxious', 'score': 0.102}, {'label': 'angry', 'score': 0.0926}, {'label': 'sad', 'score': 0.0845}, {'label': 'heartache', 'score': 0.0614}]
7569650640 [2026-01-17T18:39:39Z] torvalds/AudioNoise - PushEvent: [{'label': 'happy', 'score': 0.8114}, {'label': 'embarrassed', 'score': 0.0567}, {'label': 'anxious', 'score': 0.0417}, {'label': 'angry', 'score': 0.0373}, {'label': 'sad', 'score': 0.0292}, {'label': 'heartache', 'score': 0.0237}]

{
  "status_enum": "JOY",
  "persona_title": "코딩 갓생러",
  "comment": "오늘도 키보드와 함께 달립니다. 멈추지 않는 푸쉬!"
}
"""

"""noridorimari/emotion_classifier

7621489697 [2026-01-19T19:32:53Z] torvalds/uemacs - PushEvent: [{'label': '분노', 'score': 0.5207}, {'label': '당황', 'score': 0.1886}, {'label': '상처', 'score': 0.1536}, {'label': '기쁨', 'score': 0.0488}, {'label': '불안', 'score': 0.0451}, {'label': '슬픔', 'score': 0.0431}]
7620741436 [2026-01-19T18:58:10Z] torvalds/uemacs - PushEvent: [{'label': '당황', 'score': 0.4793}, {'label': '상처', 'score': 0.2373}, {'label': '분노', 'score': 0.1529}, {'label': '기쁨', 'score': 0.0507}, {'label': '불안', 'score': 0.0451}, {'label': '슬픔', 'score': 0.0347}]
7618585211 [2026-01-19T17:25:41Z] torvalds/HunspellColorize - PushEvent: [{'label': '상처', 'score': 0.3564}, {'label': '분노', 'score': 0.2508}, {'label': '당황', 'score': 0.1915}, {'label': '불안', 'score': 0.0786}, {'label': '슬픔', 'score': 0.0705}, {'label': '기쁨', 'score': 0.0522}]
7593945715 [2026-01-19T00:05:27Z] torvalds/HunspellColorize - PushEvent: [{'label': '당황', 'score': 0.3663}, {'label': '분노', 'score': 0.1744}, {'label': '기쁨', 'score': 0.1615}, {'label': '상처', 'score': 0.1576}, {'label': '슬픔', 'score': 0.098}, {'label': '불안', 'score': 0.0422}]
7593731760 [2026-01-18T23:49:50Z] torvalds/linux - PushEvent: [{'label': '슬픔', 'score': 0.4991}, {'label': '상처', 'score': 0.249}, {'label': '분노', 'score': 0.1349}, {'label': '당황', 'score': 0.0911}, {'label': '불안', 'score': 0.0176}, {'label': '기쁨', 'score': 0.0083}]
7592196583 [2026-01-18T21:58:01Z] torvalds/HunspellColorize - PushEvent: [{'label': '기쁨', 'score': 0.3109}, {'label': '상처', 'score': 0.2083}, {'label': '당황', 'score': 0.1747}, {'label': '분노', 'score': 0.1513}, {'label': '슬픔', 'score': 0.1093}, {'label': '불안', 'score': 0.0455}]
7576394206 [2026-01-18T03:32:52Z] torvalds/linux - PushEvent: [{'label': '기쁨', 'score': 0.7648}, {'label': '당황', 'score': 0.0903}, {'label': '분노', 'score': 0.0404}, {'label': '슬픔', 'score': 0.0391}, {'label': '상처', 'score': 0.0356}, {'label': '불안', 'score': 0.0298}]
5884121095 [2026-01-18T03:24:10Z] torvalds/AudioNoise - IssueCommentEvent: [{'label': '상처', 'score': 0.384}, {'label': '분노', 'score': 0.176}, {'label': '당황', 'score': 0.14}, {'label': '슬픔', 'score': 0.1186}, {'label': '기쁨', 'score': 0.091}, {'label': '불안', 'score': 0.0903}]
7576261026 [2026-01-18T03:21:13Z] torvalds/AudioNoise - PushEvent: [{'label': '기쁨', 'score': 0.2489}, {'label': '분노', 'score': 0.246}, {'label': '상처', 'score': 0.2075}, {'label': '당황', 'score': 0.1807}, {'label': '슬픔', 'score': 0.0721}, {'label': '불안', 'score': 0.0448}]
7573768000 [2026-01-17T23:55:08Z] torvalds/AudioNoise - PushEvent: [{'label': '상처', 'score': 0.4474}, {'label': '당황', 'score': 0.2844}, {'label': '분노', 'score': 0.1475}, {'label': '불안', 'score': 0.0457}, {'label': '슬픔', 'score': 0.0385}, {'label': '기쁨', 'score': 0.0364}]
7571750643 [2026-01-17T21:14:04Z] torvalds/AudioNoise - PushEvent: [{'label': '분노', 'score': 0.3154}, {'label': '기쁨', 'score': 0.1941}, {'label': '상처', 'score': 0.1651}, {'label': '당황', 'score': 0.1242}, {'label': '불안', 'score': 0.1235}, {'label': '슬픔', 'score': 0.0776}]
7569650640 [2026-01-17T18:39:39Z] torvalds/AudioNoise - PushEvent: [{'label': '상처', 'score': 0.3679}, {'label': '당황', 'score': 0.2788}, {'label': '분노', 'score': 0.1544}, {'label': '슬픔', 'score': 0.084}, {'label': '불안', 'score': 0.0649}, {'label': '기쁨', 'score': 0.0498}]

{
  "status_enum": "ANXIETY",
  "reason": ...
  "persona_title": "코드 늪",
  "comment": "코드와 씨름 중. 다음은 무엇일까요?"
}
"""


"""LLM 감정 분석

{
  "status_enum": "NEUTRAL",
  "persona_title": "평화로운 코더",
  "comment": "영혼은 집으로, 손가락은 키보드로. 코드는 쉬고 있네요.",
  "reason": "일련의 PushEvent가 발생했지만, 메시지 내용이 'add LICENSE', 'update README', 'Use pkg-config', 'refactor' 등 유지보수, 문서화, 코드 개선 작업에 해당하며, 명확한 감정이나 긴박함이 드러나지 않아 평온한 상태로 판단됨."
}
"""
