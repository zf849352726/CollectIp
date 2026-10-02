from django.core.management.base import BaseCommand

from proxy_web.jobs import enqueue_job, process_job


class Command(BaseCommand):
    help = "Check every proxy and update availability, latency, and score"

    def handle(self, *args, **options):
        job, created = enqueue_job("score")
        if not created:
            self.stdout.write(self.style.WARNING("评分任务已在运行"))
            return
        process_job(job)
        job.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(job.message))
