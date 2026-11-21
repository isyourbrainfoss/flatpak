# Avvik

Deviations and changes to how the shared Flatpak repository is published. Each entry records what changed, why, which files, the sha256, the off switch, and the rollback.

## 2026-11-21 — Deploy GitHub Pages in a separate `deploy` job

### What

In `.github/workflows/publish.yml`, `actions/deploy-pages@v4` moved out of the `publish` job into a new `deploy` job:

- `deploy` has `needs: publish`, runs on `ubuntu-24.04`, and holds the `github-pages` environment (`url: ${{ steps.deploy.outputs.page_url }}`) and the permissions `pages: write` and `id-token: write`.
- `publish` keeps everything else unchanged (download the plan, build artifacts and release bundles, import the key, assemble, sign, prune, remove the key, `actions/upload-pages-artifact@v3`). Its permissions are now just `contents: read`, and it no longer uses the `github-pages` environment, because it no longer deploys.

The triggers, concurrency, `plan`, `build`, `tools/` scripts, signing key handling and the site content are unchanged.

### Why

On 2026-11-21 three publish attempts failed at the deploy step after the new Flowlog build-228, Navigation build-21 and Spectrogram build-24 (Flutter 3.47.8, no Wayland subsurface renderer) had been imported and signed:

- Run 44891399375, attempt 1, and run 44892410448: `deploy-pages` started in the same second the 291 MB `github-pages` artifact was created and reported `No artifacts named "github-pages" were found`.
- Run 44891399375, attempt 2 ("Re-run failed jobs"): the re-run uploaded a second `github-pages` artifact, and `deploy-pages` then failed with `Multiple artifacts named "github-pages"`.

Putting deploy in its own job is the standard GitHub Pages pattern. The job starts only after the upload job has fully finished, so the artifact is finalized and visible. If deploy still fails, re-running the failed jobs re-runs only `deploy` and reuses the same artifact, with no duplicate upload.

### Files

- `.github/workflows/publish.yml`
- `docs/AVVIK.md`

### sha256

| File | sha256 |
|---|---|
| `.github/workflows/publish.yml` (after this change) | `84c7c5d4fb204600bca3a3327f2ba2c1a4fbec5ae568caf29e85a3336e035fe8` |

### Off switch

None needed. Pages deployment works the same way. Only the job that runs `deploy-pages` changed.

### Rollback

Revert the commit. This puts `deploy-pages` back as the last step of `publish`.
