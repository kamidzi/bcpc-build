from enum import Enum
from sqlalchemy_utils.types.uuid import UUIDType

class BuildStateEnum(Enum):
    provisioned = 'provisioned'
    provisioning = 'provisioning'
    building = 'building'
    done = 'done'
    configuring = 'configuring'
    configured = 'configured'
    failed = 'failed'
    failed_provision = 'failed:provision'
    failed_build = 'failed:build'
