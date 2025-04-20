import logging
_logger = logging.getLogger(__name__)

_logger.info("Loading models from custom_crm_add_call")

from . import crm_call_log
from . import crm_lead_inherit
