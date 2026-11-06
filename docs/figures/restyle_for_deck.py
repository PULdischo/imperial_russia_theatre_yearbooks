"""Make deck-styled copies of the slide diagrams, matching
"2026 CDH Fellowship/2026_DissertationWorkInProgress_Presentation.pptx": dark green background (theme bg2 = 2C3932),
beige text (lt1 DFD2C4), Playfair headings, Raleway body, accents steel 8296AA / tan D2BD9A / sage C5D2CB.

Reads docs/figures/<name>.svg (the light originals, left unchanged) and writes docs/figures/deck/<name>.svg.
Run make_ballet_slides.py first if the ballet data changed.

usage: uv run python docs/figures/restyle_for_deck.py
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'deck'
NAMES = ['yearbook_to_database', 'raw_to_research', 'ballet_sleeping_beauty', 'ballet_don_quixote', 'ballet_magic_mirror']

BG, PANEL, PANEL2, RULE = '#2C3932', '#36463D', '#3F4F45', '#6F7D73'
TEXT, MUTED, FAINT = '#DFD2C4', '#BDB2A5', '#9C9488'
STEEL, STEEL_F, STEEL_T = '#8296AA', '#2F3F4C', '#AFC0D1'      # was blue   (St Petersburg, Works, research layer)
TAN, TAN_F, TAN_T = '#D2BD9A', '#4A4537', '#DCCAA8'            # was orange (Moscow, People)
SAGE, SAGE_F, SAGE_T = '#C5D2CB', '#3B4A42', '#D3DED8'          # was green  (Events)
ROSE, ROSE_F, ROSE_T = '#C49A98', '#4A3A3B', '#D4B0AE'          # was purple (Theatres, "both cities")

COLORS = {
    '#ffffff': BG,
    '#1f2328': TEXT, '#5b6470': MUTED, '#8a929c': FAINT, '#9aa1aa': FAINT,
    '#f4f1ea': PANEL, '#b9ae96': RULE, '#d9d3c5': RULE, '#6b5d3f': TAN_T,
    '#faf8f4': PANEL, '#e2ddd1': RULE, '#f6f7f9': PANEL2, '#c3c8cf': RULE,
    '#2f6db5': STEEL, '#e9f0f9': STEEL_F, '#1f4f8a': STEEL_T, '#2f5d94': STEEL_T,
    '#c0623b': TAN, '#b5562f': TAN, '#fbeee8': TAN_F, '#8f3f1f': TAN_T,
    '#2e8a57': SAGE, '#e8f4ed': SAGE_F, '#1d6640': SAGE_T,
    '#7a4fa3': ROSE, '#6b5d9a': ROSE, '#f1ebf7': ROSE_F, '#593680': ROSE_T,
}
BODY = "'Raleway', 'Helvetica Neue', Helvetica, Arial, sans-serif"
HEAD = "Playfair, 'Playfair Display', Georgia, 'Times New Roman', serif"


def restyle(svg: str) -> str:
    svg = re.sub(r'#[0-9a-fA-F]{6}\b', lambda m: COLORS.get(m.group(0).lower(), m.group(0)), svg)
    svg = re.sub(r'font-family="[^"]*"', f'font-family="{BODY}"', svg, count=1)
    svg = svg.replace("font-family=\"'Helvetica Neue', Helvetica, Arial, sans-serif\"", f'font-family="{BODY}"')

    # headings: the slide title and the big entity names take the deck's serif, regular weight like the deck's titles
    def head(m):
        tag = m.group(0)
        m2 = re.search(r'font-size="([\d.]+)"', tag)
        if not m2:
            return tag
        size = float(m2.group(1))
        if size >= 25 and 'font-weight="700"' in tag:
            tag = tag.replace('font-weight="700"', f'font-weight="400" font-family="{HEAD}"')
            if size >= 40:
                tag = re.sub(r'font-size="[\d.]+"', f'font-size="{size + 4:g}"', tag)
        return tag
    svg = re.sub(r'<text\b[^>]*>', head, svg)
    # Raleway sets wider than the Helvetica the layout was sized for: trim the 15 px card text a little
    svg = svg.replace('font-size="15"', 'font-size="14.5"')
    return svg


def main():
    OUT.mkdir(exist_ok=True)
    for n in NAMES:
        src = (HERE / f'{n}.svg').read_text(encoding='utf-8')
        (OUT / f'{n}.svg').write_text(restyle(src), encoding='utf-8')
        print('wrote', OUT / f'{n}.svg')


if __name__ == '__main__':
    main()
