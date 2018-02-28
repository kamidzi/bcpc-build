from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from bcpc_build import config

# TODO: make configurable
engine = create_engine(config.db.url)
Session = sessionmaker(bind=engine)
