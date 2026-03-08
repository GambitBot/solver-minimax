"""Benchmark solution module solution times"""

# Run benchmark with "python -u" flag for unbuffered STDOUT

import time

import solver

# Opening FEN states taken from: https://www.365chess.com/chess-openings/
FEN_OPENINGS = {
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


print("Gambit Solution Module Performance Benchmark")
board = solver.board.Board()
start_time = 0.0
print("Midgame states (9 pieces remaining)")
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
