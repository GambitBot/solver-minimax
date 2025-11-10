"""Gambit chess solving engine using a Minimax algorithm"""

from .board import Board

FEN_STRING = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

print("Parsing FEN string:")
print(FEN_STRING)
b = Board.from_fen_string(FEN_STRING)
print("Resulting board")
print(b)
print(f"Board state weight: {b.get_state_value()}")

pass
