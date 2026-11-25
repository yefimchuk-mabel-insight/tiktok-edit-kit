"""preview.py — see an edit in seconds instead of waiting for the final render. Run from the project folder.
    python3 path/to/preview.py sheet [--n 12]      a contact sheet of N evenly spaced frames      (seconds)
    python3 path/to/preview.py draft               a quick 30 fps draft MP4 → out/draft.mp4       (a few times faster than final)
    python3 path/to/preview.py final               the delivery render: 60 fps + finish.py → out/final.mp4
Live preview in the browser (scrub, instant): npx hyperframes preview
Order: sheet (Claude checks it) → live preview / draft (the user checks it) → final only after the user says OK."""
import sys as _u8
try:                                                       # Windows pipes default to cp1252: print UTF-8
    _u8.stdout.reconfigure(encoding="utf-8"); _u8.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
import shutil as _sh, sys as _sys
if not (_sh.which("ffmpeg") and _sh.which("ffprobe")):
    _sys.exit("ffmpeg / ffprobe not found. Run:  node scripts/doctor.mjs")
import os, re, argparse, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__))
import shlex
HF = ["npx", "--yes", "hyperframes@0.9.78"]
if os.environ.get("HYPERFRAMES_CLI"): HF = shlex.split(os.environ["HYPERFRAMES_CLI"], posix=(os.name != "nt"))     # e.g. a wrapper or a local plugin-cli
ap = argparse.ArgumentParser(); ap.add_argument("mode", choices=["sheet", "draft", "final"]); ap.add_argument("--n", type=int, default=12)
ap.add_argument("--grain", type=int, default=6)
ap.add_argument("--deliver", help="final only: also copy it to the user's Movies/Videos folder under this name and open the folder")
ap.add_argument("--hits", default=""); ap.add_argument("--cut-loop", action="store_true")
a = ap.parse_args()
if not os.path.exists("index.html"): _sys.exit("run this from the project folder (the one with index.html)")
dur = float(re.search(r'data-composition-id="main"[^>]*data-duration="([\d.]+)"', open("index.html", encoding="utf-8").read()).group(1))
win = os.name == "nt"
def hf(args, **kw):
    t = time.time(); r = subprocess.run(HF + args, shell=win, **kw); return r.returncode, time.time() - t
os.makedirs("out", exist_ok=True)
if a.mode == "sheet":
    ts = ",".join(f"{dur * (k + 0.5) / a.n:.2f}" for k in range(a.n))
    rc, s = hf(["snapshot", "-o", "out/sheet", "--no-end", "--at", ts], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    sheets = sorted(f for f in os.listdir("out/sheet") if f.startswith("contact-sheet")) if os.path.isdir("out/sheet") else []
    print("\n".join(os.path.join("out/sheet", f) for f in sheets) or "snapshot failed", f"({s:.0f} s)")
elif a.mode == "draft":
    rc, s = hf(["render", "--quality", "draft", "--fps", "30", "-o", "out/draft.mp4"])
    print(f"out/draft.mp4 ({s:.0f} s) — a draft: soft and without the finishing pass; the timing is exact." if rc == 0 else "draft render failed")
else:
    rc, s = hf(["render", "--quality", "looks", "--fps", "60", "-o", "out/raw60.mp4"])
    if rc == 0: rc = subprocess.run([_sys.executable, "-I", os.path.join(HERE, "finish.py"), "out/raw60.mp4", "out/final.mp4", "--grain", str(a.grain)]).returncode
    if rc == 0:
        nfr = round(dur * 30)
        v = subprocess.run([_sys.executable, "-I", os.path.join(HERE, "verify.py"), "out/final.mp4", "--length-frames", str(nfr)]
                           + (["--hits", a.hits] if a.hits else []) + (["--cut-loop"] if a.cut_loop else []), capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(v.stdout.strip().splitlines()[-1] if v.stdout else v.stderr[-300:])
        if a.deliver and v.returncode != 0:
            print("not delivered: the final failed verify.py (see above). Fix it, or rerun with the right --hits / --cut-loop.")
        elif a.deliver:
            home = os.path.expanduser("~")
            dest = os.path.join(home, "Movies", "TikTok Edits") if _sys.platform == "darwin" else os.path.join(home, "Videos", "TikTok Edits")
            os.makedirs(dest, exist_ok=True); target = os.path.join(dest, a.deliver + ".mp4"); _sh.copy2("out/final.mp4", target)
            if os.path.exists("POST.md"): _sh.copy2("POST.md", os.path.join(dest, a.deliver + "-POST.md"))
            opener = {"darwin": ["open"], "win32": ["explorer"]}.get(_sys.platform, ["xdg-open"])
            try: subprocess.Popen(opener + [dest])
            except Exception: pass
            print(f"delivered: {target}")
    print(f"out/final.mp4 ({s:.0f} s render)" if rc == 0 else "final render failed")
_sys.exit(rc)
