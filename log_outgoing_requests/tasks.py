import logging

from .compat import shared_task
from .constants import SaveLogsChoice

logger = logging.getLogger(__name__)


@shared_task
def prune_logs():
    from .models import OutgoingRequestsLog

    num_deleted = OutgoingRequestsLog.objects.prune()
    logger.info("Deleted %d outgoing request log(s)", num_deleted)
    return num_deleted


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
