"""sync.py — measure how a posted video (picture + sound) lines up with our render and the guide track.
   python3 -I sync.py <posted.mp4> <ours.mp4> <guide.wav>"""
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
import sys, subprocess, numpy as np
posted, ours, guide = sys.argv[1:4]
def pcm(p, sr=8000):
    raw = subprocess.run(["ffmpeg","-v","error","-i",p,"-vn","-ac","1","-ar",str(sr),"-f","f32le","-"],capture_output=True,check=True).stdout
    return np.frombuffer(raw,np.float32)
def env(x, sr=8000, hop=80):  # onset-ish envelope at 100 Hz
    n = len(x)//hop; e = np.sqrt((x[:n*hop].reshape(n,hop)**2).mean(1)); d = np.maximum(0, np.diff(np.log(e+1e-4))); return d
def lag(a, b, maxlag):  # best shift s (in samples) such that a[t] ~ b[t - s]
    best = None
    for s in range(-maxlag, maxlag+1):
        if s >= 0: x, y = a[s:], b[:len(a)-s]
        else: x, y = a[:s], b[-s:]
        n = min(len(x), len(y)); x, y = x[:n], y[:n]
        c = np.dot(x-x.mean(), y-y.mean())/(np.std(x)*np.std(y)*n+1e-9)
        if best is None or c > best[1]: best = (s, c)
    return best
ea, eg = env(pcm(posted)), env(pcm(guide))
s, c = lag(ea, eg, 300)
print(f"SOUND: posted audio vs guide track: shift {s*10:+d} ms (corr {c:.2f})  [+ = song plays later than in the guide]")
def vdiff(p):
    raw = subprocess.run(["ffmpeg","-v","error","-i",p,"-vf","fps=30,scale=160:90,format=gray","-f","rawvideo","-"],capture_output=True,check=True).stdout
    f = np.frombuffer(raw,np.uint8).reshape(-1,90,160).astype(np.float32); return f.mean((1,2))
lp, lo = vdiff(posted), vdiff(ours)
s2, c2 = lag(np.diff(lp), np.diff(lo), 60)
print(f"PICTURE: posted video vs our render: shift {s2:+d} frames = {s2*1000/30:+.0f} ms (corr {c2:.2f})")
print(f"=> sound relative to picture: {s*10 - s2*1000/30:+.0f} ms  (0 = exactly like the reference; + = sound late, - = sound early)")
