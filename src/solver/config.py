"""Gambit Solver configuration class"""

import logging
import pathlib
import tomllib

_log = logging.getLogger(__name__)


class GambitConfig:
	"""Gambit Solver configuration class"""

	server_port: int
	client_port: int
	search_depth: int
	search_target_time: float | None
	search_max_time: float | None

	def __init__(self, file: str | pathlib.Path):
		"""Initializes a configuration object

		Parameters
		----------
		file : str | pathlib.Path
			Configuration file

		Raises
		------
		FileNotFoundError
			Configuration file not found
		"""
		if isinstance(file, str):
			file = pathlib.Path(file)
		if not file.exists():
			raise FileNotFoundError(f"Unable to find configuration file: {file.absolute()}")

		t = tomllib.loads(file.read_text())

		self.server_port = t["solution"]["port"]
		self.client_port = t["movement"]["port"]
		self.search_depth = t["solution"]["depth"]
		self.search_target_time = t["solution"].get("target_time", None)
		# Only read the max time if the target time was found
		if self.search_target_time is not None:
			self.search_max_time = t["solution"]["max_time"]
		else:
			_log.info("Target search time not found. Ignoring max search time entries.")
			self.search_max_time = None
