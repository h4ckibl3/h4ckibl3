"""Generate dark_mode.svg / light_mode.svg (Andrew6rant-style neofetch card)."""
import datetime, json, urllib.request
from xml.sax.saxutils import escape
from dateutil.relativedelta import relativedelta
from PIL import Image, ImageOps

USER = "h4ckibl3"
W, H, WIDTH = 39, 24, 57
ART_X, ART_Y = 15, 30
LIGHT_GAMMA = 1.0   # small face, centred in the left column   # ascii cols/rows, info line width in chars

def uptime():
    d = relativedelta(datetime.date.today(), datetime.date(2005, 7, 11))
    p = lambda n, w: f"{n} {w}" + ("s" if n != 1 else "")
    return f"{p(d.years,'year')}, {p(d.months,'month')}, {p(d.days,'day')}"

def gh(*args):
    import subprocess
    return json.loads(subprocess.run(["gh", "api", *args], capture_output=True, text=True, check=True).stdout)

def stats():
    """Live stats (like Andrew6rant's today.py) via the gh CLI + GraphQL: repos, contributed,
    stars, followers, and commits / additions / deletions authored by USER in owned repos."""
    q = """query($login:String!){ user(login:$login){ id followers{totalCount}
      repositories(first:100, ownerAffiliations:OWNER){ totalCount nodes{ name isFork stargazerCount } }
      repositoriesContributedTo(first:1, includeUserRepositories:true,
        contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY]){ totalCount } } }"""
    hq = """query($owner:String!,$name:String!,$id:ID!,$after:String){ repository(owner:$owner,name:$name){
      defaultBranchRef{ target{ ... on Commit{ history(first:100, after:$after, author:{id:$id}){
        totalCount pageInfo{hasNextPage endCursor} nodes{additions deletions} } } } } } }"""
    try:
        u = gh("graphql", "-f", f"query={q}", "-f", f"login={USER}")["data"]["user"]
        repos = u["repositories"]["nodes"]
        commits = add = dele = 0
        for r in repos:
            if r["isFork"]: continue
            after = None
            while True:
                args = ["graphql", "-f", f"query={hq}", "-f", f"owner={USER}", "-f", f"name={r['name']}", "-f", f"id={u['id']}"]
                if after: args += ["-f", f"after={after}"]
                ref = gh(*args)["data"]["repository"]["defaultBranchRef"]
                if not ref: break
                h = ref["target"]["history"]
                for n in h["nodes"]:
                    commits += 1; add += n["additions"]; dele += n["deletions"]
                if not h["pageInfo"]["hasNextPage"]: break
                after = h["pageInfo"]["endCursor"]
        return dict(repos=u["repositories"]["totalCount"], contrib=u["repositoriesContributedTo"]["totalCount"],
                    stars=sum(r["stargazerCount"] for r in repos), followers=u["followers"]["totalCount"],
                    commits=commits, add=add, dele=dele)
    except Exception as e:
        print("stats unavailable:", e)
        return None

def ascii_art(light=False):
    """Subject-only ASCII: flood-fill the black bg + white ring/outline from the border,
    equalize the subject, gamma, unsharp mask, crop head & shoulders."""
    import numpy as np
    from PIL import ImageFilter
    src = Image.open("avatar.png").convert("RGB")
    a = np.asarray(src).astype(int); v = a.max(2); sat = v - a.min(2)
    ok = (v < 14) | ((v > 170) & (sat < 40))          # black bg or white ring/outline
    bg = np.zeros_like(ok); bg[0, :] = bg[-1, :] = bg[:, 0] = bg[:, -1] = True; bg &= ok
    while True:
        n = bg.copy(); n[1:] |= bg[:-1]; n[:-1] |= bg[1:]; n[:, 1:] |= bg[:, :-1]; n[:, :-1] |= bg[:, 1:]; n &= ok
        if (n == bg).all(): break
        bg = n
    bg = np.asarray(Image.fromarray((bg * 255).astype("uint8")).filter(ImageFilter.MaxFilter(7))) > 0
    import cv2
    s = a.shape[0] / 800   # tight face crop (hair to chin) tuned for the 800px avatar
    fh = 350; fw = int(fh * W * 9.6 / (H * 20)); cx = 418          # crop aspect = cell grid aspect
    box = tuple(int(c * s) for c in (cx - fw // 2, 150, cx + fw // 2, 150 + fh))
    g = cv2.createCLAHE(clipLimit=3, tileGridSize=(4, 4)).apply(cv2.cvtColor(np.asarray(src).astype("uint8"), cv2.COLOR_RGB2GRAY))
    lo, hi = np.percentile(g[~bg], [2, 98]); g = np.clip((g.astype(float) - lo) / (hi - lo), 0, 1); g[bg] = 0
    t = Image.fromarray((g * 255).astype("uint8")).crop(box).filter(ImageFilter.MinFilter(3))  # thicken frames/brows
    x = np.asarray(t.resize((W, H), Image.BOX)).astype(float) / 255
    if light:   # dense chars read dark on a light card: invert tone so skin stays light, hair/glasses/beard dark
        mk = np.asarray(Image.fromarray((bg * 255).astype("uint8")).crop(box).resize((W, H), Image.BOX)) > 127
        x = np.clip(1 - x, 0, 1) ** LIGHT_GAMMA; x[mk] = 0
    ramp = " .:-=+*#%@"
    return ["".join(ramp[int(c * (len(ramp) - 1))] for c in row) for row in x]

def kv(y, keys, value):
    keystr = ".".join(keys)
    dots = max(1, WIDTH - 5 - len(keystr) - len(value))
    k = '</tspan>.<tspan class="key">'.join(keys)
    return (f'<tspan x="390" y="{y}" class="cc">. </tspan><tspan class="key">{k}</tspan>:'
            f'<tspan class="cc"> {"." * dots} </tspan><tspan class="value">{escape(value)}</tspan>')

def header(y, title):
    return f'<tspan x="390" y="{y}">{title}</tspan> -' + "—" * (WIDTH - len(title) - 5) + "-—-"

def raw_line(parts):
    return lambda y: f'<tspan x="390" y="{y}">' + "".join(
        escape(t) if c is None else f'<tspan class="{c}">{escape(t)}</tspan>' for c, t in parts) + "</tspan>"

def build():
    rows = [header(30, f"asutosh@{USER}"),
        (["OS"], "Linux"),
        (["Uptime"], uptime()),
        (["Host"], "Breachlabz (we hack cars legally)"),
        (["Kernel"], "Penetration Tester, Automotive & IoT"),
        (["IDE"], "Ghidra, Burp Suite, VSCode"),
        None,
        (["Languages", "Programming"], "Bash, C, Python, JavaScript"),
        (["Languages", "Computer"], "HTML, CSS"),
        (["Languages", "Real"], "English"),
        None,
        (["Hobbies", "Software"], "Figuring out"),
        (["Hobbies", "Hardware"], "CAN bus / UDS, JTAG/UART/SWD, SDR"),
        (["Hobbies", "Real"], "Hackathons, Bikes"),
        "skip", "- Contact",
        (["Email", "Personal"], "asutoshkumar560@gmail.com"),
        (["LinkedIn"], "asutosh-kumar-h4ckibl3"),
        (["Twitter"], "x.com/h4ckibl3")]
    s = stats()
    if s:
        f = lambda n: f"{n:,}"
        d = lambda n, v: ("cc", " " + "." * max(1, n - len(v)) + " ")
        loc = f(s["add"] - s["dele"])
        rows += ["skip", "- GitHub Stats",
            raw_line([("cc", ". "), ("key", "Repos"), (None, ":"), d(5, f(s["repos"])), ("value", f(s["repos"])),
                      (None, " {"), ("key", "Contributed"), (None, ": "), ("value", f(s["contrib"])), (None, "} | "),
                      ("key", "Stars"), (None, ":"), d(12, f(s["stars"])), ("value", f(s["stars"]))]),
            raw_line([("cc", ". "), ("key", "Commits"), (None, ":"), d(19, f(s["commits"])), ("value", f(s["commits"])),
                      (None, " | "), ("key", "Followers"), (None, ":"), d(8, f(s["followers"])), ("value", f(s["followers"]))]),
            raw_line([("cc", ". "), ("key", "Lines of Code on GitHub"), (None, ":"), d(2, loc), ("value", loc),
                      (None, " ( "), ("add", f(s["add"]) + "++"), (None, ", "), ("del", f(s["dele"]) + "--"), (None, " )")])]
    out = []
    for i, r in enumerate(rows):
        y = 30 + 20 * i
        if r == "skip": continue
        if r is None: out.append(f'<tspan x="390" y="{y}" class="cc">. </tspan>')
        elif callable(r): out.append(r(y))
        elif isinstance(r, str): out.append(r if r.startswith("<") else header(y, r))
        else: out.append(kv(y, *r))
    return out

def svg(name, bg, fg, key, val, cc, add, dl, art_fg=None, light=False):
    art = "\n".join(f'<tspan x="{ART_X}" y="{ART_Y+20*i}">{escape(l)}</tspan>' for i, l in enumerate(ascii_art(light)))
    open(name, "w").write(f"""<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,monospace" width="985px" height="530px" font-size="16px">
<style>
@font-face {{
src: local('Consolas'), local('Consolas Bold');
font-family: 'ConsolasFallback';
font-display: swap;
-webkit-size-adjust: 109%;
size-adjust: 109%;
}}
.key {{fill: {key};}}
.value {{fill: {val};}}
.cc {{fill: {cc};}}
.add {{fill: {add};}}
.del {{fill: {dl};}}
text, tspan {{white-space: pre;}}
</style>
<rect width="985px" height="530px" fill="{bg}" rx="15"/>
<text x="{ART_X}" y="{ART_Y}" fill="{art_fg or fg}" class="ascii">
{art}
</text>
<text x="390" y="30" fill="{fg}">
""" + "\n".join(build()) + "\n</text>\n</svg>\n")

svg("dark_mode.svg", "#161b22", "#c9d1d9", "#ffa657", "#a5d6ff", "#616e7f", "#3fb950", "#f85149")
svg("light_mode.svg", "#f6f8fa", "#24292f", "#953800", "#0a3069", "#c2cfde", "#1a7f37", "#cf222e", light=True)

try:  # local preview only (monospace substitute for Consolas)
    import cairosvg
    import re
    for mode, out in (("dark", "/workspace/gh_profile_preview.png"), ("light", "/workspace/gh_profile_preview_light.png")):
        prev = open(f"{mode}_mode.svg").read().replace("ConsolasFallback,Consolas,monospace", "monospace")
        prev = re.sub(r'(<tspan x="\d+" y="\d+">)([^<]*)', lambda m: m.group(1) + m.group(2).replace(" ", "\u00a0"), prev)
        cairosvg.svg2png(bytestring=prev.encode(), write_to=out)
except Exception:
    pass
