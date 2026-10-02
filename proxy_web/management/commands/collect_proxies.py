from django.core.management.base import BaseCommand

from proxy_web.jobs import enqueue_job, process_job


class Command(BaseCommand):
    help = "Collect proxies with Playwright and save them to the IP pool"

    def add_arguments(self, parser):
        parser.add_argument("--max-pages", type=int)

    def handle(self, *args, **options):
        if options["max_pages"]:
            from proxy_web.models import SystemSettings

            config = SystemSettings.load()
            config.max_pages = options["max_pages"]
            config.save(update_fields=["max_pages"])
        job, created = enqueue_job("collect")
        if not created:
            self.stdout.write(self.style.WARNING("采集任务已在运行"))
            return
        process_job(job)
        job.refresh_from_db()
        self.stdout.write(self.style.SUCCESS(job.message))
