from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# TODO: make configurable
engine = create_engine('sqlite:///bcpc_build.db')
Session = sessionmaker(bind=engine)
