#!/usr/bin/env bash
# Import the signing key from the environment into an ephemeral GNUPGHOME and preset
# its passphrase in gpg-agent, so flatpak/ostree can sign non-interactively.
# Env: FLATPAK_GPG_PRIVATE_KEY, FLATPAK_GPG_PASSPHRASE, GNUPGHOME. Prints only the fingerprint.
set -euo pipefail
: "${FLATPAK_GPG_PRIVATE_KEY:?missing secret FLATPAK_GPG_PRIVATE_KEY}"
: "${FLATPAK_GPG_PASSPHRASE:?missing secret FLATPAK_GPG_PASSPHRASE}"
mkdir -p -m 700 "$GNUPGHOME"
printf 'allow-preset-passphrase\nmax-cache-ttl 86400\ndefault-cache-ttl 86400\n' > "$GNUPGHOME/gpg-agent.conf"
gpgconf --kill gpg-agent 2>/dev/null || true
gpgconf --launch gpg-agent
printf '%s\n' "$FLATPAK_GPG_PRIVATE_KEY" | gpg --batch --quiet --import 2>/dev/null
preset=$(gpgconf --list-dirs libexecdir)/gpg-preset-passphrase
for grip in $(gpg --batch --with-keygrip --with-colons -K | awk -F: '/^grp/{print $10}'); do
  printf '%s' "$FLATPAK_GPG_PASSPHRASE" | "$preset" --preset "$grip"
done
fpr=$(gpg --batch --with-colons -K | awk -F: '/^fpr/{print $10; exit}')
expected=$(gpg --batch --show-keys --with-colons keys/isyourbrainfoss-flatpak.gpg | awk -F: '/^fpr/{print $10; exit}')
[ "$fpr" = "$expected" ] || { echo "secret key $fpr does not match keys/ ($expected)"; exit 1; }
echo test | gpg --batch --pinentry-mode error --local-user "$fpr" --detach-sign >/dev/null
echo "GPG_FPR=$fpr" >> "${GITHUB_ENV:-/dev/null}"
echo "Signing key ready: $fpr"
