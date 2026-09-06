from datetime import timedelta

from fastapi import HTTPException, status
from passlib.exc import UnknownHashError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from textAnalysisService.auth.config.database import get_session
from textAnalysisService.auth.config.exception_handler import exception_handler
from textAnalysisService.auth.utils import hashing
from textAnalysisService.auth.repositories.user_repository import UserRepository
from textAnalysisService.auth.schema import *
import logging

from textAnalysisService.auth.utils.Jwt_token import create_access_token

logger = logging.getLogger(__name__)


class UserService:
	
	async def register_user(self, register_user_request: RegisteredUserCreate) -> RegisteredUserResponse:
		"""Register a new user"""
		try:
			logger.debug("Attempting to register user: %s", register_user_request.email)
			with get_session() as session:
				user_repo = UserRepository(session)
				existing_user = await user_repo.verify_existing_user(register_user_request.email,
				                                                     register_user_request.user_name)
				if existing_user:
					logger.warning("User already exists email: %s or username :%s ", register_user_request.email,
					               register_user_request.user_name)
					raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
					                    detail=f"User {register_user_request.user_name} exist")
				logger.info(f"Attempting to register new user: {register_user_request.user_name}")
				new_user = await user_repo.register_user(register_user_request)
				logger.info("User registered successfully: %s", new_user.email)
				return RegisteredUserResponse.model_validate(new_user)
		except IntegrityError as e:
			logger.error("Database error while registering user: %s", str(e))
			raise HTTPException(
				status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
				detail="A database error occurred.",
			) from e
		except HTTPException as http_exc:
			raise http_exc
		except Exception as e:
			logger.exception("Unexpected error during user registration.")
			raise HTTPException(
				status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
				detail=f"An unexpected error occurred while registering the user {str(e)}",
			) from e
	
	@exception_handler
	async def login(self, login_request: LoginRequest) -> LoginResponse:
		try:
			with get_session() as session:
				user_repo = UserRepository(session)
				found_user = await user_repo.verify_existing_user(login_request.username,
				                                                  login_request.username)
				if found_user is None or self._is_correct_password(found_user.hashed_password,
				                                                   login_request.password) is False:
					logger.warning("Invalid login credentials.")
					raise HTTPException(
						status_code=status.HTTP_401_UNAUTHORIZED,
						detail="Invalid credentials"
					)
				logger.info(f"Login token is getting created for user: {login_request.username}")
				token = create_access_token(JWTTokenPayload(user_id=found_user.id, username=found_user.email,
				                                            exp=datetime.utcnow() + timedelta(hours=1)))
				logger.debug("token: %s", token)
				return LoginResponse(access_token=token, token_type="bearer", user_id=found_user.id,
				                     name=found_user.user_name)  # Return both the token and user_id
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
			logger.exception("Unexpected error during user registration.")
			raise HTTPException(
				status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
				detail=f"An unexpected error occurred while registering the user {str(e)}",
			) from e
	
	def _is_correct_password(self, password: str, request_password: str) -> bool:
		hashing.verify_password(request_password, password) or hashing.verify_password(hashing.hash_password(password),
		                                                                               request_password)
	
	def _is_token_blacklisted(self, token: str) -> bool:
		return token in self.blacklisted_tokens
