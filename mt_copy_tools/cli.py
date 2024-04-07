import sys
from os import environ, path
from argparse import ArgumentParser

def parse_remote_definition(definition):
  try:
    destination_username_host, destination_path = definition.split(':', 1)
  except ValueError as e:
    sys.stderr.write('destination must be set in the hostname:path format\n')
    sys.exit(1)

  try:
    username, destination_host = destination_username_host.split('@', 1)
  except ValueError:
    username = environ.get('USER', None) or environ.get('USERNAME', '')
    destination_host = destination_username_host

  return username, destination_host, destination_path

def parse_args():
  parser = ArgumentParser()
  parser.add_argument(
    '-i', '--key', type=str, default=path.join(environ.get('HOME', ''), '.ssh', 'id_rsa'),
    help='Ssh key for authorization')
  parser.add_argument(
    '-a', '--algo', type=str, choices=('md5', 'sha1', 'sha256', 'sha512'), default=None,
    help='Algorithm for integrity check')
  parser.add_argument('-p', '--port', type=int, default=22, help='Port for sftp connection')
  parser.add_argument('-t', '--threads', type=int, default=10, help='Number of threads')
  parser.add_argument('-d', '--start-delay', type=float, default=0.2, help='Delay of a thread start')
  parser.add_argument('-c', '--chunk-size', type=int, default=4096, help='Chunk size to read and transfer. KB')
  parser.add_argument('source_path', help='Source path')
  parser.add_argument('destination', help='Destination definition as hostname:path')
  args = parser.parse_args()

  args.chunk_size *= 1024

  args.username, args.destination_host, args.destination_path = parse_remote_definition(args.destination)

  return args
