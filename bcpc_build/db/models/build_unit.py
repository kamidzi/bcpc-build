import sqlalchemy as sa
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from bcpc_build.db.types import GUID

Base = declarative_base()

class BuildUnitBase(Base):
    __tablename__ = 'build_unit'

    id = Column(GUID, primary_key=True)
    build_dir = Column(sa.Unicode(200), nullable=False)
    build_user = Column(sa.Unicode(64), nullable=False)
    description = Column(sa.Unicode(200))
    name = Column(sa.Unicode(128), nullable=False)
    source_url = Column(sa.Unicode(200), nullable=False)

    def __repr__(self):
        return ("<BuildUnit(name='{name}', build_dir={build_dir},"
                " build_user={build_user}, source_url='{source_url}')>"
                "".format(**self.__dict__))
