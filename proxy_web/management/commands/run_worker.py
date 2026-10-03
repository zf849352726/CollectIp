import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from proxy_web.jobs import claim_next_job, enqueue_due_jobs, process_job


class Command(BaseCommand):
    help = "Run the persistent CollectIP job worker and scheduler"

    def add_arguments(self, parser):
        parser.add_argument("--poll", type=float, default=2.0, help="poll seconds")
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        poll = max(0.2, options["poll"])
        while True:
            close_old_connections()
            enqueue_due_jobs()
            job = claim_next_job()
            if job:
                self.stdout.write(f"Running {job.kind} job #{job.pk}")
                process_job(job)
                if options["once"]:
                    return
            elif options["once"]:
                return
            else:
                time.sleep(poll)
