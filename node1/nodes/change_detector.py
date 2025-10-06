from django.utils import timezone


class ChangeDetector:
    def __init__(self):
        self.message_count = 0
        self.last_check = timezone.now()

    def check_for_changes(self):
        """Check if significant changes occurred since last sync"""
        from chat.models import Message

        new_count = Message.objects.count()
        changes_detected = new_count != self.message_count

        if changes_detected:
            self.message_count = new_count
            return True

        return False

    def should_sync(self):
        """Determine if sync should be triggered"""
        time_since_last_sync = timezone.now() - self.last_check

        # Sync if:
        # 1. Significant time passed (30 minutes)
        # 2. Many changes detected
        # 3. Manual trigger
        if time_since_last_sync.total_seconds() > 1800:  # 30 minutes
            return True

        return self.check_for_changes()
