"""Reusable Base Server"""

import logging
import socket
from typing import Optional


class OutboundSender:
	"""
	Maintains a persistent outbound TCP connection for sending.

	The connection is made on first sent and remade if it drops.
	"""

	def __init__(self, host: str, port: int, timeout: float = 2.0, logging_id: str = "") -> None:
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
		self._log = logging.getLogger(logging_id)

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

	def __init__(self, host: str, port: int, logging_id: str = "") -> None:
		"""
		Initialize the inbound server.

		Args:
			host: Local address to bind to.
			port: TCP port to listen on.
		"""
		self._host: str = host
		self._port: int = port
		self._sock: Optional[socket.socket] = None
		self._log: logging.Logger = logging.getLogger(logging_id)

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

	def close(self) -> None:
		"""Close the inbound listening socket."""
		if self._sock is not None:
			try:
				self._sock.close()
			finally:
				self._sock = None
