# Ezekiel — Signal Station

A small composite "crisis indicator" dashboard, in the spirit of Kyle
McDonald's [Apocalypse Early Warning System](https://ews.kylemcdonald.net/).
Instead of tracking private jets, it combines three free, no-API-key data
sources:

1. **SEC EDGAR** — daily count of Form 4 filings (insider stock transactions),
   compared to a 30-day baseline.
2. **Google Trends** — average interest in a basket of "panic" search terms
   (`bunker`, `gold storage`, `potassium iodide`, `evacuation route`).
3. **VIX** — the CBOE volatility index, via Yahoo Finance.
4. **E-4B "Nightwatch" fleet** — how many of the Air Force's 4 airborne
   nuclear command posts are currently airborne, via the free
   [adsb.lol](https://api.adsb.lol) public API. Unlike the other three, this
   one doesn't have a real historical baseline available for free, so it
   uses a hand-set rule instead of a proper z-score: 0–1 airborne is
   treated as routine (near-daily training flights happen), 2+ simultaneously
   airborne is scored as increasingly unusual.
5. **Polymarket odds** — the highest live probability across a watchlist of
   crisis-adjacent questions (nuclear war, US recession, a newly-declared
   pandemic, direct NATO-Russia conflict), via Polymarket's free public
   Gamma API. This is arguably the most directly on-topic signal of the
   five: it's real money betting on the literal events this dashboard is
   trying to anticipate. Same as the E-4B channel, there's no free
   historical odds series to compute a real z-score against, so it uses a
   hand-set rule on the raw probability instead (these questions normally
   price in the low single digits; double digits is the signal).
6. **Billionaire/oligarch yacht fleet** — how many of 11 tracked
   superyachts are currently clustered in known "safe haven" waters
   (sanctions-indifferent ports for the sanctioned owners; the
   "billionaire bunker" Pacific for the Western tech owners), via the free
   [aisstream.io](https://aisstream.io) WebSocket API. **Needs a free API
   key** — sign up at aisstream.io and set it as `AISSTREAM_API_KEY` (see
   below). Aggregate count only; no individual yacht/owner is named on the
   dashboard itself, deliberately, to keep this in the same spirit as
   Kyle's anonymous jet-count rather than singling out named people.

### Yacht watchlist sourcing

| Yacht | Owner | MMSI | Status |
|---|---|---|---|
| Koru | Jeff Bezos | 319225400 | active |
| Musashi | Larry Ellison | 319032600 | active |
| Symphony | Bernard Arnault | 319076700 | active |
| Venus | Laurene Powell Jobs | 319327000 | active |
| Launchpad | Mark Zuckerberg | 538072122 | active (has gone AIS-dark before) |
| Ocean Victory | Viktor Rashnikov | 319055400 | active, sanctioned owner |
| Dilbar | Alisher Usmanov | 319094900 | detained (Germany, since 2022) |
| Sailing Yacht A | Andrey Melnichenko | 667002036 | seized (Trieste, Italy, since 2022) |
| Nord | Alexei Mordashov | 273610820 | active, sanctioned, re-flagged since 2022 |
| Eclipse | Roman Abramovich | 518999664 | active, sanctioned, re-flagged since 2022 |
| Solaris | Roman Abramovich | 518999189 | active, sanctioned, re-flagged since 2022 |

Sourced from Wikipedia infoboxes cross-checked against VesselFinder/
vesseltracker.com, mid-2026. **The three re-flagged entries (Nord, Eclipse,
Solaris) are the least stable** — sanctioned owners' yachts get
re-registered under new flags (and therefore new MMSIs) periodically to
complicate tracking, so re-verify these every few months rather than
trusting them indefinitely. Two more from the original candidate list
were skipped rather than guessed: **Ulysses** (Graeme Hart) because the
name has been recycled across two different yachts he's owned (the old
one was sold and renamed *Andromeda* in 2018, and the current one is new
enough that I couldn't confirm its MMSI), and three others (Dragonfly,
Drizzle, Ice) weren't looked up at all — add them the same way (search
`"<name>" yacht wikipedia` for the Wikipedia infobox, or `"<name>" IMO MMSI
vesselfinder`) if you want a bigger fleet.

**Setting up the AISStream API key:** sign up free at
[aisstream.io](https://aisstream.io), grab the API key, and add it as a
GitHub secret named `AISSTREAM_API_KEY` (same Settings → Secrets and
variables → Actions page) if running this via GitHub Actions, or export it
as an environment variable if running `_dev/scripts/fetch_data.py` locally.
Without it, this channel is skipped (shows "unavailable") but the other
five still run fine.

Each channel gets a z-score against its own recent history; the three are
averaged into a 1–5 "alert level" shown on the dashboard.

This is a rough signal, not a forecast. Treat it the way McDonald treats his
own project: a lens on nervousness, not a doomsday clock.

## Language

The page detects the browser's language (`navigator.languages`) on load: if
it starts with `ru`, the UI and labels render in Russian; otherwise it stays
in English. This is a static, no-build front-end translation — the
dictionary lives in `script.js` (`STRINGS.en` / `STRINGS.ru`), and every
static piece of text on the page is tagged with a `data-i18n` attribute in
`index.html` so it's picked up automatically.

Two things stay in English regardless of browser language, since they're
external data rather than page copy: the specific Polymarket question text
(pulled live from Polymarket, arbitrary and not ours to translate) and any
`baseline_mean` string from `data/dashboard.json` that isn't already in the
small `DATA_STRING_TRANSLATIONS` map in `script.js`. If you add new channels
or change existing baseline strings, add their translations there too, or
they'll silently fall back to English.

## Folder layout — this mirrors what goes on the live site

```
index.html            \
style.css              >  upload these four straight into the
script.js              >  "ezekiel" folder on alexgebhardt.de
data/dashboard.json   /

_dev/                  not part of the site — dev tooling only, don't upload
  scripts/fetch_data.py
  requirements.txt
  README.md (this file)
.github/workflows/update.yml   only relevant if you push this to GitHub
```

Everything **outside** `_dev/` and `.github/` is the whole site. Upload
`index.html`, `style.css`, `script.js`, and `data/` as-is into your `ezekiel`
folder once and it works immediately at `https://alexgebhardt.de/ezekiel/`.
After that first upload, `data/dashboard.json` specifically gets kept fresh
automatically (see below) — you won't need to touch it again by hand.

## Keeping the data fresh — fully automatic, no PC required

This runs entirely on GitHub's own servers, on a schedule, whether your
computer is on or not. Once set up, you never touch it again:

1. **Push this whole folder to a GitHub repository** (a free GitHub account
   is all you need — this doesn't use your computer to run anything, just
   to upload the files once).

2. **Add 5 secrets** in that repo: Settings → Secrets and variables →
   Actions → New repository secret. Add each of these:
   - `FTP_SERVER` — your host's FTP address
   - `FTP_USERNAME`
   - `FTP_PASSWORD`
   - `FTP_DATA_DIR` — the remote path to the `data` folder specifically,
     e.g. `/ezekiel/data/` (this workflow only ever touches this one
     folder — it never re-uploads `index.html`/`style.css`/`script.js`,
     so there's no risk of it overwriting anything else on your site)
   - `AISSTREAM_API_KEY` — free key from aisstream.io (see below)

3. **Run it once manually** to confirm it works: Actions tab → "Update
   signal data" → Run workflow. Check the logs for each channel.

From then on, `.github/workflows/update.yml` runs on GitHub's servers every
6 hours, on its own: fetches fresh numbers, commits `data/dashboard.json`
back into the repo, and FTPs that one file straight to your live site. Your
computer is never involved in any of it — it only mattered for the
one-time step of pushing the code to GitHub in the first place.

If you'd rather not use GitHub Actions at all, `_dev/scripts/fetch_data.py`
also works run locally (`python3 _dev/scripts/fetch_data.py`) and you upload
the resulting `data/dashboard.json` yourself — but that's the manual
fallback, not the recommended path.

## Known fragility (read before you trust the numbers)

- **pytrends is unofficial.** It scrapes Google Trends rather than using a
  documented API, and Google changes the page layout occasionally. If it
  breaks, `google_trends` will just show "unavailable" on the dashboard
  rather than crashing the whole run.
- **SEC asks for a real contact** in the User-Agent header for automated
  requests — edit `SEC_USER_AGENT` in `_dev/scripts/fetch_data.py` to include
  your real email before running this regularly.
- **yfinance** is also an unofficial wrapper around Yahoo's endpoints, same
  caveat.
- The 1–5 thresholds in `combine_signals()` are a first guess, not calibrated
  against real history. Once you've got a few weeks of real data in
  `history`, it's worth revisiting them.
- I wasn't able to test the live SEC/Trends/VIX calls from my own sandboxed
  environment — no outbound access to sec.gov, finance.yahoo.com, or
  trends.google.com there. The logic is written and the JSON shape is
  verified against sample data, but give it a real run early to catch any
  API quirks.

## Known fragility for the E-4B channel specifically

- `adsb.lol`'s public API is free and requires no signup, but per its own
  docs it's newer than their feeder-only API and "subject to change" —
  it may eventually need an API key or add rate limits. If it stops
  responding, swap the `ADSB_API_BASE` in `_dev/scripts/fetch_data.py` for
  `https://opendata.adsb.fi/api/v2/hex` instead (same response shape,
  same free/public terms, asks that you credit adsb.fi if you use it).
- The 0-1-airborne "normal" assumption is a reasonable guess from public
  reporting on this fleet, not a calibrated baseline — worth revisiting
  once you've watched it for a few months.

## Known fragility for the Polymarket channel specifically

- I could not verify the exact response shape of Gamma's `/public-search`
  endpoint from inside this sandbox (no outbound access to polymarket.com
  here) — `_best_market_for_keyword()` in `_dev/scripts/fetch_data.py` guesses
  at a reasonable shape (a top-level `markets` list, or `markets` nested
  inside `events`) and is defensive about it, but treat this as the first
  thing to check if the channel comes back "unavailable." Print/log the raw
  response once and adjust the parsing to match.
- Gamma requires a real `User-Agent` header or it intermittently blocks
  requests — already set in the script, but worth knowing if it starts
  failing silently.
- `outcomePrices` and `outcomes` come back as JSON-encoded *strings*, not
  arrays — already handled, but a common source of bugs if you extend this.
- The keyword search takes whichever open market currently has the highest
  volume for that theme — as new markets get created for later years, the
  matched question will naturally roll forward, but check occasionally that
  it's still matching something sensible.

## Known fragility for the yacht channel specifically

- Needs `AISSTREAM_API_KEY` (see above) or it's skipped entirely.
- I couldn't test the actual WebSocket message format from this sandbox
  (no outbound access to aisstream.io here) — `_collect_yacht_positions()`
  in `_dev/scripts/fetch_data.py` follows aisstream's documented
  `PositionReport` message shape, but verify against a real run.
- The 45-second listen window (`AISSTREAM_LISTEN_SECONDS`) means the
  script may not hear from every tracked yacht every run - AIS reports
  land whenever that specific vessel happens to transmit, not on a fixed
  schedule. A yacht docked with a weak signal, or one that's gone
  AIS-dark on purpose (Zuckerberg's Launchpad has done this before), may
  simply be absent from a given run rather than "not in a safe haven."
  `positions_received` in the signal's data tells you how many of the 11
  were actually heard from.
- The safe-haven bounding boxes in `SAFE_HAVEN_REGIONS` are deliberately
  rough approximations, not precise port boundaries - a yacht just outside
  a box (or one moored in a safe-haven-adjacent spot the boxes don't cover,
  like Dubai marina itself vs. open Gulf waters) won't register. Widen or
  add regions as you watch real data come in.

## Next steps to consider

- Tune the keyword basket and baseline windows once you see real noise
  levels.
- Add the RSS/email alert pattern Kyle's own project uses, for level 4–5 only.
