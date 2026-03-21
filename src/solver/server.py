"""Gambit solver IPC server"""

import logging
import selectors
import socket
from typing import Callable

from solver.exceptions import CheckmateException

from .board import Board
from .client import GambitClient
from .config import GambitConfig

_log = logging.getLogger(__name__)


class GambitServer:
	"""Gambit Solver IPC server class"""

	board: Board

	def __init__(self, config: GambitConfig, viewer: int | None = None) -> None:
		"""Initializes a Gambit Solver IPC server"""
		self.board = Board()
		# Configuration object
		self.config = config
		# Temporarily hard-code these values for now
		self.socket_address = "localhost"
		self.socket_port = config.server_port
		# Socket-related values
		self.__socket: socket.socket | None = None
		self.__connections: set[socket.socket] = set()
		self.__selector: selectors.BaseSelector | None = None
		self.__buffers: dict[socket.socket, bytearray] = {}
		# Client setup
		if viewer is None:
			self.client = GambitClient(config.client_port)
			self.viewer = False
		else:
			self.client = GambitClient(viewer)
			self.viewer = True

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
			try:
				self.__handle_command(self.__buffers[conn].decode())
			finally:
				self.__selector.unregister(conn)
				self.__connections.remove(conn)
				del self.__buffers[conn]
				conn.close()

	def __handle_command(self, commandstr: str) -> None:
		_log.info(f"Executing command: {commandstr}")
		try:
			command, data = commandstr.split(" ", maxsplit=1)
		except ValueError:
			command = commandstr
			data = ""
		# Casefold the command for comparison safety
		command = command.casefold()
		# Strip any newline characters from the end of the data
		data = data.strip("\r\n")
		try:
			match command:
				case "reset":
					self.__command_reset()
				case "solve":
					self.__command_solve(data)
				case "update":
					self.__command_update(data)
				case "debug_solve":
					self.__command_debug_solve(data)
				case "debug_status":
					self.__command_debug_status()
				case "move":
					self.__command_move(data)
				case _:
					_log.warning(f"Received invalid command: {command}")
		except Exception as e:
			_log.error(f"Error executing command: {command}")
			_log.exception(e)

	def __command_reset(self) -> None:
		_log.info("Resetting board state")
		self.board.reset()

	def __command_solve(self, data: str) -> None:
		self.__command_update(data)
		_log.info("Solving board state")
		# Set Gambit as the active player before solving
		self.board.set_gambit_as_player()
		try:
			if self.config.search_target_time is not None:
				move, _ = self.board.solve(
					self.config.search_depth, self.config.search_target_time, self.config.search_max_time
				)
			else:
				move, _ = self.board.solve(self.config.search_depth)
		except CheckmateException:
			_log.info("Gambit is in Checkmate!")
			return

		if self.viewer:
			# If we are using the viewer, we don't need to send
			# anything to the movement bridge.
			# Start by applying the move
			self.board.apply_move(move)
			# Then send the board state to the viewer
			fen = self.board.to_partial_fen()
			_log.info(f"Sending board to viewer: {fen}")
			self.client.send(fen)
		else:
			# Get the move command to send to the movement bridge
			moveCommand = self.board.get_move_command(move)
			# Apply the move to the board
			self.board.apply_move(move)
			_log.info(f"Selected move: {move}")
			_log.debug(f"Sending move command: {moveCommand}")
			self.client.send(moveCommand)

	def __command_debug_solve(self, data: str) -> None:
		_log.info(f"Solving for board state: {data}")
		self.board.load_fen_string(data)
		try:
			move, _ = self.board.solve(self.config.search_depth)
			# Print results of the solve
			print(f"Optimal move: {move}")
		except CheckmateException:
			print("Checkmate. No moves available.")

	def __command_update(self, data: str) -> None:
		_log.info(f"Updating board with state: {data}")
		self.board.update_board(data)

	def __command_debug_status(self) -> None:
		print("Current board state:")
		print(self.board)
		print(f"Board initialized: {self.board.is_initialized()}")
		print(f"Active player: {repr(self.board.get_active_move())}")
		print(f"Gambit playing as: {repr(self.board.get_gambit_colour())}")

	def __command_move(self, data: str) -> None:
		_log.info(f"Applying manual move(s): {data}")
		self.board.apply_manual_moves(data)
		# Send the updated board state to the viewer if we're using the viewer
		if self.viewer:
			fen = self.board.to_partial_fen()
			self.client.send(fen)
		# Set Gambit as the active player before solving
		self.board.set_gambit_as_player()
		try:
			if self.config.search_target_time is not None:
				move, _ = self.board.solve(
					self.config.search_depth, self.config.search_target_time, self.config.search_max_time
				)
			else:
				move, _ = self.board.solve(self.config.search_depth)
		except CheckmateException:
			_log.info("Gambit is in Checkmate!")
			return

		if self.viewer:
			# If we are using the viewer, we don't need to send
			# anything to the movement bridge.
			# Start by applying the move
			self.board.apply_move(move)
			# Then send the board state to the viewer
			fen = self.board.to_partial_fen()
			_log.info(f"Selected move: {move}")
			_log.info(f"Sending board to viewer: {fen}")
			self.client.send(fen)
		else:
			# Get the move command to send to the movement bridge
			moveCommand = self.board.get_move_command(move)
			# Apply the move to the board
			self.board.apply_move(move)
			_log.info(f"Selected move: {move}")
			_log.debug(f"Sending move command: {moveCommand}")
			self.client.send(moveCommand)

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


def run_server(configfile: str, viewer: int | None = None) -> None:
	"""Runs the Gambit solver IPC server"""
	_log.info("Running Gambit Solver server")
	config = GambitConfig(configfile)
	server = GambitServer(config, viewer)
	server.run()
