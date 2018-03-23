from bcpc_build.db.migration_types import BuildStateEnum
from bcpc_build.db.migration_types import UUIDType
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Enum, Integer, String
import sqlalchemy as sa
import uuid

Base = declarative_base()

class BuildUnitBase(Base):
    __tablename__ = 'build_unit'

    id = Column(UUIDType(), primary_key=True, default=uuid.uuid4)
    build_dir = Column(sa.Unicode(200), nullable=False)
    build_user = Column(sa.Unicode(64), nullable=False)
    description = Column(sa.Unicode(200))
    name = Column(sa.Unicode(128), nullable=False)
    source_url = Column(sa.Unicode(200), nullable=False)
    build_state = Column(
        'build_state',
        Enum(BuildStateEnum, values_callable=lambda x: [e.value for e in x])
    )
    created_at = Column(sa.TIMESTAMP(True), nullable=False,
                                            default=datetime.utcnow)
    updated_at = Column(sa.TIMESTAMP(True), nullable=False,
                                            onupdate=datetime.utcnow,
                                            default=datetime.utcnow)

    def __repr__(self):
        return ("<BuildUnit(name='{name}', build_dir={build_dir},"
                " build_user={build_user}, source_url='{source_url}',"
                " build_state='{build_state}')>"
                "".format(**self.__dict__))
