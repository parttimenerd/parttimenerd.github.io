# parttimenerd.github.io

Personal GitHub Pages site at https://parttimenerd.github.io/ — a Hugo static site with two collection pages:

- **[/femto/](https://parttimenerd.github.io/femto/)** — femto* Java libraries
- **[/jvm-tools/](https://parttimenerd.github.io/jvm-tools/)** — JVM tools

## How it builds

On every push to `main`:

1. `npm ci` — installs Tailwind CSS + Alpine.js
2. `npx tailwindcss … -o static/main.css` — builds CSS
3. `python scripts/gen_og_image.py` — generates per-page og-images from front matter
4. `hugo --minify` — builds the site
5. `actions/deploy-pages` — publishes to GitHub Pages

---

## Triggering a rebuild from another repo's release workflow

When a tool or library in the `femto` or `jvm-tools` collection cuts a new release, add this step at the end of its release workflow to update the version shown on the site:

### For femto libs (femtolz4, femtocli, femtojson, femtoschema, femtojar)

```yaml
- name: Notify parttimenerd.github.io
  if: success()
  run: |
    curl -s -X POST \
      -H "Authorization: token ${{ secrets.PAGES_DISPATCH_TOKEN }}" \
      -H "Accept: application/vnd.github.v3+json" \
      https://api.github.com/repos/parttimenerd/parttimenerd.github.io/dispatches \
      -d '{"event_type":"femto-release"}'
```

### For jvm tools

```yaml
- name: Notify parttimenerd.github.io
  if: success()
  run: |
    curl -s -X POST \
      -H "Authorization: token ${{ secrets.PAGES_DISPATCH_TOKEN }}" \
      -H "Accept: application/vnd.github.v3+json" \
      https://api.github.com/repos/parttimenerd/parttimenerd.github.io/dispatches \
      -d '{"event_type":"supportability-release"}'
```

### Required secret

Create a fine-grained PAT at https://github.com/settings/personal-access-tokens/new:

- **Name:** `PAGES_DISPATCH_TOKEN`
- **Repository access:** only `parttimenerd/parttimenerd.github.io`
- **Permissions:** Contents (read+write), Actions (write)

Then add it as a secret to each tool repo:

```bash
gh secret set PAGES_DISPATCH_TOKEN --repo parttimenerd/<repo-name>
```

### Triggering manually

```bash
gh workflow run update-femto.yml --repo parttimenerd/parttimenerd.github.io
gh workflow run update-jvm-tools.yml --repo parttimenerd/parttimenerd.github.io
```

---

## Adding a new collection

1. **`content/<section>/_index.md`** — add `title`, `description`, `og_title`, `og_subtitle`, `og_out` in front matter
2. **`data/<section>/static.yaml`** — tool/library entries (copy schema from `data/femto/static.yaml`)
3. **`data/<section>/releases.json`** — seed with `{"entries": {}}`
4. **`.github/workflows/update-<section>.yml`** — copy `update-femto.yml`, change `--section` and event type
5. **`config.yaml`** — add one line to the `params.nav` list
6. **Dispatch snippet** — add to each tool repo's release workflow (see above)

No theme changes needed — og-image is auto-discovered from front matter, collection template is shared.

---

## Local development

```bash
npm install
npx tailwindcss -i themes/projects-theme/assets/css/main.css -o static/main.css --watch &
hugo server --buildDrafts
```

Open http://localhost:1313/
