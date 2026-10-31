# Tiny DLNA

A tiny DLNA sender & receiver.

## Install

```
$ cargo install --path .
```

This installs two binaries: `tiny-render` and `tiny-cli`.

## Usage for Tiny DLNA Render

Just to support subtitles.

```
$ tiny-render
```

This will activate a DLNA receiver named "Tiny Render", which can stream videos
from apps like 虎牙直播, Bilibili, and other video platforms. Additionally, you
can also use `tiny-cli play` (see below) to play local videos (like in your
RaspberryPi) on it.

Options:

```
--name <NAME>     Specify render name
--port <PORT>     Server port (default: 59876, or 59877 when recording)
--dump-to <FILE>  Save the stream into a file (see below)
--http-logs       Enable HTTP and SSDP server logs
-v, --verbose     Enable debug logs
```

### Save video streaming into a file (Stream Recording)

```
$ tiny-render --dump-to ~/Movie/lol-msi-2024.mp4
```

The recorder shows up as "Tiny Recorder". It records one stream: once the
sender stops (or plays something else), the recorder quits and leaves mpv
running so the recording can finish.

## Usage for Tiny DLNA Cli

List the names of available DLNA devices:
```
$ tiny-cli list
```

List devices with all their attributes (location, control URL, USN, ...) as
JSON:
```
$ tiny-cli list -v
```

Play a local video file on a DLNA device having "TV" in its name:
```
$ tiny-cli play ~/Movies/foo/bar.mp4 -q TV
```

If there is a `bar.srt` in the same directory, it will be served as long as
the DLNA render supports subtitles. Use `--title` to override the title shown
on the device. Press `Ctrl-C` to stop playing.

An `http://` or `https://` URL can be played the same way:
```
$ tiny-cli play 'https://example.com/live.m3u8' -q TV
```

Stop the streaming on a device:
```
$ tiny-cli stop -q TV
```

When a video is playing, you can issue a `seek` command to adjust its position:
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

### Network

Devices find each other with SSDP (UDP multicast on port 1900), so the firewall
should allow it. `tiny-cli play` serves the video from a random TCP port in the
50000–58999 range; `tiny-render` listens on 59876 (59877 when recording) unless
`--port` is given.

## Files

Both tools keep their state in `~/.config/tiny-dlna/`:

- `tiny-render.json`: the render's UUID, so devices recognize it across
  restarts.
- `live-renders.json`: renders running on this machine. Several renders can run
  at once (on different ports), and discovery replies cover all of them.

## Dev

```
$ cargo run --bin tiny-cli -- -h
$ cargo run --bin tiny-render -- -h
$ cargo test
```
