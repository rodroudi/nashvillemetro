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
No scheduled jobs are set up. Run these by hand when you want new data.

Independent project built from public records. Not an official Metro Nashville site.
