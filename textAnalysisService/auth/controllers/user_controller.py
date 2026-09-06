from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from textAnalysisService.auth.services.user_service import UserService
from textAnalysisService.auth.schema import *
from textAnalysisService.auth.utils.Jwt_token import verify_access_token
import logging

router = APIRouter(tags=['Authentication Management'], prefix="/api")

user_service = UserService()

logger = logging.getLogger(__name__)


@router.post('/signup', response_model=RegisteredUserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(register_user_request: RegisteredUserCreate):
	try:
		logger.debug(f"register_user request : {register_user_request}")
		return await user_service.register_user(register_user_request)
	except HTTPException as http_exc:
		raise http_exc
	except Exception as e:
		logger.error(f"Failed to register new user: {register_user_request.user_name}", exc_info=e)
		return JSONResponse(
			status_code=500,
			content={"detail": "Internal server error while creating user."},
		)


@router.post('/swaggerlogin', response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def swaggerlogin(login_request: OAuth2PasswordRequestForm = Depends()):
	try:
		logger.debug(f"register_user request : {login_request.username}")
		return await user_service.login(login_request)
	except HTTPException as http_exc:
		raise http_exc
	except Exception as e:
		logger.error(f"Failed to login: {login_request.username}", exc_info=e)
		return JSONResponse(
			status_code=500,
			content={"detail": f"Internal server error while login user. {str(e)}"},
		)


@router.post('/login', response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(login_request: LoginRequest):
	try:
		logger.debug(f"register_user request : {login_request.username}")
		return await user_service.login(login_request)
	except HTTPException as http_exc:
		raise http_exc
	except Exception as e:
		logger.error(f"Failed to login: {login_request.username}", exc_info=e)
		return JSONResponse(
			status_code=500,
			content={"detail": f"Internal server error while login user. {str(e)}"},
		)


@router.post('/verifylogin', response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def verifylogin(payload: JWTTokenPayload = Depends(verify_access_token)):
	try:
		logger.debug(f"verifylogin request : {payload.username}")
		return LoginResponse(token_type="", access_token=payload.username, user_id=payload.user_id,
		                     name=payload.username)
	except HTTPException as http_exc:
		raise http_exc
	except Exception as e:
		logger.error(f"Failed to login: {payload.username}", exc_info=e)
		return JSONResponse(
			status_code=500,
			content={"detail": f"Internal server error while login user. {str(e)}"},
		)
