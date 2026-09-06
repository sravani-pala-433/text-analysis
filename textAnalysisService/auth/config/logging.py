import logging
import sys
import os


def configure_logging():
	"""
	   Configures logging dynamically based on the environment.
	   The log level can be controlled via the LOG_LEVEL environment variable.
	   """
	# Get the log level from the environment, defaulting to DEBUG if not set
	log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
	
	# Validate the log level and set the logging level accordingly
	log_level_dict = {
		"DEBUG": logging.DEBUG,
		"INFO": logging.INFO,
		"WARNING": logging.WARNING,
		"ERROR": logging.ERROR,
		"CRITICAL": logging.CRITICAL
	}
	
	level = log_level_dict.get(log_level, logging.DEBUG)  # Default to DEBUG if invalid level
	
	logger = logging.getLogger()  # Root logger
	logger.setLevel(level)  # Set root logger level dynamically
	# Console handler for stdout
	console_handler = logging.StreamHandler(sys.stdout)
	console_handler.setLevel(logging.DEBUG)
	
	formatter = logging.Formatter(
		"%(asctime)s - %(name)s - %(levelname)s - %(filename)s - %(lineno)d - %(funcName)s - %(message)s"
	)
	console_handler.setFormatter(formatter)
	
	# File handler for logging into a file
	file_handler = logging.FileHandler("app.log")
	file_handler.setLevel(logging.DEBUG)
	file_handler.setFormatter(formatter)
	
	logger.addHandler(console_handler)
	logger.addHandler(file_handler)


def logger(name: str) -> logging.Logger:
	"""
	Returns a logger with the given module name.
	"""
	return logging.getLogger(name)
