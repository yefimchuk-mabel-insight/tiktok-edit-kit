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
    # ── probe: a word filled with the frame's negative, a glyph that grows in two hard steps, a locked camera
    if os.path.exists(os.path.join(HERE, "probe.py")):
        PW, PH, PN = 640, 360, 90
        yy, xx = np.mgrid[0:PH, 0:PW].astype(np.float32)
        bg = np.stack([128 + 100 * np.sin(xx / 40), 128 + 100 * np.sin(yy / 30 + 1), 128 + 100 * np.cos((xx + yy) / 50)], 2)
        word = np.zeros((PH, PW), bool)
        for k in range(3): word[110:200, 120 + k * 110:190 + k * 110] = True; word[130:180, 140 + k * 110:170 + k * 110] = False
        pv = os.path.join(tmp, "probe.mp4"); fr = bytearray()
        for f in range(PN):
            m = word.copy() if f < 30 else np.zeros_like(word)
            if f >= 30:
                r = 30 if f < 50 else (40 if f < 70 else 52)                       # steps at 50 and 70
                cy, cx = 220, 400; m[cy - r:cy + r, cx - r:cx + r] = True; m[cy - r // 2:cy + r // 2, cx - r // 2:cx + r // 2] = False
            img = bg.copy(); img[m] = 255 - img[m]; fr += np.clip(img, 0, 255).astype(np.uint8).tobytes()
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{PW}x{PH}", "-r", "30", "-i", "-",
                        "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", pv], input=bytes(fr), check=True)
        po = os.path.join(tmp, "probe-out")
        r = subprocess.run([PY, "-I", os.path.join(HERE, "probe.py"), pv, "-o", po, "--no-person"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        check("probe runs", r.returncode == 0, r.stderr.strip()[-300:])
        if r.returncode == 0:
            P = json.load(open(os.path.join(po, "probe.json"), encoding="utf-8")); E = P["elements"]
            check("probe: the word's fill is the negative", any("negative" in (e["fill"] or "") and (e["on"] or [99])[0] <= 5 for e in E), str([(e["box"], e["fill"]) for e in E]))
            steps = sorted({s_ for e in E for s_ in (e.get("steps") or [])})
            check("probe: glyph steps at 50 and 70", any(abs(s_ - 50) <= 1 for s_ in steps) and any(abs(s_ - 70) <= 1 for s_ in steps), f"got {steps}")
            check("probe: camera locked", all(sh["camera"]["move"] in ("locked", "too short to tell") for sh in P["shots"]), str([sh["camera"]["move"] for sh in P["shots"]]))
    # ── depthtext block: builds a project from a tiny clone.json (no render, no cut-out)
    dt = os.path.join(os.path.dirname(HERE), "styles", "depthtext", "build.py")
    if os.path.exists(dt):
        ph = os.path.join(tmp, "photo.jpg"); pj = os.path.join(tmp, "dt"); os.makedirs(pj, exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=640x360", "-frames:v", "1", ph], check=True)
        cj = os.path.join(tmp, "clone.json")
        json.dump({"size": [640, 360], "length_frames": 60, "shots": [
            {"start": 0, "end": 30, "photo": ph, "word": "SKY", "box": [0.1, 0.2, 0.9, 0.5]},
            {"start": 30, "end": 60, "photo": ph, "glyph": "ろ", "box": [0.4, 0.3, 0.6, 0.7], "steps": [[45, 1.3, 0, 0]]}]}, open(cj, "w", encoding="utf-8"))
        r = subprocess.run([PY, "-I", dt, cj, pj], capture_output=True, text=True, encoding="utf-8", errors="replace")
        ok = r.returncode == 0 and os.path.exists(os.path.join(pj, "index.html")) and os.path.exists(os.path.join(pj, "compositions", "depth.html"))
        check("depthtext block builds a project", ok, (r.stdout + r.stderr).strip()[-300:])
finally:
    shutil.rmtree(tmp, ignore_errors=True)
# every script compiles under THIS Python (a 3.12-only f-string broke the kit on 3.11; stress.py caught it)
import py_compile as _pc, glob as _gl
_kit = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_bad = []
for _f in _gl.glob(os.path.join(_kit, "scripts", "*.py")) + _gl.glob(os.path.join(_kit, "styles", "*", "template", "*.py")) + _gl.glob(os.path.join(_kit, "styles", "*", "*.py")):
    try: compile(open(_f, encoding="utf-8").read(), _f, "exec")
    except SyntaxError as _e: _bad.append(f"{os.path.basename(_f)}:{_e.lineno}")
check("every script compiles on this Python", not _bad, ", ".join(_bad))

bad = [n for n, ok, _ in results if not ok]
print(f"\n{len(results) - len(bad)}/{len(results)} passed." + (" All good — the kit works on this machine." if not bad else " Failed: " + ", ".join(bad)))
if not bad:   # step 0 is "once per machine": a new session skips doctor + selftest when this marker holds the version
    try:
        import re as _re
        _kitd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _vf = os.path.join(_kitd, "VERSION")
        _v = _re.search(r"(\d+\.\d+\.\d+)", open(_vf, encoding="utf-8").read() if os.path.exists(_vf) else open(os.path.join(_kitd, "CHANGELOG.md"), encoding="utf-8").read())
        _d = os.path.join(os.path.expanduser("~"), ".cache", "tiktok-edit-kit"); os.makedirs(_d, exist_ok=True)
        open(os.path.join(_d, "setup-ok"), "w").write((_v.group(1) if _v else "?") + "\n")
    except Exception:
        pass
sys.exit(1 if bad else 0)
