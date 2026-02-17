"""Chess board classes"""

from collections.abc import Iterable

import numpy as np

from .piece import ChessPiece, PieceColour, PieceType

INF = 10**9
DEFAULT_PIECETYPE_WEIGHTS = {
	PieceType.KING: 100000,
	PieceType.QUEEN: 900,
	PieceType.ROOK: 500,
	PieceType.BISHOP: 300,
	PieceType.KNIGHT: 300,
	PieceType.PAWN: 100,
}


class ChessMove:
	"""Representation of a chess move."""

	piece: np.uint8
	idx_from: int
	idx_to: int
	promotion: PieceType | None
	capture: int | None
	enpassant: bool
	score: float

	def __init__(
		self,
		piece: np.uint8,
		idx_from: int,
		idx_to: int,
		*,
		promotion: PieceType | None = None,
		capture: int | None = None,
		enpassant: bool = False,
		score: float = -float("inf"),
	):
		"""Initializes a move"""
		self.piece = piece
		self.idx_from = idx_from
		self.idx_to = idx_to
		self.promotion = promotion
		self.capture = capture
		self.enpassant = enpassant
		self.score = score

	def __str__(self) -> str:
		"""Return a string representation of a move."""
		s = f"Piece: {ChessPiece.to_string(self.piece)} | Move: {Board.idx_to_square(self.idx_from)}{Board.idx_to_square(self.idx_to)}"
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
					s += "."
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

	def __move_linear(self, idx: int, directions: Iterable[int]) -> list[ChessMove]:
		"""Generates moves for repeatable linear motion (rooks, bishops, queens)

		Parameters
		----------
		idx : int
			Piece starting index
		directions : list[int]
			Index directions to move

		Returns
		-------
		list[ChessMove]
			Possible chess moves
		"""
		moves = []
		piece_num = self.__board[idx]
		for m in directions:  # Corresponds to North, East, South, West, respectively
			new_idx = idx + m
			while Board.idx_on_board(new_idx):
				# Check if the new index contains a piece
				if ChessPiece.is_piece(self.__board[new_idx]):
					# If the index contains a piece, check if it's an opponent piece
					if ChessPiece.decode_piece(self.__board[new_idx])[0] != self.__active_move:
						# Opponent piece detected. Add a move to capture it.
						moves.append(ChessMove(piece_num, idx, new_idx, capture=new_idx))
					# Regardless of if the piece could be captured or not, stop the loop
					break
				# If the space was blank, add a move to move there
				moves.append(ChessMove(piece_num, idx, new_idx))
				new_idx += m
		return moves

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
					# Rooks can move any cardinal direction
					moves += self.__move_linear(i, (16, 1, -16, -1))

				case PieceType.KNIGHT:
					# Knights can only move to specific nearby squares
					for m in (33, 18, -14, -31, -33, -18, 14, 31):
						new_idx = i + m
						if Board.idx_on_board(new_idx):
							if (
								# Target square is a chess piece
								ChessPiece.is_piece(self.__board[new_idx])
								# Target piece is not friendly
								and (ChessPiece.decode_piece(self.__board[new_idx])[0] != self.__active_move)
							):
								# Target square contains an enemy piece that can be captured
								moves.append(ChessMove(piece_num, i, new_idx, capture=new_idx))
							elif not ChessPiece.is_piece(self.__board[new_idx]):
								# Target square is empty
								moves.append(ChessMove(piece_num, i, new_idx))
							# If the target square contains a friendly piece, nothing happens

				case PieceType.BISHOP:
					# Bishops can move diagonally
					moves += self.__move_linear(i, (15, 17, -15, -17))

				case PieceType.QUEEN:
					# Queens can move along cardinal directions, or diagonally
					moves += self.__move_linear(i, (15, 16, 17, 1, -15, -16, -17, -1))

				case PieceType.KING:
					# The king can move in any direction, but only by one tile at a time
					for m in (15, 16, 17, 1, -15, -16, -17, -1):
						new_idx = i + m
						if Board.idx_on_board(new_idx):
							# Check if the target contains an opposing piece
							if (
								ChessPiece.is_piece(self.__board[new_idx])
								and ChessPiece.decode_piece(self.__board[new_idx])[0] != self.__active_move
							):
								moves.append(ChessMove(piece_num, i, new_idx, capture=new_idx))
							elif not ChessPiece.is_piece(self.__board[new_idx]):
								moves.append(ChessMove(piece_num, i, new_idx))

					# TODO: Allow castling

		return moves

	def with_move(self, move: ChessMove) -> "Board":
		"""Returns a new instance of the board with a given chess move applied.

		Parameters
		----------
		move : ChessMove
			Chess move to apply.

		Returns
		-------
		Board
			New board with chess move applied.
		"""
		# Initialize a new board
		new_board = Board()
		# Copy the existing board state to start
		new_board.__board = self.__board.copy()
		# Swap the active move
		if self.__active_move == PieceColour.WHITE:
			new_board.__active_move = PieceColour.BLACK
		else:
			new_board.__active_move = PieceColour.WHITE

		# Increment the move count
		new_board.__move_count = self.__move_count + 1

		# If a pawn was moved, or a piece was captured, reset the halfmove clock.
		if ChessPiece.decode_piece(move.piece)[1] == PieceType.PAWN or move.capture is not None:
			new_board.__halfmove_clock = 0
		else:
			# Otherwise, incremenet the clock by one.
			new_board.__halfmove_clock = self.__halfmove_clock + 1

		# Copy the reversed and initialized states of the board
		new_board.__reversed = self.__reversed
		new_board.__initialized = self.__initialized

		# Apply the move
		if move.capture is not None:
			# If the move is capturing a piece, set the capture index to 0
			new_board.__board[move.capture] = 0

		# Move the piece to its new location
		new_board.__board[move.idx_to] = move.piece
		new_board.__board[move.idx_from] = 0

		# If the piece was a pawn that moved two squares, set the new enpassant index
		if ChessPiece.decode_piece(move.piece)[1] == PieceType.PAWN and abs(move.idx_to - move.idx_from) > 20:
			# This will set the enpassant index to the halfway point between the two squares, which
			# will correspond to the square that the pawn jumped over.
			new_board.__enpassant = move.idx_from + ((move.idx_to - move.idx_from) // 2)
		else:
			new_board.__enpassant = None

		return new_board

	def solve(self, target_depth: int) -> ChessMove:
		"""Calculates an optimal chess move to make.

		Searches a specific depth in a move tree.

		Parameters
		----------
		target_depth : int
			Target depth to search to.

		Returns
		-------
		ChessMove
			Optimal chess move
		"""
		# Generate a list of moves that we could make
		move_list = self.get_moves()

		best_move = move_list[0]

		# For each move, recursively solve for the worst possible outcome, up to the target depth
		for depth in range(1, target_depth + 1):
			best_score = -INF
			best_idx = 0
			alpha = -INF
			for i, m in enumerate(move_list):
				score = self.with_move(m).__solve_recurse(self.__active_move, depth, -INF, -alpha)
				if score > best_score:
					best_score = score
				if score > alpha:
					alpha = score
					best_move = m
					best_idx = i
			move_list[0], move_list[best_idx] = (move_list[best_idx], move_list[0])

		return best_move

	def __solve_recurse(
		self,
		player: PieceColour,
		depth: int,
		alpha: int,
		beta: int,
	) -> int:
		# Disable null move pruning if there are few pieces left
		if not self.is_endgame():
			# Null move pruning
			if depth >= 4 and not self.is_in_check():
				null_score = -self.__solve_recurse(
					player,
					depth - 1 - 2,  # Reduce depth more aggressively
					-beta,
					-beta + 1,
				)
				if null_score >= beta:
					return beta

		# Base case: leaf node
		if depth == 0:
			return self.get_state_value(player)

		best = -INF

		for move in self.get_moves():
			child = self.with_move(move)
			score = -child.__solve_recurse(
				player,
				depth - 1,
				-beta,
				-alpha,
			)

			if score > best:
				best = score

			if score > alpha:
				alpha = score

			if alpha >= beta:
				break  # beta cutoff

		return best

	def is_in_check(self) -> bool:
		"""Check if the current player is in check."""
		# Find king position
		king_idx = None
		for idx in range(128):
			if ChessPiece.is_piece(self.__board[idx]):
				piece_colour, piece_type = ChessPiece.decode_piece(self.__board[idx])
				if piece_type == PieceType.KING and piece_colour == self.__active_move:
					king_idx = idx
					break

		if king_idx is None:
			return False

		# Check if any opponent piece can capture the king
		opponent_colour = PieceColour.BLACK if self.__active_move == PieceColour.WHITE else PieceColour.WHITE
		for idx in range(128):
			if ChessPiece.is_piece(self.__board[idx]):
				piece_colour, piece_type = ChessPiece.decode_piece(self.__board[idx])
				if piece_colour == opponent_colour and self.is_attacking(king_idx, idx, piece_type):
					return True

		return False

	def is_attacking(self, king_idx: int, attacker_idx: int, attacker_type: PieceType) -> bool:
		"""Check if a piece at attacker_idx can attack king at king_idx."""
		# Simplified attack detection
		dx = abs(king_idx - attacker_idx)
		dy = abs((king_idx >> 4) - (attacker_idx >> 4))
		dx %= 16
		dy %= 8

		match attacker_type:
			case PieceType.PAWN:
				# Pawn attacks diagonally
				return dx == 1 and dy == 1
			case PieceType.KNIGHT:
				# Knight moves in L-ish-shape
				return (dx == 2 and dy == 1) or (dx == 1 and dy == 2)
			case PieceType.BISHOP:
				# Bishop moves diagonally
				return dx == dy
			case PieceType.ROOK:
				# Rook moves orthogonally
				return dx == 0 or dy == 0
			case PieceType.QUEEN:
				# Queen moves like rook or bishop
				return dx == dy or dx == 0 or dy == 0
			case PieceType.KING:
				# King moves one square in any direction
				return dx <= 1 and dy <= 1
		return False

	def is_endgame(self) -> bool:
		"""Check if the game is in an endgame phase (few pieces left)."""
		piece_count = 0
		for idx in range(128):
			if ChessPiece.is_piece(self.__board[idx]):
				piece_count += 1
				# Early exit if we already have counted enough pieces
				if (
					piece_count >= 10
				):  # This is arbitrary but reasonable to still maintain speed but still play a good endgame
					return False
		return True

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

	@staticmethod
	def idx_to_square(idx: int) -> str:
		"""Converts a 0x88 board index into chess square notation.

		Parameters
		----------
		idx : int
			0x88 board index

		Returns
		-------
		str
			Chess square string
		"""
		rank, file = Board.idx_to_rank_and_file(idx)
		return f"{chr(97 + file)}{rank + 1}"
