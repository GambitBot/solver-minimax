import numpy as np
import pytest

from solver.piece import ChessPiece


@pytest.mark.parametrize(
	"fen, pieceNum",
	[
		pytest.param("p", np.uint8(0b01001)),
		pytest.param("r", np.uint8(0b01010)),
		pytest.param("n", np.uint8(0b01011)),
		pytest.param("b", np.uint8(0b01100)),
		pytest.param("q", np.uint8(0b01101)),
		pytest.param("k", np.uint8(0b01110)),
		pytest.param("P", np.uint8(0b10001)),
		pytest.param("R", np.uint8(0b10010)),
		pytest.param("N", np.uint8(0b10011)),
		pytest.param("B", np.uint8(0b10100)),
		pytest.param("Q", np.uint8(0b10101)),
		pytest.param("K", np.uint8(0b10110)),
	],
)
def test_from_FEN(fen: str, pieceNum: np.uint8) -> None:
	assert ChessPiece.from_FEN(fen) == pieceNum


@pytest.mark.parametrize(
	"pieceNum, fen",
	[
		pytest.param(np.uint8(0b01001), "p"),
		pytest.param(np.uint8(0b01010), "r"),
		pytest.param(np.uint8(0b01011), "n"),
		pytest.param(np.uint8(0b01100), "b"),
		pytest.param(np.uint8(0b01101), "q"),
		pytest.param(np.uint8(0b01110), "k"),
		pytest.param(np.uint8(0b10001), "P"),
		pytest.param(np.uint8(0b10010), "R"),
		pytest.param(np.uint8(0b10011), "N"),
		pytest.param(np.uint8(0b10100), "B"),
		pytest.param(np.uint8(0b10101), "Q"),
		pytest.param(np.uint8(0b10110), "K"),
	],
)
def test_to_FEN(pieceNum: np.uint8, fen: str) -> None:
	assert ChessPiece.to_FEN(pieceNum) == fen


@pytest.mark.parametrize(
	"pieceNum, is_piece",
	[
		pytest.param(np.uint8(0b00001), False),
		pytest.param(np.uint8(0b00010), False),
		pytest.param(np.uint8(0b00011), False),
		pytest.param(np.uint8(0b00100), False),
		pytest.param(np.uint8(0b00101), False),
		pytest.param(np.uint8(0b00110), False),
		pytest.param(np.uint8(0b01001), True),
		pytest.param(np.uint8(0b01010), True),
		pytest.param(np.uint8(0b01011), True),
		pytest.param(np.uint8(0b01100), True),
		pytest.param(np.uint8(0b01101), True),
		pytest.param(np.uint8(0b01110), True),
		pytest.param(np.uint8(0b10001), True),
		pytest.param(np.uint8(0b10010), True),
		pytest.param(np.uint8(0b10011), True),
		pytest.param(np.uint8(0b10100), True),
		pytest.param(np.uint8(0b10101), True),
		pytest.param(np.uint8(0b10110), True),
	],
)
def test_is_piece(pieceNum: np.uint8, is_piece: bool) -> None:
	assert ChessPiece.is_piece(pieceNum) == is_piece
