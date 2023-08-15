# NOTE: since this is imported in models.py, ensure it doesn't use functionality that
# requires django to be fully initialized.
from .conf import settings
from .tasks import reset_config


def schedule_config_reset():
    reset_after = settings.LOG_OUTGOING_REQUESTS_RESET_DB_SAVE_AFTER
    if not reset_after:
        return

    countdown = reset_after * 60
    reset_config.apply_async(countdown=countdown)
