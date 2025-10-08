from django.core.management.base import BaseCommand
from django.utils import timezone
from nodes.models import Node
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Monitor node status and mark offline nodes"

    def handle(self, *args, **options):
        self.stdout.write("🔍 Monitoring node status...")

        offline_threshold = timezone.now() - timedelta(minutes=2)

        # Find nodes that haven't sent heartbeat recently
        offline_nodes = Node.objects.filter(
            last_heartbeat__lt=offline_threshold, status__in=["online", "overloaded"]
        )

        for node in offline_nodes:
            old_status = node.status
            node.status = "offline"
            node.save(update_fields=["status", "updated_at"])

            logger.warning(
                f"🔴 Node {node.name} marked OFFLINE (last heartbeat: {node.last_heartbeat})"
            )
            self.stdout.write(self.style.WARNING(f"Marked {node.name} as offline"))

        if offline_nodes:
            self.stdout.write(
                self.style.SUCCESS(f"Marked {offline_nodes.count()} nodes as offline")
            )
        else:
            self.stdout.write("✅ All nodes are online")
