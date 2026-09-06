from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from contextlib import contextmanager

from . import config
import logging

logger = logging.getLogger(__name__)


DATABASE_URL = config.DATABASE_URL

logger.debug(DATABASE_URL)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


@contextmanager
def get_session():
	session = SessionLocal()
	try:
		yield session
		logger.debug("Transaction yielded hence session committed")
		session.commit()
	except Exception:
		logger.exception("Exception occurred soll session rolling back")
		session.rollback()
		raise
	finally:
		logger.debug("Transaction committed hence session closed")
		session.close()


def get_db() -> Session:
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()
