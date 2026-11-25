"""selftest.py — proves the tools work on this machine. Builds an 8 s test video with KNOWN cuts, flashes, a black dip
and a 120 BPM click track, then checks that beatgrid.py, analyze.py and verify.py find exactly those.
    python3 -I scripts/selftest.py        (needs ffmpeg + numpy; writes into a temp folder, deletes it after)"""
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
import os, sys, json, shutil, tempfile, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); PY = sys.executable
W, H, N, FPS, SR = 360, 640, 240, 30, 44100
CUTS, FLASHES, DIP = [30, 90, 150, 210], [60, 120], (180, 182)     # flash frames also start a new shot
tmp = tempfile.mkdtemp(prefix="tek-selftest-"); vid = os.path.join(tmp, "test.mp4")
results = []
def check(name, cond, detail=""):
    results.append((name, bool(cond), detail)); print(f"  {'PASS' if cond else 'FAIL'}  {name}  {detail}")
try:
    # ── video: a different noise texture per shot, flashes are white frames, the dip is black
    rng = np.random.default_rng(7); bounds = sorted(CUTS + FLASHES); shot_of = np.searchsorted(bounds, np.arange(N), side="right")
    tex = [(rng.random((H // 8, W // 8, 3)) * 200 + 30).repeat(8, 0).repeat(8, 1).astype(np.uint8) for _ in range(len(bounds) + 1)]
    frames = bytearray()
    for f in range(N):
        img = tex[shot_of[f]]
        if f in FLASHES: img = np.full_like(img, 245)
        if DIP[0] <= f <= DIP[1]: img = np.zeros_like(img)
        frames += img.tobytes()
    # ── audio: 120 BPM clicks (a beat every 15 frames), 8 s
    t = np.arange(int(SR * N / FPS)) / SR; a = np.zeros_like(t, dtype=np.float32)
    for b in np.arange(0, N / FPS, 0.5):
        i = int(b * SR); n = int(0.03 * SR); a[i:i + n] += (np.sin(2 * np.pi * 1000 * t[:n]) * np.exp(-t[:n] * 120)).astype(np.float32) * 0.8
    wav = os.path.join(tmp, "a.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", wav], input=a.tobytes(), check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
                    "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", vid], input=bytes(frames), check=True)
    print("tools:")
    # ── beatgrid
    r = subprocess.run([PY, "-I", os.path.join(HERE, "beatgrid.py"), wav], capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("beatgrid runs", r.returncode == 0, r.stderr.strip()[-200:])
    bpm = float(r.stdout.split("tempo ≈ ")[1].split(" ")[0]) if "tempo ≈ " in r.stdout else 0
    check("beatgrid tempo ≈ 120 BPM", abs(bpm - 120) < 3, f"got {bpm}")
    # the last click is at 7.5 s; trailing silence must NOT count (TikTok loops when the sound ends) → 226 frames
    check("beatgrid length = last sound (226 frames)", "226 frames" in r.stdout, r.stdout.split("\n")[1] if "\n" in r.stdout else "")
    # ── analyze
    out = os.path.join(tmp, "an")
    if not os.path.exists(os.path.join(HERE, "analyze.py")):
        print("  (analyze.py not in this edition: skipped)"); r = None
    else: r = subprocess.run([PY, "-I", os.path.join(HERE, "analyze.py"), vid, "-o", out], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r is not None: check("analyze runs", r.returncode == 0, r.stderr.strip()[-300:])
    if r is not None and r.returncode == 0:
        A = json.load(open(os.path.join(out, "analysis.json"), encoding="utf-8"))
        ev = A["events"]; fl = [e["frame"] for e in ev if e["type"] == "flash"]; cuts = [e["frame"] for e in ev if e["type"] == "cut"]
        dips = [e for e in ev if e["type"] == "dip"]
        check("flashes found at 60, 120", all(any(abs(x - f) <= 1 for x in fl) for f in FLASHES) and len(fl) == 2, f"got {fl}")
        check("cuts found at 30, 90, 150, 210", all(any(abs(x - c) <= 1 for x in cuts) for c in CUTS), f"got {cuts}")
        check("black dip found at 180", any(abs(d["frame"] - DIP[0]) <= 1 for d in dips), f"got {[d['frame'] for d in dips]}")
        check("tempo from the video's audio", A.get("sound") and abs(A["sound"]["bpm"] - 120) < 3, f"got {A.get('sound', {}) and A['sound']['bpm']}")
        for f in ("report.md", "shots.jpg", "events.jpg", "timeline.png", "palette.png"):
            check(f"analyze wrote {f}", os.path.exists(os.path.join(out, f)))
    # ── verify
    r = subprocess.run([PY, "-I", os.path.join(HERE, "verify.py"), vid, "--hits", "60,120", "--length-frames", "240", "--cut-loop"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("verify: length + flashes", r.returncode == 0 and "ALL OK" in r.stdout, r.stdout.strip().split("\n")[-1] if r.stdout else r.stderr[-200:])
finally:
    shutil.rmtree(tmp, ignore_errors=True)
bad = [n for n, ok, _ in results if not ok]
print(f"\n{len(results) - len(bad)}/{len(results)} passed." + (" All good — the kit works on this machine." if not bad else " Failed: " + ", ".join(bad)))
sys.exit(1 if bad else 0)
