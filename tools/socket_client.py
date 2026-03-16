"""Tool to test sending data to a Gambit IPC server"""

import argparse
import errno
import importlib.util
import socket

if importlib.util.find_spec("readline") is not None:
	import readline  # type: ignore # noqa: F401


class ArgNamespace(argparse.Namespace):
	"""Argument parser namespace for type hinting"""

	port: str


def main() -> None:
	"""Main function"""
	parser = argparse.ArgumentParser()
	parser.add_argument("-p", "--port", action="store", dest="port", help="Destination port", default="8081")
	args = parser.parse_args(namespace=ArgNamespace())

	dest_ip = "localhost"
	dest_port: int = int(args.port)

	sock: socket.socket

	try:
		while True:
			data = input("Enter command > ")
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			try:
				sock.connect((dest_ip, dest_port))
				sock.send(data.encode("utf-8"))
				sock.shutdown(socket.SHUT_WR)
				response = sock.recv(1000)
				try:
					sock.shutdown(socket.SHUT_RDWR)
				except OSError as exc:
					if exc.errno == errno.ENOTCONN:
						pass  # Socket is not connected, so can't send FIN packet.
					else:
						raise
				sock.close()
				print(f"Response: {response.decode('utf-8')}")
			except (ConnectionRefusedError, TimeoutError):
				print(f"Unable to connect to {dest_ip}:{dest_port}. Check if target server is running.")
	except KeyboardInterrupt:
		print("\nCaught keyboard interrupt. Exiting")


if __name__ == "__main__":
	main()
