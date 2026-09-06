import math

from dateutil import parser
import logging
import re

logger = logging.getLogger(__name__)


def extract_request_details_from_file_path(file_path):
	uuid_pattern = r'([a-f0-9\-]{36})'  # Regular expression for a UUID
	matches = re.findall(uuid_pattern, file_path)
	# Extract the first and second UUIDs
	if len(matches) >= 2:
		user_id = matches[0]
		text_set_id = matches[1]
		return {"user_id": user_id, "text_set_id": text_set_id}
	else:
		return {"user_id": None, "text_set_id": None}


def check_and_replace_nan(value):
	if isinstance(value, float) and math.isnan(value):
		return None  # Replace NaN with None
	return value


def parse_iso8601_date(date_str):
	try:
		return parser.isoparse(date_str)
	except Exception as e:
		logger.error(f"Error parsing date {date_str}: {e}")
		return None
