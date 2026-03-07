"""Gambit chess solving engine using a Minimax algorithm"""

import argparse
import logging

from .benchmark import benchmark
from .log import setup_logging
from .server import run_server

_log = logging.getLogger("gambit-solver")


class ArgNamespace(argparse.Namespace):
	"""Argument parser namespace for type hinting"""

	server: bool
	configfile: str | None


def main() -> None:
	"""Gambit Solver main function"""
	# Configure logging before anything else
	setup_logging()
	# Argument setup
	parser = argparse.ArgumentParser()
	parser.add_argument("-s", "--server", action="store_true", dest="server", help="Run as server")
	parser.add_argument("-c", "--config", action="store", dest="configfile", help="Configuration file path")
	args = parser.parse_args(namespace=ArgNamespace())

	if args.server:
		# If started as a server
		if args.configfile is not None:
			run_server(args.configfile)
		else:
			_log.error("Server requires a configuration file to run!")
	else:
		# Otherwise, run the benchmark
		benchmark()


if __name__ == "__main__":
	main()
