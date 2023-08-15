from .compat import shared_task
from .constants import SaveLogsChoice


@shared_task
def reset_config():
    from .models import OutgoingRequestsLogConfig

    config = OutgoingRequestsLogConfig.get_solo()
    assert isinstance(config, OutgoingRequestsLogConfig)

    # nothing to do
    if config.save_to_db == SaveLogsChoice.use_default:
        return

    config.save_to_db = SaveLogsChoice.use_default
    config.save(update_fields=["save_to_db"])
