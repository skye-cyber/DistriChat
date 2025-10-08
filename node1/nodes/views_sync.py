def receive_sync_from_node(request):
    """Endpoint to receive sync from nodes"""
    handler = get_central_sync_handler()

    # Set the origin before saving
    node_id = request.data.get("node_id")
    handler.set_sync_origin(node_id)

    try:
        # Process the sync data (this will trigger signals)
        # The signals will use the set sync_origin to prevent loops
        process_sync_data(request.data)

    finally:
        # Always clear the origin
        handler.clear_sync_origin()

    return Response({"status": "success"})
