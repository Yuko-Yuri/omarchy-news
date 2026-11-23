#!/usr/bin/env python3
"""Check every story and write feed.json and the README lists. Standard library only.

  python3 tools/build.py          write
  python3 tools/build.py --check  fail if anything is wrong or out of date
"""
import json, re, sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
REPO = "https://github.com/parker-brown-family/omarchy-news"
RAW = "https://raw.githubusercontent.com/parker-brown-family/omarchy-news/main"
STATUS = {"read", "counted", "said", "open"}
KINDS = {"primary", "report", "critic", "post", "code"}
DATE = re.compile(r"\d{4}-\d{2}-\d{2}$")
FIELDS = {"id", "title", "date", "summary", "topics", "claims", "sources", "to_find", "would_change"}


def load(name):
    return json.loads((R / name).read_text())


def stories():
    return sorted((json.loads(p.read_text()) for p in (R / "stories").glob("*.json")),
                  key=lambda s: (s["date"], s["id"]), reverse=True)


def problems(S, T, V):
    out, topics, ids = [], {t["id"] for t in T}, {s["id"] for s in S}
    for p in (R / "stories").glob("*.json"):
        s = json.loads(p.read_text())
        bad = lambda m: out.append(f"{p.name}: {m}")
        if set(s) != FIELDS:
            bad(f"fields differ: {sorted(set(s) ^ FIELDS)}")
            continue
        if s["id"] != p.stem: bad("id is not the file name")
        if not DATE.match(s["date"]): bad("date is not YYYY-MM-DD")
        if not s["topics"]: bad("no topic")
        for t in s["topics"]:
            if t["id"] not in topics: bad(f"unknown topic {t['id']}")
            if not t["angle"].strip(): bad(f"no angle for {t['id']}")
        angles = [t["angle"] for t in s["topics"]]
        if len(set(angles)) != len(angles): bad("two topics share an angle")
        src = {x["id"]: x for x in s["sources"]}
        if len(src) != len(s["sources"]): bad("two sources share an id")
        for x in s["sources"]:
            if not x["url"].startswith("https://"): bad(f"source {x['id']}: not https")
            if x["kind"] not in KINDS: bad(f"source {x['id']}: kind {x['kind']}")
            for k in ("published", "read"):
                if x[k] is not None and not DATE.match(x[k]): bad(f"source {x['id']}: {k}")
        for c in s["claims"]:
            if c["status"] not in STATUS: bad(f"status {c['status']}")
            if c["status"] != "open" and not c["sources"]: bad("a claim has no source: " + c["text"][:40])
            for i in c["sources"]:
                if i not in src: bad(f"claim cites missing source {i}")
                elif src[i]["read"] is None: bad(f"claim cites {i}, which nobody has read")
    for v in V:
        for i in v["stories"]:
            if i not in ids: out.append(f"videos.json: {v['id']} names missing story {i}")
        if not (R / v["poster"]).exists(): out.append(f"videos.json: no poster for {v['id']}")
    return out


def feed(S, T, V, I):
    items = [{
        "id": s["id"], "url": f"{REPO}/blob/main/stories/{s['id']}.json", "title": s["title"],
        "content_text": s["summary"], "date_published": s["date"] + "T00:00:00Z",
        "tags": [t["id"] for t in s["topics"]],
        "_omarchy_news": {"story": f"{RAW}/stories/{s['id']}.json", "angles": s["topics"], "claims": s["claims"],
                          "sources": s["sources"], "to_find": s["to_find"], "would_change": s["would_change"],
                          "issue": f"{REPO}/issues/{I[s['id']]}" if s["id"] in I else None,
                          "videos": [v["url"] for v in V if s["id"] in v["stories"]]},
    } for s in S]
    return {"version": "https://jsonfeed.org/version/1.1", "title": "Omarchy News", "home_page_url": REPO,
            "feed_url": f"{RAW}/feed.json", "description": "Omarchy news with its sources. Unofficial.",
            "_omarchy_news": {"topics": T, "videos": V}, "items": items}


def lists(S, T, V, I):
    o = ["## Videos", ""]
    for v in sorted(V, key=lambda v: v["sealed"], reverse=True):
        o += [f"[![{v['title']}]({v['poster']})]({v['release']})", "",
              f"**[{v['title']}]({v['release']})** · {v['seconds'] // 60}:{v['seconds'] % 60:02d} · sealed {v['sealed']} · "
              + "; ".join(v["credits"]), ""]
    for t in T:
        o += [f"## {t['title']}", "", f"{t['question']} Film: {t['film']}.", ""]
        for s in S:
            a = [x["angle"] for x in s["topics"] if x["id"] == t["id"]]
            if a:
                issue = f" · [open questions]({REPO}/issues/{I[s['id']]})" if s["id"] in I else ""
                o.append(f"- **[{s['title']}](stories/{s['id']}.json)** ({s['date']}). {a[0]}{issue}")
        o.append("")
    return "\n".join(o)


def main():
    S, T, V = stories(), load("topics.json"), load("videos.json")
    I = load("issues.json") if (R / "issues.json").exists() else {}
    bad = problems(S, T, V)
    if bad:
        print("\n".join(bad)); return 1
    readme = (R / "README.md").read_text()
    a, b = "<!-- news -->", "<!-- /news -->"
    new = readme[:readme.index(a) + len(a)] + "\n" + lists(S, T, V, I) + readme[readme.index(b):]
    want = {"README.md": new, "feed.json": json.dumps(feed(S, T, V, I), indent=1, ensure_ascii=False) + "\n"}
    stale = [n for n, t in want.items() if not (R / n).exists() or (R / n).read_text() != t]
    if "--check" in sys.argv:
        if stale: print("out of date, run tools/build.py:", ", ".join(stale))
        else: print(f"ok: {len(S)} stories, {sum(len(s['sources']) for s in S)} sources, {len(V)} videos")
        return 1 if stale else 0
    for n in stale: (R / n).write_text(want[n])
    print(f"{len(S)} stories; wrote {', '.join(stale) or 'nothing'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
