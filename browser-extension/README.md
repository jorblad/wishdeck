# WishDeck Browser Extension

Adds a right-click context menu item to send any web page or link to your WishDeck lists.

## How it works

This extension does **not** talk directly to the WishDeck API. Instead it opens the WishDeck web app at `/add?url=...&title=...`, where you can pick a wishlist/category, scrape the link, and save the item. This keeps authentication simple — the web app uses your existing login cookie.

## Install from a release

1. Download `wishdeck-extension.zip` from the GitHub release.
2. Extract the zip.
3. Open `chrome://extensions` (or `edge://extensions`).
4. Enable **Developer mode**.
5. Click **Load unpacked** and select the extracted folder.
6. Right-click any page or link and choose **Add to WishDeck**.

## Install from source

1. Open `chrome://extensions` (or `edge://extensions`).
2. Enable **Developer mode**.
3. Click **Load unpacked** and select this `browser-extension/` folder.
4. Right-click any page or link and choose **Add to WishDeck**.

## Build the zip

```bash
cd browser-extension
npm run build
```

The output is `dist/wishdeck-extension.zip`.

### Firefox

Firefox support for Manifest V3 service-worker backgrounds is still limited. For local testing you may need to use Firefox Nightly with the `extensions.manifestV3.enabled` flag, or convert the background to an event page for MV2.

## Configure

Open the extension options and set your WishDeck host URL. Defaults to `http://localhost:8080` for local development. Use `http://localhost:9000` when running the Vite dev server.

## Icons

The included `icon*.png` files are generated placeholders. Replace them before publishing to the Chrome Web Store / Firefox Add-ons.
