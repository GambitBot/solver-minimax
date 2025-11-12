"""Chess board classes"""

import numpy as np

from .piece import ChessPiece, PieceColour, PieceType

DEFAULT_PIECETYPE_WEIGHTS = {
	PieceType.KING: 100000,
	PieceType.QUEEN: 500,
	PieceType.ROOK: 300,
	PieceType.BISHOP: 200,
	PieceType.KNIGHT: 200,
	PieceType.PAWN: 100,
}


def idx_to_square(idx: int) -> str:
	"""Converts a board index into a readable square representation.

	Parameters
	----------
	idx : int
		Board index.

	Returns
	-------
	str
		String representation of square
	"""
	rank, file = idx_to_rank(idx)
	return f"{chr(97 + file)}{8 - rank}"


def idx_to_rank(idx: int) -> tuple[int, int]:
	"""Converts a board index into a rank and file.

	Parameters
	----------
	idx : int
		Board index

	Returns
	-------
	tuple[int, int]
		Square rank and file
	"""
	return (idx // 8, idx % 8)


def idx_on_board(idx: int) -> bool:
	"""Determines if an index is valid for a board position.

	Parameters
	----------
	idx : int
		Board index

	Returns
	-------
	bool
		Index is valid
	"""
	return idx >= 0 and idx < 64


class ChessMove:
	"""Representation of a chess move."""

	piece: np.uint8
	idx_from: int
	idx_to: int
	promotion: PieceType | None
	capture: int | None
	enpassant: bool

	def __init__(
		self,
		piece: np.uint8,
		idx_from: int,
		idx_to: int,
		*,
		promotion: PieceType | None = None,
		capture: int | None = None,
		enpassant: bool = False,
	):
		"""Initializes a move"""
		self.piece = piece
		self.idx_from = idx_from
		self.idx_to = idx_to
		self.promotion = promotion
		self.capture = capture
		self.enpassant = enpassant

	def __str__(self) -> str:
		"""Return a string representation of a move."""
		s = f"Piece: {ChessPiece.to_string(self.piece)} | Move: {idx_to_square(self.idx_from)}{idx_to_square(self.idx_to)}"
		if self.capture is not None:
			s += " Capture"
		if self.enpassant:
			s += " en-passant"
		if self.promotion is not None:
			s += f" | Promotion: {ChessPiece.to_string(np.uint8(self.promotion))}"
		return s


class Board:
	"""Representation of a chess board."""

	# Which player is moving next
	__active_move: PieceColour
	# Total number of moves in the game
	__move_count: int
	# Number of moves since last pawn move or piece capture
	__halfmove_clock: int
	# Index of en-passant square (if present)
	__enpassant: int | None
	# Board data array
	__board: np.ndarray[tuple[int], np.dtype[np.uint8]]
	# Weights for individual pieces
	__piecetype_weights: dict[PieceType, int]
	# Board direction.
	# False if viewed from white, true if viewed from black.
	__reversed: bool
	# If the board is currently "initialized", or if it is reset
	__initialized: bool

	def __init__(self):
		"""Initializes an empty chess board."""
		# Initialize a blank board using the 0x88 board format
		self.__board = np.zeros(128, dtype=np.uint8)
		# Set default values for the move counts and enpassant
		self.__move_count = 0
		self.__halfmove_clock = 0
		self.__enpassant = None
		# Initialize the default piece type weights
		self.__piecetype_weights = DEFAULT_PIECETYPE_WEIGHTS.copy()
		# Set the default board orientation
		self.__reversed = False
		# Default the board into the reset state
		self.__initialized = False

	def __str__(self) -> str:
		"""Returns a string representation of the board state"""
		s = " |abcdefgh\n-+--------"
		# Ranks count down from the top of the board
		for rank in reversed(range(0, 8)):
			# Put a row header for each rank
			s += f"\n{rank + 1}|"
			for file in range(0, 8):
				idx = Board.idx_from_rank_and_file(rank, file)
				# If the index is the en-passant square, place an asterisk
				if idx == self.__enpassant:
					s += "*"
				# If the index holds a chess piece, use its FEN string representation
				elif ChessPiece.is_piece(self.__board[idx]):
					s += ChessPiece.to_FEN(self.__board[idx])
				# Otherwise, use an empty space
				else:
					s += " "
		return s

	def reset(self) -> None:
		"""Resets the board to an initial state."""
		self.__board[:] = 0
		self.__move_count = 0
		self.__halfmove_clock = 0
		self.__enpassant = None
		self.__reversed = False
		self.__initialized = False

	def load_fen_string(self, fen: str) -> None:
		"""Loads an FEN string onto the board.

		Parameters
		----------
		fen : str
			Input FEN string to load.

		Raises
		------
		ValueError
			Invalid FEN string provided
		"""
		# Loading an FEN string necessitates clearing the existing board state
		self.__board[:] = 0
		# Split the FEN string up into segments to facilitate parsing
		fen_segments: list[str] = fen.split(" ")
		# These do not exactly match with the real ranks and files used
		# on a chess board, but they work better for computer calcualtion
		rank = 7
		file = 0
		# Iterate over the beginning of the FEN string to fill the board
		for char in fen_segments[0]:
			# If the character is a slash, move to the next rank
			if char == "/":
				# If the file was not already at the end of the rank, throw an error
				if file < 8:
					raise ValueError(f"Error parsing FEN string. Missing squares for rank {rank + 1}.")
				# Reset the file, and decrement the rank
				rank -= 1
				file = 0
				continue
			# If the character is a number, move the file over by that value
			elif char.isnumeric():
				file += int(char)
				if file > 8:
					raise ValueError(f"Error parsing FEN string. Rank {rank + 1} contains too many squares.")
				continue
			# Character is a letter, which indicates a piece
			else:
				# Add the piece to the board
				self.__board[Board.idx_from_rank_and_file(rank, file)] = ChessPiece.from_FEN(char)
				# Increment the file by one
				file += 1

		# If we only had a partial FEN string, end here
		# TODO: update move counts and en-passant status from this
		if len(fen_segments) == 1:
			return

		if len(fen_segments) != 6:
			raise ValueError(f"Provided FEN string has {len(fen_segments)} segments, expected 6 segments.")

		# By this point we know that we have an FEN string with a correct length.

		# Determine the active move
		self.__active_move = PieceColour.WHITE if fen_segments[1].casefold() == "w" else PieceColour.BLACK

		# TODO: Implement castling checks

		# Pending en-passant status
		if fen_segments[3] != "-":
			self.__enpassant = Board.idx_from_square(fen_segments[3])

		# Halfmove clock and total moves
		self.__halfmove_clock = int(fen_segments[4])
		self.__move_count = int(fen_segments[5])

	def get_state_value(self, player: PieceColour | None = None) -> int:
		"""Return the value of the current board state for the current move.

		Parameters
		----------
		player : PieceColour (optional)
			Player to evaluate weight for.
			Defaults to player that moves next.

		Returns
		-------
		int
			Relative weight of the current board state.
		"""
		# Use the active player if not otherwise specified
		if player is None:
			player = self.__active_move
		# Initialize the weight to zero
		w = 0
		# Iterate through all of the pieces on the board
		for rank in range(8):
			for file in range(8):
				idx = Board.idx_from_rank_and_file(rank, file)
				# Only proceed if a piece exists in this space
				if ChessPiece.is_piece(self.__board[idx]):
					piece_colour, piece_type = ChessPiece.decode_piece(self.__board[idx])
					# If the piece matches the player with the active move,
					# increase the weight
					if piece_colour == player:
						w += self.__piecetype_weights[piece_type]
					else:
						# Otherwise, decrease the weight
						w -= self.__piecetype_weights[piece_type]
		return w

	def get_moves(self) -> list[ChessMove]:
		"""Returns possible moves by the active player.

		Returns
		-------
		list[ChessMove]
			List of potential chess moves.
		"""
		moves = []
		# For pawns, forward is different depending on which player is moving
		# In the default board orientation, white pawns move upwards in indices
		if (self.__active_move == PieceColour.WHITE) == (not self.__reversed):
			pawn_direction = 1
		else:
			pawn_direction = -1

		# Get the indices of chess pieces that belong to the active player
		piece_indices = np.flatnonzero(np.bitwise_and(self.__board, self.__active_move))

		# Iterate over the player's pieces
		for i in piece_indices:
			i: int
			piece_num = self.__board[i]
			_, piece_type = ChessPiece.decode_piece(piece_num)
			match piece_type:
				case PieceType.PAWN:
					# Pawns have special move handling since it's very conditional
					# Exact rank only matters to pawns when moving
					rank, file = Board.idx_to_rank_and_file(i)
					# Check a direct move forward
					new_idx = i + (16 * pawn_direction)
					if Board.idx_on_board(new_idx):
						# If the square ahead of the pawn is empty, add the move
						if not ChessPiece.is_piece(self.__board[new_idx]):
							# If the pawn has reached the other side of the board
							# add promotions to queen and knight since those are
							# the only two that matter.
							if (pawn_direction == 1 and rank == 7) or (pawn_direction == -1 and rank == 0):
								moves.append(ChessMove(piece_num, i, new_idx, promotion=PieceType.QUEEN))
								moves.append(ChessMove(piece_num, i, new_idx, promotion=PieceType.KNIGHT))
							else:
								moves.append(ChessMove(piece_num, i, new_idx))

					# If the pawn is in its starting row, it can move twice
					if (pawn_direction == 1 and rank == 1) or (pawn_direction == -1 and rank == 6):
						new_idx = i + (32 * pawn_direction)
						if not ChessPiece.is_piece(self.__board[new_idx]):
							moves.append(ChessMove(piece_num, i, new_idx))
					# Check for captures or en-passant
					for m in (15, 17):
						new_idx = i + (m * pawn_direction)
						# New index must be on the board
						if Board.idx_on_board(new_idx):
							if (
								# A piece must be present on the target square
								ChessPiece.is_piece(self.__board[new_idx])
								# The piece must be an opponent's piece
								and (ChessPiece.decode_piece(self.__board[new_idx])[0] != self.__active_move)
							):
								moves.append(ChessMove(piece_num, i, new_idx, capture=new_idx))

							elif new_idx == self.__enpassant:
								# If the target is the en-passant square, it's always a valid move
								moves.append(
									ChessMove(
										piece_num,
										i,
										new_idx,
										capture=new_idx + (-16 * pawn_direction),
										enpassant=True,
									)
								)

				case PieceType.ROOK:
					pass  # TODO
				case PieceType.KNIGHT:
					pass  # TODO
				case PieceType.BISHOP:
					pass  # TODO
				case PieceType.QUEEN:
					pass  # TODO
				case PieceType.KING:
					pass  # TODO

		return moves

	@staticmethod
	def idx_from_rank_and_file(rank: int, file: int) -> int:
		"""Converts a chess board rank and file to an array index for 0x88 indexing.

		Parameters
		----------
		rank : int
			Chess board rank from 0-7
		file : int
			Chess board file as number from 0-7

		Returns
		-------
		int
			0x88-format array index
		"""
		return (rank << 4) + file

	@staticmethod
	def idx_from_square(square: str) -> int:
		"""Converts a chess board square to an array index for 0x88 indexing.

		Parameters
		----------
		square : str
			Chess board square in file-rank representation (e.g. a3, b4, etc.)

		Returns
		-------
		int
			0x88-format array index

		Raises
		------
		ValueError
			Invalid chess square provided
		"""
		if (len(square) != 2) or not square[1].isnumeric():
			raise ValueError(f"Invalid chess square {square}")

		idx = ((int(square[1]) - 1) << 4) + (ord(square[0].casefold()) - 97)
		if (idx < 0) or (idx > 127) or (idx & 0x88):
			raise ValueError(f"Invalid chess square {square}")

		return idx

	@staticmethod
	def idx_on_board(idx: int) -> bool:
		"""Checks if a board index is on the real chess board.

		Parameters
		----------
		idx : int
			0x88-format board index.

		Returns
		-------
		bool
			If the index is on the real chess board.
		"""
		return not (idx & 0x88)

	@staticmethod
	def idx_to_rank_and_file(idx: int) -> tuple[int, int]:
		"""Converts a 0x88 board index into a rank and file.

		Parameters
		----------
		idx : int
			0x88 board index

		Returns
		-------
		tuple[int, int]
			Rank and file of the board square
		"""
		return (idx >> 4, idx & 0x0F)
