from django.db import models


class GithubUser(models.Model):
    """
    GitHub 사용자 정보를 관리합니다.
    """

    username = models.CharField(
        max_length=150, primary_key=True, unique=True, help_text="GitHub 사용자 ID (소문자 정규화 권장)"
    )
    last_analyzed_at = models.DateTimeField(null=True, blank=True, help_text="가장 최근 분석이 완료된 시각")
    created_at = models.DateTimeField(auto_now_add=True, help_text="최초 생성 시각")
    updated_at = models.DateTimeField(auto_now=True, help_text="마지막 정보 갱신 시각")

    def __str__(self):
        return self.username


class GithubEvent(models.Model):
    """
    GitHub API로부터 수집된 원본 이벤트 데이터를 저장합니다.
    """

    event_id = models.CharField(
        max_length=50, primary_key=True, unique=True, help_text="GitHub에서 부여한 고유 이벤트 ID"
    )
    user = models.ForeignKey(
        GithubUser, on_delete=models.CASCADE, related_name="events", help_text="이벤트 발생 사용자"
    )
    event_type = models.CharField(
        max_length=100, blank=True, default="", help_text="이벤트 유형 (PushEvent, IssuesEvent 등)"
    )
    repo_name = models.CharField(max_length=255, blank=True, default="", help_text="저장소 이름 (user/repo)")
    message = models.TextField(blank=True, default="", help_text="분석 대상 텍스트 (커밋 메시지 등)")
    created_at = models.DateTimeField(help_text="이벤트 실제 발생 시각 (GitHub 시간)")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.event_type} ({self.event_id})"


class AnalysisResult(models.Model):
    """
    분석 완료된 결과를 이력으로 저장합니다.
    """

    class Status(models.TextChoices):
        JOY = "JOY", "기쁨"
        ANGER = "ANGER", "분노"
        ANXIETY = "ANXIETY", "불안"
        SADNESS = "SADNESS", "슬픔"
        CONFUSION = "CONFUSION", "혼란"
        NEUTRAL = "NEUTRAL", "중립"
        IDLE = "IDLE", "대기/없음"

    user = models.ForeignKey(
        GithubUser, on_delete=models.CASCADE, related_name="analysis_results", help_text="분석 대상 사용자"
    )
    persona_title = models.CharField(max_length=100, help_text="LLM이 생성한 페르소나 제목")
    comment = models.TextField(help_text="LLM이 생성한 한 줄 요약")
    status_enum = models.CharField(max_length=20, choices=Status, help_text="감정 상태")
    reason = models.TextField(blank=True, default="", help_text="LLM이 분석한 근거")
    analysis_metadata = models.JSONField(default=dict, help_text="사용된 모델, 분석된 이벤트 수 등 메타데이터")
    created_at = models.DateTimeField(auto_now_add=True, help_text="결과 생성 시각")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.persona_title} ({self.created_at})"
