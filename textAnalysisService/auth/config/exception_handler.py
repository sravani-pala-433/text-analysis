import logging
from functools import wraps

from fastapi import HTTPException, status
from passlib.exc import UnknownHashError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# Set up logger
logger = logging.getLogger(__name__)


def exception_handler(func):
	"""Generalized exception handling for service functions."""
	
	@wraps(func)
	def wrapper(*args, **kwargs):
		try:
			return func(*args, **kwargs)
		except IntegrityError as e:
			logger.error("Database error while registering user: %s", str(e))
			raise HTTPException(
				status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
				detail="A database error occurred.",
			) from e
		except SQLAlchemyError as e:
			logger.error(f"Database error during login: {str(e)}")
			raise HTTPException(
				status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
				detail="Login error"
			)
		except HTTPException as http_exc:
			raise http_exc
		except UnknownHashError as has_exc:
			raise HTTPException(
				status_code=status.HTTP_401_UNAUTHORIZED,
				detail="Invalid credentials"
			)
		except Exception as e:
			logger.exception("Unexpected error during operation: %s.", str(e) )
			raise HTTPException(
				status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
				detail=f"An unexpected error occurred while performing action error is {str(e)}",
			) from e
	
	return wrapper
