# Brand-Format

```
brands/<name>/
├── brand.json     { "name": "<theme-name>", "logo": "assets/<datei>" }
├── tokens.css     :root { … }
└── assets/        Logo, Hintergründe, Fonts
```

## Pflicht-Tokens
`--primary`, `--primary-dk`, `--primary-lt`, `--primary-xl`, `--dark`, `--text`, `--muted`, `--border`, `--light`, `--white`, `--grey-label`, `--grey-mid`, `--callout`, `--font`.

`--logo` setzt der Build, nicht in `tokens.css` definieren.

`brand.json.name` = `theme:` im Frontmatter der Decks.
