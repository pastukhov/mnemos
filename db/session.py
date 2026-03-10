from sqlalchemy import Engine, create_engine as sa_create_engine
from sqlalchemy.orm import sessionmaker


def create_engine(database_url: str) -> Engine:
  return sa_create_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker:
  return sessionmaker(bind=engine, expire_on_commit=False)
