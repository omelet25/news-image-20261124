# Sum up 24 November's world news in one image

[![make.fun rank](https://make.fun/api/badges/repos/omelet25/news-image-20261124/rank.svg)](https://make.fun/bounty/news-image-20261124)
[![make.fun reward](https://make.fun/api/badges/repos/omelet25/news-image-20261124/reward.svg)](https://make.fun/bounty/news-image-20261124)

Entry for the make.fun bounty
[news-image-20261124](https://make.fun/bounty/news-image-20261124):
a program that writes one image summing up the world's news of
Tuesday 24 November 2026.

## What it does

`main.py` (Python 3.13, standard library only — no PIL, no fonts, no
network) draws a one-page broadsheet front page and writes it to
`/output/entry.png`:

- a masthead with the date, a red kicker and region count chips
- 12 numbered story cards with place, category, status tag
  (ON RECORD / REPORTED / CLAIM), headline, summary and source
- a UTC hour-by-hour timeline band
- a dotted world map with numbered pins matching the cards
- a "THE DAY IN NUMBERS" box and 16 further stories in brief
- a footer DATE CHECK confirming every story is from 24 November 2026 (UTC)

The page is rendered internally at 4096×4096 with a hand-built stroke
font and downscaled to 1024×1024 by 4×4 area averaging. The program is
fully deterministic: two runs produce byte-identical output, and the
PNG stays well under the 1 MiB limit.

## Run

```sh
python3 main.py          # writes /output/entry.png
```

## License

MIT — see `LICENSE`.
