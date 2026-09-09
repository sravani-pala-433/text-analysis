from pathlib import Path

from fastapi import APIRouter, HTTPException
from starlette.responses import HTMLResponse

from textAnalysisService.auth.config.config import PUBLIC_HTML_URL
from textAnalysisService.auth.services.user_service import UserService
import logging
import requests

router = APIRouter(tags=['Application Management'])
user_service = UserService()

logger = logging.getLogger(__name__)

LOCAL_HTML_FILE = Path(__file__).resolve().parents[3] / "frontend" / "index.html"


def _get_html_content() -> str:
	if LOCAL_HTML_FILE.exists():
		with open(LOCAL_HTML_FILE, "r", encoding="utf-8") as f:
			return f.read()
	if not PUBLIC_HTML_URL:
		raise HTTPException(status_code=500, detail="Frontend not found and PUBLIC_HTML_URL is not configured")
	try:
		response = requests.get(PUBLIC_HTML_URL)
		response.raise_for_status()
		return response.text
	except requests.RequestException as e:
		raise HTTPException(status_code=500, detail=f"Error fetching HTML: {str(e)}")


@router.get("/index.html", response_class=HTMLResponse)
async def serve_index_html():
	return HTMLResponse(content=_get_html_content())


@router.get("/", response_class=HTMLResponse)
async def serve_root_html():
	return HTMLResponse(content=_get_html_content())
