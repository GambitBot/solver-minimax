"""Chess piece class"""

from enum import IntEnum


class PieceColour(IntEnum):
	"""Chess piece colour"""

	BLACK = 0
	WHITE = 8


class PieceType(IntEnum):
	"""Chess piece type"""

	PAWN = 0
	ROOK = 1
	KNIGHT = 2
	BISHOP = 3
	QUEEN = 4
	KING = 5


class ChessPiece:
	"""Chess piece"""

	__colour: PieceColour
	__type: PieceType

	def __init__(self, colour: PieceColour, type: PieceType):
		"""Initialize a chess piece

		Parameters
		----------
		colour : Colour
			Player colour
		type : PieceType
			Piece type
		"""
		self.__colour = colour
		self.__type = type

	def __int__(self) -> int:
		"""Returns an integer representation of the piece.

		Returns
		-------
		int
			Integer representation of the piece.
		"""
		return self.__type + self.__colour

	@property
	def colour(self) -> PieceColour:
		"""Piece colour"""
		return self.__colour

	@property
	def type(self) -> PieceType:
		"""Piece type"""
		return self.__type
