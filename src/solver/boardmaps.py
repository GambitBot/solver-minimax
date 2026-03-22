"""Gambit Solver Piece-Type Board Maps"""

# from math import sqrt

import numpy as np

from .piece import PieceType

_zeros = np.zeros((8, 8), dtype=np.int32)

# Board maps were inspired by Sebastian Lague's implementation
# in his video: "Coding Adventure: Making a Better Chess Bot"
# https://www.youtube.com/watch?v=_vqlIPDR2TU

# Default pawn map needs to prioritize moving pawns near
# the center of the board *without* compromizing king safety
# for castling.
_pawn_map = np.array(
	(
		# A, B, C, D, E, F, G, H
		(0, 0, 0, 0, 0, 0, 0, 0),  # 8. Pawns can never exist on the far row.
		(50, 50, 50, 50, 50, 50, 50, 50),  # Assign equal weights to threatened promotions
		(10, 10, 20, 30, 30, 20, 10, 10),
		(5, 5, 10, 25, 25, 10, 5, 5),
		(0, 0, 0, 20, 20, 0, 0, 0),
		(5, -5, -10, 0, 0, -10, -5, 5),  # No bonus for pawns on D3,D3 to encourage double moves.
		(5, 10, 20, -20, -20, 20, 10, 5),  # Penalize pawns on D2,E2 to encourage early-game moves.
		(0, 0, 0, 0, 0, 0, 0, 0),  # 1
	)
)
# Penalize rooks for being on the sides of the board
# unless they are helping trap a king on the far rank
# A small bonus is also given for positions resulting from castling.
_rook_map = np.array(
	(
		# A, B, C, D, E, F, G, H
		(0, 0, 0, 0, 0, 0, 0, 0),  # 8
		(5, 10, 10, 10, 10, 10, 10, 5),
		(-5, 0, 0, 0, 0, 0, 0, -5),
		(-5, 0, 0, 0, 0, 0, 0, -5),
		(-5, 0, 0, 0, 0, 0, 0, -5),
		(-5, 0, 0, 0, 0, 0, 0, -5),
		(-5, 0, 0, 0, 0, 0, 0, -5),
		(0, 0, 5, 5, 5, 5, 0, 0),  # 1
	)
)
# Penalize knights heavily for being on the edges of the board.
_knight_map = np.array(
	(
		# A, B, C, D, E, F, G, H
		(-50, -40, -30, -30, -30, -30, -40, -50),  # 8
		(-40, -20, 0, 0, 0, 0, -20, -40),
		(-30, 0, 10, 15, 15, 10, 0, -30),
		(-30, 5, 15, 20, 20, 15, 5, -30),
		(-30, 5, 15, 20, 20, 15, 5, -30),
		(-30, 0, 10, 15, 15, 10, 0, -30),
		(-40, -20, 0, 5, 5, 0, -20, -40),  # Small bonus to move to guard the king
		(-50, -40, -30, -30, -30, -30, -40, -50),  # 1
	)
)
# Penalize bishops for being on the edges of the board, but not nearly
# as heavily as Knights
_bishop_map = np.array(
	(
		# A, B, C, D, E, F, G, H
		(-20, -10, -10, -10, -10, -10, -10, -20),  # 8
		(-10, 0, 0, 0, 0, 0, 0, -10),
		(-10, 0, 5, 10, 10, 5, 0, -10),
		(-10, 5, 5, 10, 10, 5, 5, -10),
		(-10, 0, 10, 10, 10, 10, 0, -10),
		(-10, 10, 10, 10, 10, 10, 10, -10),
		(-10, 5, 0, 0, 0, 0, 5, -10),
		(-20, -10, -10, -10, -10, -10, -10, -20),  # 1
	)
)
# Queens get a small penalty on the edge, and a small bonus in the centre
_queen_map = np.array(
	(
		# A, B, C, D, E, F, G, H
		(-20, -10, -10, -5, -5, -10, -10, -20),  # 8
		(-10, 0, 0, 0, 0, 0, 0, -10),
		(-10, 0, 5, 5, 5, 5, 0, -10),
		(-5, 0, 5, 5, 5, 5, 0, -5),
		(-5, 0, 5, 5, 5, 5, 0, -5),
		(-10, 0, 5, 5, 5, 5, 0, -10),
		(-10, 0, 0, 0, 0, 0, 0, -10),
		(-20, -10, -10, -5, -5, -10, -10, -20),  # 1
	)
)
# Kings are penalized for being anywhere other than their corners
# at the start of the game. Bonuses are given to encourage castling.
_king_map = np.array(
	(
		# A, B, C, D, E, F, G, H
		(-80, -70, -70, -70, -70, -70, -70, -80),  # 8
		(-60, -60, -60, -60, -60, -60, -60, -60),
		(-40, -50, -50, -60, -60, -50, -50, -40),
		(-30, -40, -40, -50, -50, -40, -40, -30),
		(-20, -30, -30, -40, -40, -30, -30, -20),
		(-10, -20, -20, -20, -20, -20, -20, -10),
		(20, 20, -5, -5, -5, -5, 20, 20),
		(20, 30, 10, 0, 0, 10, 30, 20),  # 1
		# A slightly larger bonus is given for being slightly out of the corners
		# to keep options open for the King to avoid checkmate.
	)
)

# In the endgame, weight all columns of pawns equally.
# Push more heavily for promotions.
_pawn_endgame_map = np.array(
	(
		# A, B, C, D, E, F, G, H
		(0, 0, 0, 0, 0, 0, 0, 0),  # 8
		(80, 80, 80, 80, 80, 80, 80, 80),
		(50, 50, 50, 50, 50, 50, 50, 50),
		(30, 30, 30, 30, 30, 30, 30, 30),
		(20, 20, 20, 20, 20, 20, 20, 20),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),  # 1
	)
)
# No desired positions for Rooks during endgame
_rook_endgame_map = np.array(
	(
		# A, B, C, D, E, F, G, H
		(0, 0, 0, 0, 0, 0, 0, 0),  # 8
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),  # 1
	)
)
# No desired positions for Knights during endgame
_knight_endgame_map = np.array(
	(
		# A, B, C, D, E, F, G, H
		(0, 0, 0, 0, 0, 0, 0, 0),  # 8
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),  # 1
	)
)
# No desired positions for Bishops during endgame
_bishop_endgame_map = np.array(
	(
		# A, B, C, D, E, F, G, H
		(0, 0, 0, 0, 0, 0, 0, 0),  # 8
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),  # 1
	)
)
# No desired positions for Queens during endgame
_queen_endgame_map = np.array(
	(
		# A, B, C, D, E, F, G, H
		(0, 0, 0, 0, 0, 0, 0, 0),  # 8
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),
		(0, 0, 0, 0, 0, 0, 0, 0),  # 1
	)
)
# Kings should move towards the center of the board
# during endgame.
_king_endgame_map = np.array(
	(
		# A, B, C, D, E, F, G, H
		(-50, -30, -30, -30, -30, -30, -30, -50),  # 8
		(-30, -25, 0, 0, 0, 0, -25, -30),
		(-25, 0, 0, 0, 0, 0, 0, -25),
		(-25, 0, 0, 0, 0, 0, 0, -25),
		(-25, 0, 0, 0, 0, 0, 0, -25),
		(-25, 0, 0, 0, 0, 0, 0, -25),
		(-30, -25, 0, 0, 0, 0, -25, -30),
		(-50, -30, -30, -30, -30, -30, -30, -50),  # 1
	)
)

BOARD_MAPS_WHITE = {
	PieceType.PAWN: np.hstack((_pawn_map[::-1], _zeros)).reshape(128),
	PieceType.ROOK: np.hstack((_rook_map[::-1], _zeros)).reshape(128),
	PieceType.KNIGHT: np.hstack((_knight_map[::-1], _zeros)).reshape(128),
	PieceType.BISHOP: np.hstack((_bishop_map[::-1], _zeros)).reshape(128),
	PieceType.QUEEN: np.hstack((_queen_map[::-1], _zeros)).reshape(128),
	PieceType.KING: np.hstack((_king_map[::-1], _zeros)).reshape(128),
}

BOARD_MAPS_BLACK = {
	PieceType.PAWN: np.hstack((_pawn_map, _zeros)).reshape(128),
	PieceType.ROOK: np.hstack((_rook_map, _zeros)).reshape(128),
	PieceType.KNIGHT: np.hstack((_knight_map, _zeros)).reshape(128),
	PieceType.BISHOP: np.hstack((_bishop_map, _zeros)).reshape(128),
	PieceType.QUEEN: np.hstack((_queen_map, _zeros)).reshape(128),
	PieceType.KING: np.hstack((_king_map, _zeros)).reshape(128),
}

ENDGAME_MAPS_WHITE = {
	PieceType.PAWN: np.hstack((_pawn_endgame_map[::-1], _zeros)).reshape(128),
	PieceType.ROOK: np.hstack((_rook_endgame_map[::-1], _zeros)).reshape(128),
	PieceType.KNIGHT: np.hstack((_knight_endgame_map[::-1], _zeros)).reshape(128),
	PieceType.BISHOP: np.hstack((_bishop_endgame_map[::-1], _zeros)).reshape(128),
	PieceType.QUEEN: np.hstack((_queen_endgame_map[::-1], _zeros)).reshape(128),
	PieceType.KING: np.hstack((_king_endgame_map[::-1], _zeros)).reshape(128),
}

ENDGAME_MAPS_BLACK = {
	PieceType.PAWN: np.hstack((_pawn_endgame_map, _zeros)).reshape(128),
	PieceType.ROOK: np.hstack((_rook_endgame_map, _zeros)).reshape(128),
	PieceType.KNIGHT: np.hstack((_knight_endgame_map, _zeros)).reshape(128),
	PieceType.BISHOP: np.hstack((_bishop_endgame_map, _zeros)).reshape(128),
	PieceType.QUEEN: np.hstack((_queen_endgame_map, _zeros)).reshape(128),
	PieceType.KING: np.hstack((_king_endgame_map, _zeros)).reshape(128),
}

# Board map for Mahnattan distance from centre squares
CENTRE_MANHATTAN_DISTANCE_MAP = np.hstack(
	(
		np.array(
			(
				# A, B, C, D, E, F, G, H
				(6, 5, 4, 3, 3, 4, 5, 6),  # 8
				(5, 4, 3, 2, 2, 3, 4, 5),
				(4, 3, 2, 1, 1, 2, 3, 4),
				(3, 2, 1, 0, 0, 1, 2, 3),
				(3, 2, 1, 0, 0, 1, 2, 3),
				(4, 3, 2, 1, 1, 2, 3, 4),
				(5, 4, 3, 2, 2, 3, 4, 5),
				(6, 5, 4, 3, 3, 4, 5, 6),  # 1
			)
		),
		_zeros,
	)
).reshape(128)

# Generate a board map for euclidean distance between indices.
ORTHOGONAL_DISTANCE_MAP = np.zeros((128, 128), dtype=np.uint8)
for i in range(ORTHOGONAL_DISTANCE_MAP.shape[0]):
	i_x = i & 0x0F
	i_y = (i & 0xF0) >> 4
	for j in range(ORTHOGONAL_DISTANCE_MAP.shape[1]):
		j_x = j & 0x0F
		j_y = (j & 0xF0) >> 4
		ORTHOGONAL_DISTANCE_MAP[i][j] = abs(j_x - i_x) + abs(j_y - i_y)
		# ORTHOGONAL_DISTANCE_MAP[i][j] = max(abs(j_x - i_x), abs(j_y - i_y))
		# KING_DISTANCE_MAP[i][j] = np.int8(round(sqrt((j_x - i_x) ** 2 + (j_y - i_y) ** 2)))
