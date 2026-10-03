from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db import DatabaseError
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .jobs import enqueue_job, job_snapshot
from .models import OperationLog, Proxy, SystemSettings


def _filtered_proxies(request):
    query = Proxy.objects.all()
    status = request.GET.get("status")
    available_param = request.GET.get("available")
    if available_param == "true":
        status = "available"
    elif available_param == "false":
        status = "unavailable"
    if status == "available":
        query = query.filter(is_available=True, is_archived=False)
    elif status == "unavailable":
        query = query.filter(is_available=False, is_archived=False)
    elif status == "archived":
        query = query.filter(is_archived=True)
    else:
        query = query.filter(is_archived=False)
    search = request.GET.get("q", "").strip()
    if search:
        query = query.filter(Q(server__icontains=search) | Q(country__icontains=search))
    minimum = request.GET.get("min_score")
    if minimum and minimum.isdigit():
        query = query.filter(score__gte=int(minimum))
    if request.GET.get("https") == "true":
        query = query.filter(ssl__icontains="support").exclude(ssl__icontains="not")
    country = request.GET.get("country", "").strip()
    if country:
        query = query.filter(country__iexact=country)
    return query, search, status


@require_GET
def dashboard(request):
    query, search, status = _filtered_proxies(request)
    active = Proxy.objects.filter(is_archived=False)
    stats = active.aggregate(
        total=Count("id"),
        available=Count("id", filter=Q(is_available=True)),
        average_score=Avg("score"),
        average_latency=Avg("latency_ms", filter=Q(is_available=True)),
        average_success_rate=Avg("success_rate"),
    )
    stats["archived"] = Proxy.objects.filter(is_archived=True).count()
    page = Paginator(query, 50).get_page(request.GET.get("page"))
    return render(
        request,
        "proxy_web/dashboard.html",
        {
            "page": page,
            "stats": stats,
            "jobs": job_snapshot(),
            "settings": SystemSettings.load(),
            "search": search,
            "status": status,
        },
    )


@require_GET
def proxy_detail(request, pk: int):
    proxy = get_object_or_404(Proxy, pk=pk)
    history = proxy.checks.all()[:100]
    return render(
        request,
        "proxy_web/detail.html",
        {"proxy": proxy, "history": history},
    )


@staff_member_required
@require_GET
def operation_logs(request):
    query = OperationLog.objects.select_related("job")
    level = request.GET.get("level", "").upper()
    module = request.GET.get("module", "").strip()
    search = request.GET.get("q", "").strip()
    if level in {choice[0] for choice in OperationLog.LEVEL_CHOICES}:
        query = query.filter(level=level)
    if module:
        query = query.filter(module=module)
    if search:
        query = query.filter(
            Q(message__icontains=search) | Q(proxy_server__icontains=search)
        )
    page = Paginator(query, 100).get_page(request.GET.get("page"))
    modules = (
        OperationLog.objects.order_by().values_list("module", flat=True).distinct()
    )
    return render(
        request,
        "proxy_web/logs.html",
        {
            "page": page,
            "levels": OperationLog.LEVEL_CHOICES,
            "modules": modules,
            "selected_level": level,
            "selected_module": module,
            "search": search,
        },
    )


@require_GET
def api_status(request):
    stats = Proxy.objects.filter(is_archived=False).aggregate(
        total=Count("id"),
        available=Count("id", filter=Q(is_available=True)),
        unavailable=Count("id", filter=Q(is_available=False)),
    )
    return JsonResponse({"jobs": job_snapshot(), "stats": stats})


@require_GET
def api_proxies(request):
    query, _, _ = _filtered_proxies(request)
    page_size = min(max(int(request.GET.get("page_size", 50)), 1), 200)
    page = Paginator(query, page_size).get_page(request.GET.get("page"))
    items = [
        {
            "id": proxy.pk,
            "server": proxy.server,
            "available": proxy.is_available,
            "score": proxy.score,
            "success_rate": proxy.success_rate,
            "latency_ms": proxy.latency_ms,
            "country": proxy.country,
            "type": proxy.proxy_type,
            "https": "support" in proxy.ssl.lower() and "not" not in proxy.ssl.lower(),
            "last_checked_at": proxy.last_checked_at.isoformat() if proxy.last_checked_at else None,
        }
        for proxy in page
    ]
    return JsonResponse(
        {"count": page.paginator.count, "pages": page.paginator.num_pages, "results": items}
    )


@require_GET
def api_random_proxy(request):
    query, _, _ = _filtered_proxies(request)
    query = query.filter(is_available=True)
    proxy = query.order_by("?").first()
    if not proxy:
        return JsonResponse({"detail": "No matching available proxy"}, status=404)
    return JsonResponse(
        {
            "id": proxy.pk,
            "server": proxy.server,
            "score": proxy.score,
            "latency_ms": proxy.latency_ms,
        }
    )


@staff_member_required
@require_POST
def start_collect(request):
    job, started = enqueue_job("collect")
    return JsonResponse(
        {"started": started, "job_id": job.pk if job else None, "jobs": job_snapshot()},
        status=202 if started else 409,
    )


@staff_member_required
@require_POST
def start_score(request):
    job, started = enqueue_job("score")
    return JsonResponse(
        {"started": started, "job_id": job.pk if job else None, "jobs": job_snapshot()},
        status=202 if started else 409,
    )


@staff_member_required
@require_POST
def update_settings(request):
    config = SystemSettings.load()
    config.auto_collect = request.POST.get("auto_collect") == "on"
    config.auto_score = request.POST.get("auto_score") == "on"
    config.use_proxy_for_collection = request.POST.get("use_proxy_for_collection") == "on"
    config.allow_direct_fallback = request.POST.get("allow_direct_fallback") == "on"
    numeric_fields = {
        "collection_interval": (60, 86400),
        "score_interval": (30, 86400),
        "max_pages": (1, 100),
        "captcha_retries": (1, 30),
        "check_timeout": (1, 60),
        "check_workers": (1, 100),
        "archive_after_failures": (1, 100),
        "purge_after_days": (1, 3650),
        "collection_proxy_min_score": (0, 100),
        "collection_proxy_attempts": (1, 20),
        "collection_min_delay_ms": (0, 30000),
        "collection_max_delay_ms": (0, 30000),
        "collection_retry_backoff": (0, 300),
        "collection_max_runtime": (30, 3600),
        "log_retention_days": (1, 365),
    }
    for field, (minimum, maximum) in numeric_fields.items():
        try:
            value = int(request.POST.get(field, getattr(config, field)))
        except (TypeError, ValueError):
            value = getattr(config, field)
        setattr(config, field, min(maximum, max(minimum, value)))
    config.collection_max_delay_ms = max(
        config.collection_min_delay_ms, config.collection_max_delay_ms
    )
    config.save()
    return redirect("proxy_web:dashboard")


@require_GET
def health(request):
    try:
        SystemSettings.objects.exists()
    except DatabaseError:
        return JsonResponse(
            {"status": "unavailable", "database": "error"}, status=503
        )
    return JsonResponse({"status": "ok", "database": "ok"})
