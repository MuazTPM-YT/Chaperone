# Deck style

Measured from slides 2 to 5 of `/home/Muaz/Downloads/DevHack-fixed-shots.pptx` on 2026-10-17 (shape positions and
run properties read from the slide XML). Slides 6 to 8 use these values. EMU: 914,400 per inch, 12,700 per point.

## Page and grid

| Item | Value | Where measured |
|---|---|---|
| Slide size | 13.333 x 7.5 in (12,192,000 x 6,858,000 EMU) | `presentation.xml` |
| Content left edge | 0.555 in (507,491 EMU) | intro box, slides 2 and 3 |
| Content right edge | 12.885 in (11,782,043 EMU), so a 0.45 in right margin | intro box, slides 2 and 3; slide 4 table ends at 11,777,471 |
| Content width | 12.33 in (11,274,552 EMU) | same |
| Text inside a column starts | 0.08 in in from the column edge (577,974 EMU) | slide 2 headings |
| Two-column split | left column 0.555 to 6.2 in, right column from 6.73 in | slide 2 (6,155,361), slide 3 (6,108,192) |
| Bottom of content | about 7.08 in (6,480,000 EMU) | slide 2 tagline, slide 3 last caption |
| Header (slides 6 to 8 only) | template logos, title left-aligned at 0.466 in, 36 pt Times New Roman, black | slides 6 to 8 `TextBox 3`, unchanged |

## Type

All text is **Times New Roman**, left-aligned. (Slides 2 to 4 justify some body text; slides 6 to 8 never do.)

| Role | Size | Weight | Colour | Where measured |
|---|---|---|---|---|
| Intro box text | 14 pt | regular, 1 to 2 words bold | ink `#1F2328` | slides 2 to 4 |
| Section heading | 16 pt | bold | ink `#1F2328` | "Why existing safeguards fall short", "What makes it different" |
| Lead line | 13 to 14 pt | bold | ink `#1F2328` | slide 2 (14), slide 3 (13) |
| Body | 11.5 to 13 pt | regular | grey `#5B6169` | slide 2 (13), slide 3 (11.5), slide 4 cards (11) |
| Caption | 11 pt | italic | grey `#5B6169` | slide 3 captions, slide 4 labels |
| Card label (caps) | 11 pt | bold | red `#A8322A` or amber `#8A5A00` | slide 2 cards |
| Tagline | 14 to 15 pt | bold | green `#1E6B47` | slide 2 |

**Body grey on slides 6 to 8 is `#43484F`, not `#5B6169`.** The brief asks for body text at least as dark as
`#4A4A4A`; `#5B6169` is lighter than that. `#43484F` keeps the same blue-grey hue and is darker than `#4A4A4A`.
Captions and footnotes keep `#5B6169`.

## Colour

| Name | Hex | Use |
|---|---|---|
| Ink | `#1F2328` | headings, leads, intro text |
| Grey | `#5B6169` | captions, notes (body on slides 2 to 4) |
| Body grey, slides 6 to 8 | `#43484F` | body text |
| Green | `#1E6B47` | number circles, tile numbers, "Built" pills, links, taglines |
| Mint | `#E9F3ED` | cards (slide 3 tiles, slide 4 step cards) |
| Intro grey | theme `bg1` at 95% (about `#F2F2F2`) | intro box |
| Red card / label | `#FBECEA` / `#A8322A` | slide 2 risk cards |
| Amber card / label | `#FFF4D6` / `#8A5A00` | slide 2 destination card, slide 4 step 5 |

## Shapes

| Element | Value | Where measured |
|---|---|---|
| Card | rounded rectangle, corner adjust 8,000 (about 0.08 of the short side), no outline | slide 2 cards, slide 4 step cards |
| Small tile | rounded rectangle, corner adjust 16,667 | slide 3 "five questions" tiles |
| Number circle | 0.26 in (237,744 EMU), green, white 12 pt bold number | slides 3 and 4 (slide 2 uses 0.30 in) |
| Intro box | plain rectangle, 0.3 in left inset, text centred vertically | slides 2 to 4 |
| Pill (slides 6 to 8) | rounded rectangle, corner adjust 50,000, 0.52 x 0.20 in, 10 pt bold. Built: green fill, white text. Next: white fill, grey `#5B6169` text | new on slide 7, one design everywhere |

## Spacing

| Item | Value | Where measured |
|---|---|---|
| Item pitch, lead plus 2 body lines | 0.69 to 0.88 in | slide 3 (0.69), slide 2 (0.81 to 0.88) |
| Lead to body gap | 0.02 to 0.04 in | slides 2 and 3 |
| Gap between cards in a row | 0.38 in | slide 4 step cards |
| Gap between stacked cards | 0.10 in | slide 2 cards |
| Space between stacked items on slides 6 to 8 | at least 0.12 in (about 9 pt) | the brief |
