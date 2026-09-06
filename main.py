from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import textAnalysisService.auth.models as auth_models
from textAnalysisService.auth.config import config
from textAnalysisService.auth.utils.file_observer_handler import start_file_observer, stop_file_observer

from textAnalysisService.auth.config.database import engine
from textAnalysisService.auth.controllers import user_controller as auth_controller
from textAnalysisService.auth.controllers import textset_controller as text_controller
from textAnalysisService.auth.controllers import app_controller as app_controller
from textAnalysisService.auth.controllers import feed_controller as feed_controller

from textAnalysisService.auth.config.logging import configure_logging
import logging
import os

configure_logging()
logger = logging.getLogger(__name__)

UPLOAD_DIRECTORY = Path(f"{config.UPLOAD_FILE_DIR}/uploaded_files")
FAILED_FILE_DIRECTORY = Path(f"{config.UPLOAD_FILE_DIR}/failed")
COMPLETED_FILE_DIRECTORY = Path(f"{config.UPLOAD_FILE_DIR}/completed")

UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
FAILED_FILE_DIRECTORY.mkdir(parents=True, exist_ok=True)
COMPLETED_FILE_DIRECTORY.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
	# Startup actions
	observer, worker_thread = start_file_observer(UPLOAD_DIRECTORY, COMPLETED_FILE_DIRECTORY, FAILED_FILE_DIRECTORY)
	
	logger.info("File observer started.")
	
	yield  # The application runs during this time
	
	# Shutdown actions
	stop_file_observer(observer, worker_thread)
	logger.info("File observer stopped.")


app = FastAPI(title="Textualize-Demo",
              docs_url="/api/docs",  # Swagger UI
              redoc_url="/api/redoc",  # ReDoc UI
              openapi_url="/api/openapi.json",  # OpenAPI schema
              lifespan=lifespan
              )

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],  # Allow all origins
	allow_credentials=True,
	allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
	allow_headers=["*"],  # Allow all headers
)
# Create database tables on startup
auth_models.Base.metadata.create_all(bind=engine)
app.include_router(auth_controller.router)
app.include_router(text_controller.router)
app.include_router(app_controller.router)
app.include_router(feed_controller.router)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
	logger.error("Unhandled exception: %s", str(exc), exc_info=True)
	return JSONResponse(
		status_code=500,
		content={"detail": "An unexpected error occurred."},
	)
