# Earthquake catalog evidence

| Claim | Inspect |
|---|---|
| Local M00 document checks and three controlled failures | [Make transcript](M00-docs.txt) |
| M01 runtime pins, local SQLite reopen, state-volume capacity and controlled failures | [Preflight and documentation checks](M01-preflight.txt) |
| Independent USGS catalog responses and offline integrity | [M02 transcript](M02-acquire.txt) and [frozen manifest](../../earthquake/fixtures/20261126T064859Z-1bf43bf1e07e/manifest.json) |
| Windows and Docker intake | [Machine output](quake-machine.txt) and [runtime versions](quake-runtime.txt) |
| A real daily USGS snapshot was captured | [Capture log](quake-capture.txt) and [raw snapshot](usgs/20261125T182355423124Z.geojson) |
| The selected event has two superseded-query origin versions reporting the same magnitude | [Query output](quake-detail.txt), [ordinary detail](usgs/detail.json) and [superseded response](usgs/superseded.json) |

D2 live agreement, frozen restart, reader observations, benchmarks and integrated offline verification are **NOT RUN**.
