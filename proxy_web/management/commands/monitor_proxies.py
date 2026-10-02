from django.core.management.base import BaseCommand

from proxy_web.jobs import enqueue_job, process_job


class Command(BaseCommand):
    help = "Compatibility command: queue or immediately run a score job"

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        job, created = enqueue_job("score")
        if not created:
            self.stdout.write("评分任务已在队列或运行中")
            return
        if options["once"]:
            process_job(job)
            job.refresh_from_db()
            self.stdout.write(job.message)
        else:
            self.stdout.write(f"已创建评分任务 #{job.pk}，请运行 run_worker")
