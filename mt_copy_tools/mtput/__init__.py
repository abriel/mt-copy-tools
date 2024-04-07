import sys
import hashlib
from os import path, get_terminal_size
from math import ceil
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, wait
from threading import get_ident
from mt_copy_tools.sftp import SftpClientPool
from mt_copy_tools.cli import parse_args

def upload_part(sftp_client_fn, source_path, remote_path, start_position, length, algo=None):
  sftp_client = sftp_client_fn(get_ident())

  with open(source_path, 'rb') as source_fd:

    try:
      try:
        target_fd = sftp_client.open(remote_path, 'r+b')
      except FileNotFoundError:
        sftp_client.mkdir_p(path.dirname(remote_path))
        target_fd = sftp_client.open(remote_path, 'x+b')
    except FileExistsError:
      target_fd = sftp_client.open(remote_path, 'r+b')
    except OSError as e:
      if set(('File already exists', 'Failure')) & set(e.args):
        target_fd = sftp_client.open(remote_path, 'r+b')
      else:
        raise(e)

    try:
      source_fd.seek(start_position)
      buf = source_fd.read(length)

      if algo:
        for retry in range(3):
          if sftp_client.stat(remote_path).st_size > start_position:
            target_hash = target_fd.check_as_file(algo, start_position, length)
            hash_mismatch = target_hash != getattr(hashlib, algo)(buf).digest()
          else:
            hash_mismatch = True

          if hash_mismatch:
            if retry < 2:
              target_fd.seek(start_position)
              target_fd.write(buf)
            else:
              raise BufferError("Integrity check fails after multiple retries")
          else:
            break

      else:
        target_fd.seek(start_position)
        target_fd.write(buf)

    finally:
      target_fd.close()

  return len(buf)

def progress(future):
  progress.total_done += future.result()

  elapsed_time = datetime.now() - progress.start_time
  try:
    speed = progress.total_done // elapsed_time.seconds
  except ZeroDivisionError:
    speed = 1
  estimated_time = timedelta(seconds=((progress.total_expected - progress.total_done) // speed))

  sys.stdout.write(
    '\r{} % uploaded, {} KB/s, ELAPS {}, ETA {}'.format(
      round(progress.total_done / progress.total_expected * 100, 2),
      round(speed / 1024, 2),
      str(elapsed_time).split('.')[0],
      estimated_time
    ).ljust(get_terminal_size().columns)
  )

def main():
  args = parse_args()

  try:
    sys.stdout.write('Creating pool of {} connections\n'.format(args.threads))
    sftp_client_pool = SftpClientPool(args.destination_host,
                                      username=args.username, port=args.port, key=args.key,
                                      delay=args.start_delay, pool_size=args.threads)
  except Exception as e:
    sys.stderr.write(str(e) + '\n')
    sys.exit(1)

  if args.algo and args.algo not in sftp_client_pool.pop().supported_integrity_algos:
    sys.stderr.write('Server does not support {} for integrity check. Hence ignoring.\n'.format(args.algo))
    args.algo = None

  sys.stdout.write('Starting upload...\n')

  futures = []
  progress.total_done = 0
  progress.total_expected = 0

  with ThreadPoolExecutor(max_workers=args.threads) as executor:
    progress.total_expected += path.getsize(args.source_path)
    progress.start_time = datetime.now()
    parts = ceil(path.getsize(args.source_path) / args.chunk_size)
    for i in range(parts):
      future = executor.submit(upload_part, sftp_client_pool.sticky, args.source_path, args.destination_path,
                               i * args.chunk_size, args.chunk_size, algo=args.algo)
      future.add_done_callback(progress)
      futures.append(future)

  wait(futures)
