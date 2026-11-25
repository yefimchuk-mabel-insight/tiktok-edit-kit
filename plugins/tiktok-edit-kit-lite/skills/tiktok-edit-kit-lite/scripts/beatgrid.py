"""beatgrid.py — turn a sound into a cut plan on the 30 fps frame grid. The audio is only measured, never muxed.
   python3 -I beatgrid.py <sound.(mp3|wav|m4a|mp4)> [--fps 30] [--offset-ms 0] [--min 0.35]
                          [--words "WE WERE NEVER | so_we KEPT RUNNING!" [--gap 6] [--from 0]]
Prints: sound length → the root data-duration to use, tempo, strong onsets / kicks as frames, and a HITS list
ready to paste into compositions/fx.html. --offset-ms shifts everything (e.g. when your guide audio starts later
than the TikTok sound: measure it with sync.py). Needs ffmpeg + numpy."""
try:                                                       # Windows pipes default to cp1252: print UTF-8 everywhere
    _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
# ── friendly preflight: say what's missing and how to fix it, instead of a traceback
import shutil as _sh, sys as _sys
if not (_sh.which("ffmpeg") and _sh.which("ffprobe")):
    _sys.exit("ffmpeg / ffprobe not found. Run:  node scripts/doctor.mjs   (it prints the install command for your system)")
try:
    import numpy  # noqa: F401
except ImportError:
    _sys.exit("numpy is missing. Run:  python3 -m pip install --user numpy   (or: node scripts/doctor.mjs)")
import sys, subprocess, argparse, numpy as np

ap = argparse.ArgumentParser(); ap.add_argument("audio"); ap.add_argument("--fps", type=int, default=30)
ap.add_argument("--offset-ms", type=float, default=0); ap.add_argument("--min", type=float, default=0.35)
ap.add_argument("--words", help="kinetic style: words placed on onsets in order. '|' starts a new phrase, "
                "'_' joins words into one line, a trailing '!' = big, a leading '^' = red, lowercase = soft")
ap.add_argument("--gap", type=int, default=6, help="min frames between two words"); ap.add_argument("--from", dest="start", type=int, default=0)
a = ap.parse_args()
SR, HOP, N = 22050, 256, 1024
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.audio, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.float32)
length = len(x) / SR
# trailing silence does not count: TikTok loops the video when the SOUND ends
rms = np.sqrt(np.convolve(x ** 2, np.ones(SR // 20) / (SR // 20), "same"))
loud = np.where(rms > 10 ** (-45 / 20))[0]
end = (loud[-1] / SR) if len(loud) else length
frames = np.lib.stride_tricks.sliding_window_view(x, N)[::HOP] * np.hanning(N)
mag = np.log1p(30 * np.abs(np.fft.rfft(frames, axis=1)))
t = np.arange(len(mag)) * HOP / SR
def flux(m): f = np.maximum(0, np.diff(m, axis=0)).sum(1); return np.concatenate([[0], f])
full, low = flux(mag), flux(mag[:, :12])
def peaks(env, k):
    m = np.convolve(env, np.ones(9) / 9, "same"); thr = m + k * env.std(); out = []
    for i in range(4, len(env) - 5):
        if env[i] > thr[i] and env[i] == env[i - 4:i + 5].max() and (not out or t[i] - out[-1][0] > 0.09):
            out.append((t[i], env[i] / env.max()))
    return out
e = full - full.mean(); ac = np.correlate(e, e, "full")[len(e) - 1:]; lags = np.arange(len(ac)) * t[1]
# 90-180 BPM (TikTok tracks); halve/double by ear if needed
sel = (lags > 0.33) & (lags < 0.67); beat = lags[sel][np.argmax(ac[sel])]
off = a.offset_ms / 1000
fr = lambda s: int(round((s + off) * a.fps))
grid = lambda f: np.floor((f / a.fps - 0.0005) * 1000) / 1000
nframes = int(np.floor((end + off) * a.fps))
print(f"sound: {length:.3f} s, last sound at {end:.3f} s")
print(f"=> video length {nframes} frames = root data-duration \"{nframes / a.fps:.3f}\" (end WITH the sound: longer plays in silence)")
print(f"tempo ≈ {60 / beat:.1f} BPM, beat {beat * 1000:.0f} ms = {beat * a.fps:.1f} frames")
strong = [p for p in peaks(full, 0.9) if p[1] >= a.min]
kicks = peaks(low, 1.2)
print("\nstrong onsets (frame : time on the grid : strength)")
for s, v in strong:
    if 0 <= fr(s) < nframes: print(f"  {fr(s):4d} : {grid(fr(s)):7.3f} : {'#' * int(v * 20)}")
print("\nkicks (frames):", " ".join(str(fr(s)) for s, _ in kicks if 0 <= fr(s) < nframes))
top = sorted([p for p in strong if 0 <= fr(p[0]) < nframes], key=lambda p: -p[1])[:max(4, int(end / 1.5))]
hits = sorted({fr(s) for s, _ in top})
print("\nHITS for fx.html (strongest onsets, 1-frame flash; make the 2-3 biggest 2 frames):")
print("  const HITS = [" + ", ".join(f"[{h}, 1]" for h in hits) + "];")
print("scene starts / cuts: use these frames; time = frame/fps - 0.001 (inside a scene: subtract the scene start)")

if a.words:
    # every onset (not just strong ones) is a candidate; take them in order, at least --gap frames apart
    cand = sorted({fr(s) for s, v in peaks(full, 0.5)} | {fr(s) for s, v in kicks})
    toks, out, last, new = a.words.split(), [], -999, True
    it = iter([f for f in cand if a.start <= f < nframes])
    for tok in toks:
        if tok == "|": new = True; continue
        need = a.gap * (3 if new and out else 1)   # a new phrase needs room for the whip-out of the last one
        f = next((f for f in it if f - last >= need), None)
        if f is None: print(f"\n(only {len(out)} words fit before the end; the rest were dropped)"); break
        flags = []
        if new: flags.append("new"); new = False
        word = tok
        if word.startswith("^"): flags.append("red"); word = word[1:]
        if word.endswith("!"): flags.append("big"); word = word[:-1]
        word = word.replace("_", " ")
        if word == word.lower() and any(c.isalpha() for c in word): flags.append("soft")
        out.append(f'[{f}, "{word}"' + (f', "{" ".join(flags)}"' if flags else "") + "]")
        last = f
    print("\nWORDS for styles/kinetic (paste into compositions/kinetic.html):")
    print("  const WORDS = [\n    " + ",\n    ".join(out) + ",\n  ];")
    print(f"  const LENGTH = {nframes / a.fps:.3f};  const OUT_AT = {max(last + 20, nframes - 14)};")
