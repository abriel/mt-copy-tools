import sys
from os import environ, path
from argparse import ArgumentParser
from argparse import ArgumentDefaultsHelpFormatter

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

class MyParser(ArgumentParser):
  def error(self, message):
    sys.stderr.write("ERROR: {}\n\n".format(message))
    self.print_help(sys.stderr)
    sys.exit(2)

def parse_args():
  parser = MyParser(formatter_class=ArgumentDefaultsHelpFormatter)
  parser.add_argument(
    '-i', '--key', type=str, default=path.join(environ.get('HOME', ''), '.ssh', 'id_rsa'),
    help='Ssh key for authorization')
  parser.add_argument(
    '-a', '--algo', type=str, choices=('md5', 'sha1', 'sha256', 'sha512'), default=None,
    help='Algorithm for integrity check')
  parser.add_argument('-p', '--port', type=int, default=22, help='Port for sftp connection')
  parser.add_argument('-t', '--threads', type=int, default=10, help='Number of threads')
  parser.add_argument('-d', '--start-delay', type=float, default=0.2, help='Delay of a thread start in seconds')
  parser.add_argument('-c', '--chunk-size', type=int, default=4096, help='Chunk size to read and transfer. KB')
  parser.add_argument('source', help='Source. Local file or remote in format [username@]<hostname>:<path>')
  parser.add_argument('destination', help='Destination. Local file or remote in format [username@]<hostname>:<path>')
  args = parser.parse_args()

  args.chunk_size *= 1024

  if path.exists(args.source):
    args.direction = 'upload'
    args.username, args.remote_host, args.remote_path = parse_remote_definition(args.destination)
    args.local_path = args.source
    if args.remote_path.endswith('/') or args.remote_path == '':
      args.remote_path = path.join(args.remote_path, path.basename(args.local_path))

  elif path.exists(path.dirname(path.realpath(args.destination))):
    args.direction = 'download'
    args.username, args.remote_host, args.remote_path = parse_remote_definition(args.source)
    args.local_path = args.destination
    if path.isdir(args.local_path):
      args.local_path = path.join(args.local_path, path.basename(args.remote_path))

  else:
    print(
      "Neither {} nor {} exists locally".format(args.source, path.dirname(args.destination)),
      file=sys.stderr
    )
    sys.exit(3)

  return args
