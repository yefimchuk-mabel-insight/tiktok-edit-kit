# Style: kinetic text

Vertical 1080×1920. Big condensed caps land one line per beat and stack into a block that fills the width.
Small serif lowercase "breath" words give contrast. Slams get a flash and a shake. Each phrase whips toward the camera
and out. No images are needed, so the style fits any song, quote or message.

## Look
- **Colours.** Paper #0a0a0a, ink #f4f1ea (warm white), one accent #ff2d2d. `inv` lines flip to light paper with black ink.
- **Type.**
  - Lines use League Gothic, condensed caps, fitted to the full text width (840 px).
  - Slams use Archivo Black.
  - Breath words use EB Garamond lowercase at 62 % width.
  - Mono meta is Space Mono at 28 px: a `01 / 18` counter; a signature only if the user asks for one.
  - All of these fonts are bundled with HyperFrames.
- **Safe area.** Text stays within y 360–1440 and x 90–990. TikTok's top bar, caption and buttons cover the rest. A tall stack shrinks to fit (`MAXBLOCK`).
- **Grain and vignette.** Light grain, a vignette under the flash, and `finish.py` for motion blur and bloom.

## Motion (all deterministic, all on the frame grid)
- **New line.** The new line pops in: scale 1.22 → 1, expo-out, 0.12 s. A slam pops from 1.45. The stack slides up to re-centre over 0.14 s.
- **Soft words.** They type in over 0.2 s with a scrambled edge.
- **Slam.** A 1-frame flash at 0.9 white, plus a 6-frame shake that decays from about 19 px.
- **Phrase end.** In the 5 frames before the next `new`, the block zooms 1 → 2.6, blurs and fades.
- **Hold.** The block drifts 1 → 1.03 while a phrase holds. Nothing is fully still.
- **Loop.** The film starts on black and ends on black after `OUT_AT`, so the seam can't be seen.

## Data
All of the timing is in `compositions/kinetic.html`:
```js
const WORDS = [[frame, "TEXT", "flags"], ...];   // flags: new big soft red inv
const LENGTH = 8;  const OUT_AT = 226;
```
`scripts/beatgrid.py <sound> --words "WE WERE NEVER | so_we KEPT RUNNING!"` places the words on the onsets for you. In that string:
- `|` starts a new phrase;
- `_` joins words into one line;
- `!` marks a slam;
- `^` marks a red word;
- lowercase makes a soft word.

Also set the root `data-duration` and the clip `data-duration` in `index.html` and `kinetic.html` to `LENGTH`.

## Rules
- **Write one or two words per line.** A long line becomes tiny when it's fitted to the width.
- **Keep slams rare,** two or three per phrase at most. If everything slams, nothing does.
- **Use a `new` phrase on a strong onset at least ~18 frames after the last word,** which gives room for the whip. `beatgrid.py --words` does this for you.
- **Use your own words or lyrics you have the rights to.** The sound itself is added in TikTok.
