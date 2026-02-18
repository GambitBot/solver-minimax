"""Gambit chess solving engine using a Minimax algorithm"""

from __future__ import annotations

import logging
import socket
import time
from typing import Optional

from solver.config import HOST, SENSING_TO_SOLVING_SOCKET, SOLVING_TO_MOVEMENT_SOCKET

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


class OutboundSender:
	"""
	Maintains a persistent outbound TCP connection for sending.

	The connection is made on first sent and remade if it drops.
	"""

	def __init__(self, host: str, port: int, timeout: float = 2.0) -> None:
		"""
		Initialize the outbound sender.

		Args:
			host (str): Destination hostname or IP address.
			port (int): Drestination TCP port.
			timeout (float, optional): Socket timeout in seconds. Defaults to 2.0.
		"""
		self._host = host
		self._port = port
		self._timeout = timeout
		self._sock: Optional[socket.socket] = None
		self._log = logging.getLogger(LOGGING_ID)

	def connect(self) -> None:
		"""
		Make the outbound TCP connection.

		If an existing connection is present, it is closed.
		"""
		self.close()

		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.settimeout(self._timeout)
		sock.connect((self._host, self._port))

		self._sock = sock
		self._log.info("Connected outbound to %s:%d", self._host, self._port)

	def send(self, message: str) -> None:
		"""
		Send a message over the persistent outbound connection.

		If the connection is not made or has dropped, it is automatically reconnected.

		Args:
			message (str): UTF-8 encodable message payload.
		"""
		data: bytes = message.encode("utf-8")

		if self._sock is None:
			self.connect()

		try:
			self._sock.sendall(data)  # type: ignore
		except OSError:
			self._log.warning("Outbound connection lost, reconnecting")
			self.connect()
			self._sock.sendall(data)  # type: ignore

	def close(self) -> None:
		"""Close the outbound socket if it is open."""
		if self._sock is not None:
			try:
				self._sock.close()
			finally:
				self._sock = None


class InboundServer:
	"""
	Listens for inbound TCP connections.

	Each connection is handled synchronously, read once
	"""

	def __init__(self, host: str, port: int) -> None:
		"""
		Initialize the inbound server.

		Args:
			host: Local address to bind to.
			port: TCP port to listen on.
		"""
		self._host: str = host
		self._port: int = port
		self._sock: Optional[socket.socket] = None
		self._log: logging.Logger = logging.getLogger(LOGGING_ID)

	def start(self) -> None:
		"""Bind and start listening on the inbound socket."""
		sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		sock.bind((self._host, self._port))
		sock.listen(1)

		self._sock = sock
		self._log.info("Listening on %s:%d", self._host, self._port)

	def serve(self, outbound: OutboundSender) -> None:
		"""
		Accept and process inbound connections indefinitely.

		Args:
			outbound: Persistent sender used to send results.

		Raises:
			RuntimeError: If the server has not been started.
		"""
		if self._sock is None:
			raise RuntimeError("Inbound server not started")

		while True:
			conn, addr = self._sock.accept()
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

	def close(self) -> None:
		"""Close the inbound listening socket."""
		if self._sock is not None:
			try:
				self._sock.close()
			finally:
				self._sock = None


def main() -> None:
	"""Initialize and run the solver server."""
	configure_logging()

	outbound: OutboundSender = OutboundSender(HOST, OUT_PORT)
	inbound: InboundServer = InboundServer(HOST, IN_PORT)

	try:
		inbound.start()
		inbound.serve(outbound)
	finally:
		inbound.close()
		outbound.close()


if __name__ == "__main__":
	main()
