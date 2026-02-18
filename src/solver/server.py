"""Gambit solver IPC server"""

import logging
import selectors
import socket
from typing import Callable

from .board import Board

_log = logging.getLogger()


class GambitServer:
	"""Gambit Solver IPC server class"""

	board: Board

	def __init__(self) -> None:
		"""Initializes a Gambit Solver IPC server"""
		self.board = Board()
		# Temporarily hard-code these values for now
		self.socket_address = "localhost"
		self.socket_port = 8081
		# Socket-related values
		self.__socket: socket.socket | None = None
		self.__selector: selectors.BaseSelector | None = None

	def __socket_accept(self, sock: socket.socket) -> None:
		assert self.__selector is not None  # This makes the type-checker happy
		conn, addr = sock.accept()  # Socket should be ready if triggered by the selector
		_log.info(f"Accepted connection: {conn} from: {addr}")
		conn.setblocking(False)
		self.__selector.register(conn, selectors.EVENT_READ, self.__socket_read)

	def __socket_read(self, conn: socket.socket) -> None:
		assert self.__selector is not None  # This makes the type-checker happy
		data = conn.recv(1000)
		# TODO: Have this actually update the board state instead of just printing to console
		if data:
			_log.info(f"Received data: {repr(data)} from: {conn}")
			conn.send(data)
		else:
			# No data. Socket is closed.
			_log.info(f"Closing socket: {conn}")
			self.__selector.unregister(conn)
			conn.close()

	def run(self) -> None:
		"""Runs the Gambit Solver IPC server.

		This is a blocking operation that will continue until signalled to exit."""
		# Initialize the socket
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.bind((self.socket_address, self.socket_port))
		sock.listen(100)
		sock.setblocking(False)

		# Initialize the selector
		self.__selector = selectors.DefaultSelector()

		# Register the socket
		self.__selector.register(sock, selectors.EVENT_READ, self.__socket_accept)

		# Run the main loop
		# TODO: Add a signal handler here to stop everything gracefully
		try:
			while True:
				events = self.__selector.select()
				for key, mask in events:
					callback: Callable = key.data
					callback(key.fileobj)
		except KeyboardInterrupt:
			_log.info("Caught keyboard interrupt. Exiting")
		finally:
			self.__selector.close()


def run_server() -> None:
	"""Runs the Gambit solver IPC server"""
	_log.info("Running Gambit Solver server")
	server = GambitServer()
	server.run()
