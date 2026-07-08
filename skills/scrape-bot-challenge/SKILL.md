---
name: scrape-bot-challenge
description: 'Web-scraping gotcha. A 0-result page with HTTP 200/202 is not a successful empty query — it is almost certainly a bot-challenge CAPTCHA page (DuckDuckGo "anomaly-modal", Cloudflare "Just a moment...", etc.). Trigger when: a scrape returns zero hits but the HTTP status is success, OR a user reports "the search returns nothing" / "fetched but empty" / "the network is blocked" (usually the network is fine — the backend is serving a challenge), OR you are about to add a `webSearch`/`fetchUrl`/`scrape` tool and need a sanity-check parser.'
---

# Zero-hit pages are usually bot challenges, not empty results

When a web scrape returns zero hits with a success status, the most likely cause is the backend serving a bot-detection challenge page. The page is HTTP 200/202, the HTML parses cleanly, and the result list is just empty. The caller has no way to tell this apart from "the query genuinely matched nothing".

Symptoms:
- HTTP status is 2xx
- Response body is a normal HTML document (not a connection error, not a network timeout)
- Regex/CSS selectors for result items return zero matches
- But the body contains markers like `anomaly-modal`, `challenge-form`, "Just a moment...", "cf-challenge", "verify you are human", "select all squares", or an `iframe` pointing at `/challenge` or `/anomaly.js`

## Diagnostic recipe

1. **Capture the raw body** to a file and `wc -c` it. A real search page for a common query is usually 50-200 KB. A challenge page is usually 10-30 KB of inline JS + a modal.
2. **Grep for challenge markers** in the body. The exact markers differ per backend, but these are stable across years:
   - DuckDuckGo: `anomaly-modal`, `challenge-form`, "Unfortunately, bots use DuckDuckGo too"
   - Cloudflare: `cf-challenge-running`, `cf_chl_opt`, "Checking your browser before accessing"
   - Generic: `g-recaptcha`, `h-captcha`, "Please complete the following challenge"
3. **Check the URL bar / response URL** — challenges often come from `/anomaly.js?sv=...&cc=...` paths or a redirect chain ending on a `/cdn-cgi/challenge` URL.

## Fix pattern in the scraper

```rust
const CHALLENGE_MARKERS: &[&str] = &[
    "anomaly-modal",
    "challenge-form",
    "cf-challenge",
    "cf_chl_opt",
    "g-recaptcha",
    "h-captcha",
    "Please complete the following challenge",
    "Unfortunately, bots use",
    "Just a moment",
];

fn check_challenge(body: &str) -> Result<(), String> {
    if CHALLENGE_MARKERS.iter().any(|m| body.contains(m)) {
        return Err(format!(
            "Backend is serving a bot-challenge page (markers: {}). \
             Configure an alternate provider or use an API key.",
            CHALLENGE_MARKERS.iter().find(|m| body.contains(*m)).unwrap()
        ));
    }
    Ok(())
}
```

Call `check_challenge` **before** parsing, **after** the status check. The error message should name the marker that fired and tell the user what to do (set an API key env var, switch providers, etc.).

## Why this matters

Without the check, the tool returns "0 hits" — looks like a successful empty query. The model has no way to tell the backend is actually broken and will keep retrying with rephrased queries, burning turns. With the check, the tool returns a typed error and the model can either retry with a different strategy or surface a clear "search backend is blocked" to the user.

## Don't try to solve the CAPTCHA

Solving CAPTCHAs is a losing game. Detection + clear error + provider-switch path is the correct response. If the user needs to actually scrape a site that challenges every request, they need a paid API key (Brave, Tavily, SerpAPI) or a self-hosted proxy (SearXNG, ScraperAPI).