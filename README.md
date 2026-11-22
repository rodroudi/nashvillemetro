# Metro Nashville Council: districts and roll-call votes

A static, no-login web page that maps Metro Nashville's 35 council districts and shows how every council member voted on each item with a recorded roll-call vote this term (since September 2023).

How to use it: tap any district on the map (or a member card) to open that member's profile with photo, contact info, newsletter, attendance, and their full vote record with search and filters. Pick any vote in the "Every recorded vote" list to recolor the map by how each district member voted.

## Data
- Votes come from the public Legistar API, `https://webapi.legistar.com/v1/nashville`: `/events`, `/events/{id}/eventitems`, and `/eventitems/{id}/votes`.
- District boundaries and district member contacts come from the Metro GIS Council Districts layer: `https://maps.nashville.gov/arcgis/rest/services/Elections/PoliticalDistricts/MapServer/0`.
- Newsletter links and committee roles were checked by hand (`scripts/members_seed.py`).
- Voice votes have no individual record, so they are not included. The page shows how members voted, not why.

## Refresh
```
python3 scripts/refresh_data.py        # votes, about 30 minutes
python3 scripts/refresh_attendance.py  # opening roll calls
python3 scripts/build_data.py        # builds data/votes.json and data/members.json
```
To refresh the map boundaries:
```
curl -s "https://maps.nashville.gov/arcgis/rest/services/Elections/PoliticalDistricts/MapServer/0/query?where=1%3D1&outFields=*&f=geojson&outSR=4326&maxAllowableOffset=0.0008&geometryPrecision=5" -o data/districts.geojson
```
No scheduled job refreshes the votes. Run these by hand when you want new votes.

The Dolly Servitude score is separate. `python3 scripts/compute_score.py` rebuilds `data/scores.json` from the files already in the repo. A GitHub Action runs that every Monday at 12:00 UTC (`.github/workflows/dolly-servitude-score.yml`). It does not download new votes or posts.

## Dolly Servitude score

The score is a 0–100 index for the 40 council members and the Vice Mayor. It is meant to reflect two things: decency (tone and civility in public posts) and service (showing up, voting, updating constituents, posting, community meetings, answering questions). It is not an official Metro grade, and it does not reward voting with the majority.

The method page is `/score` (`score/index.html`). The number on each member card links to it. Weights, the word list, and the changelog live in `data/score_config.json`. `scripts/compute_score.py` is the only place that does the math. `python3 scripts/test_score.py` checks the math against the published files.

### What is scored today

| Component | Weight | In the number now? |
| --- | --- | --- |
| Council meeting attendance | 30 | Yes, from `data/members.json` |
| Vote presence (not marked absent) | 20 | Yes, from `data/votes.json` |
| Constituent newsletter | 10 | Yes, as a yes/no from the hand-checked link. The county-wide GovDelivery form scores 0. |
| Online engagement | 15 | Only when `data/tweets/<slug>.json` has `"fetchStatus": "ok"` |
| Decency (tone) | 10 | Same file, and only with at least 5 of the member's own posts in the window |
| Community meetings | 10 | No file yet, so left out for everyone |
| Constituent replies | 5 | No file yet, so left out for everyone |

If a component has no data, it is left out and the other weights are scaled to 0–100. The card shows that coverage. A real zero (no newsletter on file, or a complete post file with no posts) is data and scores 0. A missing file is not a zero.

Optional files that turn the pending components on, one per member:

`data/newsletters/<slug>.json` replaces the yes/no newsletter score:

```json
{
  "asOf": "2026-11-22",
  "issues": [{"date": "2026-10-01", "title": "October note", "url": "https://example.com/issue"}]
}
```

`data/community_meetings/<slug>.json`:

```json
{
  "asOf": "2026-11-22",
  "meetings": [{"date": "2026-10-04", "title": "District meeting", "attended": true, "url": "https://example.com/event"}]
}
```

`data/constituent_replies/<slug>.json`:

```json
{
  "asOf": "2026-11-22",
  "replies": [{"date": "2026-10-05", "channel": "email", "url": null}]
}
```

A file that exists and has an empty list scores 0. No file means the component is left out.

### X posts

One file per member: `data/tweets/<slug>.json`. The slug is the member's name in lowercase, with accents dropped and spaces as hyphens (`terry-vo`, `kyonzte-toombs`). `scripts/compute_score.py` also writes `data/tweets/index.json` so the page can load every file in one request. Edit the per-member file, then rerun the script. Do not hand-edit the index.

`scripts/build_tweet_files.py` writes a missing file from the handle check. It will not overwrite a file unless you pass `--force`.

```json
{
  "pid": 209,
  "slug": "sean-parker",
  "name": "Sean Parker",
  "handle": "SeanForFive",
  "profileUrl": "https://x.com/SeanForFive",
  "profileName": "Sean Parker is FOR Transit",
  "protected": false,
  "bio": "Short quote from the public profile.",
  "handleSource": {
    "title": "Where the handle was found",
    "url": "https://seanforfive.com/",
    "checked": "2026-11-22",
    "note": "Why this account is the member's."
  },
  "handleCheck": {"checked": "2026-11-22", "result": "verified"},
  "fetchedAt": "2026-11-22T18:40:00Z",
  "fetchStatus": "ok",
  "fetchNote": "What this pull covers.",
  "truncated": false,
  "posts": [
    {
      "id": "2124211124061045000",
      "url": "https://x.com/SeanForFive/status/2124211124061045000",
      "text": "Post text, plain, not HTML.",
      "createdAt": "2026-11-21T18:39:32.000Z",
      "replyCount": 24,
      "repostCount": null,
      "likeCount": 16,
      "quoteCount": null,
      "isReply": true,
      "isRetweet": false,
      "lang": "en"
    }
  ]
}
```

`fetchStatus` is one of:

- `ok` — the posts array covers the lookback window (the last 90 days, ending on the day the score is computed). Set this only when the oldest post in the file is older than the window, or the account's whole history is in the file (including an account with zero posts).
- `partial` — some verified posts are in the file for display, but it is not a full window. Shown on the card. Not scored.
- `pending` — handle is known, posts are not loaded yet.
- `no_handle` — no verified account. `handle` is null.
- `protected` — the account exists and posts cannot be read. Left out of the score, not scored as zero.
- `error` — the last pull failed. Left out.

`truncated: true` means the pull stopped inside the window. Engagement is left out unless the posts already on file reach full credit (8). Tone can still be scored once there are 5 of the member's own posts.

`replyCount`, `repostCount`, `likeCount`, and `quoteCount` are numbers, or null when the source did not provide that count. Do not write 0 for "unknown."

Handles on file were checked 2026-11-22 against a campaign site, a newsletter archive, Ballotpedia, or a profile bio that names the seat. Accounts that did not resolve are stored with `handle: null` and a note. They are not guessed.

Independent project built from public records. Not an official Metro Nashville site.
