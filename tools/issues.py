#!/usr/bin/env python3
"""One issue per story, and one per planned film. Creates what issues.json lacks.

  python3 tools/issues.py --dry-run   print the bodies
  python3 tools/issues.py             create them, record the numbers

Issue text links GitHub through redirect.github.com, so a source we cite does not
get a "mentioned this" event in someone else's repository.
"""
import json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build import R, REPO, load, stories

NAME = {"read": "We read it", "counted": "We counted it", "said": "Said, not confirmed", "open": "Open"}
quiet = lambda u: u if u.startswith(REPO) else u.replace("https://github.com/", "https://redirect.github.com/")


def story_body(s):
    src = {x["id"]: x for x in s["sources"]}
    cite = lambda c: ", ".join(f"[{src[i]['publisher']}]({quiet(src[i]['url'])})" for i in c["sources"]) or "no source"
    o = [s["summary"], "", "## What is claimed", ""]
    o += [f"- **{NAME[c['status']]}** ({c['who']}): {c['text']} {cite(c)}" for c in s["claims"]]
    o += ["", "## Sources", "", "| Source | Kind | Published | Read |", "|---|---|---|---|"]
    o += [f"| [{x['publisher']}]({quiet(x['url'])}) | {x['kind']} | {x['published'] or 'not recorded'} | {x['read'] or 'not yet'} |" for x in s["sources"]]
    o += ["", "## Where it is told", ""] + [f"- `{t['id']}`: {t['angle']}" for t in s["topics"]]
    o += ["", "## To find", ""] + [f"- [ ] {f}" for f in s["to_find"]]
    o += ["", "## What would change it", "", s["would_change"], "", "## Done when", "",
          f"Every box above is found or recorded as not findable in [`stories/{s['id']}.json`]({REPO}/blob/main/stories/{s['id']}.json), and `python3 tools/build.py --check` passes."]
    return "\n".join(o)


def film_body(t, S, I):
    o = [t["question"], "", f"Film: {t['film']}.", "", "## Stories", ""]
    for s in S:
        for x in s["topics"]:
            if x["id"] == t["id"]: o.append(f"- [ ] #{I[s['id']]} {x['angle']}")
    o += ["", "## Done when", "", "Every story used on screen has its issue closed, or the film says on screen that the point is unconfirmed; the critics' side has been read first-hand; and the sealed film is in `videos.json`."]
    return "\n".join(o)


def gh(*a, body=None):
    r = subprocess.run(["gh", *a], input=body, text=True, capture_output=True, cwd=R)
    if r.returncode: sys.exit(r.stderr)
    return r.stdout.strip()


def main():
    dry, S, T = "--dry-run" in sys.argv, stories(), load("topics.json")
    f = R / "issues.json"
    I = json.loads(f.read_text()) if f.exists() else {}
    if not dry:
        for l, c in [("provenance", "d8a55e"), ("film", "a1561c")] + [(t["id"], "5b7a99") for t in T]:
            gh("label", "create", l, "--color", c, "--force")
    def make(key, title, body, labels):
        if key in I: return
        if dry:
            print(f"=== {title} [{', '.join(labels)}]\n{body}\n"); I[key] = 0; return
        url = gh("issue", "create", "--title", title, "--body-file", "-", *sum((["--label", l] for l in labels), []), body=body)
        I[key] = int(url.rsplit("/", 1)[1]); f.write_text(json.dumps(I, indent=1) + "\n")
    for s in reversed(S): make(s["id"], s["title"], story_body(s), ["provenance"] + [t["id"] for t in s["topics"]])
    for t in T: make("film-" + t["id"], "Film: " + t["title"], film_body(t, S, I), ["film", t["id"]])
    print(len(I), "issues")


if __name__ == "__main__":
    main()
