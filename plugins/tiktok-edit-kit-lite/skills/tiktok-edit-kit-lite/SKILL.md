---
name: tiktok-edit-kit-lite
description: Makes beat-synced kinetic-text TikTok, Reels and Shorts videos with HyperFrames (HTML + GSAP → MP4) from a sound and a few lines of words. Big condensed captions land on the beats, slams flash and shake, phrases whip out, the video ends with the sound and loops without a seam. Use it when someone asks for a lyric video, a quote or text edit, a kinetic typography TikTok, or wants an edit that is "on the beat", or needs to measure a song's beats for a video.
---

# TikTok edit kit — Lite

Kinetic-text edits that land on the beat. This is the free edition: one style (`kinetic`) and the core tools that
keep any edit on the beat. The Pro edition adds four more styles (velocity/phonk, cinematic, collage, dossier) and
reference matching: give it any edit and it measures and rebuilds that style.

**Requirements:** Node 22+ (for the HyperFrames CLI), ffmpeg, and Python 3 with numpy. macOS, Windows and Linux are all supported.
**First run on a machine:** `node scripts/doctor.mjs`. If it reports anything missing, show the user the list and run
`node scripts/doctor.mjs --fix` only after they agree. Then run `python3 -I scripts/selftest.py`; it should print "All good".
On Windows use `py` where this file says `python3`.

**Network and safety:** the scripts only read local files and call ffmpeg. The template loads GSAP from `cdn.jsdelivr.net`,
which is the standard HyperFrames setup. Nothing is uploaded anywhere.

## Workflow
1. **Talk first.** Confirm the words, the exact sound (ideally a TikTok that uses it) and the length.
2. **Measure the sound:** `python3 -I scripts/beatgrid.py <sound> --words "WE WERE NEVER | so_we KEPT RUNNING!"`. It prints the
   video length in frames, the tempo and a ready `WORDS` list (`|` starts a phrase, `_` joins words, `!` slams, `^` makes a word red, and lowercase words are soft).
   **The video ends with the sound.**
3. **Copy `styles/kinetic/template/`** to a new project folder and read [`styles/kinetic/STYLE.md`](styles/kinetic/STYLE.md). Paste `WORDS`, `LENGTH` and `OUT_AT`
   into `compositions/kinetic.html`, and set `data-duration` in `index.html` to `LENGTH`.
4. **Check:** run `npx hyperframes check --json`, fix the errors, then snapshot a few frames and look at them.
5. **Preview first, render last.** `python3 scripts/preview.py sheet` gives a contact sheet in seconds, and `python3 scripts/preview.py draft` gives a fast MP4.
   `npx hyperframes preview` is a live, scrubbable preview. Run the final render only after the user says OK. `python3 -I scripts/review.py out/final.mp4`
   builds one page with the video and links to every file: open it for the user.
6. **Render and finish:**
   `npx hyperframes render --quality looks --fps 60 -o out/raw60.mp4`, then `python3 scripts/finish.py out/raw60.mp4 out/final.mp4`.
7. **Verify before saying "done":** `python3 -I scripts/verify.py out/final.mp4 --hits <slam frames> --length-frames <N>`. Report the result.
8. **Deliver** the silent video. The user adds the sound inside TikTok, so it plays from the start and the loop restarts with it.

## Core rules (each one is a mistake that already happened)
- **Put every event on the 30 fps frame grid:** time = `frame/30 − 0.001`. Off-grid times make hits land a frame late.
- **Don't change the frame pairing in `finish.py`.** It blends pairs (2m, 2m+1), so a cut stays clean.
- **A flash is ~0.9 white for 1 frame over the new line, exactly on the beat.** The vignette sits under it, in the composition.
- **The video is exactly as long as the TikTok sound.** If it runs longer, it plays in silence and the ending looks broken.
- **Apply a sync offset by shifting `WORDS`.** Never rotate the rendered loop.
- **Keep text in the safe area** (y 360–1440 and x 90–990 on 9:16), and write 1–2 words per line.
- **"Looks bad" means improve it, not delete it.** Use only words the user has the right to use.

Details on sync, TikTok sound length and the loop: [`references/timing-and-sync.md`](references/timing-and-sync.md).

## Scripts
| Script | What it does |
|---|---|
| `doctor.mjs [--fix]` | checks Node, ffmpeg, Python and numpy, and prints (or runs) the install commands for your OS |
| `selftest.py` | builds a test video with known beats and flashes, then checks that the tools find them |
| `beatgrid.py <sound> [--words …] [--offset-ms]` | sound → video length, tempo, onsets as frames, and a `WORDS` list |
| `finish.py <raw60> <out>` | 60 → 30 fps motion blur, bloom, grain, crushed blacks |
| `preview.py sheet\|draft\|final` | the preview ladder: a contact sheet (seconds), a draft MP4 (fast) and the final render |
| `review.py <video>` | one review page with the video and file links |
| `verify.py <video> --hits … --length-frames N` | checks the frame count, the flash brightness and the loop seam |
| `sync.py <upload> <render> <guide>` | compares a posted TikTok's sound with its picture, in ms |
