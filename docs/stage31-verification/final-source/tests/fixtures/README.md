# Test fixtures

Every file here is **real bronze**, copied or trimmed from `data/raw/`. None of
the values were written by hand.

That is the whole point. A fixture an author invented tests the author's idea of
what an API returns; a fixture cut from the archive tests what it actually
returned, including the shapes nobody would have thought to invent — a price of
`"0"` on a delisted game, a Twitch category with no `igdb_id`, a Store response
describing a different appid than the one requested.

**Rule: never hand-edit a value in these files.** If a fixture needs to cover a
new case, cut a new one from `data/raw/`, or record the case as unreachable (see
`transport_error` below). Trimming — dropping records, and correcting a count
field so the file stays internally consistent — is allowed and is noted per file.

| file | source | what it is here for |
|---|---|---|
| `steamspy_all_page.json` | `steamspy/all/2026-05-09/`, pages 0 and 1 | 7 records **verbatim**, assembled into one page-shaped file. Five report `price: "0"`: `730` is genuinely free-to-play, while `271590` (GTA V Legacy), `252950` (Rocket League), `813820` (Realm Royale) and `9450` (Dawn of War) are delisted and the Store confirms `is_free = false`. Those four are the trap that produced 6 100 fabricated `is_free` values, in the source's own words. Two priced records cover the other branch. |
| `steamspy_revision_before.json` / `steamspy_revision_after.json` | `steamspy/all/2026-05-09/page_0` and `2026-05-11/page_0` | The same five games, observed two days apart, caught as a sale ended — `price` and `discount` both move (Stellaris 999→3999, discount 75→0, and four others). Loading both under one `snapshot_date` is what exercises the update path; every other loader test replays a byte-identical file, which any conflict policy survives. Worth knowing while reading these: only **69 of 2 000** common appids changed at all across those two days. |
| `twitch_streams.json` | `twitch/streams/2026-05-10/streams_20260510_131724.json` | first 25 streams of a real sample; `stream_count` corrected to 25 so the file stays consistent. `fetched_at` preserved — it is the input to `sample_time`, and losing it is what forced `sample_time_source`. |
| `twitch_games_lookup.json` | `twitch/games_lookup/2026-05-11/`, files `…_160637` and `…_161047` | 12 categories, records verbatim, assembled into one response-shaped file because no single response held both cases. Six carry **no** `igdb_id`: four are genuinely not games (Just Chatting's neighbours — IRL, Sports, Always On, Food & Drink), and two are Dota 2 and Counter-Strike, Steam's largest titles in the sample. Both kinds must survive a load; deciding a category is not a game is a later, explicit step. |
| `steam_store_ok.json` | `steam_store/appdetails/2026-08-12/730_…` | envelope, `outcome: ok`. |
| `steam_store_refused.json` | `steam_store/appdetails/2026-08-12/280_…` | envelope, `outcome: refused` — Steam answered `success: false`. |
| `steam_store_redirected.json` | `steam_store/appdetails/2026-08-12/100_…104221` | envelope, `outcome: redirected`, `redirect_to: 80`. Note the archive also holds *earlier* files for appid 100 recorded as `ok`: they predate redirect detection. The later file is the correct fixture; the earlier ones are what the defect looked like. |
| `steam_store_legacy_no_envelope.json` | `steam_store/appdetails/2026-05-09/730_…` | a bare body with no envelope — the shape of the 3 148 files written before the envelope existed. The loader must keep reading these, so they are tested, not migrated. |
| `igdb_games_search.json` | `igdb/games_search/2026-05-10/bunny_garden_2_…` | a small real IGDB search response. |
| `igdb_games_search_steam_uid_shapes.json` | `igdb/games_search/2026-05-11/anno_2070_20260511_125026.json`, plus one record spliced from `igdb/games_search/2026-05-10/apex_legends_20260510_183631.json` | 3 of the Anno file's 6 records, verbatim (`8228` Anno 2070: Deep Ocean, `2959` Anno 2070, `362774` Anno 2070 DLC Complete Pack), plus 1 of the Apex file's 10 records, verbatim (`114795` Apex Legends), assembled into one file because no single archive response held every uid shape migration 016 needs. `result_count` corrected to 4 to match. `8228` gives a single numeric steam uid (`204290`); `362774` gives a comma-separated bundle uid (`204281,204282,...,204289` — nine appids in one IGDB `external_games` entry; game_type read from raw_json, not the unbackfilled game_type_label, is 3 = bundle for this row — see migration 016's comment for the full 16-row measurement, which is why detection is by uid shape, not by game_type); `2959` gives a non-steam, non-numeric Epic uid (`afded2bee4b4421981e30547bfe30636`) alongside its own single-appid steam uid (`48240`); `114795` gives a non-steam uid that *is* purely numeric — PlayStation, `232352` — the shape needed to catch a `store = 'steam'` guard dropped from the `steam_appid` expression alone, which every other non-steam uid here (GUID or SKU) cannot catch. The three dropped Anno records (`180263`, `180261`, `52401`) carry no `external_games` at all and add nothing this fixture needs. |

**No `transport_error` fixture exists, deliberately.** The archive contains none,
because no request ever failed that way during collection — and inventing one
would mean writing by hand exactly the shape whose honesty is being tested. That
path is covered instead by driving the extractor with a simulated network
failure: the mock is of the network, never of the database.
