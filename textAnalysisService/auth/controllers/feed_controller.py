import uuid

from fastapi import APIRouter, HTTPException, status, Depends, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from textAnalysisService.auth.services.textset_service import TextSetService
from textAnalysisService.auth.schema import *
from textAnalysisService.auth.config import config
from textAnalysisService.auth.utils.Jwt_token import verify_access_token
import logging
from pathlib import Path

router = APIRouter(tags=['File Management'], prefix="/api")

textset_service = TextSetService()

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(f"{config.UPLOAD_FILE_DIR}/uploaded_files")


@router.post("/TextSet/{text_set_id}/upload-file/")
async def create_text_set(text_set_id: UUID, file: UploadFile = File(...),
                          payload: JWTTokenPayload = Depends(verify_access_token)):
	try:
		logger.debug(f"upload file request : {text_set_id}")
		file_string = file.filename.replace(" ", "_")
		file_name = f"{payload.user_id}_{text_set_id}_{uuid.uuid4().hex}_{file_string}"
		file_path = UPLOAD_DIR / file_name
		with file_path.open("wb") as buffer:
			content = await file.read()  # Read file content
			buffer.write(content)  # Write content to file
		return {"message": f"File '{file.filename}' has been uploaded successfully!", "file_path": str(file_path)}
	except HTTPException as http_exc:
		raise http_exc
	except Exception as e:
		logger.error(f"Failed to upload file : {file.filename}", exc_info=e)
		return JSONResponse(
			status_code=500,
			content={"detail": f"Internal server error while uploading file . {str(e)}"},
		)
