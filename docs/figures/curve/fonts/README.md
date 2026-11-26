# Fonts for the CURVE wall PDF

The two typefaces of the Ballet Seasons by City artifact and its sister explorers: **Playfair Display** (headings, figures)
and **Raleway** (text). Both SIL Open Font License 1.1 (`OFL_*.txt`). Downloaded 2026-11-25 from Google Fonts' repository,
`github.com/google/fonts/ofl/{raleway,playfairdisplay}` (variable fonts, `*[wght].ttf`).

PyMuPDF embeds only a variable font's default instance, so `static/` holds fixed-weight instances, made with fontTools 4.55.0:

    uvx --from fonttools==4.55.0 fonttools varLib.instancer "Raleway[wght].ttf" wght=600 -o static/Raleway-SemiBold.ttf --update-name-table

(likewise Raleway 400 / 700 / Italic 400, Playfair Display 400 / Italic 400).

`static/PlayfairDisplay-Regular-LiningFigures.ttf` is Playfair Regular with 0-9 remapped to its lining figures (`zero.lf` ...),
standing in for the artifact's `font-variant-numeric: lining-nums` on big figures, since PyMuPDF cannot turn on OpenType
features. Both families default to old-style figures otherwise.

Coverage: every character on page 1 is in every file. Playfair Display has no ѳ (U+0473); Raleway has it. Ballet titles are
set in Raleway, so this only matters if Playfair is ever used for a title containing ѳ.
