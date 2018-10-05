import logging
import sys


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
LOG = logging.getLogger(__name__)


def set_log_level(level):
    _level_type = type(logging.INFO)
    if isinstance(level, _level_type):
        LOG.setLevel(level)
    else:
        try:
            LOG.setLevel(getattr(logging, level))
        except AttributeError as e:
            raise ValueError(
                '{} is not a valid log level'.format(level)
            ) from e

