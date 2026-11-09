"""Render the GitHub contribution calendar as light and dark SVGs.

Usage: python3 tools/contrib_graph.py OUT_DIR [calendar.json]
Without a JSON file it queries the GraphQL API with $GITHUB_TOKEN.
"""
import datetime
import json
import os
import sys
import urllib.request

LOGIN = "Paul-Antoine-Bonin"
QUERY = """query($login: String!) { user(login: $login) { contributionsCollection {
  contributionCalendar { totalContributions weeks { firstDay
    contributionDays { date contributionCount contributionLevel weekday } } } } } }"""

LEVELS = ["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"]
THEMES = {
    "light": dict(fg="#1F2328", muted="#59636E", accent="#1A7F64",
                  cells=["#EFF2F5", "#B7E4D3", "#6CC4A4", "#2E9D78", "#1A6E55"]),
    "dark": dict(fg="#F0F6FC", muted="#9198A1", accent="#3FB98F",
                 cells=["#151B23", "#0E3B2E", "#17664D", "#2A9A74", "#4FD1A1"]),
}
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

W, H = 900, 190
X0, Y0, CELL, STEP = 76, 64, 11, 14


def fetch():
    body = json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": "bearer " + os.environ["GITHUB_TOKEN"],
        "Content-Type": "application/json",
        "User-Agent": "contrib-graph",
    })
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def render(cal, th):
    weeks = cal["weeks"]
    total = cal["totalContributions"]
    out = []
    # Month labels where a new month starts, skipped when too close to the previous one.
    last_x, last_m = -99, None
    for i, w in enumerate(weeks):
        m = int(w["firstDay"][5:7])
        if m != last_m:
            x = X0 + i * STEP
            if x - last_x >= 3 * STEP and i < len(weeks) - 2:
                out.append('<text x="%d" y="%d" class="lab">%s</text>' % (x, Y0 - 8, MONTHS[m - 1]))
                last_x = x
            last_m = m
    for d, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append('<text x="40" y="%d" class="lab">%s</text>' % (Y0 + d * STEP + 9, name))
    for i, w in enumerate(weeks):
        cells = []
        for day in w["contributionDays"]:
            lvl = LEVELS.index(day["contributionLevel"])
            cells.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s"/>' % (
                X0 + i * STEP, Y0 + day["weekday"] * STEP, CELL, CELL, th["cells"][lvl]))
        out.append('<g class="w" style="animation-delay:%.2fs">%s</g>' % (0.2 + i * 0.012, "".join(cells)))
    # Legend.
    lx = X0 + len(weeks) * STEP - 5 * STEP - 3
    ly = Y0 + 7 * STEP + 16
    out.append('<text x="%d" y="%d" class="lab" text-anchor="end">Less</text>' % (lx - 6, ly + 9))
    for k in range(5):
        out.append('<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s"/>' % (
            lx + k * STEP, ly, CELL, CELL, th["cells"][k]))
    out.append('<text x="%d" y="%d" class="lab">More</text>' % (lx + 5 * STEP + 3, ly + 9))
    updated = datetime.date.today().isoformat()

    return """<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t">
<title id="t">{total} contributions in the last year</title>
<style>
.lab {{ font-family: {FONT}; font-size: 11px; fill: {muted}; }}
.w {{ opacity: 0; animation: fade .5s ease-out forwards; }}
@keyframes fade {{ to {{ opacity: 1; }} }}
@media (prefers-reduced-motion: reduce) {{ .w {{ animation: none; opacity: 1; }} }}
</style>
<text x="40" y="26" font-family="{FONT}" font-size="15" fill="{fg}"><tspan font-weight="700">{total}</tspan> contributions in the last year</text>
<text x="{rx}" y="26" font-family="{MONO}" font-size="11" fill="{accent}" text-anchor="end">updated {updated}</text>
{body}
</svg>
""".format(W=W, H=H, total=total, FONT=FONT, MONO=MONO, rx=X0 + len(weeks) * STEP - 3,
           updated=updated, body="\n".join(out), **{k: th[k] for k in ("fg", "muted", "accent")})


def main():
    out_dir = sys.argv[1]
    data = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else fetch()
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    os.makedirs(out_dir, exist_ok=True)
    for name, th in THEMES.items():
        with open(os.path.join(out_dir, "contrib-%s.svg" % name), "w") as f:
            f.write(render(cal, th))
    print("wrote", out_dir, cal["totalContributions"])


if __name__ == "__main__":
    main()
