"""Gambit chess solving engine using a Minimax algorithm"""

import time

from .board import Board

FEN_STRING = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
FEN_STRING_PAWN_CAPTURE = "rnbqkbnr/p1p1pppp/1p6/PPPpPPPP/8/8/3P4/RNBQKBNR w KQkq d6 0 1"
FEN_STRING_PAWN_PROMOTION = "8/3P4/8/8/8/8/8/8 w KQkq - 0 1"

print("Parsing FEN string:")
print(FEN_STRING_PAWN_CAPTURE)
b = Board()
b.load_fen_string(FEN_STRING_PAWN_CAPTURE)
print("Resulting board")
print(b)
print(f"Board state weight: {b.get_state_value()}")

print("Determining possible moves")
moves = b.get_moves()
print(f"Detected {len(moves)} moves:")
for m in moves:
	print(f"    {m}")

start_time = time.time()
print("Selecting an optimal move with depth 4")
move = b.solve(4)
print("Optimal move:")
print(f"    {move}")
end_time = time.time()
print(f"Duration: {end_time - start_time:.3f}s")

pass
