import logging
import sys

from bcpc_build.utils import set_log_level as _u_set_log_level

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
LOG = logging.getLogger(__name__)


def set_log_level(level):
    return _u_set_log_level(LOG, level)
