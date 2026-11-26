# Defending the earthquake catalog design

| Decision | Explain in an interview | Hard follow-up and reconsideration trigger |
|---|---|---|
| [Integrated scope](adr/0001-catalog-structure.md) | The same interrupted backfill gives an analyst a reference comparison and an operator old and new publication IDs. | Can a reviewer do this offline in one run? Revisit scope if the review exceeds the time budget. |
| [Independent acquisition](adr/0002-catalog-acquisition.md) | Freeze two query paths, compare duplicate counts before deduplication, and keep the live and restart verdicts separate. | What if USGS revises an event between queries? Preserve both bodies and withhold publication. Shrink the period if the whole-window reference exceeds the service limit. |
| [Transactional publication](adr/0003-catalog-storage.md) | Commit rows with their checkpoint. Each reader must digest the rows it actually receives and match its named generation. | Can the old ID still be read after recovery? Reconsider SQLite if multiple writers or measured reader stalls invalidate the design. |

**How do you know the older ID still works?** In M05 a fresh CLI process retrieved the earlier ID after the pointer advanced. The drill compared each returned row to the whole-week reference filtered to 1–3 October and recomputed the same digest observed before the switch. Returning the latest rows for both IDs would fail on count and membership. The larger count reflects four additional days of coverage. Concurrent reads during a publisher kill remain **NOT RUN**. [History drill](evidence/M05-history.txt)
