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

def download_part(sftp_client_fn, local_path, remote_path, start_position, length, algo=None):
  sftp_client = sftp_client_fn(get_ident())

  with sftp_client.open(remote_path, 'rb') as source_fd:

    try:
      try:
        target_fd = open(local_path, 'r+b')
      except FileNotFoundError:
        target_fd = open(local_path, 'x+b')
    except FileExistsError:
      target_fd = open(local_path, 'r+b')
    except OSError as e:
      raise(e)

    try:
      if algo:
        source_hash = source_fd.check_as_file(algo, start_position, length)

        for retry in range(3):
          target_fd.seek(start_position)
          test_chunk = target_fd.read(length)
          hash_mismatch = source_hash != getattr(hashlib, algo)(test_chunk).digest()

          if hash_mismatch:
            if retry < 2:
              buf_length = copy_chunk(source_fd, target_fd, start_position, length)
            else:
              raise BufferError("Integrity check fails after multiple retries")
          else:
            buf_length = len(test_chunk)
            break

      else:
        buf_length = copy_chunk(source_fd, target_fd, start_position, length)

    finally:
      target_fd.close()

  return buf_length

def copy_chunk(source_fd, target_fd, start_position, length):
  source_fd.seek(start_position)
  target_fd.seek(start_position)
  buf = source_fd.read(length)
  target_fd.write(buf)
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
  sys.stdout.flush()

def main():
  args = parse_args()

  try:
    sys.stdout.write('Creating pool of {} connections\n'.format(args.threads))
    sftp_client_pool = SftpClientPool(args.remote_host,
                                      username=args.username, port=args.port, key=args.key,
                                      delay=args.start_delay, pool_size=args.threads)
  except Exception as e:
    sys.stderr.write(str(e) + '\n')
    sys.exit(1)

  if args.algo and args.algo not in sftp_client_pool.pop().supported_integrity_algos:
    sys.stderr.write('Server does not support {} for integrity check. Hence ignoring.\n'.format(args.algo))
    args.algo = None

  sys.stdout.write('Starting {}...\n'.format(args.direction))

  futures = []
  progress.total_done = 0
  progress.total_expected = 0

  if args.direction == 'upload':
    worker_func = upload_part
    progress.total_expected = path.getsize(args.local_path)
  else:
    worker_func = download_part
    progress.total_expected = sftp_client_pool.pop().stat(args.remote_path).st_size

  with ThreadPoolExecutor(max_workers=args.threads) as executor:
    progress.start_time = datetime.now()
    parts = ceil(progress.total_expected / args.chunk_size)
    for i in range(parts):
      future = executor.submit(worker_func, sftp_client_pool.sticky, args.local_path, args.remote_path,
                               i * args.chunk_size, args.chunk_size, algo=args.algo)
      future.add_done_callback(progress)
      futures.append(future)

  wait(futures)
