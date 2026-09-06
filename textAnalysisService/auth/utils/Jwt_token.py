from fastapi.security import OAuth2PasswordBearer
from fastapi import FastAPI, HTTPException, Depends
from jose import JWTError, jwt  # type: ignore
from datetime import datetime, timedelta, timezone
import re

from textAnalysisService.auth.config import config
from textAnalysisService.auth.schema import JWTTokenPayload

# Secret key to encode and decode the JWT token
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Token expires after 30 minutes

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="swaggerlogin")


def create_access_token(data: JWTTokenPayload):
	# to_encode = data.__dict__.copy()
	# expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
	payload = {
		"user_id": str(data.user_id),
		"username": data.username,
		"exp": data.exp  # Token expires in 1 hour
	}
	encoded_jwt = jwt.encode(payload, config.SECRET_KEY, algorithm=ALGORITHM)
	return encoded_jwt


def verify_access_token(token: str = Depends(oauth2_scheme)) -> JWTTokenPayload:
	try:
		payload = jwt.decode(token, config.SECRET_KEY, algorithms=[ALGORITHM])
		return JWTTokenPayload(**payload)
	except JWTError:
		raise HTTPException(status_code=403, detail="Could not validate credentials")
