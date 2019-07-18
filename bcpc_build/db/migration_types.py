from enum import Enum
from enum import unique
import sqlalchemy_utils.types.uuid as uuid


UUIDType = uuid.UUIDType


@unique
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

    def __str__(self):
        return self.value

    @classmethod
    def names(cls):
        return cls._member_names_

    @classmethod
    def values(cls):
        return [str(x) for x in cls._member_map_.values()]
