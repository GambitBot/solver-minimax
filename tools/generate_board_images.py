"""Generates images of chess boards used for the project report.

Requires the optional "requirements-imagegen.txt" packages to be installed."""

import pathlib

import chessboard_image as cbi

IMAGE_SIZE = 400

SAMPLE_FEN = "1r1q1rk1/1p3pbp/6p1/1R1bp3/8/3P2P1/4PPBP/2BQ1RK1 w - - 0 1"

FEN_OPENINGS = {
	"start": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",  # Starting position
	"spanish": "r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",  # Ruy Lopez (Spaning Opening)
	"italian": "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",  # Italian Game
	"scotch": "r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",  # Scotch Game
	"sicilian": "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2",  # Sicilian Defence
	"french": "rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq d6 0 3",  # French Defence
	"scandanavian": "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2",  # Scandanavian Defence
	"petrov": "rnbqkb1r/pppp1ppp/5n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",  # Petrov's Defence
	"philidor": "rnbqkbnr/ppp2ppp/3p4/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 3",  # Philidor Defence
	"kings_gambit": "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2",  # King's Gambit
	"caro-kann": "rnbqkbnr/pp1ppppp/2p5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",  # Caro-Kann Defence
	"modern": "rnbqkbnr/pppppp1p/6p1/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",  # Modern Defence
	"pirc": "rnbqkbnr/ppp1pppp/3p4/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",  # Pirc Defence
	"owen": "rnbqkbnr/p1pppppp/1p6/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",  # Owen's Defence
	"alekhine": "rnbqkb1r/pppppppp/5n2/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 1 2",  # Alekhine Defence
	"vienna": "rnbqkbnr/pppp1ppp/8/4p3/4P3/2N5/PPPP1PPP/R1BQKBNR b KQkq - 1 2",  # Vienna Game
	"ponziani": "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/2P2N2/PP1P1PPP/RNBQKB1R b KQkq - 0 3",  # Ponziani Opening
	"queens-gambit": "rnbqkbnr/ppp1pppp/8/3p4/2PP4/8/PP2PPPP/RNBQKBNR b KQkq c3 0 2",  # Queen's Gambit
	"grunfeld": "rnbqkb1r/ppp1pp1p/5np1/3p4/2PP4/2N5/PP2PPPP/R1BQKBNR w KQkq d6 0 4",  # Grunfeld Defence
	"budapest": "rnbqkb1r/pppp1ppp/5n2/4p3/2PP4/8/PP2PPPP/RNBQKBNR w KQkq e6 0 3",  # Budapest Gambit
}

FEN_ENDGAME_5 = {
	"1": "1r6/1P5k/8/8/4K3/8/6R1/8 w - - 0 1",
	"2": "8/6R1/5p2/5k2/8/4r3/8/6K1 w - - 0 1",
	"3": "R7/P3r3/8/8/8/2K1k3/8/8 w - - 0 1",
	"4": "8/8/p6k/5p2/8/8/P4K2/8 w - - 0 1",
	"5": "8/3k4/5p2/8/4PKP1/8/8/8 w - - 0 1",
	"6": "8/4k3/8/2K2p2/8/7P/6P1/8 w - - 0 1",
	"7": "8/8/2P5/1P1K4/8/2k5/7r/8 w - - 0 1",
	"8": "5R2/8/k6K/1p6/7p/8/8/8 w - - 0 1",
	"9": "3k4/8/4K3/8/6R1/p5p1/8/8 b - - 0 1",
	"10": "8/5r2/8/8/6B1/4k1K1/6R1/8 b - - 0 1",
	"11": "8/8/5K2/5B1k/8/8/5r2/6R1 b - - 0 1",
	"12": "8/8/8/7k/7b/3K4/1r6/7R w - - 0 1",
	"13": "8/8/8/2K5/Q7/P7/2k5/5q2 b - - 0 1",
	"14": "2K5/2P2k2/8/8/8/6Q1/1q6/8 b - - 0 1",
	"15": "Q7/8/8/5p2/3K2k1/8/8/5q2 b - - 0 1",
	"16": "4R3/8/8/6n1/2r5/K7/2k5/8 w - - 0 1",
	"17": "8/1k6/8/3K4/3N3R/8/8/3r4 b - - 0 1",
	"18": "3R4/8/8/1K3n2/7k/8/2r5/8 w - - 0 1",
	"19": "8/8/8/3R2KP/8/8/6k1/5q2 w - - 0 1",
	"20": "8/8/8/8/5KQ1/4r1p1/5k2/8 b - - 0 1",
}

FEN_ENDGAME_9 = {
	"1": "8/8/4kp2/7p/R6P/5K2/Pr2P3/8 w - - 0 1",
	"2": "5k2/R4ppp/8/4r1P1/7P/8/6K1/8 w - - 0 1",
	"3": "8/8/R7/2rk1pp1/8/5P2/P4KP1/8 b - - 0 1",
	"4": "6k1/B1P5/5p2/6p1/6bp/P7/6K1/8 b - - 0 1",
	"5": "4bB2/3k3K/6p1/pp6/6P1/8/7P/8 b - - 0 1",
	"6": "8/5pk1/3b1p2/p7/2P5/8/2B1P1K1/8 b - - 0 1",
	"7": "4k3/R4p1p/6p1/2K5/p1P4r/8/8/8 w - - 0 1",
	"8": "7k/p7/7p/r1P4p/4R3/4p3/8/4K3 w - - 0 1",
	"9": "8/8/5R2/3k1P2/p5P1/4PK2/7P/r7 b - - 0 1",
	"10": "8/8/3k4/Pp1b4/6r1/8/P1R4K/4R3 b - - 0 1",
	"11": "1R6/8/5pk1/6p1/2r3r1/4BK2/5P2/8 w - - 0 1",
	"12": "4R3/2r3k1/5p2/4bP1R/7P/5K2/8/8 b - - 0 1",
	"13": "8/3k4/8/B3R3/P1r2P2/KP3r2/8/8 w - - 0 1",
	"14": "4r3/4r3/5R1k/8/4B1P1/4PK2/4P3/8 b - - 0 1",
	"15": "8/3pR1R1/1kb4K/1pp5/8/1r6/8/8 w - - 0 1",
	"16": "7Q/5p2/4p1kp/r7/8/r5P1/6K1/8 w - - 0 1",
	"17": "8/8/1NP1k3/8/2N1pp2/8/5K1n/5n2 w - - 0 1",
	"18": "5k2/5p2/4n2p/NN2K3/7n/1P6/8/8 b - - 0 1",
	"19": "8/5k2/5p2/8/7P/3KBPP1/8/1r1n4 w - - 0 1",
	"20": "3R4/5pk1/4pNb1/4P3/8/1p6/8/2K5 b - - 0 1",
}

output_folder = pathlib.Path("./output")
if not output_folder.exists():
	output_folder.mkdir()

# Sample FEN image
output_folder.joinpath("sample_board.png").write_bytes(cbi.generate_bytes(SAMPLE_FEN, IMAGE_SIZE, show_coordinates=True))

opening_output_folder = output_folder.joinpath("openings")
opening_output_folder.mkdir(exist_ok=True)

for i, f in enumerate(FEN_OPENINGS.keys()):
	opening_output_folder.joinpath(f"opening_{i:02d}_{f}.png").write_bytes(
		cbi.generate_bytes(FEN_OPENINGS[f], IMAGE_SIZE, show_coordinates=True)
	)

endgame_5_output_folder = output_folder.joinpath("endgame5")
endgame_5_output_folder.mkdir(exist_ok=True)

for i, f in enumerate(FEN_ENDGAME_5.keys()):
	endgame_5_output_folder.joinpath(f"endgame5_{i:02d}_{f}.png").write_bytes(
		cbi.generate_bytes(FEN_ENDGAME_5[f], IMAGE_SIZE, show_coordinates=True)
	)

endgame_9_output_folder = output_folder.joinpath("endgame9")
endgame_9_output_folder.mkdir(exist_ok=True)

for i, f in enumerate(FEN_ENDGAME_9.keys()):
	endgame_9_output_folder.joinpath(f"endgame9_{i:02d}_{f}.png").write_bytes(
		cbi.generate_bytes(FEN_ENDGAME_9[f], IMAGE_SIZE, show_coordinates=True)
	)
