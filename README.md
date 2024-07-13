# Tiny DLNA

## Install

```
$ pip install tiny-dlna
```

## Tiny DLNA Render

Just to support subtitles.

```
$ tiny-render
```

This will activate a DLNA receiver named "Tiny Render", which can stream videos
from apps like 虎牙直播, Bilibili, and other video platforms. Additionally, you
can also use `nano-dlna` to play local videos (like in your RaspberryPi) on it.

Note that [mpv](https://mpv.io/) needs to be installed on your system. On Mac,
do following (for Windows, add the mpv's root into PATH):

```
$ ln -sf /Applications/mpv.app/Contents/MacOS/mpv /usr/local/bin/
```

## Tiny DLNA Cli

List available DLNA devices:
```
$ tiny-cli list
```

Play a local video file on a DLNA device having "TV" in its name:
```
$ tiny-cli play ~/Movies/foo/bar.mp4 -q TV
```

If there is a `bar.srt` in the same directory, it will be served as long as
the DLNA device supports subtitles.

## Dev

```
$ python -m tiny_dlna.tiny_cli -h
$ python -m tiny_dlna.tiny_render -h
```

### More DLNA Actions, like Seek/Pause?

This repository will be kept minimal. For additional DLNA actions, consider
forking it.

## Related projects

- https://github.com/xfangfang/Macast
- https://github.com/gabrielmagno/nano-dlna
