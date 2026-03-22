"""Gambit Solver Exceptions"""


class NoKingException(Exception):
	"""No King found on Board"""

	pass


class CheckmateException(Exception):
	"""No solution can be found. Player is in Checkmate"""

	pass


class StalemateException(Exception):
	"""No solution can be found, but player is not in Check."""

	pass
