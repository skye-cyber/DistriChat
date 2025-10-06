# Batch processing for large sync operations
def sync_in_batches(queryset, batch_size=1000):
    """Sync large datasets in batches"""
    for i in range(0, queryset.count(), batch_size):
        batch = queryset[i : i + batch_size]
        yield batch
