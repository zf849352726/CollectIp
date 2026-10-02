from __future__ import annotations

from typing import Iterable

from django.utils import timezone

from ip_operator.ip_collection import ProxyRecord

from .models import Proxy


def upsert_records(records: Iterable[ProxyRecord]) -> tuple[int, int]:
    created = 0
    updated = 0
    for record in records:
        now = timezone.now()
        was_archived = Proxy.objects.filter(
            server=record.server, is_archived=True
        ).exists()
        proxy, was_created = Proxy.objects.update_or_create(
            server=record.server,
            defaults={
                "ping": record.ping,
                "speed": record.speed,
                "uptime1": record.uptime1,
                "uptime2": record.uptime2,
                "proxy_type": record.type_data,
                "country": record.country,
                "ssl": record.ssl,
                "conn": record.conn,
                "post": record.post,
                "source_last_work_time": record.last_work_time,
                "source": "freeproxylist.org",
                "last_seen_at": now,
                "is_archived": False,
                "archived_at": None,
            },
        )
        if was_archived:
            proxy.consecutive_failures = 0
            proxy.score = max(proxy.score, 50)
            proxy.save(update_fields=["consecutive_failures", "score"])
        created += int(was_created)
        updated += int(not was_created)
    return created, updated
