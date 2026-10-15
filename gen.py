"""Generate dark_mode.svg / light_mode.svg (Andrew6rant-style neofetch card)."""
import datetime, json, urllib.request
from xml.sax.saxutils import escape
from dateutil.relativedelta import relativedelta
from PIL import Image, ImageOps

USER = "h4ckibl3"
W, H, WIDTH = 30, 20, 57
ART_X, ART_Y = 58, 85   # small face, centred in the left column   # ascii cols/rows, info line width in chars

def uptime():
    d = relativedelta(datetime.date.today(), datetime.date(2005, 7, 11))
    p = lambda n, w: f"{n} {w}" + ("s" if n != 1 else "")
    return f"{p(d.years,'year')}, {p(d.months,'month')}, {p(d.days,'day')}"

def stats():
    try:
        get = lambda u: json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": USER}), timeout=20))
        u = get(f"https://api.github.com/users/{USER}")
        repos = get(f"https://api.github.com/users/{USER}/repos?per_page=100")
        return u["public_repos"], sum(r["stargazers_count"] for r in repos), u["followers"]
    except Exception:
        return None

def ascii_art():
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
    s = a.shape[0] / 800   # tight face crop (hair to chin) tuned for the 800px avatar; w/h 0.72 = 30x20 cells
    box = tuple(int(c * s) for c in (305, 150, 530, 462))
    t = ImageOps.autocontrast(src.convert("L"), cutoff=3, mask=Image.fromarray(((~bg) * 255).astype("uint8")))
    t = t.crop(box).filter(ImageFilter.MinFilter(3))   # thicken glasses frames / brows
    x = np.asarray(t.resize((W, H), Image.BOX)).astype(float) / 255
    x[np.asarray(Image.fromarray(bg).crop(box).resize((W, H)))] = 0
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
        (["Languages", "Real"], "English, Hindi"),
        None,
        (["Hobbies", "Software"], "Figuring out"),
        (["Hobbies", "Hardware"], "CAN bus / UDS, JTAG/UART/SWD, SDR"),
        "skip", "- Contact",
        (["Email", "Personal"], "asutoshkumar560@gmail.com"),
        (["LinkedIn"], "asutosh-kumar-h4ckibl3")]
    s = stats()
    if s:
        rows += ["skip", "- GitHub Stats",
                 (["Repos"], f"{s[0]:,}"), (["Stars"], f"{s[1]:,}"), (["Followers"], f"{s[2]:,}")]
    out = []
    for i, r in enumerate(rows):
        y = 30 + 20 * i
        if r == "skip": continue
        if r is None: out.append(f'<tspan x="390" y="{y}" class="cc">. </tspan>')
        elif isinstance(r, str): out.append(r if r.startswith("<") else header(y, r))
        else: out.append(kv(y, *r))
    return out

def svg(name, bg, fg, key, val, cc):
    art = "\n".join(f'<tspan x="{ART_X}" y="{ART_Y+20*i}">{escape(l)}</tspan>' for i, l in enumerate(ascii_art()))
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
text, tspan {{white-space: pre;}}
</style>
<rect width="985px" height="530px" fill="{bg}" rx="15"/>
<text x="{ART_X}" y="{ART_Y}" fill="{fg}" class="ascii">
{art}
</text>
<text x="390" y="30" fill="{fg}">
""" + "\n".join(build()) + "\n</text>\n</svg>\n")

svg("dark_mode.svg", "#161b22", "#c9d1d9", "#ffa657", "#a5d6ff", "#616e7f")
svg("light_mode.svg", "#f6f8fa", "#24292f", "#953800", "#0a3069", "#c2cfde")

try:  # local preview only (monospace substitute for Consolas)
    import cairosvg
    prev = open("dark_mode.svg").read().replace("ConsolasFallback,Consolas,monospace", "monospace")
    import re
    prev = re.sub(r'(<tspan x="\d+" y="\d+">)([^<]*)', lambda m: m.group(1) + m.group(2).replace(" ", "\u00a0"), prev)
    cairosvg.svg2png(bytestring=prev.encode(),
                     write_to="/workspace/gh_profile_preview.png")
except Exception:
    pass
