"""verify.py — the checks to run before saying "done". python3 -I verify.py <final.mp4> [--hits 24,48,...] [--length-frames N]
  * frame count / duration (must equal the TikTok sound length: --length-frames)
  * brightness of each hit frame (a flash should read ≥ 230 on 0..255, flat to the corners)
  * loop seam: similarity of the LAST frame to the FIRST (≥ 0.9 = no visible jump when TikTok loops)
Needs ffmpeg + numpy."""
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
ap = argparse.ArgumentParser(); ap.add_argument("video"); ap.add_argument("--hits", default="")
ap.add_argument("--length-frames", type=int)
ap.add_argument("--cut-loop", action="store_true", help="the loop point is a deliberate hard cut on a beat: report the seam, don't fail on it")
a = ap.parse_args()
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.video, "-vf", "fps=30,scale=320:180,format=gray", "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
f = np.frombuffer(raw, np.uint8).reshape(-1, 180, 320).astype(np.float64)
n = len(f); ok = True
print(f"frames: {n} ({n / 30:.3f} s at 30 fps)", end="")
if a.length_frames:
    r_ = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", a.video], capture_output=True, text=True).stdout.strip() or "30/1"
    src_fps = float(r_.split("/")[0]) / float(r_.split("/")[1] or 1)
    tol = max(0, round(30 / src_fps) - 1) if src_fps < 29 else 0          # a 15 fps fast draft can only land on every 2nd frame
    good = abs(n - a.length_frames) <= tol; ok &= good
    print(f"  {'OK' if good else 'MISMATCH, want ' + str(a.length_frames)}" + (f" (±{tol}: {src_fps:g} fps file)" if tol else ""))
else: print()
def ssim(x, y):
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2; mx, my = x.mean(), y.mean()
    return ((2 * mx * my + c1) * (2 * ((x - mx) * (y - my)).mean() + c2)) / ((mx ** 2 + my ** 2 + c1) * (x.var() + y.var() + c2))
def blocks(x): return [x[i:i + 20, j:j + 20] for i in range(0, 180, 20) for j in range(0, 320, 20)]
seam = float(np.mean([ssim(p, q) for p, q in zip(blocks(f[-1]), blocks(f[0]))]))
good = seam >= 0.9 or a.cut_loop; ok &= good
print(f"loop seam (last vs first frame) SSIM {seam:.3f}  {'OK' if seam >= 0.9 else ('hard cut (allowed: --cut-loop, keep it on a beat)' if a.cut_loop else 'JUMP: make the last frame match the first')}")
for h in [int(v) for v in a.hits.split(",") if v.strip()]:
    if h >= n: print(f"hit {h}: beyond the end"); ok = False; continue
    m, corner = f[h].mean(), f[h][:30, :50].mean()
    good = m >= 230 and corner >= 220; ok &= good
    print(f"hit {h:4d}: luma {m:5.1f} (corner {corner:5.1f}), before {f[h - 1].mean() if h else 0:5.1f}  {'OK' if good else 'weak / dark corners'}")
print("ALL OK" if ok else "SOME CHECKS FAILED")
_sys.exit(0 if ok else 1) if "_sys" in globals() else __import__("sys").exit(0 if ok else 1)
