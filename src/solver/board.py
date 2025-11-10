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
				cls.__pieces[(rank * 8) + file] = ChessPiece(piececolour, piecetype)

		# Determine the active move
		cls.__active_move = PieceColour.WHITE if fen_segments[1] == "w" else PieceColour.BLACK

		# TODO: Implement castling checks

		# Pending en-passant status
		if fen_segments[3] != "-":
			cls.__enpassant = ((8 - int(fen_segments[3][1])) * 8) + (ord(fen_segments[3][0]) - 97)

		# Halfmove clock and total moves
		cls.__halfmove_clock = int(fen_segments[4])
		cls.__move_count = int(fen_segments[5])

		return board
