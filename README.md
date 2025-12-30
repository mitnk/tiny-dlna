# Tiny DLNA

[![PyPI](https://img.shields.io/pypi/v/tiny-dlna.svg)](https://pypi.org/project/tiny-dlna/)

## Install

```
$ pip install tiny-dlna
```

## Usage for Tiny DLNA Render

Just to support subtitles.

```
$ tiny-render
```

This will activate a DLNA receiver named "Tiny Render", which can stream videos
from apps like 虎牙直播, Bilibili, and other video platforms. Additionally, you
can also use `tiny-cli play` (see below) to play local videos (like in your
RaspberryPi) on it.

### Save video streaming into a file (Stream Recording)

```
$ tiny-render --dump-to ~/Movie/lol-msi-2024.mp4
```

## Usage for Tiny DLNA Cli

List available DLNA devices:
```
$ tiny-cli list
```

Play a local video file on a DLNA device having "TV" in its name:
```
$ tiny-cli play ~/Movies/foo/bar.mp4 -q TV
```

If there is a `bar.srt` in the same directory, it will be served as long as
the DLNA render supports subtitles.

Stop the streaming on a device:
```
$ tiny-cli stop -q TV
```

When a video is playing, you can issue a `seek` command to adjust its postion:
```
$ tiny-cli seek '00:17:25' -q TV
```

## Requirements for your System

### For Render

For running the render, [mpv](https://mpv.io/) needs to be installed. On Mac,
you may do following:

```
$ ln -sf /Applications/mpv.app/Contents/MacOS/mpv /usr/local/bin/
```

For Windows, after installed mpv, add `mpv.exe`'s directory [into
PATH](https://stackoverflow.com/a/2571200/665869).

### For Cli

On Windows, you need [config your current
user](https://stackoverflow.com/a/65504258/665869) to have permission to create
soft links:

1. Open gpedit.msc
2. Computer Configuration → Windows Settings → Security Settings → Local
   Policies → User Rights Assignment → Create symbolic links
3. Type the user name (checkout `whoami` command) and click “Check Names” then
   OK.
4. Reboot the computer

You can also use [Develper Mode](https://stackoverflow.com/a/76292992/665869) I
guess.


## Dev

```
$ python -m tiny_dlna.tiny_cli -h
$ python -m tiny_dlna.tiny_render -h
```
