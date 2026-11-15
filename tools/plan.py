#!/usr/bin/env python3
"""Resolve what to (re)publish.

Reads apps.yml and the currently published state.json, asks the GitHub API for
the newest source of every app, and writes:
  - plan.json   : full plan (consumed by the publish job)
  - $GITHUB_OUTPUT: build_matrix (JSON) and has_builds (true/false)

The publish job writes the new state.json only for what it actually imported.
An app/arch is rebuilt or re-imported only when its source changed, unless
FORCE=true or the app is named in ONLY_APP with FORCE=true.
"""
import json
import os
import subprocess
import sys
import urllib.request

import yaml

SITE = os.environ.get("SITE_URL", "https://isyourbrainfoss.github.io/flatpak").rstrip("/")
FORCE = os.environ.get("FORCE", "false") == "true"
ONLY_APP = os.environ.get("ONLY_APP", "").strip()
RUNNERS = {"x86_64": "ubuntu-24.04", "aarch64": "ubuntu-24.04-arm"}


def gh(path):
    out = subprocess.run(["gh", "api", path], check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def published_state():
    try:
        with urllib.request.urlopen(f"{SITE}/state.json", timeout=30) as r:
            return json.load(r)
    except Exception as e:  # first run, or site down
        print(f"no published state.json ({e}); treating everything as new", file=sys.stderr)
        return {"apps": {}}


def newest_release(repo, prefix=None):
    rels = gh(f"repos/{repo}/releases?per_page=50")
    rels = [r for r in rels if not r["draft"] and (prefix is None or r["tag_name"].startswith(prefix))]
    rels.sort(key=lambda r: r["published_at"] or r["created_at"], reverse=True)
    return rels


def main():
    cfg = yaml.safe_load(open("apps.yml"))
    state = published_state()
    plan = {"apps": [], "downloads": [], "builds": [], "previous_state": state}

    for app in cfg["apps"]:
        app_id, src = app["id"], app["source"]
        prev = state.get("apps", {}).get(app_id, {})
        force = FORCE and (not ONLY_APP or ONLY_APP == app_id)
        entry = {k: app.get(k) for k in ("id", "name", "summary", "homepage", "icon", "archs")}
        entry["published"] = {}

        if src["type"] == "build":
            rels = newest_release(src["repo"])
            if not rels:
                print(f"{app_id}: no releases in {src['repo']}, skipping", file=sys.stderr)
            else:
                tag = rels[0]["tag_name"]
                for arch in app["archs"]:
                    key = f"{src['repo']}@{tag}"
                    if prev.get(arch) == key and not force:
                        print(f"{app_id}/{arch}: {key} already published")
                        continue
                    plan["builds"].append({
                        "app": app_id, "arch": arch, "runner": RUNNERS[arch],
                        "repo": src["repo"], "ref": tag, "manifest": src["manifest"], "key": key,
                    })
        elif src["type"] == "release":
            rels = newest_release(src["repo"], src.get("tag_prefix"))
            for arch in app["archs"]:
                asset_name = f"{app_id}-{arch}.flatpak"
                pick = None
                for r in rels:
                    names = {a["name"]: a for a in r["assets"]}
                    if asset_name in names:
                        pick = (r, names[asset_name], names.get(asset_name + ".sha256"))
                        break
                if not pick:
                    print(f"{app_id}/{arch}: no release with {asset_name} yet, skipping", file=sys.stderr)
                    continue
                rel, asset, sha = pick
                key = f"{src['repo']}@{rel['tag_name']}#{asset['id']}"
                if prev.get(arch) == key and not force:
                    print(f"{app_id}/{arch}: {key} already published")
                    continue
                plan["downloads"].append({
                    "app": app_id, "arch": arch, "repo": src["repo"], "tag": rel["tag_name"],
                    "asset": asset_name, "sha256_asset": sha["name"] if sha else None, "key": key,
                })
        else:
            sys.exit(f"{app_id}: unknown source type {src['type']}")

        plan["apps"].append(entry)

    json.dump(plan, open("plan.json", "w"), indent=2)
    print(json.dumps(plan, indent=2))
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as out:
        out.write(f"build_matrix={json.dumps({'include': plan['builds']})}\n")
        out.write(f"has_builds={'true' if plan['builds'] else 'false'}\n")


if __name__ == "__main__":
    main()
