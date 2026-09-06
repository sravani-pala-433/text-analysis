from passlib.context import CryptContext
import logging

pwd_context = CryptContext(schemes=['argon2'], deprecated='auto')

logger = logging.getLogger(__name__)


def hash_password(password):
	return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
	logger.debug("plain_password:%s hashed_password=%s", plain_password, hashed_password)
	is_valid = pwd_context.verify(plain_password, hashed_password)
	logger.debug("is_valid=%s", is_valid)
	return is_valid
