"""Tool to test sending data to a Gambit IPC server"""

import argparse
import socket


def main() -> None:
	"""Main function"""
	parser = argparse.ArgumentParser()
	parser.add_argument("-p", "--port", action="store", dest="port", help="Destination port")
	args = parser.parse_args()

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
				sock.shutdown(socket.SHUT_RDWR)
				sock.close()
				print(f"Response: {response.decode('utf-8')}")
			except (ConnectionRefusedError, TimeoutError):
				print(f"Unable to connect to {dest_ip}:{dest_port}. Check if target server is running.")
	except KeyboardInterrupt:
		print("\nCaught keyboard interrupt. Exiting")


if __name__ == "__main__":
	main()
