# Multi Thread Copy Tools

Upload / Download a file(s) to a remote using multiple connections at a time.

`mtput` comes from the package does upload a given file.

Supported remote protocols:
* SFTP


# Why?

Some Internet Service Providers apply a shaper for an outbound traffic in a way,
that each established connection has a quite low speed, but you are not limited with number of connections.
Thus, leveraging multiple connections gives a good speed.
Good example is a torrent, which makes a tens connections to different remotes and downloads a file by pieces.

But what if you need to upload a huge file from your laptop to a backup server?
That is when the `mtput` comes into the play.


# SFTP Notes

Using `proftpd` as a server (version >= 1.3.9) enables a resume feature.
Proftpd provides a feature to calculate a hash sum for a file pieces on a server side and return to a client.
Thus, `mtput` knows what parts are uploaded already and where to resume from.

Proftpd related issues: [1570](https://github.com/proftpd/proftpd/issues/1570), [1569](https://github.com/proftpd/proftpd/issues/1569)

Compatible with openssh, without resume and checksum validation. This limitation is possible to overcome by using `mt-copy-tools-cs`.
Compile it and place under a $PATH on a remote server, e.g. in `/usr/local/bin`.


# Installation

### Linux / MacOS

```
$ poetry install
$ poetry build --format=wheel
$ pip install dist/mt_copy_tools-0.1.0-py3-none-any.whl
```

### Build for Windows (under Linux)

Prerequisites:
* wine (with WINEARCH=win32 and custom WINEPREFIX)
* [upx](https://github.com/upx/upx) installed in wine by the `C:/upx` path
* python 3.4.4 installed in wine by the `C:/Python34` path (https://www.python.org/downloads/release/python-344/)

```
$ make wine_setup
$ make build_exe
```

Result binary is `dist/mtput.exe` which should work on Windows XP and newer


# Limitations

* There is `mtput` only
* Upload a single file only is supported
* Only one remote protocol is supported
