from __future__ import annotations

import random
import time
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import BackgroundJob, OperationLog, Proxy, SystemSettings


def write_operation_log(
    level: str,
    module: str,
    event: str,
    message: str,
    *,
    job_id: int | None = None,
    proxy_server: str = "",
    details: dict | None = None,
) -> OperationLog:
    return OperationLog.objects.create(
        level=level,
        module=module,
        event=event,
        message=message,
        job_id=job_id,
        proxy_server=proxy_server,
        details=details or {},
    )


def enqueue_job(kind: str) -> tuple[BackgroundJob | None, bool]:
    if kind not in {choice[0] for choice in BackgroundJob.KIND_CHOICES}:
        raise ValueError(f"Unknown job: {kind}")
    try:
        with transaction.atomic():
            job = BackgroundJob.objects.create(kind=kind, active_key=kind)
        return job, True
    except IntegrityError:
        return BackgroundJob.objects.filter(active_key=kind).first(), False


def job_snapshot() -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for kind, _ in BackgroundJob.KIND_CHOICES:
        job = BackgroundJob.objects.filter(kind=kind).first()
        result[kind] = {
            "id": job.pk if job else None,
            "name": kind,
            "status": job.status if job else "idle",
            "message": job.message if job else "",
            "progress": job.progress if job else 0,
            "total": job.total if job else 0,
            "started_at": job.started_at.isoformat() if job and job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job and job.finished_at else None,
        }
    return result


def _progress(job_id: int, current: int, total: int) -> None:
    BackgroundJob.objects.filter(pk=job_id).update(progress=current, total=total)


def select_collection_proxies(config: SystemSettings) -> list[Proxy]:
    if not config.use_proxy_for_collection:
        return []
    cutoff = timezone.now() - timedelta(hours=24)
    pool = list(
        Proxy.objects.filter(
            is_available=True,
            is_archived=False,
            score__gte=config.collection_proxy_min_score,
            last_success_at__gte=cutoff,
        )
    )
    selected: list[Proxy] = []
    now = timezone.now()
    while pool and len(selected) < config.collection_proxy_attempts:
        weights = []
        for proxy in pool:
            history_ratio = (proxy.collection_successes + 1) / (
                proxy.collection_successes + proxy.collection_failures + 2
            )
            recency_factor = 1.0
            if (
                proxy.last_collection_used_at
                and now - proxy.last_collection_used_at < timedelta(hours=1)
            ):
                recency_factor = 0.25
            weights.append(
                max(1, proxy.score) * (0.5 + history_ratio) * recency_factor
            )
        proxy = random.choices(pool, weights=weights, k=1)[0]
        selected.append(proxy)
        pool.remove(proxy)
    return selected


def _collector_event_buffer(events: list[dict], proxy_server: str):
    def callback(level: str, event: str, message: str, details: dict) -> None:
        events.append(
            {
                "level": level,
                "event": event,
                "message": message,
                "proxy_server": proxy_server,
                "details": details,
            }
        )

    return callback


def _flush_collector_events(job_id: int, events: list[dict]) -> None:
    OperationLog.objects.bulk_create(
        [
            OperationLog(
                level=event["level"],
                module="collector",
                event=event["event"],
                message=event["message"],
                job_id=job_id,
                proxy_server=event["proxy_server"],
                details=event["details"],
            )
            for event in events
        ]
    )


def _short_error(exc: Exception, limit: int = 1000) -> str:
    return f"{type(exc).__name__}: {exc}"[:limit]


def _collect(job_id: int) -> dict[str, int | str]:
    from ip_operator.ip_collection import PlaywrightCollectorConfig, collect_proxies

    from .repository import upsert_records

    config = SystemSettings.load()
    candidates = select_collection_proxies(config)
    attempts: list[Proxy | None] = list(candidates)
    if not config.use_proxy_for_collection or config.allow_direct_fallback:
        attempts.append(None)
    if not attempts:
        raise RuntimeError("No eligible collection proxy and direct fallback is disabled")

    write_operation_log(
        "INFO",
        "collector",
        "collection_plan",
        f"Prepared {len(candidates)} proxy candidate(s)",
        job_id=job_id,
        details={
            "candidate_count": len(candidates),
            "direct_fallback": config.allow_direct_fallback,
        },
    )
    last_error: Exception | None = None
    for attempt_number, proxy in enumerate(attempts, start=1):
        proxy_server = proxy.server if proxy else ""
        route = f"http://{proxy.server}" if proxy else None
        if proxy:
            proxy.last_collection_used_at = timezone.now()
            proxy.save(update_fields=["last_collection_used_at"])
        write_operation_log(
            "INFO",
            "collector",
            "collection_attempt",
            f"Collection attempt {attempt_number} via {proxy_server or 'direct'}",
            job_id=job_id,
            proxy_server=proxy_server,
            details={"attempt": attempt_number, "route": "proxy" if proxy else "direct"},
        )
        try:
            collector_events: list[dict] = []
            records = collect_proxies(
                PlaywrightCollectorConfig(
                    max_pages=config.max_pages,
                    captcha_retries=config.captcha_retries,
                    proxy_server=route,
                    min_delay_ms=config.collection_min_delay_ms,
                    max_delay_ms=config.collection_max_delay_ms,
                    max_runtime_seconds=config.collection_max_runtime,
                ),
                event_callback=_collector_event_buffer(
                    collector_events, proxy_server
                ),
            )
        except Exception as exc:
            _flush_collector_events(job_id, collector_events)
            last_error = exc
            infrastructure_error = "Executable doesn't exist" in str(exc)
            if infrastructure_error:
                write_operation_log(
                    "ERROR",
                    "collector",
                    "browser_missing",
                    _short_error(exc),
                    job_id=job_id,
                )
                raise RuntimeError(
                    "Playwright Chromium is not installed; run "
                    "`python -m playwright install chromium`"
                ) from exc
            if proxy:
                proxy.collection_failures += 1
                proxy.collection_last_error = str(exc)[:255]
                proxy.save(
                    update_fields=["collection_failures", "collection_last_error"]
                )
            write_operation_log(
                "WARNING",
                "collector",
                "collection_attempt_failed",
                _short_error(exc),
                job_id=job_id,
                proxy_server=proxy_server,
                details={"attempt": attempt_number},
            )
            if attempt_number < len(attempts):
                backoff = min(
                    120,
                    config.collection_retry_backoff * (2 ** (attempt_number - 1)),
                )
                write_operation_log(
                    "INFO",
                    "collector",
                    "retry_backoff",
                    f"Waiting {backoff} seconds before the next route",
                    job_id=job_id,
                    details={"seconds": backoff},
                )
                time.sleep(backoff)
            continue

        _flush_collector_events(job_id, collector_events)
        if proxy:
            proxy.collection_successes += 1
            proxy.collection_last_error = ""
            proxy.save(
                update_fields=["collection_successes", "collection_last_error"]
            )
        created, updated = upsert_records(records)
        config.last_collection_at = timezone.now()
        config.save(update_fields=["last_collection_at"])
        result: dict[str, int | str] = {
            "collected": len(records),
            "created": created,
            "updated": updated,
            "route": proxy_server or "direct",
            "attempts": attempt_number,
        }
        write_operation_log(
            "INFO",
            "collector",
            "collection_succeeded",
            f"Collected {len(records)} proxies via {proxy_server or 'direct'}",
            job_id=job_id,
            proxy_server=proxy_server,
            details=result,
        )
        return result

    raise RuntimeError(f"All collection routes failed: {_short_error(last_error)}")


def _score(job_id: int) -> dict[str, int]:
    from .scoring import score_all_proxies

    return score_all_proxies(lambda current, total: _progress(job_id, current, total))


def cleanup_proxies() -> dict[str, int]:
    config = SystemSettings.load()
    cutoff = timezone.now() - timedelta(days=config.purge_after_days)
    archived = Proxy.objects.filter(
        is_archived=False,
        consecutive_failures__gte=config.archive_after_failures,
    ).update(is_archived=True, archived_at=timezone.now())
    purged, _ = Proxy.objects.filter(is_archived=True, archived_at__lt=cutoff).delete()
    log_cutoff = timezone.now() - timedelta(days=config.log_retention_days)
    logs_purged, _ = OperationLog.objects.filter(created_at__lt=log_cutoff).delete()
    return {"archived": archived, "purged": purged, "logs_purged": logs_purged}


def process_job(job: BackgroundJob) -> None:
    job.status = "running"
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])
    write_operation_log(
        "INFO", "worker", "job_started", f"Started {job.kind} job", job_id=job.pk
    )
    try:
        if job.kind == "collect":
            result = _collect(job.pk)
        elif job.kind == "score":
            result = _score(job.pk)
        else:
            result = cleanup_proxies()
        job.status = "success"
        job.message = str(result)
        write_operation_log(
            "INFO",
            "worker",
            "job_succeeded",
            f"{job.kind} job completed",
            job_id=job.pk,
            details=result,
        )
    except Exception as exc:
        job.status = "failed"
        job.message = _short_error(exc)
        write_operation_log(
            "ERROR",
            "worker",
            "job_failed",
            job.message,
            job_id=job.pk,
        )
    finally:
        job.finished_at = timezone.now()
        job.active_key = None
        job.save(
            update_fields=["status", "message", "finished_at", "active_key"]
        )


def claim_next_job() -> BackgroundJob | None:
    candidate_id = (
        BackgroundJob.objects.filter(status="queued")
        .order_by("created_at")
        .values_list("pk", flat=True)
        .first()
    )
    if candidate_id is None:
        return None
    claimed = BackgroundJob.objects.filter(
        pk=candidate_id, status="queued"
    ).update(status="running", started_at=timezone.now())
    if not claimed:
        return None
    return BackgroundJob.objects.get(pk=candidate_id)


def recover_stale_jobs(max_age: timedelta = timedelta(hours=2)) -> int:
    """Release jobs abandoned by a terminated worker."""
    return BackgroundJob.objects.filter(
        status="running", started_at__lt=timezone.now() - max_age
    ).update(
        status="failed",
        message="Worker stopped before the job completed",
        finished_at=timezone.now(),
        active_key=None,
    )


def enqueue_due_jobs() -> int:
    recover_stale_jobs()
    config = SystemSettings.load()
    now = timezone.now()
    queued = 0
    last_collect_job = (
        BackgroundJob.objects.filter(
            kind="collect", status__in=["success", "failed"], finished_at__isnull=False
        )
        .order_by("-finished_at")
        .first()
    )
    last_score_job = (
        BackgroundJob.objects.filter(
            kind="score", status__in=["success", "failed"], finished_at__isnull=False
        )
        .order_by("-finished_at")
        .first()
    )
    collect_reference = (
        last_collect_job.finished_at if last_collect_job else config.last_collection_at
    )
    score_reference = last_score_job.finished_at if last_score_job else config.last_score_at
    collect_due = not collect_reference or now >= (
        collect_reference + timedelta(seconds=config.collection_interval)
    )
    score_due = not score_reference or now >= (
        score_reference + timedelta(seconds=config.score_interval)
    )
    if config.auto_collect and collect_due:
        queued += int(enqueue_job("collect")[1])
    if config.auto_score and score_due:
        queued += int(enqueue_job("score")[1])
    last_cleanup = BackgroundJob.objects.filter(
        kind="cleanup", status="success"
    ).order_by("-finished_at").first()
    cleanup_due = not last_cleanup or not last_cleanup.finished_at or now >= (
        last_cleanup.finished_at + timedelta(days=1)
    )
    if cleanup_due:
        queued += int(enqueue_job("cleanup")[1])
    return queued
