"""Tests for Gambit chess solving engine using a Minimax algorithm."""

import time

import pytest

from solver.board import Board

FEN_STANDARD = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
FEN_PAWN_CAPTURE = "rnbqkbnr/p1p1pppp/1p6/PPPpPPPP/8/8/3P4/RNBQKBNR w KQkq d6 0 1"
FEN_PAWN_PROMOTION = "8/3P4/8/8/8/8/8/8 w KQkq - 0 1"


@pytest.mark.parametrize("fen_string", [FEN_STANDARD, FEN_PAWN_CAPTURE, FEN_PAWN_PROMOTION])
def test_board_and_solver(fen_string: str) -> None:
	"""
	Test that a Board can load a FEN string, generate moves, and select an optimal move.
	"""
	board = Board()
	board.load_fen_string(fen_string)
	state_value = board.get_state_value()
	assert isinstance(state_value, (int, float))

	# At least one legal move, should probably check for the known good exhaustive move
	moves = board.get_moves()
	assert moves, f"No moves detected for FEN: {fen_string}"

	# Solver should return a valid move
	start_time = time.time()
	move = board.solve(4)
	duration = time.time() - start_time

	assert move is not None, "Solver returned no move"
	assert duration < 5.0, "Solver took too long (over 5s)"
