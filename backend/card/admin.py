from django.contrib import admin
from .models import GithubUser, GithubEvent, AnalysisResult

@admin.register(GithubUser)
class GithubUserAdmin(admin.ModelAdmin):
    list_display = ("username", "last_analyzed_at", "created_at")
    search_fields = ("username",)

@admin.register(GithubEvent)
class GithubEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "user", "event_type", "repo_name", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("user__username", "repo_name", "message")
    ordering = ("-created_at",)

@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ("user", "persona_title", "status_enum", "created_at")
    list_filter = ("status_enum", "created_at")
    search_fields = ("user__username", "persona_title", "comment")
    ordering = ("-created_at",)