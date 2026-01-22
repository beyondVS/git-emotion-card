from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch
from django.utils import timezone
from datetime import timedelta
from .models import GithubUser, AnalysisResult

class CardViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("card:svg")

    @patch("card.views.analyze_user_task.delay")
    def test_cold_miss(self, mock_task):
        """
        데이터가 없는 경우(Cold Miss) Placeholder를 반환하고 Task를 트리거해야 함.
        """
        response = self.client.get(self.url, {"username": "newuser"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Analyzing System", response.content)
        mock_task.assert_called_once_with("newuser")

    def test_hit_fresh(self):
        """
        최신 데이터가 있는 경우(Fresh) 카드를 반환하고 Task를 트리거하지 않아야 함.
        """
        user = GithubUser.objects.create(username="freshuser", last_analyzed_at=timezone.now())
        AnalysisResult.objects.create(
            user=user,
            persona_title="Tester",
            comment="Good job",
            status_enum="JOY"
        )
        
        # Patching inside context to ensure no call
        with patch("card.views.analyze_user_task.delay") as mock_task:
            response = self.client.get(self.url, {"username": "freshuser"})
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Tester", response.content)
            self.assertIn(b"JOY", response.content)
            mock_task.assert_not_called()

    @patch("card.views.analyze_user_task.delay")
    def test_hit_stale(self, mock_task):
        """
        오래된 데이터가 있는 경우(Stale) 카드를 반환하고 백그라운드에서 Task를 트리거해야 함.
        """
        past = timezone.now() - timedelta(hours=2)
        user = GithubUser.objects.create(username="staleuser", last_analyzed_at=past)
        AnalysisResult.objects.create(
            user=user,
            persona_title="Old Tester",
            comment="Old comment",
            status_enum="IDLE"
        )
        response = self.client.get(self.url, {"username": "staleuser"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Old Tester", response.content)
        mock_task.assert_called_once_with("staleuser")

    def test_missing_username(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Something went wrong", response.content)