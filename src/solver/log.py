"""Gambit Solver logging setup"""

import logging


def setup_logging(level: int = logging.INFO) -> None:
	"""Configures logging for the Gambit Solver"""
	# Configure the log handler and formatter
	logHandler = logging.StreamHandler()
	logFormatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
	logHandler.setFormatter(logFormatter)

	# Assign the handler and level to the root log
	log = logging.getLogger()
	log.addHandler(logHandler)
	log.setLevel(level)
