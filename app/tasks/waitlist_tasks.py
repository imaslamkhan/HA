from app.celery_app import celery_app


@celery_app.task(name="app.tasks.waitlist.notify_waitlist_joined")
def notify_waitlist_joined_task(waitlist_entry_id: str) -> dict:
    # Placeholder task wiring for waitlist notifications.
    return {"waitlist_entry_id": waitlist_entry_id, "status": "queued"}
