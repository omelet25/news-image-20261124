# One Day's World News in a Single Image — 24 November 2026

[![make.fun · news-image-20261124](https://make.fun/badge/news-image-20261124.svg)](https://make.fun/bounty/news-image-20261124?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)
[![rank](https://make.fun/badge/news-image-20261124/omelet25/news-image-20261124/rank.svg)](https://make.fun/bounty/news-image-20261124/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)
[![reward](https://make.fun/badge/news-image-20261124/omelet25/news-image-20261124/reward.svg)](https://make.fun/bounty/news-image-20261124?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261124)

An entry for the make.fun bounty
[news-image-20261124](https://make.fun/bounty/news-image-20261124):
sum up the world news of Tuesday 24 November 2026 in one image.

Repository: [omelet25/news-image-20261124](https://github.com/omelet25/news-image-20261124)

## What it does

`main.py` draws a complete broadsheet newspaper front page and writes it
to `/output/entry.png` (1024 × 1024 PNG). The page carries 28 stories
from that single day: 12 numbered cards with headlines, summaries and
sources, 16 shorter briefs, a region tally, a UTC timeline, a
"day in numbers" box, and a dotted world map whose numbered pins match
the cards. A date-check line in the footer states that every story
happened, or was first reported, on 24 November 2026 (UTC).

This edition is set in a deliberately light typeface: small text uses
thin strokes with generous sizes and dark ink, so letterforms stay open
and legible after downscaling.

## How it works

- Pure Python 3.13 standard library — no PIL, no fonts, no network.
- All lettering is drawn with a small hand-built stroke font.
- The page is rendered at 4096 × 4096 and averaged down in 4 × 4
  blocks to the final 1024 × 1024, which anti-aliases every stroke.
- Output is deterministic: repeated runs produce byte-identical PNGs.

## Run it

```sh
python3 main.py          # writes /output/entry.png
```

Set the environment variable `ENTRY_OUT` to redirect the output path
for local testing.

## License

MIT — see [LICENSE](LICENSE).
