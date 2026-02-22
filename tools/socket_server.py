"""Tool to emulate a Gambit IPC server"""

import argparse
import logging
import selectors
import socket
from typing import Callable

_log = logging.getLogger("socket_server")


class ArgNamespace(argparse.Namespace):
	"""Argument parser namespace for type hinting"""

	port: str


def setup_logging(level: int = logging.INFO) -> None:
	"""Configures logging"""
	# Configure the log handler and formatter
	logHandler = logging.StreamHandler()
	logFormatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
	logHandler.setFormatter(logFormatter)

	# Assign the handler and level to the root log
	log = logging.getLogger()
	log.addHandler(logHandler)
	log.setLevel(level)


class GambitServer:
	"""Gambit emulated IPC server class"""

	def __init__(self, port: int) -> None:
		"""Initializes a Gambit emulated IPC server"""
		# Temporarily hard-code these values for now
		self.socket_address = "localhost"
		self.socket_port = port
		# Socket-related values
		self.__socket: socket.socket | None = None
		self.__connections: set[socket.socket] = set()
		self.__selector: selectors.BaseSelector | None = None
		self.__buffers: dict[socket.socket, bytearray] = {}

	def __socket_accept(self, sock: socket.socket) -> None:
		assert self.__selector is not None  # This makes the type-checker happy
		conn, addr = sock.accept()  # Socket should be ready if triggered by the selector
		_log.debug(f"Accepted connection: {conn} from: {addr}")
		conn.setblocking(False)
		# Create a buffer for the connection
		self.__buffers[conn] = bytearray()
		# Register the connection with the selector
		self.__selector.register(conn, selectors.EVENT_READ, self.__socket_read)
		# Add the connection to the connections list
		self.__connections.add(conn)

	def __socket_read(self, conn: socket.socket) -> None:
		assert self.__selector is not None  # This makes the type-checker happy
		data = conn.recv(1000)
		# TODO: Have this actually update the board state instead of just printing to console
		if data:
			_log.debug(f"Received data: {repr(data)} from: {conn}")
			self.__buffers[conn] += data
		else:
			# No data. Socket is closed (or other side shut down sending).
			# Process the received data for that socket
			_log.debug(f"Closing socket: {conn}")
			# Send a zero response to indicate OK
			conn.send("0".encode())
			# Shut down the socket while we close it down
			conn.shutdown(socket.SHUT_RDWR)
			# Handle the command
			peer_host, peer_port = conn.getpeername()
			_log.info(f"Processing command from {peer_host}:{peer_port} : {self.__buffers[conn].decode('utf-8')}")
			self.__selector.unregister(conn)
			self.__connections.remove(conn)
			del self.__buffers[conn]
			conn.close()

	def run(self) -> None:
		"""Runs the Gambit Solver IPC server.

		This is a blocking operation that will continue until signalled to exit."""
		# Initialize the socket
		_log.info(f"Starting IPC server on [{self.socket_address}:{self.socket_port}]")
		self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.__socket.bind((self.socket_address, self.socket_port))
		self.__socket.listen(100)
		self.__socket.setblocking(False)

		# Initialize the selector
		self.__selector = selectors.DefaultSelector()

		# Register the socket
		self.__selector.register(self.__socket, selectors.EVENT_READ, self.__socket_accept)

		# Run the main loop
		# TODO: Add a signal handler here to stop everything gracefully
		try:
			while True:
				events = self.__selector.select(0.5)
				for key, _ in events:
					callback: Callable = key.data
					callback(key.fileobj)
		except KeyboardInterrupt:
			_log.info("Caught keyboard interrupt. Exiting")
		finally:
			# Close all of the connections
			for c in self.__connections:
				c.close()
			self.__socket.close()
			# Close the selector
			self.__selector.close()


def main() -> None:
	"""Main function"""
	setup_logging()
	parser = argparse.ArgumentParser()
	parser.add_argument("-p", "--port", action="store", dest="port", help="Destination port")
	args = parser.parse_args(namespace=ArgNamespace())

	server = GambitServer(int(args.port))

	server.run()


if __name__ == "__main__":
	main()
