"""Chess board classes"""

import logging
import time
from collections.abc import Iterable
from enum import IntEnum

import numpy as np

from .boardmaps import (
	BOARD_MAPS_BLACK,
	BOARD_MAPS_WHITE,
	CENTRE_MANHATTAN_DISTANCE_MAP,
	ENDGAME_MAPS_BLACK,
	ENDGAME_MAPS_WHITE,
	ORTHOGONAL_DISTANCE_MAP,
)
from .exceptions import CheckmateException, NoKingException, StalemateException
from .piece import ChessPiece, PieceColour, PieceType
from .utils import invert_stockfish_move

INF = 10**9
DEFAULT_PIECETYPE_WEIGHTS = {
	PieceType.KING: 100000,
	PieceType.QUEEN: 900,
	PieceType.ROOK: 500,
	PieceType.BISHOP: 300,
	PieceType.KNIGHT: 300,
	PieceType.PAWN: 100,
}

ENDGAME_PCT_WEIGHTS = {
	PieceType.KING: 0,
	PieceType.QUEEN: 45,
	PieceType.ROOK: 20,
	PieceType.BISHOP: 10,
	PieceType.KNIGHT: 10,
	PieceType.PAWN: 0,
}

# Define the starting endgame weight as a player having all of their
# knights, bishops, rooks, and their queen
ENDGAME_START_WEIGHT = (
	ENDGAME_PCT_WEIGHTS[PieceType.QUEEN]
	+ (2 * ENDGAME_PCT_WEIGHTS[PieceType.ROOK])
	+ (2 * ENDGAME_PCT_WEIGHTS[PieceType.KNIGHT])
	+ (2 * ENDGAME_PCT_WEIGHTS[PieceType.BISHOP])
)


_log = logging.getLogger(__name__)
_rng = np.random.default_rng()


class ChessMove:
	"""Representation of a chess move."""

	piece: np.uint8
	idx_from: int
	idx_to: int
	promotion: PieceType | None
	capture: int | None
	enpassant: bool
	castle: int | None
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
		castle: int | None = None,
		score: float = -float("inf"),
	):
		"""Initializes a move"""
		self.piece = piece
		self.idx_from = idx_from
		self.idx_to = idx_to
		self.promotion = promotion
		self.capture = capture
		self.enpassant = enpassant
		self.castle = castle
		self.score = score

	def __str__(self) -> str:
		"""Return a string representation of a move."""
		s = f"Piece: {ChessPiece.to_string(self.piece)} | Move: {Board.idx_to_square(self.idx_from)}{Board.idx_to_square(self.idx_to)}"
		if self.capture is not None:
			s += " Capture"
		if self.enpassant:
			s += " en-passant"
		if self.castle is not None:
			s += f" Castle with {Board.idx_to_square(self.castle)}"
		if self.promotion is not None:
			s += f" | Promotion: {ChessPiece.to_string(np.uint8(self.promotion))}"
		return s

	def __repr__(self) -> str:
		"""Return a string representation of a move."""
		return f"{ChessPiece.to_string(self.piece)} {Board.idx_to_square(self.idx_from)}{Board.idx_to_square(self.idx_to)}"


class Difficulty(IntEnum):
	"""Solver difficulty settings"""

	EASY = 1
	MEDIUM = 2
	HARD = 3


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
	# Difficulty setting.
	__difficulty: Difficulty
	# If the board is currently "initialized", or if it is reset
	__initialized: bool
	# Valid castling indices
	__castle_white: list[int]
	__castle_black: list[int]

	def __init__(self):
		"""Initializes an empty chess board."""
		# Initialize a blank board using the 0x88 board format
		self.__board = np.zeros(128, dtype=np.uint8)
		# Initialize the active move as none
		self.__active_move = PieceColour.NONE
		# Set default values for the move counts and enpassant
		self.__move_count = 0
		self.__halfmove_clock = 0
		self.__enpassant = None
		# Initialize the default piece type weights
		self.__piecetype_weights = DEFAULT_PIECETYPE_WEIGHTS.copy()
		# Set the default board orientation
		self.__reversed = False
		# Set up the castling lists
		self.__castle_white = []
		self.__castle_black = []
		# Set the difficulty to hard
		self.__difficulty = Difficulty.HARD
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
		self.__active_move = PieceColour.NONE
		self.__move_count = 0
		self.__halfmove_clock = 0
		self.__enpassant = None
		self.__reversed = False
		self.__castle_white = []
		self.__castle_black = []
		self.__initialized = False

	def set_difficulty(self, difficulty: Difficulty | int) -> None:
		"""Sets the difficulty of the solver.

		Parameters
		----------
		difficulty : Difficulty | int
			Difficulty to set
		"""
		if isinstance(difficulty, int):
			try:
				difficulty = Difficulty(difficulty)
			except ValueError:
				difficulty = Difficulty.HARD

		self.__difficulty = difficulty

	def load_fen_string(self, fen: str, set_player: bool = False) -> None:
		"""Loads an FEN string onto the board.

		Parameters
		----------
		fen : str
			Input FEN string to load.
		set_player: bool (optional)
			Sets gambit as the active player

		Raises
		------
		ValueError
			Invalid FEN string provided
		"""
		# Loading an FEN string necessitates clearing the existing board state
		self.__board[:] = 0
		# Split the FEN string up into segments to facilitate parsing
		fen_segments: list[str] = fen.split(" ")

		# Parse the FEN board state
		self.__parse_fen_board_state(fen_segments[0], self.__board)

		# If we only had a partial FEN string, end here
		# TODO: update move counts and en-passant status from this
		if len(fen_segments) == 1:
			return

		if len(fen_segments) != 6:
			raise ValueError(f"Provided FEN string has {len(fen_segments)} segments, expected 6 segments.")

		# By this point we know that we have an FEN string with a correct length.

		# Determine the active move
		self.__active_move = PieceColour.WHITE if fen_segments[1].casefold() == "w" else PieceColour.BLACK

		# Set board direction (if specified)
		if set_player:
			self.__reversed = True if self.__active_move == PieceColour.BLACK else False

		# Check for castling status
		self.__castle_white.clear()
		self.__castle_black.clear()
		if fen_segments[2] != "-":
			# Check the first letter to see which if standard FEN or Shredder-FEN is in use.
			if fen_segments[2][0] >= "K":
				# Standard FEN is in use
				for i in fen_segments[2]:
					# Uppercase letters represent white pieces
					if i == "K":
						# King-side castling for white is on the right
						self.__castle_white.append(0x07 if not self.__reversed else 0x70)
					elif i == "Q":
						# Queen-side castling for white is on the left
						self.__castle_white.append(0x00 if not self.__reversed else 0x77)
					if i == "k":
						# King-side castling for black is on the left
						self.__castle_black.append(0x77 if not self.__reversed else 0x00)
					elif i == "q":
						# Queen-side castling for black is on the right
						self.__castle_black.append(0x70 if not self.__reversed else 0x07)
			else:
				# Shredder-FEN is in use
				# Castling is represented as alphabetical columns for each player
				for i in fen_segments[2]:
					if i.isupper():
						# Uppercase letters represent white pieces
						idx_base = -65 if not self.__reversed else 47
						self.__castle_white.append(ord(i) + idx_base)
					else:
						idx_base = 15 if not self.__reversed else -97
						self.__castle_black.append(ord(i) + idx_base)

		# Pending en-passant status
		if fen_segments[3] != "-":
			self.__enpassant = Board.idx_from_square(fen_segments[3])

		# Halfmove clock and total moves
		self.__halfmove_clock = int(fen_segments[4])
		self.__move_count = int(fen_segments[5])

		# Set the board as initialized
		self.__initialized = True

	def to_fen(self) -> str:
		"""Returns the piece locations as a partial FEN string

		Returns
		-------
		str
			Partial FEN string representing the current piece locations
		"""
		# Get current piece locations
		# Ranks count down from the top of the board
		fen_parts: list[str] = []
		fen_parts.append("")
		empty_count = 0
		for rank in reversed(range(0, 8)):
			for file in range(0, 8):
				idx = Board.idx_from_rank_and_file(rank, file)
				# If the index is not a piece, ignore it
				if not ChessPiece.is_piece(self.__board[idx]):
					# Increment the empty count by 1
					empty_count += 1
					continue
				# We have a valid piece by this point
				if empty_count > 0:
					fen_parts[0] += str(empty_count)
					empty_count = 0
				fen_parts[0] += ChessPiece.to_FEN(self.__board[idx])

			# We have reached the end of the rank
			# If the empty count is not zero, write it to the board string
			if empty_count > 0:
				fen_parts[0] += str(empty_count)
			# Reset the empty space count
			empty_count = 0
			# If it is not the last rank, add a forward slash as a separator
			if rank != 0:
				fen_parts[0] += "/"

		# Add next to move
		if self.__active_move == PieceColour.WHITE:
			fen_parts.append("w")
		else:
			fen_parts.append("b")

		# Casting info
		if len(self.__castle_white) == 0 and len(self.__castle_black) == 0:
			# No castling
			fen_parts.append("-")
		else:
			fen_parts.append("")
			for c in self.__castle_white:
				fen_parts[2] += Board.idx_to_square(c)[0].upper()
			for c in self.__castle_black:
				fen_parts[2] += Board.idx_to_square(c)[0].lower()

		# En passant
		if self.__enpassant is not None:
			fen_parts.append(Board.idx_to_square(self.__enpassant))
		else:
			fen_parts.append("-")

		# Halfmove clock
		fen_parts.append(str(self.__halfmove_clock))

		# Full move count
		fen_parts.append(str(self.__move_count))

		return (" ").join(fen_parts)

	def update_board(self, boardstate: str) -> None:
		"""Parses the piece location part of the FEN string.
		Applies updates to the board state accordingly.

		Parameters
		----------
		boardstate : str
			Partial board-state component of an FEN string
		"""

		if self.__initialized:
			_log.info(f"Updating board state using partial FEN: {boardstate}")
			# If the board is initialized, we need to compare the board new
			# board state to the previous board state to detect changes to
			# castling requirements, halfmove clock, etc.
			tempboard = np.zeros(128, dtype=np.uint8)
			# Parse the partial board state to the temporary board
			self.__parse_fen_board_state(boardstate, tempboard)
			# If the number of pieces on the board has changed, we need to reset
			# the halfmove clock
			if np.count_nonzero(self.__board) != np.count_nonzero(tempboard):
				self.__halfmove_clock = 0
			else:
				# Otherwise, increase the halfmove clock by 1
				self.__halfmove_clock += 1
			# Applying an update to the board means that it should now be Gambit's
			# turn to make a move.
			if self.__reversed:
				self.__active_move = PieceColour.BLACK
			else:
				# When black makes a move, the total move counter is increased
				self.__move_count += 1
				self.__active_move = PieceColour.WHITE

			# Check for differences between the two boards
			board_diff = np.logical_not(self.__board == tempboard)
			board_diff_idx: np.ndarray[tuple[int], np.dtype[np.int64]] = np.flatnonzero(board_diff)
			# Clear the en-passant index for now.
			self.__enpassant = None
			# Check the conditions for en-passant. We must meet the following conditions:
			#     - There must be exactly two difference indices (pawn moved from one location to another)
			#     - The two indices must be exactly 32 apart to account for moving two rows forward
			#     - On the old board, one index must contain a pawn, and the other must be empty.
			if len(board_diff_idx == 2) and abs(board_diff_idx[0] - board_diff_idx[1]) == 32:
				_, pieceType1 = ChessPiece.decode_piece(self.__board[board_diff_idx[0]])  # type: ignore
				_, pieceType2 = ChessPiece.decode_piece(self.__board[board_diff_idx[1]])  # type: ignore
				if (pieceType1 == PieceType.PAWN and pieceType2 == PieceType.NONE) or (
					pieceType1 == PieceType.NONE and pieceType2 == PieceType.PAWN
				):
					# En-Passant detected. Set the En-Passant index to the gap between the two indices
					self.__enpassant = int(board_diff_idx[0] + ((board_diff_idx[1] - board_diff_idx[0]) / 2))

			# Check for moves that would violate castling validity
			for i in board_diff_idx:
				i = int(i)
				pieceColour, pieceType = ChessPiece.decode_piece(self.__board[i])
				# If one of the moved pieces was a king, clear all castling options
				if pieceType == PieceType.KING:
					if pieceColour == PieceColour.WHITE:
						self.__castle_white.clear()
					else:
						self.__castle_black.clear()
				# If one of the moved pieces was a rook, clear that castling index if present
				elif pieceType == PieceType.ROOK:
					if (pieceColour == PieceColour.WHITE) and (i in self.__castle_white):
						self.__castle_white.remove(i)
					elif (pieceColour == PieceColour.BLACK) and (i in self.__castle_black):
						self.__castle_black.remove(i)

			# Assign the new board state to the board
			np.copyto(self.__board, tempboard)

		else:
			_log.info(f"Initializing board state using partial FEN: {boardstate}")
			# If the board is not initialized, we can just apply
			# the board state directly without doing any comparisons.
			self.__parse_fen_board_state(boardstate, self.__board)

			# White always moves first
			self.__active_move = PieceColour.WHITE

			# We now need to calculate which colour Gambit is playing as
			# For this, we will look at the rows closest to Gambit, and select
			# the colour of the first king that we find.
			for i in range(len(self.__board)):
				pieceColour, pieceType = ChessPiece.decode_piece(self.__board[i])
				# If we find a king
				if pieceType == PieceType.KING:
					if pieceColour == PieceColour.WHITE:
						# If we found the white king, the board is in normal orientation.
						_log.info("Detected Gambit playing as White")
						self.__reversed = False
					else:
						# If we found the black king, the board is in reverse orientation.
						_log.info("Detected Gambit playing as Black")
						self.__reversed = True
					break

			# Look for the rooks for each player to set up the castling indices
			# Rooks must start on the back row to be valid for castling
			for i in tuple(range(0x00, 0x08)) + tuple(range(0x70, 0x78)):
				pieceColour, pieceType = ChessPiece.decode_piece(self.__board[i])
				if pieceType == PieceType.ROOK:
					if pieceColour == PieceColour.WHITE:
						self.__castle_white.append(i)
					else:
						self.__castle_black.append(i)

			# Mark the board as initialized once we have completed setup.
			self.__initialized = True

	def __parse_fen_board_state(self, boardstate: str, board: np.ndarray[tuple[int], np.dtype[np.uint8]]) -> None:
		# We will always parse board states from the same point of view
		# of the board, regardless of which colour starts on each side.
		# These do not exactly match with the real ranks and files used
		# on a chess board, but they work better for computer calculation
		rank = 7
		file = 0

		# Iterate over the beginning of the FEN string to fill the board
		for char in boardstate:
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
				board[Board.idx_from_rank_and_file(rank, file)] = ChessPiece.from_FEN(char)
				# Increment the file by one
				file += 1

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
		piece_weight: int
		# Use the active player if not otherwise specified
		if player is None:
			player = self.__active_move
		# Initialize the weight to zero
		w = 0
		# Get the endgame percentage
		player_endgame_pct = self.get_endgame_pct(player)
		opponent_endgame_pct = self.get_endgame_pct(player.opponent())
		# Iterate through all of the pieces on the board
		for rank in range(8):
			for file in range(8):
				idx = Board.idx_from_rank_and_file(rank, file)
				# Only proceed if a piece exists in this space
				if ChessPiece.is_piece(self.__board[idx]):
					piece_colour, piece_type = ChessPiece.decode_piece(self.__board[idx])
					piece_weight = self.__piecetype_weights[piece_type]
					if (piece_colour == PieceColour.WHITE) == (not self.__reversed):
						board_map = BOARD_MAPS_WHITE[piece_type]
						endgame_map = ENDGAME_MAPS_WHITE[piece_type]
					else:
						board_map = BOARD_MAPS_BLACK[piece_type]
						endgame_map = ENDGAME_MAPS_BLACK[piece_type]

					if piece_colour == player:
						endgame_pct = player_endgame_pct
					else:
						endgame_pct = opponent_endgame_pct

					# Apply the map values based on the endgame percentage
					piece_weight += round(((1 - endgame_pct) * board_map[idx]) + (endgame_pct * endgame_map[idx]))

					# If the piece matches the player with the active move,
					# increase the weight
					if piece_colour == player:
						w += piece_weight
					else:
						# Otherwise, decrease the weight
						w -= piece_weight

		# If the score is already positive by at least 200 (two pawns worth), and the endgame
		# percentage is not zero, add additional score for pushing the player's king
		# close to the opposing King, and additional score for pushing the opposing king
		# to the corner of the board.
		# For performance reasons, these read from pre-computed lookup tables.
		if (w > 200) and player_endgame_pct > 0:
			player_king_idx = self.get_king_idx(player)
			enemy_king_idx = self.get_king_idx(player.opponent())
			# Score bonus for enemy king manhattan distance from board centre
			w += CENTRE_MANHATTAN_DISTANCE_MAP[enemy_king_idx] * 10
			# Score bonus for proximity between kings
			# 14 is the greatest score between opposite board corners
			w += (14 - ORTHOGONAL_DISTANCE_MAP[player_king_idx][enemy_king_idx]) * 4

		return w

	def __move_linear(self, idx: int, directions: Iterable[int], captures_only: bool = False) -> list[ChessMove]:
		"""Generates moves for repeatable linear motion (rooks, bishops, queens)

		Parameters
		----------
		idx : int
			Piece starting index
		directions : list[int]
			Index directions to move
		captures_only : bool, optional
			Only return captures, by default False

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
				if not captures_only:
					moves.append(ChessMove(piece_num, idx, new_idx))
				new_idx += m
		return moves

	def get_moves(self, captures_only: bool = False) -> list[ChessMove]:
		"""Returns possible moves by the active player.

		Parameters
		----------
		captures_only : bool, optional
			Only return captures, by default False

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
					# Only scan for regular moves if we're not only looking for captures
					if not captures_only:
						# Check a direct move forward
						new_idx = i + (16 * pawn_direction)
						if Board.idx_on_board(new_idx):
							# If the square ahead of the pawn is empty, add the move
							if not ChessPiece.is_piece(self.__board[new_idx]):
								# If the pawn has reached the other side of the board
								# add promotions to queen and knight since those are
								# the only two that matter.
								if (pawn_direction == 1 and rank == 6) or (pawn_direction == -1 and rank == 1):
									moves.append(ChessMove(piece_num, i, new_idx, promotion=PieceType.QUEEN))
									moves.append(ChessMove(piece_num, i, new_idx, promotion=PieceType.KNIGHT))
								else:
									moves.append(ChessMove(piece_num, i, new_idx))

								# If the pawn is in its starting row, it can move twice
								# only if the single move is also valid
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
					moves += self.__move_linear(i, (16, 1, -16, -1), captures_only)

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
							elif not ChessPiece.is_piece(self.__board[new_idx]) and not captures_only:
								# Target square is empty
								moves.append(ChessMove(piece_num, i, new_idx))
							# If the target square contains a friendly piece, nothing happens

				case PieceType.BISHOP:
					# Bishops can move diagonally
					moves += self.__move_linear(i, (15, 17, -15, -17), captures_only)

				case PieceType.QUEEN:
					# Queens can move along cardinal directions, or diagonally
					moves += self.__move_linear(i, (15, 16, 17, 1, -15, -16, -17, -1), captures_only)

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
							elif not ChessPiece.is_piece(self.__board[new_idx]) and not captures_only:
								moves.append(ChessMove(piece_num, i, new_idx))

					# Check for castling validity
					if not captures_only:
						# Castling is only valid if the king is not in check (i.e. being threatened)
						attacker = PieceColour.BLACK if self.__active_move == PieceColour.WHITE else PieceColour.WHITE
						if not self.is_threatened(i, attacker):
							castle_indices = self.get_valid_castling_idx(self.__active_move)

							for c in castle_indices:
								# Initialize the target index at 1
								king_target_idx = 1
								if self.__reversed:
									# If White is the active player, add 70
									if self.__active_move == PieceColour.WHITE:
										king_target_idx += 70
								else:
									# If the board is not reversed, add 1
									king_target_idx += 1
									# If Black is the active player, add 70
									if self.__active_move == PieceColour.BLACK:
										king_target_idx += 71
								# If the target is a higher index than the King, add 4
								if c > i:
									king_target_idx += 4

								# Check that all squares between the king and rook are empty
								valid = True
								castle_check_indices = sorted((i, c))
								castle_check_range = tuple(range(castle_check_indices[0] + 1, castle_check_indices[1]))
								for j in castle_check_range:
									if ChessPiece.is_piece(self.__board[j]):
										valid = False
										break

								# If we found a piece between the king and rook, stop further checks
								if not valid:
									continue

								# Check that all squares that the king will past through are not threatened
								castle_check_indices = sorted((i, king_target_idx))
								castle_check_range = tuple(range(castle_check_indices[0], castle_check_indices[1] + 1))
								for j in castle_check_range:
									if j == i:
										# Don't check the King's current square a second time
										continue

									if self.is_threatened(j, attacker):
										valid = False
										break

								# If the king would be threatened, stop further checks
								if not valid:
									continue

								# If we reach this point, that means that castling is a valid move
								moves.append(ChessMove(piece_num, i, king_target_idx, castle=c))

		# Validate that new moves don't put us in check.
		# If we are currently in check, this also validates
		# that the new move takes us out of check.
		moves_filtered = []
		for m in moves:
			if not self.with_move(m).is_check(self.__active_move):
				moves_filtered.append(m)

		return moves_filtered

	def apply_move(self, move: ChessMove) -> None:
		"""Applies a move to the board.

		Parameters
		----------
		move : ChessMove
			Chess move to apply
		"""
		pieceColour, pieceType = ChessPiece.decode_piece(move.piece)
		# Increment the move count if black moved
		if pieceColour == PieceColour.BLACK:
			self.__move_count += 1

		# Swap the active move
		if self.__active_move == PieceColour.WHITE:
			self.__active_move = PieceColour.BLACK
		else:
			self.__active_move = PieceColour.WHITE

		# If a pawn was moved, or a piece was captured, reset the halfmove clock.
		if ChessPiece.decode_piece(move.piece)[1] == PieceType.PAWN or move.capture is not None:
			self.__halfmove_clock = 0
		else:
			# Otherwise, increment the clock by one.
			self.__halfmove_clock = self.__halfmove_clock + 1
		if move.capture is not None:
			# If the move is capturing a piece, set the capture index to 0
			self.__board[move.capture] = 0

		# If the moved piece was a king or rook, update castling flags
		if pieceType == PieceType.ROOK:
			if pieceColour == PieceColour.WHITE:
				if move.idx_from in self.__castle_white:
					self.__castle_white.remove(move.idx_from)
			else:
				if move.idx_from in self.__castle_black:
					self.__castle_black.remove(move.idx_from)

		elif pieceType == PieceType.KING:
			if pieceColour == PieceColour.WHITE:
				self.__castle_white.clear()
			else:
				self.__castle_black.clear()

		# Move the piece to its new location
		self.__board[move.idx_to] = move.piece
		self.__board[move.idx_from] = 0

		# If the move was a promotion, update the type of the new piece
		if move.promotion is not None:
			self.__board[move.idx_to] = move.promotion + pieceColour

		# If the move was a castling move, move the rook as well
		if move.castle is not None:
			if move.castle < move.idx_from:
				self.__board[move.idx_to + 1] = self.__board[move.castle]
				self.__board[move.castle] = 0
			else:
				self.__board[move.idx_to - 1] = self.__board[move.castle]
				self.__board[move.castle] = 0

		# If the piece was a pawn that moved two squares, set the new enpassant index
		if ChessPiece.decode_piece(move.piece)[1] == PieceType.PAWN and abs(move.idx_to - move.idx_from) > 20:
			# This will set the enpassant index to the halfway point between the two squares, which
			# will correspond to the square that the pawn jumped over.
			self.__enpassant = move.idx_from + ((move.idx_to - move.idx_from) // 2)
		else:
			self.__enpassant = None

	def apply_manual_moves(self, movestr: str) -> None:
		"""Applies manual chess moves to the board.

		Parameters
		----------
		movestr : str
			Comma-separated string of moves to execute.
		"""
		# Split up the move string
		moves = movestr.split(",")
		move_pieces = []

		# Start by getting the piece types at each source location
		# Handles edge cases for Chess960 (such as castling where
		# the king and rook swap places)
		for m in moves:
			start_idx = Board.idx_from_square(m[0:2])
			move_pieces.append(self.__board[start_idx])

		# Apply all of the moves
		for i, m in enumerate(moves):
			start_idx = Board.idx_from_square(m[0:2])
			end_idx = Board.idx_from_square(m[2:4])
			# Get the piece information
			piece_colour, piece_type = ChessPiece.decode_piece(move_pieces[i])
			# Handle piece-specific flags
			match piece_type:
				case PieceType.KING:
					# If the king moved two tiles, handle it as a castling operation
					if abs(end_idx - start_idx) == 1:
						castling_indices = self.get_valid_castling_idx(self.__active_move)
						rook_idx = None
						if end_idx > start_idx:
							# Search for castling indices above the king index
							for c in castling_indices:
								if c > start_idx:
									rook_idx = c
									break
						else:
							# Search for castling indices below the king index
							for c in castling_indices:
								if c < start_idx:
									rook_idx = c
									break

						if rook_idx is not None:
							# Place the rook on the tile next to the king's destination
							if end_idx > start_idx:
								self.__board[end_idx - 1] = self.__board[rook_idx]
							else:
								self.__board[end_idx + 1] = self.__board[rook_idx]
							self.__board[rook_idx] = 0

					# Clear castling options if kings move
					if piece_colour == PieceColour.WHITE:
						self.__castle_white.clear()
					else:
						self.__castle_black.clear()
				case PieceType.ROOK:
					# Remove the rook as a valid castling
					# option if it moves
					if piece_colour == PieceColour.WHITE:
						if start_idx in self.__castle_white:
							self.__castle_white.remove(start_idx)
					else:
						if start_idx in self.__castle_black:
							self.__castle_black.remove(start_idx)
				case PieceType.PAWN:
					# Set enpassant if the piece moved two squares
					if abs(end_idx - start_idx) > 20:
						self.__enpassant = start_idx + ((end_idx - start_idx) // 2)
					elif end_idx == self.__enpassant:
						# En passant capture
						if self.__active_move == PieceColour.WHITE:
							self.__board[end_idx - 16] = 0
						else:
							self.__board[end_idx + 16] = 0

			# Write the stored chess piece into the end index
			self.__board[end_idx] = move_pieces[i]
			# Clear the start index
			self.__board[start_idx] = 0

			# If a new piece type was specified, update the piece target
			if len(m) == 5:
				self.__board[end_idx] = piece_colour + (ChessPiece.decode_piece(ChessPiece.from_FEN(m[4]))[1])

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
		# Copy the existing board state
		new_board.__active_move = self.__active_move
		new_board.__move_count = self.__move_count
		new_board.__halfmove_clock = self.__halfmove_clock
		new_board.__enpassant = self.__enpassant
		new_board.__board = self.__board.copy()
		new_board.__piecetype_weights = self.__piecetype_weights.copy()
		new_board.__reversed = self.__reversed
		new_board.__difficulty = self.__difficulty
		new_board.__initialized = self.__initialized
		new_board.__castle_white = self.__castle_white.copy()
		new_board.__castle_black = self.__castle_black.copy()

		# Apply the move
		new_board.apply_move(move)

		return new_board

	def get_move_command(self, move: ChessMove) -> str:
		"""Generates the IPC command associated with a move from a given board state.

		Parameters
		----------
		move : ChessMove
			Chess move to use

		Returns
		-------
		str
			IPC command(s) for the associated chess move
		"""
		# Initialize the command
		command = "move "
		if move.capture is not None:
			# If the move is a capture, we need to first move the captured piece
			# out of the way.
			# Get the type of the piece being captured
			captureType = ChessPiece.to_FEN(self.__board[move.capture]).casefold()
			captureSource = Board.idx_to_square(move.capture)
			command += f"{captureType}{captureSource}xx,"

		# Get the piece type being moved
		pieceType = ChessPiece.to_FEN(move.piece).casefold()
		# Get the squares for the move
		squareFrom = Board.idx_to_square(move.idx_from)
		squareTo = Board.idx_to_square(move.idx_to)
		command += f"{pieceType}{squareFrom}{squareTo}"

		# Check castling
		if move.castle is not None:
			# If the move is a castling move, we need to move the rook as well
			# as the king.
			# TODO: Check for move conflicts for Chess960
			castleTargetIdx = move.idx_to + 1 if move.castle < move.idx_from else move.idx_to - 1
			# This shouldn't be needed, but it's a useful check anyways
			castleType = ChessPiece.to_FEN(self.__board[move.castle]).casefold()
			castleFrom = Board.idx_to_square(move.castle)
			castleTo = Board.idx_to_square(castleTargetIdx)
			command += f",{castleType}{castleFrom}{castleTo}"

		return command

	def set_gambit_as_player(self) -> None:
		"""Sets Gambit as the active player."""
		self.__active_move = self.get_gambit_colour()

	def set_human_as_player(self) -> None:
		"""Sets the human as the active player."""
		self.__active_move = self.get_gambit_colour().opponent()

	def solve(
		self, target_depth: int, target_time: float | None = None, max_time: float | None = None
	) -> tuple[ChessMove, int]:
		"""Calculates an optimal chess move to make.

		Searches up to a specific depth in a move tree.
		If a target time is specified, the search will not begin a new search
		after the target time has elapsed.
		If a maximum time is specified, the search will end upon reaching
		the maximum time.

		Parameters
		----------
		target_depth : int
			Target depth to search to.
		max_time : float | None, optional
			Maximum time to search for, by default None

		Returns
		-------
		tuple[ChessMove, int]
			Optimal chess move, search depth reached

		Raises
		------
		CheckmateException
			Player is in Checkmate. No moves are available.
		"""
		# If the active player is not gambit, throw a warning here
		if self.__active_move != self.get_gambit_colour():
			_log.warning(f"Solving move for {self.__active_move} while Gambit is playing as {self.get_gambit_colour()}")
		# Generate a list of moves that we could make
		move_list = self.get_moves()
		# If no moves are available, we are in a stalemate or in check
		if len(move_list) == 0:
			if self.is_check(self.__active_move):
				# In check with no moves means Checkmate
				raise CheckmateException
			else:
				# No moves without being in check is a Stalemate
				raise StalemateException
		# Initialize an array of scores for each move
		move_scores = np.zeros(len(move_list), dtype=np.int32)
		# Initialize an array to hold the move order
		move_order = np.array(tuple(range(len(move_list))), dtype=np.int16)

		# Initialize the depth to avoid potential return errors
		depth = 1

		end_time = time.time() + target_time if target_time is not None else None
		cut_time = time.time() + max_time if max_time is not None else None

		# For each move, recursively solve for the worst possible outcome, up to the target depth
		for depth in range(1, target_depth + 1):
			_log.debug(f"Starting depth {depth} search")
			# Initialize alpha to -infinity
			alpha = -INF
			for move_idx in move_order:
				if cut_time is not None and time.time() > cut_time:
					_log.debug("Maximum time exceeded for search. Stopping immediately.")
					break
				# move_idx = move_order[i]
				m = move_list[move_idx]
				move_scores[move_idx] = self.with_move(m).__solve_recurse(self.__active_move, depth - 1, alpha, INF)
				if move_scores[move_idx] > alpha:
					alpha = int(move_scores[move_idx])

			# Sort the move order list only if we have not exceeded the cut time
			if cut_time is None or time.time() < cut_time:
				# The result of the argsort needs to be reversed to provide
				# descending ordering for the sort.
				move_order = move_scores.argsort()[::-1]

			# If we have exceeded the alotted time, break out of the loop
			if end_time is not None and time.time() > end_time:
				_log.debug(f"Target search time exceeded. Stopping search at depth {depth}.")
				break

		# If we exceeded the cut time, decrement the depth to report the accurate search depth
		if cut_time is not None and time.time() > cut_time:
			depth -= 1

		selected_idx: int

		match self.__difficulty:
			case Difficulty.HARD:
				# Hard will always select the best move
				selected_idx = move_order[0]
			case Difficulty.MEDIUM:
				# Medium will select from the five best moves with decreasing
				# probability, following the equation 1 / i^2
				move_count = min(len(move_list), 5)
				move_p = np.array(tuple(range(1, move_count + 1)))
				move_p = 1 / (move_p**2)
				selected_idx = _rng.choice(move_order[0:move_count], p=move_p)
			case Difficulty.EASY:
				# Easy selects equally from the five best moves available
				move_count = min(len(move_list), 5)
				selected_idx = _rng.choice(move_order[0:move_count])

		return move_list[selected_idx], depth

	def __solve_recurse(self, player: PieceColour, depth: int, alpha: int, beta: int, captures_only: bool = False) -> int:
		# Disable null move pruning if there are few pieces left
		# if not self.is_endgame():
		# 	# Null move pruning
		# 	if depth >= 4 and not self.is_in_check():
		# 		null_score = self.__solve_recurse(
		# 			player,
		# 			depth - 1 - 2,  # Reduce depth more aggressively
		# 			-beta,
		# 			-beta + 1,
		# 		)
		# 		if null_score >= beta:
		# 			return beta

		# If a king is missing, return immediately
		try:
			self.get_king_idx(player)
		except NoKingException:
			# Player king is missing
			return -INF

		try:
			self.get_king_idx(player.opponent())
		except NoKingException:
			# Opponent king is missing
			return INF

		# If we hit the bottom of the search, proceed by performing
		# "capture-only" searches indefinitely.
		if depth <= 0:
			# Get the current board value
			value = self.get_state_value(player)
			# Perform a preliminary check to see if captures are good moves
			if value >= alpha:
				# If the current value is better than our "current best",
				# return that value and stop the search
				return value
			# Update beta if necessary
			elif value < beta:
				beta = value

			# Otherwise, set the captures only flag
			captures_only = True

		# Generate the move list
		move_list = self.get_moves(captures_only=captures_only)

		# If we didn't find any moves, return the current board value
		# unless we have a stalemate
		if len(move_list) == 0:
			if depth <= 0:
				return self.get_state_value(player)
			else:
				# Stalemate detected. Return 0
				return 0

		if player == self.__active_move:
			# Evaluating moves for the active player. We want to maximize results.
			value = -INF
			for move in move_list:
				value = max(value, self.with_move(move).__solve_recurse(player, depth - 1, alpha, beta))
				if value >= beta:
					# Beta cutoff
					break
				alpha = max(alpha, value)
		else:
			# Evaluating moves for the opposing player. We want to minimize results.
			value = INF
			for move in move_list:
				value = min(value, self.with_move(move).__solve_recurse(player, depth - 1, alpha, beta))
				if value <= alpha:
					# Alpha cutoff
					break
				beta = min(beta, value)

		return value

	def is_threatened(self, target_idx: int, attacker: PieceColour) -> bool:
		"""Checks if a piece from the attacker is threatening the target board index.

		Parameters
		----------
		target_idx : int
			Board index to check
		attacker : PieceColour
			Attacking player

		Returns
		-------
		bool
			If the board index is being threatened

		Raises
		------
		ValueError
			Invalid board index provided
		"""

		# Verify that the target index is on the board
		if not Board.idx_on_board(target_idx):
			raise ValueError(f"Provided index {target_idx} is not a valid board index.")

		# We can search backwards from the target index to check if any enemy piece can threaten it
		# Start by checking for pawns since it's a easy check to do separately
		# We will need to check the opposite direction to normal pawn movement for this.
		pawn_direction = -1 if (attacker == PieceColour.WHITE) == (not self.__reversed) else 1
		for d in (15, 17):
			a_idx = target_idx + (d * pawn_direction)
			if Board.idx_on_board(a_idx):
				a_num = self.__board[a_idx]
				if ChessPiece.is_piece(a_num):
					a_colour, a_type = ChessPiece.decode_piece(a_num)
					if a_colour == attacker and a_type == PieceType.PAWN:
						# Pawn is threatening the square
						return True

		# Search four cardinal directions
		# Stop if we reach a piece of any type
		for d in (16, 1, -16, -1):
			i = 1
			a_idx = target_idx + (d * i)
			while Board.idx_on_board(a_idx):
				a_num = self.__board[a_idx]
				if ChessPiece.is_piece(a_num):
					# If we ran into a piece, we are going to end the while loop no matter what
					a_colour, a_type = ChessPiece.decode_piece(a_num)
					if a_colour == attacker and (
						(a_type == PieceType.KING and i == 1) or (a_type in (PieceType.ROOK, PieceType.QUEEN))
					):
						# If the piece can attack the target, return true
						return True
					else:
						# Otherwise, stop the while loop and continue to the next direction
						break

				i += 1
				a_idx = target_idx + (d * i)

		# Search the four diagonals
		for d in (15, 17, -15, -17):
			i = 1
			a_idx = target_idx + (d * i)
			while Board.idx_on_board(a_idx):
				a_num = self.__board[a_idx]
				if ChessPiece.is_piece(a_num):
					# If we ran into a piece, we are going to end the while loop no matter what
					a_colour, a_type = ChessPiece.decode_piece(a_num)
					if a_colour == attacker and (
						(a_type == PieceType.KING and i == 1) or (a_type in (PieceType.BISHOP, PieceType.QUEEN))
					):
						# If the piece can attack the target, return true
						return True
					else:
						# Otherwise, stop the while loop and continue to the next direction
						break

				i += 1
				a_idx = target_idx + (d * i)

		# Search directly for knights
		for d in (33, 18, -14, -31, -33, -18, 14, 31):
			a_idx = target_idx + d
			if Board.idx_on_board(a_idx):
				a_num = self.__board[a_idx]
				if ChessPiece.is_piece(a_num):
					a_colour, a_type = ChessPiece.decode_piece(a_num)
					if a_colour == attacker and a_type == PieceType.KNIGHT:
						# Knight is threatening the square
						return True

		# If we reached the end, that means no piece is threatening the square
		return False

	def is_check(self, player: PieceColour) -> bool:
		"""Checks if a specified player is in Check.

		Parameters
		----------
		player : PieceColour
			Player to check is in check

		Returns
		-------
		bool
			Player is in check
		"""
		king_idx = self.get_king_idx(player)
		attacker = PieceColour.BLACK if player == PieceColour.WHITE else PieceColour.WHITE
		return self.is_threatened(king_idx, attacker)

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

	def is_endgame(self, player: PieceColour) -> bool:
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

	def get_endgame_pct(self, player: PieceColour) -> float:
		"""Returns the endgame percentage for a given player.

		Used to map between early and late-game position maps.

		Parameters
		----------
		player : PieceColour
			Active player.

		Returns
		-------
		float
			Endgame percentage.
		"""
		# Implementation adapted from Sebastian Lague's "Coding Adventure: Making a Better Chess Bot"
		# video and Github repository: https://www.youtube.com/watch?v=_vqlIPDR2TU
		opposing_indices = np.flatnonzero(np.bitwise_and(self.__board, player.opponent()))
		opposing_pieces = self.__board[opposing_indices]
		endgame_weight = 0
		for piece_num in opposing_pieces:
			_, piece_type = ChessPiece.decode_piece(piece_num)
			endgame_weight += ENDGAME_PCT_WEIGHTS[piece_type]

		return 1 - min(1, endgame_weight / ENDGAME_START_WEIGHT)

	def is_initialized(self) -> bool:
		"""Checks if the board is considered to be initialized.

		Returns
		-------
		bool
			Board is initialized
		"""
		return self.__initialized

	def is_reversed(self) -> bool:
		"""Checks if the board is reversed.

		Returns
		-------
		bool
			Board is reversed
		"""
		return self.__reversed

	def get_active_move(self) -> PieceColour:
		"""Returns the active player.

		Returns
		-------
		PieceColour
			Active player colour
		"""
		return self.__active_move

	def get_gambit_colour(self) -> PieceColour:
		"""Returns the player colour for Gambit.

		Returns
		-------
		PieceColour
			Gambit's player colour
		"""
		if not self.__initialized:
			return PieceColour.NONE
		elif not self.__reversed:
			return PieceColour.WHITE
		else:
			return PieceColour.BLACK

	def get_valid_castling_idx(self, player: PieceColour) -> tuple[int, ...]:
		"""Gets indices of rooks for valid castling moves.

		Parameters
		----------
		player : PieceColour
			Player colour to retrieve castling indices for.

		Returns
		-------
		tuple[int, ...]
			Valid castling indices
		"""
		if player == PieceColour.WHITE:
			return tuple(self.__castle_white)
		elif player == PieceColour.BLACK:
			return tuple(self.__castle_black)
		else:
			return tuple()

	def get_king_idx(self, player: PieceColour) -> int:
		"""Returns the board index of the specified player's King.

		Parameters
		----------
		player : PieceColour
			Piece colour to search for.

		Returns
		-------
		int
			Board index of King.

		Raises
		------
		NoKingException
			No King found on board.
		"""
		result = np.flatnonzero(np.equal(self.__board, player + PieceType.KING))
		try:
			return int(result[0])
		except Exception:
			# If we didn't find the king, raise an exception
			raise NoKingException

	def get_move_from_stockfish(self, move_str: str) -> ChessMove:
		"""Returns a ChessMove object from a Stockfish move string.

		Parameters
		----------
		move_str : str
			Stockfish move string.

		Returns
		-------
		ChessMove
			Chess Move object.
		"""
		# If the board is reversed, invert the stockfish move
		if self.__reversed:
			move_str = invert_stockfish_move(move_str)

		start_idx = Board.idx_from_square(move_str[0:2])
		end_idx = Board.idx_from_square(move_str[2:4])
		if len(move_str) > 4:
			promotion_fen = move_str[4]
		else:
			promotion_fen = None

		# Get the piece type
		piece = self.__board[start_idx]

		# If the promotion FEN is not none, get a promotion
		if promotion_fen is not None:
			promotion = ChessPiece.decode_piece(ChessPiece.from_FEN(promotion_fen))[1]
		else:
			promotion = None

		# Check for castling
		castle = None
		if ChessPiece.decode_piece(self.__board[start_idx])[1] == PieceType.KING:
			# If the king moved two tiles, handle it as a castling operation
			if abs(end_idx - start_idx) == 2:
				castling_indices = self.get_valid_castling_idx(self.get_gambit_colour())
				if end_idx > start_idx:
					# Search for castling indices above the king index
					for c in castling_indices:
						if c > start_idx:
							castle = c
							break
				else:
					# Search for castling indices below the king index
					for c in castling_indices:
						if c < start_idx:
							castle = c
							break

		# Check for captures
		# Suppress capture operations when castling is detected
		if castle is None and ChessPiece.is_piece(self.__board[end_idx]):
			capture = end_idx
		else:
			capture = None

		# Check for en passant
		if end_idx == self.__enpassant:
			enpassant = True
		else:
			enpassant = False

		return ChessMove(piece, start_idx, end_idx, promotion=promotion, capture=capture, enpassant=enpassant, castle=castle)

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
