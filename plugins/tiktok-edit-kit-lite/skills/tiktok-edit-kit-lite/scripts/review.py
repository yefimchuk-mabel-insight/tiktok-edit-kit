"""review.py — ONE page to review an edit: the reference and ours playing side by side in sync, the element-by-element
check, the scorecard, and where every file is. Open it in any browser; nothing is uploaded.
    python3 -I review.py <ours.mp4> [--ref ref.mp4] [--compare compare-dir] [--draft out/draft.mp4] [-o out/review.html]
Then:  macOS `open out/review.html` · Windows `start out\\review.html` · Linux `xdg-open out/review.html`"""
import sys as _u8
try:                                                       # Windows pipes default to cp1252: print UTF-8
    _u8.stdout.reconfigure(encoding="utf-8"); _u8.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
import os, sys, html, shutil, argparse, re, json

ap = argparse.ArgumentParser(); ap.add_argument("ours"); ap.add_argument("--ref"); ap.add_argument("--compare"); ap.add_argument("--draft")
ap.add_argument("-o", "--out", default="out/review.html"); ap.add_argument("--title", default="Review")
ap.add_argument("--lang", default="en", help="language of the page (the user's language; en and uk are built in, others fall back to en)")
ap.add_argument("--stage", default="final", choices=["analyzed", "built", "checked", "draft", "final"], help="how far the work is (progress bar)")
ap.add_argument("--watch", action="store_true", help="reload the page every 5 s (while Claude is still working)")
ap.add_argument("--note", default="", help="one plain sentence for the user at the top")
ap.add_argument("--details", action="store_true", help="also show the reference, the element pairs and the scorecard (for Claude, not the user)")
a = ap.parse_args()
out_dir = os.path.dirname(os.path.abspath(a.out)); media = os.path.join(out_dir, "review-files"); os.makedirs(media, exist_ok=True)

def bring(path, name):
    """copy a file next to the page so the page works on its own (relative links)"""
    if not path or not os.path.exists(path): return None
    dst = os.path.join(media, name)
    if os.path.abspath(path) != os.path.abspath(dst): shutil.copy2(path, dst)
    return "review-files/" + name

ours = bring(a.ours, "ours" + os.path.splitext(a.ours)[1]); ref = bring(a.ref, "reference" + os.path.splitext(a.ref or "")[1]) if (a.ref and a.details) else None
draft = bring(a.draft, "draft.mp4") if a.draft else None
imgs, table, verdict = [], "", ""
if a.details and a.compare and os.path.isdir(a.compare):
    for f, label in (("elements.jpg", "Element by element: reference | ours, same frame"), ("compare.jpg", "Reference (top) and ours (bottom) at the same moments")):
        p = bring(os.path.join(a.compare, f), f)
        if p: imgs.append((label, p))
    for sub in sorted(os.listdir(a.compare)):
        sq = os.path.join(a.compare, sub, "sequence.jpg")
        if os.path.exists(sq): imgs.append((f"Every 2nd frame: {sub.replace('-analysis', '')}", bring(sq, sub + "-sequence.jpg")))
    md = os.path.join(a.compare, "compare.md")
    if os.path.exists(md):
        rows = [l for l in open(md, encoding="utf-8").read().splitlines() if l.startswith("| ") and not l.startswith("| metric") and not l.startswith("|---")]
        trs = []
        for l in rows:
            c = [x.strip() for x in l.strip("|").split("|")]
            cls = {"OK": "ok", "CLOSE": "close", "OFF": "off"}.get(c[3] if len(c) > 3 else "", "")
            trs.append(f'<tr class="{cls}">' + "".join(f"<td>{html.escape(x)}</td>" for x in c) + "</tr>")
        table = "<table><tr><th>metric</th><th>reference</th><th>ours</th><th>verdict</th><th>fix</th></tr>" + "".join(trs) + "</table>"
        m = re.search(r"\*\*(\d+) OK, (\d+) close, (\d+) off\.\*\*", open(md, encoding="utf-8").read())
        if m: verdict = f"{m.group(1)} OK · {m.group(2)} close · {m.group(3)} off"

TR = {
 "en": dict(final="Final video", draft="Draft (fast preview)", reference="Reference", ours="Ours (silent: the sound is added in TikTok)",
            play="▶ Play both", pause="❚❚ Pause", files="Files", score="Scorecard", folder="Open folder", steps=["Reference analysed", "Edit built", "Independent check", "Draft", "Final"],
            like="👍 Looks good — make the final", likemsg="final", change="Change something at this moment",
            comment="Comment on this frame", placeholder="e.g. the caption should be bigger here", copy="Copy for Claude", copied="Copied — paste it into the chat",
            at="At {t} s (frame {f})", how="How to review: press Play, pause where something looks off, write a note and copy it to Claude."),
 "uk": dict(final="Фінальне відео", draft="Чернетка (швидкий перегляд)", reference="Приклад", ours="Наше (без звуку: звук додається в TikTok)",
            play="▶ Грати обидва", pause="❚❚ Пауза", files="Файли", score="Що збігається", folder="Відкрити папку", steps=["Приклад розібрано", "Відео зібрано", "Незалежна перевірка", "Чернетка", "Фінал"],
            like="👍 Подобається — роби фінал", likemsg="фінал", change="Змінити щось у цьому місці",
            comment="Коментар до цього кадру", placeholder="напр.: тут текст має бути більшим", copy="Скопіювати для Claude", copied="Скопійовано — встав у чат",
            at="На {t} с (кадр {f})", how="Як дивитися: натисни «Грати», зупини там, де щось не так, напиши коментар і скопіюй його для Claude."),
}
T = TR.get(a.lang, TR["en"])
STAGES = ["analyzed", "built", "checked", "draft", "final"]; reached = STAGES.index(a.stage)
steps = "".join(f'<li class="{"done" if i <= reached else ""}">{"✓ " if i <= reached else ""}{html.escape(n)}</li>' for i, n in enumerate(T["steps"]))
files = [(T["final"], ours if a.stage == "final" else None), (T["draft"], draft or (ours if a.stage != "final" else None)), (T["reference"], ref)]
page = f"""<!doctype html><html lang="{html.escape(a.lang)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(a.title)}</title>{'<meta http-equiv="refresh" content="5">' if a.watch else ''}
<style>
:root {{ --bg:#111214; --fg:#ececec; --mut:#9a9da3; --ok:#3ecf8e; --close:#e8b44a; --off:#ef5b5b; --card:#1a1c1f; }}
* {{ box-sizing:border-box }} body {{ margin:0; background:var(--bg); color:var(--fg); font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif; }}
main {{ max-width:1200px; margin:0 auto; padding:24px 16px 64px }} h1 {{ font-size:22px; margin:0 0 4px }} h2 {{ font-size:16px; margin:32px 0 10px; color:var(--mut); font-weight:600 }}
.sub {{ color:var(--mut) }} ol.steps {{ list-style:none; display:flex; gap:8px; flex-wrap:wrap; padding:0; margin:14px 0 0 }}
ol.steps li {{ background:var(--card); color:var(--mut); padding:6px 12px; border-radius:99px; font-size:13px }} ol.steps li.done {{ color:var(--ok) }}
.phone {{ max-width:420px; margin:16px auto 0; background:#000; border-radius:28px; padding:14px; box-shadow:0 0 0 2px #2b2e33 }}
.big {{ font-size:16px; padding:12px 18px; background:#2f6f4f }} .note {{ background:#1e2a22; border-radius:10px; padding:10px 14px; margin-top:14px }} textarea {{ width:100%; min-height:64px; background:var(--card); color:var(--fg); border:1px solid #2b2e33; border-radius:8px; padding:8px; font:inherit }} .vids {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:12px; margin-top:16px }}
.vids figure {{ margin:0; background:var(--card); border-radius:10px; padding:8px }} video {{ width:100%; border-radius:6px; background:#000; display:block }}
figcaption {{ color:var(--mut); font-size:13px; padding:6px 2px 0 }} .bar {{ display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-top:12px }}
button {{ background:#2b2e33; color:var(--fg); border:0; border-radius:8px; padding:8px 14px; font:inherit; cursor:pointer }} button:hover {{ background:#373b41 }}
input[type=range] {{ flex:1; min-width:160px }} .files a {{ color:var(--fg); background:var(--card); padding:8px 12px; border-radius:8px; text-decoration:none; display:inline-block; margin:4px 6px 0 0 }}
img {{ width:100%; border-radius:8px; display:block; background:#000 }} table {{ width:100%; border-collapse:collapse; font-size:13px }}
td,th {{ padding:6px 8px; border-bottom:1px solid #262a2f; text-align:left; vertical-align:top }} tr.ok td:nth-child(4) {{ color:var(--ok) }}
tr.close td:nth-child(4) {{ color:var(--close) }} tr.off td:nth-child(4) {{ color:var(--off); font-weight:600 }} .pill {{ display:inline-block; padding:2px 10px; border-radius:99px; background:var(--card) }}
</style></head><body><main>
<h1>{html.escape(a.title)}</h1><div class="sub">{html.escape(T["how"])}</div>
<ol class="steps">{steps}</ol>{f'<div class="note">{html.escape(a.note)}</div>' if a.note else ''}
<div class="sub" style="margin-top:8px">{(html.escape(T["score"]) + ': <span class="pill">' + verdict + '</span>') if verdict else ''}</div>
{('<div class="vids"><figure><video id="vr" src="' + ref + '" muted playsinline preload="auto"></video><figcaption>' + html.escape(T["reference"]) + '</figcaption></figure><figure><video id="vo" src="' + ours + '" muted playsinline preload="auto"></video><figcaption>' + html.escape(T["ours"]) + '</figcaption></figure></div>') if ref else
  ('<div class="phone"><video id="vo" src="' + ours + '" muted playsinline preload="auto" style="border-radius:16px"></video></div><div class="sub" style="text-align:center;margin-top:6px">' + html.escape(T["ours"]) + '</div>')}
<div class="bar" style="justify-content:center"><button id="like" class="big">{html.escape(T["like"])}</button></div>
<div class="bar"><button id="pp">{T["play"]}</button><button id="fb">−1 frame</button><button id="ff">+1 frame</button>
<input id="sk" type="range" min="0" max="1000" value="0"><span id="tc" class="sub">0.00 s</span></div>
<h2>{html.escape(T["change"])}</h2><textarea id="cm" placeholder="{html.escape(T["placeholder"])}"></textarea>
<div class="bar"><button id="cp">{html.escape(T["copy"])}</button><span id="cpok" class="sub"></span></div>
<h2>{html.escape(T["files"])}</h2><div class="files">{''.join(f'<a href="{p}" download>⬇ {html.escape(n)}</a>' for n, p in files if p)}<a href="review-files/">📂 {html.escape(T["folder"])}</a></div>
{''.join(f'<h2>{html.escape(l)}</h2><img src="{p}" alt="{html.escape(l)}">' for l, p in imgs)}
{('<h2>' + html.escape(T["score"]) + '</h2>' + table) if table else ''}
</main><script>
const V = [...document.querySelectorAll("video")], pp = document.getElementById("pp"), sk = document.getElementById("sk"), tc = document.getElementById("tc");
const main = document.getElementById("vo"); let playing = false;
const dur = () => Math.max(...V.map(v => v.duration || 0)) || 1;
function seek(t) {{ V.forEach(v => {{ v.currentTime = Math.min(t, (v.duration || t) - 0.001); }}); }}
const L = {json.dumps(T, ensure_ascii=False)};
pp.onclick = () => {{ playing = !playing; V.forEach(v => playing ? v.play() : v.pause()); pp.textContent = playing ? L.pause : L.play; }};
document.getElementById("like").onclick = async () => {{ try {{ await navigator.clipboard.writeText(L.likemsg); }} catch (e) {{}}
  document.getElementById("cpok").textContent = L.copied; }};
document.getElementById("cp").onclick = async () => {{
  const t = main.currentTime, msg = L.at.replace("{{t}}", t.toFixed(2)).replace("{{f}}", Math.round(t * 30)) + ": " + document.getElementById("cm").value.trim();
  try {{ await navigator.clipboard.writeText(msg); }} catch (e) {{ const ta = document.getElementById("cm"); ta.value = msg; ta.select(); document.execCommand("copy"); }}
  document.getElementById("cpok").textContent = L.copied; }};
document.getElementById("fb").onclick = () => seek(Math.max(0, main.currentTime - 1 / 30));
document.getElementById("ff").onclick = () => seek(main.currentTime + 1 / 30);
sk.oninput = () => seek(sk.value / 1000 * dur());
main.addEventListener("timeupdate", () => {{ sk.value = main.currentTime / dur() * 1000; tc.textContent = main.currentTime.toFixed(2) + " s · frame " + Math.round(main.currentTime * 30);
  V.forEach(v => {{ if (v !== main && Math.abs(v.currentTime - main.currentTime) > 0.08) v.currentTime = main.currentTime; }}); }});
main.addEventListener("ended", () => {{ playing = false; pp.textContent = L.play; }});
</script></body></html>"""
open(a.out, "w", encoding="utf-8").write(page)
print(a.out)
