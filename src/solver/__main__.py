"""Gambit chess solving engine using a Minimax algorithm"""

import argparse
import logging

from .benchmark import benchmark
from .log import setup_logging
from .server import run_server

_log = logging.getLogger("gambit-solver")


def main() -> None:
	"""Gambit Solver main function"""
	# Configure logging before anything else
	setup_logging()
	# Argument setup
	parser = argparse.ArgumentParser()
	parser.add_argument("-s", "--server", action="store_true", dest="server", help="Run as server")
	args = parser.parse_args()

	if args.server:
		# If started as a server
		run_server()
	else:
		# Otherwise, run the benchmark
		benchmark()


if __name__ == "__main__":
	main()
