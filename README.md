# isyourbrainfoss Flatpak repository

Signed Flatpak repository for isyourbrainfoss apps, served from GitHub Pages:
**https://isyourbrainfoss.github.io/flatpak/**

```sh
flatpak remote-add --user --if-not-exists isyourbrainfoss \
  https://isyourbrainfoss.github.io/flatpak/isyourbrainfoss.flatpakrepo
flatpak install isyourbrainfoss org.gator.Gator
```

Opening `isyourbrainfoss.flatpakrepo` in GNOME Software or KDE Discover adds it too. Bazaar
(0.10) then lists, updates and removes the apps. Runtimes come from Flathub (`RuntimeRepo`).

| App | Archs | Source |
|---|---|---|
| Gator `org.gator.Gator` | x86_64, aarch64 | built here from the newest [gator](https://github.com/isyourbrainfoss/gator) release tag |
| Cake Wallet Mobile `io.github.isyourbrainfoss.CakeWalletMobile` | aarch64 | bundle from [cake_wallet](https://github.com/isyourbrainfoss/cake_wallet) releases `mobile-*` |
| Proton Pass GTK `io.github.isyourbrainfoss.ProtonPassGtk` | x86_64, aarch64 | bundles from [proton-pass-gtk](https://github.com/isyourbrainfoss/proton-pass-gtk) releases `v*` |

## Signing key

`keys/isyourbrainfoss-flatpak.gpg`, fingerprint `BABF8418E33AC28EED200FA6AAF9EBAFDEC4B371` (RSA 4096, expires 2031-11-14).
Commits, the summary and appstream are signed. The private key and its passphrase exist only as
Actions secrets in this repo (`FLATPAK_GPG_PRIVATE_KEY`, `FLATPAK_GPG_PASSPHRASE`) and in an
offline backup. Nothing secret is stored in git.

## How publishing works

`.github/workflows/publish.yml` runs on `repository_dispatch` (`app-updated`, sent by app
release workflows), weekly, on manual dispatch, and on pushes to `main`:

1. `tools/plan.py`: compares the newest release of every app in `apps.yml` with the published `state.json`.
2. `build`: builds `source.type: build` apps on native `ubuntu-24.04` / `ubuntu-24.04-arm` runners.
3. `publish`: mirrors the live repo (`ostree pull --mirror --depth=1`, signature-checked), imports new
   builds/bundles with `flatpak build-commit-from` on branch `stable`, then
   `flatpak build-update-repo --generate-static-deltas --prune --prune-depth=1`, all GPG-signed.
4. `tools/gen_site.py`: generates `index.html`, `isyourbrainfoss.flatpakrepo`, one `.flatpakref` per
   app and `state.json`, then deploys with `actions/deploy-pages`. There is no `gh-pages` branch, so
   nothing else can overwrite the landing page.

The run fails before deploying if the site exceeds 900 MB or any file exceeds 95 MB (Pages limits: 1 GB, 100 MB).

### Notifying from an app repo

```sh
gh api repos/isyourbrainfoss/flatpak/dispatches -f event_type=app-updated \
  -F 'client_payload[app]=<app-id>' -F 'client_payload[tag]=<tag>'
```
This needs a token in the app repo's `FLATPAK_DISPATCH_TOKEN` secret. Without it, the weekly run picks up new releases.
