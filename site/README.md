# DataCore CLI documentation

The public documentation is built with Astro Starlight and published through GitHub Pages.

```bash
npm ci
npm run build
npm run dev -- --background
```

`npm run build` regenerates the CLI command reference, Markdown twins, `llms.txt`, `commands.json`, and published Skill files from the current repository sources before building the site.
