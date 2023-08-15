try:
    from .tasks import reset_config
except ImportError:
    reset_config = None


def schedule_config_reset():
    # nothing to do, celery not installed
    if reset_config is None:
        return

    from .conf import settings

    reset_after = settings.LOG_OUTGOING_REQUESTS_RESET_DB_SAVE_AFTER
    if not reset_after:
        return

    countdown = reset_after * 60
    reset_config.apply_async(countdown=countdown)
