#!/usr/bin/env python3
"""Render the GitHub Pages site (landing page, .flatpakrepo, .flatpakref, state.json).

The landing page is generated on every publish, so nothing else can overwrite it.
"""
import base64
import html
import json
import os
import shutil
import subprocess

SITE_URL = os.environ.get("SITE_URL", "https://isyourbrainfoss.github.io/flatpak").rstrip("/")
REPO_URL = f"{SITE_URL}/repo/"
REMOTE = "isyourbrainfoss"
COLLECTION_ID = "io.github.isyourbrainfoss.Flatpak"
RUNTIME_REPO = "https://dl.flathub.org/repo/flathub.flatpakrepo"
KEYFILE = "keys/isyourbrainfoss-flatpak.gpg"

plan = json.load(open("plan.json"))
key_b64 = base64.b64encode(open(KEYFILE, "rb").read()).decode()
fpr = subprocess.run(
    ["gpg", "--show-keys", "--with-colons", KEYFILE], capture_output=True, text=True, check=True
).stdout
fpr = next(l.split(":")[9] for l in fpr.splitlines() if l.startswith("fpr:"))
refs = subprocess.run(["ostree", "--repo=repo", "refs"], capture_output=True, text=True, check=True).stdout.split()

present = {}
for r in refs:
    parts = r.split("/")
    if len(parts) == 4 and parts[0] == "app":
        present.setdefault(parts[1], set()).add(parts[2])

os.makedirs("site/keys", exist_ok=True)
shutil.copytree("repo", "site/repo")
shutil.copy(KEYFILE, "site/keys/")
shutil.copy("site-static/style.css", "site/style.css")
open("site/.nojekyll", "w").close()

open(f"site/{REMOTE}.flatpakrepo", "w").write(f"""[Flatpak Repo]
Title=isyourbrainfoss apps
Url={REPO_URL}
Homepage={SITE_URL}/
Comment=Signed Flatpak builds of isyourbrainfoss apps
Description=Gator, Cake Wallet Mobile and other apps by isyourbrainfoss, for x86_64 and aarch64
DeployCollectionID={COLLECTION_ID}
RuntimeRepo={RUNTIME_REPO}
GPGKey={key_b64}
""")

# State: previous state, updated only for app/arch refs that now exist and were part of this plan.
state = plan.get("previous_state", {"apps": {}})
state.setdefault("apps", {})
for item in plan["builds"] + plan["downloads"]:
    if item["arch"] in present.get(item["app"], set()):
        state["apps"].setdefault(item["app"], {})[item["arch"]] = item["key"]
json.dump(state, open("site/state.json", "w"), indent=2)

cards = []
for app in plan["apps"]:
    archs = sorted(present.get(app["id"], set()))
    e = {k: html.escape(str(v or "")) for k, v in app.items()}
    if archs:
        open(f"site/{app['id']}.flatpakref", "w").write(f"""[Flatpak Ref]
Title={app['name']}
Name={app['id']}
Branch=stable
Url={REPO_URL}
SuggestRemoteName={REMOTE}
Homepage={app['homepage']}
Icon={app['icon']}
RuntimeRepo={RUNTIME_REPO}
IsRuntime=false
DeployCollectionID={COLLECTION_ID}
GPGKey={key_b64}
""")
        action = (f'<a class="btn" href="{e["id"]}.flatpakref">Install</a>'
                  f'<code>flatpak install {REMOTE} {e["id"]}</code>')
        status = " · ".join(archs)
    else:
        action = '<span class="soon">Not published yet</span>'
        status = "coming soon"
    cards.append(f"""<article class="app">
  <img src="{e['icon']}" alt="" width="64" height="64" onerror="this.style.visibility='hidden'">
  <div><h2><a href="{e['homepage']}">{e['name']}</a></h2><p>{e['summary']}</p>
  <p class="meta"><code>{e['id']}</code> · {status}</p>{action}</div>
</article>""")

fpr_spaced = " ".join(fpr[i:i + 4] for i in range(0, len(fpr), 4))
open("site/index.html", "w").write(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>isyourbrainfoss Flatpak repository</title>
<link rel="stylesheet" href="style.css"></head>
<body><main>
<h1>isyourbrainfoss Flatpak repository</h1>
<p>Signed Flatpak builds for x86_64 and aarch64. Runtimes come from Flathub.
Add the repository once; after that, apps update through <code>flatpak update</code>,
GNOME Software, KDE Discover or Bazaar.</p>
<p><a class="btn" href="{REMOTE}.flatpakrepo">Add repository</a></p>
<pre>flatpak remote-add --user --if-not-exists {REMOTE} {SITE_URL}/{REMOTE}.flatpakrepo</pre>
<section class="apps">{''.join(cards)}</section>
<h2>Signing key</h2>
<p>Everything (commits, summary, appstream) is signed with
<a href="keys/isyourbrainfoss-flatpak.gpg">this key</a>:<br><code>{fpr_spaced}</code></p>
<h2>Moving from an older install</h2>
<pre># Gator from the old unsigned repo (remote "gator"):
flatpak install --user --reinstall {REMOTE} org.gator.Gator
flatpak remote-delete --user gator

# Cake Wallet Mobile installed from a .flatpak bundle:
flatpak install --user --reinstall {REMOTE} io.github.isyourbrainfoss.CakeWalletMobile
flatpak remote-delete --user cakewalletmobile1-origin</pre>
<p>App data in <code>~/.var/app/</code> is kept. Use <code>--system</code> instead of
<code>--user</code> for system-wide installs.</p>
<footer><a href="https://github.com/isyourbrainfoss/flatpak">Source and build workflow</a></footer>
</main></body></html>
""")
print("site rendered; apps present:", {k: sorted(v) for k, v in present.items()})
