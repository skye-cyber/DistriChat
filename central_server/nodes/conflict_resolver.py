class ConflictResolver:
    def resolve_message_conflict(self, local_msg, remote_msg):
        """Resolve conflicts between local and remote messages"""
        # Use last-write-wins strategy
        if local_msg.updated_at > remote_msg.updated_at:
            return local_msg
        else:
            return remote_msg
