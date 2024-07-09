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
do following:

```
$ ln -sf /Applications/mpv.app/Contents/MacOS/mpv /usr/local/bin/
```

## Tiny DLNA Cli

List available DLNA devices:
```
$ tiny-cli list
```

## Related projects

- https://github.com/xfangfang/Macast
- https://github.com/gabrielmagno/nano-dlna
