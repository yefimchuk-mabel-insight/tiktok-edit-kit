# Install — tiktok-edit-kit-lite 1.3.5

1. Unzip so that this folder sits at `~/.claude/skills/tiktok-edit-kit-lite/` (all projects) or `<your project>/.claude/skills/tiktok-edit-kit-lite/`.
   `SKILL.md` must be directly inside that folder.
2. Restart Claude Code (or open a new session).
3. Ask, in any language, e.g. *"make a kinetic text TikTok of these lines to my song"*.
   On the first run Claude runs `node scripts/doctor.mjs` and offers to install what is missing: Node 22+, ffmpeg, Python 3 with numpy.
4. Check: `python3 -I scripts/selftest.py` (Windows: `py -I scripts\selftest.py`) prints "All good".

Runs on macOS and Linux; Windows is beta. No telemetry, no accounts, nothing uploaded.
Updating: replace this folder with the new version. Something broke? Send the doctor output and the last lines of the failing command.
