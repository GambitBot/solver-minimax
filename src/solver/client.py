"""Gambit solver IPC client"""

import logging
import socket

_log = logging.getLogger(__name__)


class GambitClient:
	"""Gambit Solver IPC client class"""

	def __init__(self, target_port: int) -> None:
		"""Initializes a Gambit Solver IPC client"""
		self.server_address = "localhost"
		self.server_port = target_port

	def send(self, message: str) -> None:
		"""Sends data through the IPC client.

		Parameters
		----------
		message : str
			Data to send
		"""
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.settimeout(15)  # 15 second timeout so that we don't deadlock
		try:
			sock.connect((self.server_address, self.server_port))
			sock.send(message.encode("utf-8"))
			sock.shutdown(socket.SHUT_WR)
			response = sock.recv(1000)
			sock.shutdown(socket.SHUT_RDWR)
			if response.decode("utf-8") != "0":
				_log.warning(
					f"Unexpected response from ({self.server_address}:{self.server_port}): {response.decode('utf-8')}"
				)
		except (ConnectionRefusedError, TimeoutError):
			_log.error(f"Unable to send message to target socket ({self.server_address}:{self.server_port})")
		finally:
			sock.close()
