"""preview.py — see an edit in seconds instead of waiting for the final render. Run from the project folder.
    python3 path/to/preview.py sheet [--n 12]      a contact sheet of N evenly spaced frames      (seconds)
    python3 path/to/preview.py draft --fast        960×540 at 15 fps → out/draft-fast.mp4 for the gates and timing (verify, compare)
    python3 path/to/preview.py draft               the ONE full 30 fps draft, to show the user → out/draft.mp4
    python3 path/to/preview.py final               the delivery render: 60 fps + finish.py → out/final.mp4
Live preview in the browser (scrub, instant): npx hyperframes preview
Ladder: snapshots + pairs.py while iterating → draft --fast for gates → ONE draft for the user → final only after the user says OK."""
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
ap.add_argument("--pad", help="draft/final: also write a padded copy at this size, e.g. 1080x1920 for a 16:9 edit posted vertically (verify runs on the unpadded file)")
ap.add_argument("--fast", action="store_true", help="draft only: half size (e.g. 960×540) at 15 fps, for gates and timing")
a = ap.parse_args()
if not os.path.exists("index.html"): _sys.exit("run this from the project folder (the one with index.html)")
dur = float(re.search(r'data-composition-id="main"[^>]*data-duration="([\d.]+)"', open("index.html", encoding="utf-8").read()).group(1))
import math as _m
if _m.ceil(dur * 30 - 1e-9) != round(dur * 30):   # e.g. 26.367 for 791 frames renders 792 (buyer test 3): use N/30 − 0.001
    print(f"note: data-duration {dur} renders {_m.ceil(dur * 30 - 1e-9)} frames, not {round(dur * 30)}: write {round(dur * 30)}/30 − 0.001 = {round(dur * 30) / 30 - 0.001:.4f}")
win = os.name == "nt"
def hf(args, **kw):
    if args[0] == "render" and os.environ.get("TEK_RENDER_WORKERS"):     # e.g. 3 in a 4-CPU container, where "auto" picks 1
        args = args + ["--workers", os.environ["TEK_RENDER_WORKERS"]]
    t = time.time(); r = subprocess.run(HF + args, shell=win, **kw); return r.returncode, time.time() - t
os.makedirs("out", exist_ok=True)
if a.mode == "sheet":
    ts = ",".join(f"{dur * (k + 0.5) / a.n:.2f}" for k in range(a.n))
    rc, s = hf(["snapshot", "-o", "out/sheet", "--no-end", "--at", ts], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    sheets = sorted(f for f in os.listdir("out/sheet") if f.startswith("contact-sheet")) if os.path.isdir("out/sheet") else []
    for f in sheets:                                       # ≤1200 px wide: one cheap read
        p_ = os.path.join("out/sheet", f); tmp_ = p_ + ".tmp.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p_, "-vf", "scale='min(1200,iw)':-2:flags=area", tmp_]); os.replace(tmp_, p_)
    print("\n".join(os.path.join("out/sheet", f) for f in sheets) or "snapshot failed", f"({s:.0f} s)")
elif a.mode == "draft" and a.fast:
    # a half-size copy of the root page: the same compositions, zoomed to 0.5 (no project file is changed)
    src = open("index.html", encoding="utf-8").read()
    m = re.search(r'data-composition-id="main"[^>]*', src); tag = m.group(0)
    W_ = int(re.search(r'data-width="(\d+)"', tag).group(1)); H_ = int(re.search(r'data-height="(\d+)"', tag).group(1))
    w2, h2 = W_ // 4 * 2, H_ // 4 * 2
    fast = src.replace(tag, tag.replace(f'data-width="{W_}"', f'data-width="{w2}"').replace(f'data-height="{H_}"', f'data-height="{h2}"'))
    fast = re.sub(r'(<meta name="viewport" content=")width=\d+, height=\d+', rf'\1width={w2}, height={h2}', fast)
    fast = fast.replace("</head>", f"<style>html, body {{ width: {w2}px !important; height: {h2}px !important; }} "
                                   f"#root {{ width: {w2}px; height: {h2}px; overflow: hidden; }} #root > * {{ zoom: 0.5; }}</style></head>", 1)
    open("_fast.html", "w", encoding="utf-8").write(fast)
    try: rc, s = hf(["render", "-c", "_fast.html", "--quality", "draft", "--fps", "15", "-o", "out/draft-fast.mp4"])
    finally: os.remove("_fast.html")
    print(f"out/draft-fast.mp4 ({s:.0f} s) — {w2}×{h2} at 15 fps: for verify / compare and timing, not for the user." if rc == 0 else "fast draft render failed")
elif a.mode == "draft":
    rc, s = hf(["render", "--quality", "draft", "--fps", "30", "-o", "out/draft.mp4"])
    print(f"out/draft.mp4 ({s:.0f} s) — a draft: soft and without the finishing pass; the timing is exact." if rc == 0 else "draft render failed")
    if rc == 0 and a.pad:
        pw, ph = a.pad.lower().split("x")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "out/draft.mp4", "-vf", f"scale={pw}:-2,pad={pw}:{ph}:0:(oh-ih)/2:black",
                        "-c:a", "copy", "out/draft-padded.mp4"])
        print(f"out/draft-padded.mp4 — {pw}×{ph} for the user; run verify on out/draft.mp4 (bars fail the flash check)")
else:
    rc, s = hf(["render", "--quality", "looks", "--fps", "60", "-o", "out/raw60.mp4"])
    if rc == 0: rc = subprocess.run([_sys.executable, "-I", os.path.join(HERE, "finish.py"), "out/raw60.mp4", "out/final.mp4", "--grain", str(a.grain)]).returncode
    if rc == 0 and a.pad:
        pw, ph = a.pad.lower().split("x")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", "out/final.mp4", "-vf", f"scale={pw}:-2,pad={pw}:{ph}:0:(oh-ih)/2:black",
                        "-c:a", "copy", "out/final-padded.mp4"])
    if rc == 0:
        nfr = round(dur * 30)
        if not a.cut_loop:      # the reference itself ends on a cut / black: a hard loop seam is right, not a failure
            import glob as _g, json as _j
            for _p in _g.glob("ref-recipe/analysis/analysis.json") + _g.glob("*-recipe/analysis/analysis.json"):
                try:
                    if (_j.load(open(_p, encoding="utf-8")).get("summary") or {}).get("loop_ssim", 1) < 0.3:
                        a.cut_loop = True; print("reference ends on a cut: checking the loop as a hard cut (--cut-loop)")
                except Exception:
                    pass
        v = subprocess.run([_sys.executable, "-I", os.path.join(HERE, "verify.py"), "out/final.mp4", "--length-frames", str(nfr)]
                           + (["--hits", a.hits] if a.hits else []) + (["--cut-loop"] if a.cut_loop else []), capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(v.stdout.strip().splitlines()[-1] if v.stdout else v.stderr[-300:])
        if a.deliver and v.returncode != 0:
            print("not delivered: the final failed verify.py (see above). Fix it, or rerun with the right --hits / --cut-loop.")
        elif a.deliver:
            home = os.path.expanduser("~")
            dest = os.path.join(home, "Movies", "TikTok Edits") if _sys.platform == "darwin" else os.path.join(home, "Videos", "TikTok Edits")
            in_container = os.path.exists("/.dockerenv") or os.environ.get("container")
            if os.environ.get("TEK_DELIVER_DIR"):
                dest = os.environ["TEK_DELIVER_DIR"]        # e.g. a folder mounted from the host
            elif in_container:                               # the container's home is not the user's: keep it in the project
                dest = os.path.abspath("out/deliver")        # (blind test 1: the file was copied inside the container and lost)
                print("running in a container: delivered into the project's out/deliver/ — copy it to the user's Movies folder on the host")
            os.makedirs(dest, exist_ok=True); target = os.path.join(dest, a.deliver + ".mp4"); _sh.copy2("out/final-padded.mp4" if a.pad and os.path.exists("out/final-padded.mp4") else "out/final.mp4", target)
            if os.path.exists("POST.md"): _sh.copy2("POST.md", os.path.join(dest, a.deliver + "-POST.md"))
            opener = {"darwin": ["open"], "win32": ["explorer"]}.get(_sys.platform, ["xdg-open"])
            try:
                if not in_container: subprocess.Popen(opener + [dest])
            except Exception: pass
            print(f"delivered: {target}")
    print(f"out/final.mp4 ({s:.0f} s render)" if rc == 0 else "final render failed")
_sys.exit(rc)
