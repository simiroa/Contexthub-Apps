# Contexthub-Apps (Marketplace)

This repository hosts the marketplace applications for ContextHub.

## How to add/update an app

1.  **Create a folder** in `apps/` with your app's ID (e.g., `apps/my-cool-tool/`).
2.  **Add a `manifest.json`** inside that folder with the correct `id`, `name`, and `version`.
3.  **Place your source code** (e.g., `.py` files) in the same folder.
4.  **Push to `main`**.

## How it works (Automation)

- A GitHub Action (`market-release.yml`) triggers on every push to the `apps/` directory.
- It automatically zips each app folder.
- It updates the `market.json` registry file with the new download links.
- It creates/updates a GitHub Release named `marketplace-latest` with the updated ZIP assets.

## Integration with ContextHub

The ContextHub Host app fetches the registry from:
`https://raw.githubusercontent.com/[YOUR-USERNAME]/Contexthub-Apps/main/market.json`
