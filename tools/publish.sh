#!/usr/bin/env bash
# Assemble, sign and prune the ostree repo, then render the Pages site into ./site.
# Expects: GNUPGHOME with the signing key (passphrase preset), GPG_FPR, plan.json,
# build artifacts in ./artifacts/build-*/repo.tar, release bundles in ./bundles/.
set -euo pipefail

SITE_URL=${SITE_URL:-https://isyourbrainfoss.github.io/flatpak}
COLLECTION_ID=io.github.isyourbrainfoss.Flatpak
BRANCH=stable
SIGN=(--gpg-sign="$GPG_FPR" --gpg-homedir="$GNUPGHOME")

rm -rf repo incoming site
ostree --repo=repo init --mode=archive-z2 --collection-id="$COLLECTION_ID"

# 1. Start from what is live, so unchanged apps keep their commits and history.
if curl -fsSI "$SITE_URL/repo/summary" >/dev/null 2>&1; then
  ostree --repo=repo remote add --gpg-import=keys/isyourbrainfoss-flatpak.gpg \
    --collection-id="$COLLECTION_ID" live "$SITE_URL/repo/"
  ostree --repo=repo pull --mirror --depth=1 live
  ostree --repo=repo remote delete live
else
  echo "::notice::No live repo yet, starting empty"
fi
echo "Live refs:"; ostree --repo=repo refs | sort

# 2. Gather new content in an unsigned scratch repo.
ostree --repo=incoming init --mode=archive-z2
shopt -s nullglob
for t in artifacts/build-*/repo.tar; do
  d=$(mktemp -d); tar -xf "$t" -C "$d"
  for r in $(ostree --repo="$d/repo" refs); do
    case "$r" in *.Debug/*) continue ;; esac
    ostree --repo=incoming pull-local "$d/repo" "$r"
  done
  rm -rf "$d"
done
for b in bundles/*.flatpak; do
  flatpak build-import-bundle --no-update-summary incoming "$b"
done

# 3. Commit each ref into the public repo on branch 'stable', signed, parented on the live commit.
imported=()
for src in $(ostree --repo=incoming refs | sort); do
  case "$src" in app/*|runtime/*) ;; *) continue ;; esac
  IFS=/ read -r kind id arch _branch <<<"$src"
  dst="$kind/$id/$arch/$BRANCH"
  flatpak build-commit-from --src-repo=incoming --src-ref="$src" "${SIGN[@]}" \
    --no-update-summary --subject="Publish $id ($arch)" repo "$dst"
  imported+=("$dst")
done
printf 'Imported: %s\n' "${imported[@]:-none}"

# 4. Summary, appstream, deltas, prune. All signed.
flatpak build-update-repo "${SIGN[@]}" --gpg-import=keys/isyourbrainfoss-flatpak.gpg \
  --title="isyourbrainfoss apps" --default-branch="$BRANCH" \
  --generate-static-deltas --static-delta-ignore-ref='*.Debug' \
  --prune --prune-depth=1 repo
ostree --repo=repo summary --view | grep -v 'xa.gpg-keys' | cut -c1-200 | head -40

# 5. Site.
python3 tools/gen_site.py
du -sh site
size=$(du -sb site | cut -f1)
if [ "$size" -gt $((900 * 1024 * 1024)) ]; then echo "::error::site is $size bytes (> 900 MB)"; exit 1; fi
big=$(find site -type f -size +95M)
if [ -n "$big" ]; then echo "::error::files over 95 MB: $big"; exit 1; fi
