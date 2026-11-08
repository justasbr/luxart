# Paveikslai

Local Luxart catalogue search. Filters match **one actual size option** against both inclusive width and height bounds. No Python dependencies; use `uv`.

## Run

```sh
uv run python app.py
```

Open http://127.0.0.1:8765. The catalogue in `data/catalog.json` reports its import status and record counts. To populate or update it, run in another terminal with internet access:

```sh
uv run python importer.py
```

Reload the page after importing. Progress is saved every 20 products. The importer discovers product URLs from XML sitemaps, falling back to catalogue pagination, fetches individual product pages, and caches HTML. Requests use 32 workers with one adaptive rate shared by all workers: start at 10 requests/second, increase by 10% after at least 30 seconds and 50 successful network responses, up to 40 requests/second. Cached reads do not increase the rate. HTTP 403/429, server errors, network failures, and recognized challenge-page titles trigger a shared slowdown and cooldown. The rate halves once per failure wave (normally down to 0.5 requests/second), pauses for at least 30 seconds on blocking responses or 5 seconds on other transient errors, and honors longer Retry-After values (seconds or HTTP dates). Each URL gets at most three attempts; failed URLs remain recorded for a later run. Rate increases, backoffs, and the current target rate are printed to the terminal. Large catalogues may take hours; rerunning reuses cached pages. Failed fetches are recorded and the UI labels incomplete imports. Stop/restart with Ctrl-C safely; pages already cached need no new download. Refresh the remote cache when needed:

```sh
uv run python importer.py --refresh
```

The importer follows robots.txt; network errors stop the import. If Luxart changes markup or returns dynamically rendered listings, discovery may fail explicitly. Do not interpret “import finished” as a guarantee that every shop product was published in its sitemap. Missing sizes remain visible without dimension filters and never match numeric filters. Sold/unavailable options are not yet distinguished; check the shop before purchasing.

Adjust concurrency and adaptive rate bounds if needed:

```sh
uv run python importer.py --workers 32 --start-rate 10 --max-rate 40
```

The rate is a target ceiling; actual throughput depends on response latency. Restart the importer to apply code or option changes; cached pages are reused. Recognized challenge pages are not cached. This is response-based backoff, not a guarantee against blocking.

After the import completes, rebuild orientation/category metadata using cached HTML and create a page that opens directly without a server:

```sh
uv run python local.py
open dist/index.html
```

The standalone page embeds the full catalogue, styles, and search logic. Artwork previews still load from Luxart; image files are not mirrored locally. Rebuild it after updating the catalogue. Sitemap entries resolving to listing pages are excluded and recorded in `excluded`.

## Search

- Independent min/max bounds for width and height (cm), inclusive, supporting decimals.
- Expand **Excluded authors** to hide multiple authors. Algis Kriščiūnas is excluded by default; uncheck him or use Include all authors to restore his works. Exclusions are retained in the URL, including an explicitly empty list. Clear restores the default.
- Title/artist search ignores accents; artist dropdown; width, height, area or title sorting.
- Filters are stored in the URL for bookmarks and sharing locally.
- Click a work to view its product page; prices from parsed option labels are shown when available.
- Automatic orientation compares available size ratios against the primary artwork image dimensions published in the HTML. It resolves width/height only when all non-square options agree, the best ratio differs by at most 15%, and it clearly beats the reverse order. This is an inference from image proportions, not a shop guarantee. Ambiguous works are excluded from numeric filters in automatic mode. Manual width × height, height × width, and either-order overrides remain available. Cards display normalized width × height in automatic mode and retain the original label on hover.
- The default Artworks collection excludes explicitly categorized accessories and gift vouchers. Unclassified products remain visible; a category filter offers finer control.
- Both bounds must match the same variant, never separate variants of the same painting.

## Verification

```sh
uv run python -m unittest discover -s tests
node --test tests/search.test.js
```

Tests cover extraction, orientation, inclusive variant ranges, adaptive throttling, cache behavior, and standalone packaging. The full import runs from the user’s terminal, with progress monitored through shared files. Browser visual QA is unavailable in this session; no connected browser tool is exposed. No public hosting or account is required.

## GitHub Pages

The `justasbr/luxart` repository publishes only `dist/` to https://justasbr.github.io/luxart/. The main homepage repository is not modified and no homepage link is added.

In repository **Settings → Pages**, choose **GitHub Actions** as the build source. The Deploy Luxart search workflow deploys when `dist/` changes on `main`, or when started manually from the Actions tab.

After changing the interface, rebuild the standalone snapshot without downloading or reprocessing products:

```sh
uv run python -c 'import json; from pathlib import Path; from local import bundle; Path("dist/index.html").write_text(bundle(json.loads(Path("data/catalog.json").read_text())))'
```

Commit and push the updated `dist/index.html` to publish it. Cached shop HTML, virtual environments, and SSH credentials are excluded from Git. The SSH key remains configured only in local Git configuration.
