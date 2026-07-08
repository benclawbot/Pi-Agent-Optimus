---
name: browser-fingerprint-scrapers
description: 'When a raw HTTP scraper gets bot-blocked (CAPTCHA / 0 results / challenge page) despite valid requests, the fix is not to retry harder or fake headers — it is to switch to a browser-fingerprinting client (curl-cffi, ddgs, rquest, undici-impersonate) that mimics a real browser''s TLS handshake. Trigger when: scrapes return 0 results with HTTP 200, OR you are adding a new web-scrape/search tool and need to pick a backend, OR a user reports "the network is blocked" but `curl` to the same URL works.'
---

# Browser-fingerprint scrapers: the actual fix for bot-blocked raw HTTP

The instinct when raw `requests` / `reqwest` / `httpx` gets 0 hits is to retry, rotate User-Agents, slow down, or set more headers. None of that works against modern bot detectors (Cloudflare, Akamai, DataDome, DDG's anomaly detector). They fingerprint the **TLS handshake** itself — cipher suites, extensions, ALPN, key share curves — and reject anything that doesn't match a real browser's signature.

The fix is not to lie better. The fix is to use a client that *actually speaks like a browser* at the TLS layer.

## The library ecosystem (by language)

| Language | Library | What it does |
|---|---|---|
| Python | [`ddgs`](https://pypi.org/project/ddgs/) | High-level DDG wrapper; uses curl-cffi internally. Best choice for DDG. |
| Python | [`curl-cffi`](https://pypi.org/project/curl-cffi/) | curl with browser TLS impersonation. Pick the browser version with `curl_cffi.requests.get(url, impersonate="chrome120")`. |
| Python | [`cloudscraper`](https://pypi.org/project/cloudscraper/) | Cloudflare-specific. Older approach. |
| Rust | [`rquest`](https://crates.io/crates/rquest) | reqwest fork with browser impersonation. Use `rquest::Client::builder().impersonate(Impersonate::Chrome120).build()`. |
| Rust | [`reqwest-impersonate`](https://crates.io/crates/reqwest-impersonate) | Older fork of the same idea. |
| Node | [`undici`](https://github.com/nodejs/undici) + `client.http2Session` tweaks | Possible but fragile. Use Python instead. |
| Any | **Pay for it.** Brave Search API (2000 free/month), Tavily (1000 free/month), SerpAPI, Exa. No scraping required. |

## Why this matters: live evidence

A custom Rust scraper using `reqwest` against `https://html.duckduckgo.com/html/`:
- HTTP 202, 14 KB body, 0 `result__a` elements
- Body contains `anomaly-modal` + "Unfortunately, bots use DuckDuckGo too"
- Looks like "0 results" but actually a bot challenge

The same query via `ddgs` (which uses `curl-cffi` with Chrome impersonation):
- HTTP 200, real result list
- 5 BBC / CNN / AP / Wikipedia URLs in ~5s

The difference is the TLS fingerprint. Same IP, same User-Agent string, same headers — only the handshake differs.

## How to wire it from a non-Python app

For a Rust/Tauri/Go app, the cleanest path is **subprocess** + JSON output:

```rust
// Pseudocode
let output = Command::new("ddgs")
    .args(["text", "-q", query, "-m", "5", "-o", "json"])
    .output()?;
let hits: Vec<Hit> = serde_json::from_slice(&output.stdout)?;
```

The CLI tool ships with the `ddgs` pip package. Install once with `pip install ddgs`, then point `PATH` or set an explicit binary path env var. No Python interpreter embedding, no pyo3 dependency, no FFI.

For a Python app, just `import ddgs; DDGS().text(query)` directly.

## When NOT to use this

- The site is fine with normal HTTP and you're just over-engineering. Test `curl` against the URL first; if it returns real results, raw HTTP is enough.
- You need to scrape at scale. Browser-fingerprint scrapers are 5-10x slower than raw HTTP and use more memory per request.
- The site has a free API. Always prefer the API. The fingerprint scraper is the second-best fallback, not the default.

## Detection vs bypass

This skill covers **bypass** (how to actually get the data). For **detection** (how to tell the bot challenge is happening vs. the site genuinely having 0 results), see the `scrape-bot-challenge` skill. The two compose: detect with markers, then bypass with the right library.