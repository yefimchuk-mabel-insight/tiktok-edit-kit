# TikTok Edit Kit: Lite

A free Claude Code plugin for **kinetic-text TikTok, Reels and Shorts videos**, made with [HyperFrames](https://hyperframes.heygen.com)
(HTML + GSAP rendered to MP4). Give it a sound and a few lines of words. Big captions land on the beat, slams flash and shake,
phrases whip out, the video ends with the sound and loops without a seam.

![Kinetic text demo](docs/kinetic.gif)

## Install (two commands in Claude Code)

```
/plugin marketplace add yefimchuk-mabel-insight/tiktok-edit-kit
/plugin install tiktok-edit-kit-lite@tiktok-edit-kit
```

Then just ask: *"make a kinetic text TikTok of these lines to my sound"*. On the first run Claude checks your machine
(`doctor.mjs`) and offers to install what's missing. It runs on **macOS, Windows and Linux**, and needs Node 22+, ffmpeg and Python 3 with numpy.
No Docker and no accounts. Nothing is uploaded.

## What's inside
- `beatgrid.py`: turns the sound into the video length and the beat frames, and places your words on the onsets (`--words "WE WERE | so_we KEPT RUNNING!"`).
- The kinetic style template: condensed caps fitted to the width, soft serif breath words, slams, inverted frames and a phrase whip.
- `finish.py`: motion blur, bloom and grain, without blending cut frames.
- `verify.py`: before you post, checks that the length equals the sound, that the flashes are bright and that the loop seam is clean.
- `sync.py`: measures a real TikTok upload, sound vs. picture in ms.
- `doctor.mjs` and `selftest.py`: a setup check, and a proof the tools work on your machine.
- Rules that come from real complaints: "not on the beat", "the end is silent", "the loop jumps".

## Pro edition
Pro adds **four more styles** (velocity/phonk with speed ramps, cinematic, collage/scrapbook, dark manga dossier) and
**reference matching**. You drop in any edit you like. It measures every cut, flash, camera move, colour and its timing,
writes a numeric style spec, builds yours to match, and scores the result against the reference.

## Licence
MIT. The renders are silent on purpose: add the sound inside TikTok, so it plays from the start and the loop restarts with it.
