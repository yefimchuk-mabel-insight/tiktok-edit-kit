# Timing, sync and the loop

## The frame grid
- The edit is 30 fps. An event at frame `k` gets time `k/30 − 0.001`. The 1 ms margin stops float rounding from pushing it into the next frame.
- In a sub-composition, times are relative: `rel = (k/30 − 0.001) − sceneStart`. A scene's start and duration should also be on the grid.
- Render at 60 fps, then run `scripts/finish.py`. It blends frame pairs (2m, 2m+1) and keeps the odd one. A cut on the 30 fps grid therefore stays a clean cut: no blended frame and no 1-frame lag.

## Which sound, and how long
- **The user adds the sound in TikTok**, so the file you deliver is silent. TikTok plays the sound from its own start and loops the video when the **sound** ends.
- **The best guide is a TikTok video that already uses the sound.** Its audio is exactly what plays. Extract it with `ffmpeg -i upload.mp4 -vn guide.wav` and run `scripts/beatgrid.py guide.wav`.
- **The video length is the sound length.** Cut trailing silence; `beatgrid.py` reports the last audible moment. If the video runs longer, it shows a silent tail. If it is shorter, the music restarts mid-phrase.

## Offset between a guide and the TikTok sound
Sometimes the beats were measured on a screen recording or another copy of the song that starts at a different point:
- **On the user's TikTok upload,** `scripts/sync.py upload.mp4 render.mp4 guide.wav` prints the sound shift (ms), the picture shift (frames) and the sound-vs-picture error. Aim for under ±20 ms.
- **To apply a shift of N frames,** hold the first shot N frames longer and start every later scene N frames later. Add N to every `HITS` frame, and keep the total length equal to the sound.
- **Never rotate the finished loop** to fake an offset. The video would then open on its end card.

## The seamless loop
- The end card returns to the exact first frame of the intro: same element, same scale and rotation, no text.
- Check it with `scripts/verify.py final.mp4`. The seam SSIM (last frame vs. first frame) should be ≥ 0.9.
- A cut on the loop point is fine if it lands on a beat. A jump that doesn't is what users notice.

## When the user says "it's not on the beat"
1. **Check the delivered file.** Do cuts sit on the grid? Look at the frames around each cut (`ffmpeg -ss <t> -i final.mp4 -frames:v 8 f%d.png`, or `analyze.py`'s `events.jpg` in the full kit) for blended or late frames.
2. **Check that the video starts with the sound.** Use `sync.py` on their upload.
3. **Check the flash.** It should be 1–2 frames, flat white over the new shot. A flash that is late or too long reads as off-beat.
4. **Check the length.** A silent tail makes the loop feel off.

Explain what you found before changing anything.
