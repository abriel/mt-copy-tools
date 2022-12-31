import os
import struct
from time import sleep
from random import random
from socket import create_connection
from paramiko.transport import Transport
from paramiko.ssh_exception import SSHException
from paramiko.dsskey import DSSKey
from paramiko.rsakey import RSAKey
from paramiko.ecdsakey import ECDSAKey
from paramiko.ed25519key import Ed25519Key
from paramiko.sftp_file import SFTPFile
from paramiko.sftp_client import SFTPClient
from paramiko.sftp import CMD_EXTENDED, CMD_VERSION, CMD_INIT, _VERSION
from paramiko.transport import Transport
from paramiko.py3compat import long

class TransportNg(Transport):
  def open_sftp_client(self):
    return SFTPClientNg.from_transport(self)

class SFTPClientNg(SFTPClient):
  def open(self, filename, mode="r", bufsize=-1):
    sftp_file = super().open(filename, mode, bufsize)
    sftp_file.name = self._adjust_cwd(filename)
    sftp_file.__class__ = SFTPFileNg
    return sftp_file

  def _send_version(self):
    self._send_packet(CMD_INIT, struct.pack(">I", _VERSION))
    t, data = self._read_packet()
    if t != CMD_VERSION:
      raise SFTPError("Incompatible sftp protocol")
    version = struct.unpack(">I", data[:4])[0]

    # Ugly test for capabilities
    self.extensions = {}
    try:
      self._request(CMD_EXTENDED, 'check-file-name', str(random()), 'md5', long(0), long(32), 0)
      self.extensions['check-file'] = ['sha1', 'md5']
    except Exception as e:
      if set(('Invalid parameter', 'No such file')) & set(e.args):
        self.extensions['check-file'] = ['sha1', 'md5']

    return version

  def mkdir_p(self, path):
    to_be_created = []
    parent_folder = path
    while True:
      try:
        self.stat(parent_folder)
        break
      except FileNotFoundError as e:
        to_be_created.append(parent_folder)
        parent_folder = os.path.dirname(parent_folder)
        if not parent_folder:
          break

    to_be_created.reverse()
    for dirname in to_be_created:
      try:
        self.mkdir(dirname)
      except OSError as e:
        if set(('File already exists', 'Failure')) & set(e.args):
          pass
        else:
          raise(e)

class SFTPFileNg(SFTPFile):
  def check_as_file(self, hash_algorithm, offset=0, length=0, block_size=0):
    t, msg = self.sftp._request(
      CMD_EXTENDED,
      "check-file-name",
      self.name,
      hash_algorithm,
      long(offset),
      long(length),
      block_size,
    )
    msg.get_text()  # alg
    data = msg.get_remainder()
    return data

class SftpClientPool():
  def __init__(self, host, port=22, username='', key=None, delay=None, pool_size=5):
    self.index = 0
    self.pool = []
    self.sticky_pool = {}

    for pkey_cls in [DSSKey, RSAKey, ECDSAKey, Ed25519Key]:
      try:
        pkey = pkey_cls.from_private_key_file(key)
        pkey.sign_ssh_data(b'testdata')
        break
      except (SSHException, ValueError):
        pass

    for i in range(pool_size):
      if delay:
        sleep(delay)

      transport = Transport(create_connection((host, port)))
      transport.connect(username=username, pkey=pkey)
      transport.__class__ = TransportNg
      self.pool.append(transport.open_sftp_client())

  def pop(self):
    self.index += 1

    if self.index >= len(self.pool):
      self.index = 0

    return self.pool[self.index]

  def sticky(self, ident):
    if ident not in self.sticky_pool:
      self.sticky_pool[ident] = self.pop()

    return self.sticky_pool[ident]
