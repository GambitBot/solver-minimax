"""Gambit chess solving engine using a Minimax algorithm"""

from .board import Board

FEN_STRING = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
FEN_STRING_PAWN_CAPTURE = "rnbqkbnr/p1p1pppp/1p6/PPPpPPPP/8/8/3P4/RNBQKBNR w KQkq d6 0 1"
FEN_STRING_PAWN_PROMOTION = "8/3P4/8/8/8/8/8/8 w KQkq - 0 1"

print("Parsing FEN string:")
print(FEN_STRING_PAWN_PROMOTION)
b = Board.from_fen_string(FEN_STRING_PAWN_PROMOTION)
print("Resulting board")
print(b)
print(f"Board state weight: {b.get_state_value()}")

print("Determining possible moves")
moves = b.get_moves()
for m in moves:
	print(f"    {m}")

pass
