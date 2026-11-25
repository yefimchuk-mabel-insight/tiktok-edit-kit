"""finish.py — optical finishing pass for a 60 fps HyperFrames render (real pixels, not DOM tricks). Any OS.
    python3 finish.py <in-60fps.mp4> <out.mp4> [--no-bloom] [--grain 6] [--crf 20]
1. motion blur: blend frame pairs of the 60 fps render and keep 30 fps (180° shutter). Pairs are (2m, 2m+1), so a cut
   placed on the 30 fps grid stays a clean cut: no blended frame, no 1-frame lag. Don't change the pairing.
2. bloom: two blurred highlight passes screened back on (tight + wide)            (--no-bloom to skip)
3. slight lens softness, fine grain, then blacks crushed to pure #000 (so TikTok's bars match).
No vignette here: it would grey the corners of white flashes; vignettes live in the composition, under the flash."""
try:                                                       # Windows pipes default to cp1252: print UTF-8 everywhere
    _sys.stdout.reconfigure(encoding="utf-8"); _sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
# ── friendly preflight: say what's missing and how to fix it, instead of a traceback
import shutil as _sh, sys as _sys
if not (_sh.which("ffmpeg") and _sh.which("ffprobe")):
    _sys.exit("ffmpeg / ffprobe not found. Run:  node scripts/doctor.mjs   (it prints the install command for your system)")
import sys, argparse, subprocess
ap = argparse.ArgumentParser(); ap.add_argument("inp"); ap.add_argument("out")
ap.add_argument("--no-bloom", action="store_true"); ap.add_argument("--grain", type=int, default=6); ap.add_argument("--crf", type=int, default=20)
a = ap.parse_args()
head = "[0:v]tmix=frames=2:weights='1 1',select='mod(n,2)',setpts=N/(30*TB),fps=30,format=gbrp"
tail = f"noise=alls={a.grain}:allf=t,curves=all='0/0 0.04/0 0.12/0.06 0.5/0.52 1/1',format=yuv420p[v]"
if a.no_bloom:
    graph = f"{head},gblur=sigma=0.55,{tail}"
else:
    graph = (f"{head},split=3[base][h1][h2];[base]gblur=sigma=0.55[soft];"
             "[h1]curves=all='0/0 0.58/0 1/1',gblur=sigma=10[g1];[h2]curves=all='0/0 0.68/0 1/1',gblur=sigma=48[g2];"
             "[soft][g1]blend=all_mode=screen:all_opacity=0.55[s1];"
             f"[s1][g2]blend=all_mode=screen:all_opacity=0.5,{tail}")
cmd = ["ffmpeg", "-v", "error", "-stats", "-y", "-i", a.inp, "-filter_complex", graph, "-map", "[v]", "-map", "0:a?",
       "-c:v", "libx264", "-crf", str(a.crf), "-preset", "slow", "-tune", "grain", "-c:a", "copy", "-movflags", "+faststart", a.out]
sys.exit(subprocess.run(cmd).returncode)
