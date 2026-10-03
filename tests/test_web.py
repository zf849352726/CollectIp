from __future__ import annotations

from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from ip_operator.ip_collection import ProxyRecord
from proxy_web.jobs import (
    claim_next_job,
    enqueue_job,
    enqueue_due_jobs,
    process_job,
    recover_stale_jobs,
    select_collection_proxies,
)
from proxy_web.models import (
    BackgroundJob,
    OperationLog,
    Proxy,
    ProxyCheckHistory,
    SystemSettings,
)
from proxy_web.repository import upsert_records
from proxy_web.scoring import CheckAttempt, CheckResult, ProxyScorer, score_all_proxies


class RepositoryTests(TestCase):
    def test_upserts_collected_records_without_resetting_score(self):
        record = ProxyRecord(server="127.0.0.1:8080", country="China")
        self.assertEqual(upsert_records([record]), (1, 0))
        proxy = Proxy.objects.get(server=record.server)
        proxy.score = 88
        proxy.save(update_fields=["score"])

        changed = ProxyRecord(server=record.server, country="Japan")
        self.assertEqual(upsert_records([changed]), (0, 1))
        proxy.refresh_from_db()
        self.assertEqual(proxy.country, "Japan")
        self.assertEqual(proxy.score, 88)

    def test_reappearing_proxy_is_unarchived(self):
        proxy = Proxy.objects.create(
            server="127.0.0.1:8080", is_archived=True, archived_at="2026-01-01T00:00:00Z"
        )
        upsert_records([ProxyRecord(server=proxy.server)])
        proxy.refresh_from_db()
        self.assertFalse(proxy.is_archived)
        self.assertIsNone(proxy.archived_at)


class ScoringTests(TestCase):
    @patch("proxy_web.scoring.requests.get")
    def test_successful_check_returns_latency_and_score(self, get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"ip": "8.8.8.8"}
        get.return_value = response
        result = ProxyScorer(test_urls=["https://example.com/ip"], timeout=1).check(
            "127.0.0.1:8080"
        )
        self.assertTrue(result.available)
        self.assertGreater(result.score, 0)
        self.assertIsNotNone(result.latency_ms)

    @patch("proxy_web.scoring.ProxyScorer.check")
    def test_score_all_updates_dynamic_status(self, check):
        attempt = CheckAttempt(
            True,
            "https://example.com/ip",
            "https",
            latency_ms=120,
            exit_ip="8.8.8.8",
        )
        check.return_value = CheckResult(True, 91, 120, (attempt,))
        proxy = Proxy.objects.create(server="127.0.0.1:8080")
        result = score_all_proxies()
        proxy.refresh_from_db()
        self.assertEqual(result["available"], 1)
        self.assertTrue(proxy.is_available)
        self.assertEqual(proxy.score, 91)
        self.assertEqual(proxy.latency_ms, 120)
        self.assertEqual(ProxyCheckHistory.objects.filter(proxy=proxy).count(), 1)

    @patch("proxy_web.scoring.ProxyScorer.check")
    def test_repeated_failure_archives_proxy(self, check):
        config = SystemSettings.load()
        config.archive_after_failures = 1
        config.save()
        attempt = CheckAttempt(
            False,
            "https://example.com/ip",
            "https",
            error_type="ProxyError",
            error_message="failed",
        )
        check.return_value = CheckResult(False, 0, None, (attempt,))
        proxy = Proxy.objects.create(server="127.0.0.1:8080")
        score_all_proxies()
        proxy.refresh_from_db()
        self.assertTrue(proxy.is_archived)


class JobTests(TestCase):
    def test_database_lock_prevents_duplicate_active_jobs(self):
        first, created = enqueue_job("score")
        second, duplicate_created = enqueue_job("score")
        self.assertTrue(created)
        self.assertFalse(duplicate_created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(BackgroundJob.objects.count(), 1)

    def test_job_can_only_be_claimed_once(self):
        queued, _ = enqueue_job("score")
        claimed = claim_next_job()
        self.assertEqual(claimed.pk, queued.pk)
        self.assertIsNone(claim_next_job())

    def test_stale_running_job_is_released(self):
        job, _ = enqueue_job("score")
        BackgroundJob.objects.filter(pk=job.pk).update(
            status="running", started_at="2026-01-01T00:00:00Z"
        )
        self.assertEqual(recover_stale_jobs(), 1)
        job.refresh_from_db()
        self.assertEqual(job.status, "failed")
        self.assertIsNone(job.active_key)

    def test_selects_only_recent_high_quality_proxies_without_duplicates(self):
        eligible = [
            Proxy.objects.create(
                server=f"127.0.0.{index}:8080",
                is_available=True,
                score=80 + index,
                last_success_at=timezone.now(),
            )
            for index in range(1, 4)
        ]
        Proxy.objects.create(
            server="127.0.0.9:8080",
            is_available=True,
            score=10,
            last_success_at=timezone.now(),
        )
        config = SystemSettings.load()
        config.collection_proxy_attempts = 2
        selected = select_collection_proxies(config)
        self.assertEqual(len(selected), 2)
        self.assertEqual(len({proxy.pk for proxy in selected}), 2)
        self.assertTrue(set(selected).issubset(set(eligible)))

    @patch("proxy_web.jobs.time.sleep")
    @patch("ip_operator.ip_collection.collect_proxies")
    def test_collection_rotates_proxy_then_falls_back_to_direct(self, collect, sleep):
        route = Proxy.objects.create(
            server="127.0.0.1:8080",
            is_available=True,
            score=90,
            last_success_at=timezone.now(),
        )
        collect.side_effect = [
            RuntimeError("proxy rejected"),
            [ProxyRecord(server="127.0.0.2:8080")],
        ]
        config = SystemSettings.load()
        config.collection_proxy_attempts = 1
        config.collection_retry_backoff = 0
        config.save()
        job, _ = enqueue_job("collect")
        process_job(job)
        job.refresh_from_db()
        route.refresh_from_db()
        self.assertEqual(job.status, "success")
        self.assertEqual(route.collection_failures, 1)
        self.assertEqual(collect.call_count, 2)
        self.assertEqual(
            collect.call_args_list[0].args[0].proxy_server,
            "http://127.0.0.1:8080",
        )
        self.assertIsNone(collect.call_args_list[1].args[0].proxy_server)
        self.assertTrue(Proxy.objects.filter(server="127.0.0.2:8080").exists())
        self.assertTrue(OperationLog.objects.filter(event="collection_succeeded").exists())

    def test_failed_automatic_job_respects_collection_interval(self):
        config = SystemSettings.load()
        config.auto_collect = True
        config.auto_score = False
        config.collection_interval = 3600
        config.save()
        BackgroundJob.objects.create(
            kind="collect",
            status="failed",
            message="failed",
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )
        self.assertEqual(enqueue_due_jobs(), 1)
        self.assertFalse(
            BackgroundJob.objects.filter(kind="collect", status="queued").exists()
        )

    @patch("ip_operator.ip_collection.collect_proxies")
    def test_missing_browser_does_not_penalize_proxy_or_retry_routes(self, collect):
        collect.side_effect = RuntimeError("Executable doesn't exist")
        route = Proxy.objects.create(
            server="127.0.0.1:8080",
            is_available=True,
            score=90,
            last_success_at=timezone.now(),
        )
        config = SystemSettings.load()
        config.collection_proxy_attempts = 1
        config.save()
        job, _ = enqueue_job("collect")
        process_job(job)
        route.refresh_from_db()
        job.refresh_from_db()
        self.assertEqual(job.status, "failed")
        self.assertEqual(route.collection_failures, 0)
        self.assertEqual(collect.call_count, 1)
        self.assertTrue(OperationLog.objects.filter(event="browser_missing").exists())

    @patch("ip_operator.ip_collection.collect_proxies")
    def test_collector_events_are_flushed_after_browser_call(self, collect):
        def fake_collect(config, *, event_callback):
            event_callback(
                "INFO",
                "page_collected",
                "Collected page 1",
                {"page": 1, "unique_proxies": 1},
            )
            return [ProxyRecord(server="127.0.0.2:8080")]

        collect.side_effect = fake_collect
        config = SystemSettings.load()
        config.use_proxy_for_collection = False
        config.save()
        job, _ = enqueue_job("collect")
        process_job(job)
        self.assertTrue(
            OperationLog.objects.filter(
                job=job, event="page_collected", message="Collected page 1"
            ).exists()
        )


class WebTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="admin", password="secret", is_staff=True
        )

    def test_dashboard_and_status_api(self):
        Proxy.objects.create(server="127.0.0.1:8080", is_available=True)
        dashboard = self.client.get(reverse("proxy_web:dashboard"))
        status = self.client.get(reverse("proxy_web:api_status"))
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "127.0.0.1:8080")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["stats"]["available"], 1)

    def test_health_checks_database(self):
        response = self.client.get(reverse("proxy_web:health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})

    def test_static_assets_and_favicon_are_served(self):
        css = self.client.get("/static/proxy_web/dashboard.css")
        favicon = self.client.get("/favicon.ico")
        self.assertEqual(css.status_code, 200)
        self.assertEqual(favicon.status_code, 301)
        self.assertEqual(favicon["Location"], "/static/proxy_web/favicon.svg")

    def test_operation_logs_require_staff_and_support_filters(self):
        OperationLog.objects.create(
            level="WARNING",
            module="collector",
            event="blocked",
            message="HTTP 429",
            proxy_server="127.0.0.1:8080",
        )
        anonymous = self.client.get(reverse("proxy_web:operation_logs"))
        self.assertEqual(anonymous.status_code, 302)
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("proxy_web:operation_logs"),
            {"level": "WARNING", "q": "429"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "HTTP 429")

    def test_list_detail_and_random_api(self):
        proxy = Proxy.objects.create(
            server="127.0.0.1:8080", is_available=True, score=90
        )
        listing = self.client.get(reverse("proxy_web:api_proxies"), {"min_score": 80})
        random_proxy = self.client.get(reverse("proxy_web:api_random_proxy"))
        detail = self.client.get(reverse("proxy_web:proxy_detail", args=[proxy.pk]))
        self.assertEqual(listing.json()["count"], 1)
        self.assertEqual(random_proxy.json()["server"], proxy.server)
        self.assertEqual(detail.status_code, 200)

    @patch("proxy_web.views.enqueue_job")
    def test_job_endpoints_require_staff_and_enqueue_work(self, enqueue):
        job = Mock(pk=1)
        enqueue.return_value = (job, True)
        anonymous = self.client.post(reverse("proxy_web:start_collect"))
        self.assertEqual(anonymous.status_code, 302)
        self.client.force_login(self.staff)
        collect = self.client.post(reverse("proxy_web:start_collect"))
        score = self.client.post(reverse("proxy_web:start_score"))
        self.assertEqual(collect.status_code, 202)
        self.assertEqual(score.status_code, 202)
        self.assertEqual(enqueue.call_count, 2)
