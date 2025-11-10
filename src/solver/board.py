"""Chess board classes"""

from .piece import ChessPiece, PieceColour, PieceType


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

	piece: ChessPiece
	idx_from: int
	idx_to: int
	promotion: PieceType | None
	capture: ChessPiece | None
	enpassant: bool

	def __init__(
		self,
		piece: ChessPiece,
		idx_from: int,
		idx_to: int,
		*,
		promotion: PieceType | None = None,
		capture: ChessPiece | None = None,
		enpassant: bool | None = None,
	):
		"""Initializes a move"""
		self.piece = piece
		self.idx_from = idx_from
		self.idx_to = idx_to
		self.promotion = promotion
		self.capture = capture
		self.enpassant = enpassant if enpassant is not None else False

	def __str__(self) -> str:
		"""Return a string representation of a move."""
		s = f"Piece: {self.piece} | Move: {idx_to_square(self.idx_from)}{idx_to_square(self.idx_to)}"
		if self.capture is not None:
			s += f" | Capture: {self.capture}"
		if self.enpassant:
			s += " en-passant"
		if self.promotion is not None:
			s += f" | Promotion: {self.promotion}"
		return s


class Board:
	"""Representation of a chess board."""

	__piecetype_map: dict[str, PieceType] = {
		"k": PieceType.KING,
		"q": PieceType.QUEEN,
		"r": PieceType.ROOK,
		"b": PieceType.BISHOP,
		"n": PieceType.KNIGHT,
		"p": PieceType.PAWN,
	}

	__active_move: PieceColour
	__move_count: int
	__halfmove_clock: int
	__enpassant: int | None
	__pieces: list[ChessPiece | None]
	__piecetype_weights: dict[PieceType, int]

	def __init__(self):
		"""Initializes a new chess board.

		Not intended to be called directly."""
		self.__pieces = [None] * 64
		self.__piecetype_weights = {
			PieceType.KING: 100000,
			PieceType.QUEEN: 500,
			PieceType.ROOK: 300,
			PieceType.BISHOP: 200,
			PieceType.KNIGHT: 200,
			PieceType.PAWN: 100,
		}
		self.__enpassant = None

	def __str__(self) -> str:
		"""Returns a string representation of the board state"""
		s = " |abcdefgh\n-+--------"
		# Iterate over all pieces in the board with the index
		for i, p in enumerate(self.__pieces):
			rank = i // 8
			file = i % 8
			# If we're at the beginning of a rank, add the rank number to the string
			if file == 0:
				s += f"\n{8 - rank}|"
			# If the square is the en-passant square, mark it with an asterisk
			if i == self.__enpassant:
				s += "*"
			# If the space is empty, add a space
			elif p is None:
				s += " "
			else:
				# If the space is not empty, add the FEN string representation
				# of the piece occupying that space
				s += p.to_FEN()

		return s

	@classmethod
	def from_fen_string(cls, fen: str) -> "Board":
		"""Initializes a board from an FEN string.

		Parameters
		----------
		fen : str
			Input FEN string

		Returns
		-------
		Board
			Chess board representation

		Raises
		------
		ValueError
			Invalid FEN string
		"""
		board = cls()
		# Split the FEN string up into segments to facilitate parsing
		fen_segments: list[str] = fen.split(" ")
		# These do not exactly match with the real ranks and files used
		# on a chess board, but they work better for computer calcualtion
		rank = 0
		file = 0
		# Iterate over the beginning of the FEN string to fill the board
		for char in fen_segments[0]:
			# If the character is a slash, move to the next rank
			if char == "/":
				# If the file was not already at the end of the rank, throw an error
				if file < 8:
					raise ValueError(f"Error parsing FEN string in rank {8 - rank}. Missing information for rank.")
				# Reset the file, and increment the rank
				rank += 1
				file = 0
				continue
			# If the character is a number, move the file over by that value
			elif char.isnumeric():
				file += int(char)
				if file > 8:
					raise ValueError(f"Error parsing FEN string in rank {8 - rank}. File exceeds end of rank.")
				continue
			# Character is a letter, which indicates a piece
			else:
				if char.casefold() not in Board.__piecetype_map.keys():
					raise ValueError(f"Error parsing FEN string in rank {8 - rank}. Invalid piece definition: {char}")
				piecetype = Board.__piecetype_map[char.casefold()]
				piececolour = PieceColour.WHITE if char.isupper() else PieceColour.BLACK
				# Add the piece to the board
				board.__pieces[(rank * 8) + file] = ChessPiece(piececolour, piecetype)
				# Increment the file by one
				file += 1

		# Determine the active move
		board.__active_move = PieceColour.WHITE if fen_segments[1] == "w" else PieceColour.BLACK

		# TODO: Implement castling checks

		# Pending en-passant status
		if fen_segments[3] != "-":
			board.__enpassant = ((8 - int(fen_segments[3][1])) * 8) + (ord(fen_segments[3][0]) - 97)

		# Halfmove clock and total moves
		board.__halfmove_clock = int(fen_segments[4])
		board.__move_count = int(fen_segments[5])

		return board

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
		for p in self.__pieces:
			# Only proceed if a piece exists in this space
			if p is not None:
				# If the piece matches the player with the active move,
				# increase the weight
				if p.colour == player:
					w += self.__piecetype_weights[p.type]
				else:
					# Otherwise, decrease the weight
					w -= self.__piecetype_weights[p.type]
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
		# White actually moves down in indices, while black moves up
		pawn_direction = -1 if self.__active_move == PieceColour.WHITE else 1

		# Iterate over all of the chess pieces on the board
		for i, p in enumerate(self.__pieces):
			# If there is no piece on the current square, continue
			if p is None:
				continue
			# If the piece is an opponent's piece, continue
			if p.colour != self.__active_move:
				continue
			# We now know that the piece must exist, and belong to the active player.
			# This part needs different logic depending on the type of piece
			# Begin by storing the rank and file of the piece being evaluated
			rank, file = idx_to_rank(i)

			match p.type:
				case PieceType.PAWN:
					# Pawns can move forward unless there is a piece in the way
					target_idx = i + (8 * pawn_direction)
					# Only continue if the target index is on the board and
					# there is no piece blocking the way
					if idx_on_board(target_idx) and self.__pieces[target_idx] is None:
						# Pawn can move forward.
						# If the pawn has reached the opposing side of the board we can promote it
						if (self.__active_move == PieceColour.WHITE and idx_to_rank(target_idx)[0] == 0) or (
							self.__active_move == PieceColour.BLACK and idx_to_rank(target_idx)[0] == 7
						):
							# The only promotions that make any sense are promotions
							# to queen or knight, since all other pieces have only subsets
							# of a queen's movement
							moves.append(ChessMove(p, i, target_idx, promotion=PieceType.QUEEN))
							moves.append(ChessMove(p, i, target_idx, promotion=PieceType.KNIGHT))
						else:
							# If the pawn is not in the last row, it cannot promote.
							moves.append(ChessMove(p, i, target_idx))

					# If the pawn is in its starting row,
					# it can also optionally move two squares forward
					target_idx = i + (16 * pawn_direction)
					if (
						(self.__active_move == PieceColour.WHITE and rank == 6)
						or (self.__active_move == PieceColour.BLACK and rank == 1)
					) and self.__pieces[target_idx] is None:
						moves.append(ChessMove(p, i, target_idx))

					# The pawn can move forward diagonally if it can capture a piece
					for offset in (7, 9):
						target_idx = i + (offset * pawn_direction)
						# Ensure that the pawn is moving forward by one row
						# i.e not overflowing off of one side of the board
						if idx_to_rank(target_idx)[0] != rank + pawn_direction:
							continue

						# If the target index is the en-passant index, allow the move
						if self.__enpassant is not None and target_idx == self.__enpassant:
							moves.append(
								ChessMove(
									p,
									i,
									target_idx,
									capture=self.__pieces[self.__enpassant + (-8 * pawn_direction)],
									enpassant=True,
								)
							)
							continue

						target = self.__pieces[target_idx]
						# If there is no piece diagonally to capture, the pawn cannot move
						if target is not None:
							# There must be a piece diagonally at this point
							if target.colour == self.__active_move:
								# Piece is friendly. We cannot move there.
								continue
							else:
								moves.append(ChessMove(p, i, target_idx, capture=target))

		return moves
