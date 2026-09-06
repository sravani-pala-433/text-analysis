import os

from dotenv import load_dotenv

load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")
TEST_DB_NAME = os.getenv("TEST_DB_NAME")
SECRET_KEY = os.getenv("SECRET_KEY")
PUBLIC_HTML_URL = os.getenv("PUBLIC_HTML_URL")
UPLOAD_FILE_DIR = os.getenv("UPLOAD_FILE_DIR", "/tmp")
FILE_CHUNK_SIZE = int(os.getenv("FILE_CHUNK_SIZE", 100))
