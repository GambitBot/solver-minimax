"""Benchmark solution module solution times"""

# Run benchmark with "python -u" flag for unbuffered STDOUT

import time

import solver

# Opening FEN states taken from: https://www.365chess.com/chess-openings/
FEN_OPENINGS = {
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


print("Gambit Solution Module Performance Benchmark")
board = solver.board.Board()
start_time = 0.0
print("Endgame states (5 pieces remaining)")
depth = 6
for k in FEN_OPENINGS:
	print(f"{k}", end="")
	board.reset()
	results = [0.0] * depth
	for d in range(0, depth):
		board.load_fen_string(FEN_OPENINGS[k], True)
		start_time = time.time()
		board.solve(d + 1)
		results[d] = time.time() - start_time
		print(f",{results[d]}", end="")
	print("")  # Make sure we have a line break
