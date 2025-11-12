"""Chess piece class"""

from enum import IntEnum

import numpy as np


class PieceColour(IntEnum):
	"""Chess piece colour"""

	# We're going to need to use 8 bits for each board square anyways,
	# so we can use
	NONE = 0
	BLACK = 8
	WHITE = 16


class PieceType(IntEnum):
	"""Chess piece type"""

	NONE = 0
	PAWN = 1
	ROOK = 2
	KNIGHT = 3
	BISHOP = 4
	QUEEN = 5
	KING = 6


class ChessPiece:
	"""Chess piece function class"""

	__piecetype_map: dict[str, PieceType] = {
		"k": PieceType.KING,
		"q": PieceType.QUEEN,
		"r": PieceType.ROOK,
		"b": PieceType.BISHOP,
		"n": PieceType.KNIGHT,
		"p": PieceType.PAWN,
	}

	__piecechar_map: dict[PieceType | int, str] = {
		PieceType.KING: "k",
		PieceType.QUEEN: "q",
		PieceType.ROOK: "r",
		PieceType.BISHOP: "b",
		PieceType.KNIGHT: "n",
		PieceType.PAWN: "p",
	}

	__piecestr_map: dict[PieceType | int, str] = {
		PieceType.KING: "King",
		PieceType.QUEEN: "Queen",
		PieceType.ROOK: "Rook",
		PieceType.BISHOP: "Bishop",
		PieceType.KNIGHT: "Knight",
		PieceType.PAWN: "Pawn",
	}

	@staticmethod
	def decode_piece(piece_num: np.uint8) -> tuple[PieceColour, PieceType]:
		"""Decodes a piece number into its colour and type.

		Parameters
		----------
		piece_num : np.uint8
			Piece number.

		Returns
		-------
		tuple[PieceColour, PieceType]
			Piece colour and piece type.

		Raises
		------
		ValueError
			Invalid piece number provided.
		"""
		try:
			piece_colour = PieceColour(piece_num & 0b11000)
			piece_type = PieceType(piece_num & 0b111)
		except ValueError as e:
			raise e

		return (piece_colour, piece_type)

	@staticmethod
	def from_FEN(char: str) -> np.uint8:
		"""Converts an FEN string character to an integer representation of a chess piece.

		Parameters
		----------
		char : str
			FEN string character

		Returns
		-------
		np.uint8
			Integer piece representation

		Raises
		------
		ValueError
			Invalid character
		"""
		# If the character is invalid, throw an error
		if char.casefold() not in ChessPiece.__piecetype_map:
			raise ValueError(f"Invalid FEN string character: {char}")
		# Initialize the result value
		result = np.uint8(0)
		# Set the colour of the piece. Capital letters indicate white pieces.
		result += PieceColour.WHITE if char.isupper() else PieceColour.BLACK
		# Retrieve the value
		result += ChessPiece.__piecetype_map[char.casefold()]
		return result

	@staticmethod
	def to_FEN(piece_num: np.uint8) -> str:
		"""Converts a piece number to its FEN string representation.

		Parameters
		----------
		pieceNum : np.uint8
			Integer piece representation

		Returns
		-------
		str
			FEN character of the piece

		Raises
		------
		ValueError
			Invalid piece type
		ValueError
			Empty piece provided
		"""
		# Retrieve the type of the piece
		pieceType = piece_num & 0b111
		if pieceType not in ChessPiece.__piecechar_map:
			raise ValueError(f"Invalid piece number: {piece_num}")
		# Extra conversion to int is needed to make the type checker happy
		result = ChessPiece.__piecechar_map[int(pieceType)]

		# Retrieve the colour of the piece
		colourInt = piece_num & 0b11000
		if colourInt == PieceColour.WHITE:
			# If the piece is a white piece, use an uppercase character
			result = result.upper()
		elif colourInt == PieceColour.BLACK:
			# We don't need to do anything for a black piece since the character
			# is already lowercase
			pass
		else:
			raise ValueError("Unable to generate FEN character from nonexistent piece.")

		return result

	@staticmethod
	def is_piece(piece_num: np.uint8) -> bool:
		"""Checks if an integer represents a chess piece or an empty square.

		Parameters
		----------
		pieceNum : np.uint8
			Input integer

		Returns
		-------
		bool
			If the integer represents a chess piece.
		"""
		return piece_num & 0b11000 != 0
