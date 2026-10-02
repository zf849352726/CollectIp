from __future__ import annotations

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import BackgroundJob, Proxy, SystemSettings


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


def _collect() -> dict[str, int]:
    from ip_operator.ip_collection import PlaywrightCollectorConfig, collect_proxies

    from .repository import upsert_records

    config = SystemSettings.load()
    records = collect_proxies(
        PlaywrightCollectorConfig(
            max_pages=config.max_pages,
            captcha_retries=config.captcha_retries,
        )
    )
    created, updated = upsert_records(records)
    config.last_collection_at = timezone.now()
    config.save(update_fields=["last_collection_at"])
    return {"collected": len(records), "created": created, "updated": updated}


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
    return {"archived": archived, "purged": purged}


def process_job(job: BackgroundJob) -> None:
    job.status = "running"
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])
    try:
        if job.kind == "collect":
            result = _collect()
        elif job.kind == "score":
            result = _score(job.pk)
        else:
            result = cleanup_proxies()
        job.status = "success"
        job.message = str(result)
    except Exception as exc:
        job.status = "failed"
        job.message = f"{type(exc).__name__}: {exc}"
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
    collect_due = not config.last_collection_at or now >= (
        config.last_collection_at + timedelta(seconds=config.collection_interval)
    )
    score_due = not config.last_score_at or now >= (
        config.last_score_at + timedelta(seconds=config.score_interval)
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
