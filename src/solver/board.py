"""Chess board class"""

from .piece import ChessPiece, PieceColour, PieceType


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

	def __init__(self):
		"""Initializes a new chess board.

		Not intended to be called directly."""
		self.__pieces = [None] * 64

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
			# If the space is empty, add a space
			if p is None:
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
