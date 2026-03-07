"""Gambit solver benchmark code"""

import time

from .board import Board
from .piece import PieceColour


def benchmark() -> None:
	"""Gambit benchmark function"""
	# FEN_STRING = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

	FEN_STRING_PAWN_CAPTURE = "rnbqkbnr/p1p1pppp/1p6/PPPpPPPP/8/8/3P4/RNBQKBNR w KQkq d6 0 1"
	# FEN_STRING_PAWN_PROMOTION = "8/3P4/8/8/8/8/8/8 w KQkq - 0 1"

	print("Parsing FEN string:")
	print(FEN_STRING_PAWN_CAPTURE)
	b = Board()
	b.load_fen_string(FEN_STRING_PAWN_CAPTURE)
	print("Resulting board")
	print(b)
	print(f"White castling on: {tuple(map(lambda x: Board.idx_to_square(x), b.get_valid_castling_idx(PieceColour.WHITE)))}")
	print(f"Black castling on: {tuple(map(lambda x: Board.idx_to_square(x), b.get_valid_castling_idx(PieceColour.BLACK)))}")
	print(f"Board state weight: {b.get_state_value()}")

	print("Determining possible moves")
	moves = b.get_moves()
	print(f"Detected {len(moves)} moves:")
	for m in moves:
		print(f"    {m}")

	search_depth = 4
	start_time = time.time()
	print(f"Selecting an optimal move with depth {search_depth}")
	move, depth = b.solve(search_depth, 5.0, 10.0)
	print(f"Search completed to depth: {depth}")
	print("Optimal move:")
	print(f"    {move}")
	end_time = time.time()
	print(f"Duration: {end_time - start_time:.3f}s")

	print("Applying selected move")
	print("Board state before:")
	print(b)
	b.apply_move(move)
	print("Board state after:")
	print(b)

	pass
