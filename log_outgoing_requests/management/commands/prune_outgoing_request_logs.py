from django.core.management.base import BaseCommand

from ...models import OutgoingRequestsLog


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        num_deleted = OutgoingRequestsLog.objects.prune()
        self.stdout.write(f"Deleted {num_deleted} outgoing request log(s)")
