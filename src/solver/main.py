"""Gambit chess solving engine using a Minimax algorithm"""

from __future__ import annotations

import logging
import time

from solver.config import HOST, SENSING_TO_SOLVING_SOCKET, SOLVING_TO_MOVEMENT_SOCKET
from solver.server_base import InboundServer, OutboundSender

from .board import Board

LOGGING_ID = "solver"
IN_PORT: int = SENSING_TO_SOLVING_SOCKET
OUT_PORT: int = SOLVING_TO_MOVEMENT_SOCKET


def configure_logging() -> None:
	"""Configure logging for the solver"""
	logging.basicConfig(
		level=logging.INFO,
		format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
		datefmt="%Y-%m-%d %H:%M:%S",
	)


def solve_fen(fen: str, depth: int = 4) -> str:
	"""
	Solve a chess position given as a FEN string.

	Args:
		fen (str): A valid FEN string representing the board state.
		depth (int, optional): Search depth for the solver. Defaults to 4.

	Returns:
		str: The chosen move encoded as a string.
	"""
	board = Board()
	board.load_fen_string(fen)

	start = time.time()
	move = board.solve(depth)
	elapsed = time.time() - start

	logging.getLogger("solver").info("Solved in %.3fs | Move: %s", elapsed, move)

	return str(move)


class SolvingServer(InboundServer):
	"""Extends the generic InboundServer to handle solving logic"""

	def serve(self, outbound: OutboundSender) -> None:
		"""Processes solving logic"""

		super().serve(outbound)

		while True:
			conn, addr = self._sock.accept()  # type: ignore
			self._log.info("Listening from %s:%d", *addr)

			with conn:
				data: bytes = conn.recv(4096)
				if not data:
					continue

				fen: str = data.decode("utf-8").strip()
				self._log.info("Received FEN: %s", fen)

				try:
					move: str = solve_fen(fen)
					outbound.send(move)
				except Exception:
					self._log.exception("Solver failure")
					try:
						outbound.send("ERROR")
					except Exception:
						self._log.exception("Failed to send error result")


def main() -> None:
	"""Initialize and run the solver server."""
	configure_logging()

	outbound: OutboundSender = OutboundSender(HOST, OUT_PORT)
	inbound: SolvingServer = SolvingServer(HOST, IN_PORT)

	try:
		inbound.start()
		inbound.serve(outbound)
	finally:
		inbound.close()
		outbound.close()


if __name__ == "__main__":
	main()
