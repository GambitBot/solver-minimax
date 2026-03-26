"""Gambit Utility Function"""


def invert_fen(input_fen: str) -> str:
	"""Inverts the board-state portion of an FEN string"""
	fen_parts = input_fen.split(" ")
	board_fen_parts = fen_parts[0].split("/")
	board_fen_parts.reverse()
	for i in range(len(board_fen_parts)):
		row = list(board_fen_parts[i])
		row.reverse()
		board_fen_parts[i] = "".join(row)
	fen_parts[0] = "/".join(board_fen_parts)
	return " ".join(fen_parts)


def invert_stockfish_move(move: str) -> str:
	"""Inverts the board-orientation of a stockfish move.

	Parameters
	----------
	move : str
		Stockfish move string

	Returns
	-------
	str
		Inverted Stockfish move string
	"""
	move_list = list(move)
	move_list[0] = chr(104 - (ord(move_list[0]) - 97))
	move_list[1] = str(9 - int(move_list[1]))
	move_list[2] = chr(104 - (ord(move_list[2]) - 97))
	move_list[3] = str(9 - int(move_list[3]))
	return "".join(move_list)
