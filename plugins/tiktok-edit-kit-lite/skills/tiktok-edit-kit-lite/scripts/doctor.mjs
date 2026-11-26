#!/usr/bin/env node
// doctor.mjs — checks everything the kit needs and says exactly how to fix what's missing.
//   node scripts/doctor.mjs          check only (safe, changes nothing)
//   node scripts/doctor.mjs --fix    also install what's missing with the system package manager (asks nothing: only run it after the user said yes)
// Needs only Node. Works on macOS, Windows and Linux. No network calls except the installers it runs with --fix.
import { spawnSync } from "node:child_process";
import os from "node:os";

const fix = process.argv.includes("--fix");
const plat = os.platform(); // darwin | win32 | linux
const ok = (m) => console.log("  OK   " + m), bad = (m) => console.log("  MISS " + m), warn = (m) => console.log("  WARN " + m);
const run = (cmd, args, opts = {}) => spawnSync(cmd, args, { encoding: "utf8", shell: plat === "win32", ...opts });
const has = (cmd) => { const r = run(cmd, ["-version"]); return !r.error && r.status === 0 ? r : null; };
const pm = plat === "darwin" ? (run("brew", ["--version"]).status === 0 ? "brew" : null)
  : plat === "win32" ? (run("winget", ["--version"]).status === 0 ? "winget" : null)
  : ["apt-get", "dnf", "pacman"].find((p) => run("which", [p]).status === 0) || null;
const INSTALL = {
  ffmpeg: { brew: "brew install ffmpeg", winget: "winget install --id Gyan.FFmpeg -e", "apt-get": "sudo apt-get install -y ffmpeg", dnf: "sudo dnf install -y ffmpeg", pacman: "sudo pacman -S --noconfirm ffmpeg" },
  python: { brew: "brew install python", winget: "winget install --id Python.Python.3.12 -e", "apt-get": "sudo apt-get install -y python3 python3-pip", dnf: "sudo dnf install -y python3 python3-pip", pacman: "sudo pacman -S --noconfirm python python-pip" },
  node: { brew: "brew install node", winget: "winget install --id OpenJS.NodeJS.LTS -e", "apt-get": "see https://nodejs.org (Node 22+)", dnf: "sudo dnf install -y nodejs", pacman: "sudo pacman -S --noconfirm nodejs npm" },
};
const todo = [];
console.log(`tiktok-edit-kit doctor · ${plat} ${os.arch()} · package manager: ${pm || "none found"}\n`);

// Node (HyperFrames needs 22+)
const major = +process.versions.node.split(".")[0];
if (major >= 22) ok(`node ${process.versions.node}`); else { bad(`node ${process.versions.node}: HyperFrames needs Node 22+`); todo.push(["node", INSTALL.node[pm] || "https://nodejs.org"]); }

// ffmpeg + ffprobe with the filters the scripts use
const ff = has("ffmpeg"), fp = has("ffprobe");
if (ff && fp) {
  const filters = run("ffmpeg", ["-hide_banner", "-filters"]).stdout || "";
  const need = ["tmix", "gblur", "curves", "noise", "blend", "scale", "crop", "tile", "silencedetect"];
  const missing = need.filter((f) => !new RegExp(`\\s${f}\\s`).test(filters));
  if (missing.length) { bad(`ffmpeg is missing filters: ${missing.join(", ")} (install a full build)`); todo.push(["ffmpeg", INSTALL.ffmpeg[pm] || "https://ffmpeg.org/download.html"]); }
  else ok("ffmpeg + ffprobe (" + (ff.stdout.split("\n")[0].split(" ")[2] || "?") + ")");
} else { bad("ffmpeg / ffprobe not found"); todo.push(["ffmpeg", INSTALL.ffmpeg[pm] || "https://ffmpeg.org/download.html"]); }

// Python 3 + numpy
const py = ["python3", "python", "py"].find((p) => { const r = run(p, ["--version"]); return r.status === 0 && /Python 3/.test(r.stdout + r.stderr); });
if (!py) { bad("python 3 not found"); todo.push(["python", INSTALL.python[pm] || "https://www.python.org/downloads/"]); }
else {
  const v = run(py, ["--version"]); ok(`${(v.stdout || v.stderr).trim()} (${py})`);
  const np = run(py, ["-c", "import numpy; print(numpy.__version__)"]);
  if (np.status === 0) ok(`numpy ${np.stdout.trim()}`);
  else { bad("numpy not installed"); todo.push(["numpy", `${py} -m pip install --user numpy`]); }
  // optional: yt-dlp lets scripts/fetch.py take a TikTok / Reels / YouTube LINK instead of a file
  const yd = run("yt-dlp", ["--version"]); const ym = run(py, ["-c", "import yt_dlp"]);
  if (yd.status === 0 || ym.status === 0) ok("yt-dlp (links instead of files)");
  else console.log("  INFO yt-dlp not installed (optional: lets you send a link instead of a file) — " + `${py} -m pip install --user yt-dlp`);
}

// HyperFrames CLI reachable through npx (downloads on first use)
const hf = run("npx", ["--yes", "hyperframes@0.9.78", "--version"], { timeout: 180000 });
if (hf.status === 0) ok("hyperframes CLI " + (hf.stdout || "").trim().split("\n").pop());
else warn("couldn't run `npx hyperframes` (offline?). It is fetched on first render; check your network/npm.");

if (!todo.length) { console.log("\nAll set. Try:  python3 -I scripts/selftest.py   (Windows: py -I scripts\\selftest.py)"); process.exit(0); }
console.log("\nTo fix:");
if (plat === "darwin" && !pm && todo.length)
  console.log('  FIRST   install Homebrew (one line, paste in Terminal; it asks for your Mac password):\n          /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"\n          then run this check again: the rest installs with brew.');
for (const [what, cmd] of todo) console.log(`  ${what.padEnd(7)} ${cmd}`);
if (!fix) { console.log("\nRun again with --fix to install these automatically (after the user agrees)."); process.exit(1); }
for (const [what, cmd] of todo) {
  if (/^(see|https?:)/.test(cmd)) { warn(`${what}: install by hand — ${cmd}`); continue; }
  console.log(`\n$ ${cmd}`);
  const r = spawnSync(cmd, { stdio: "inherit", shell: true });
  if (r.status !== 0) warn(`${what}: the installer exited with ${r.status}`);
}
console.log("\nDone. Run `node scripts/doctor.mjs` again to confirm.");
