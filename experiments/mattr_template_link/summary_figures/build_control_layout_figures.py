"""Frame actual heatmap-app screenshots; do not draw or reposition any words.

Run build_control_layout_viewer.py first, capture the five pages in the browser,
and save the screenshot bounds in control_layout_captures.json. This script only
crops those captures, adds headings, and marks the shared close-up area.
"""
import gzip
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
CAPTURES = HERE / 'control_layout_viewer'
PAPER = '#fffefb'
INK = '#243231'
MUTED = '#5d6d68'
TEAL = '#78b7a6'
DETAIL = (550, 145, 1005, 389)
CASES = [
    ('manuscript', 'Voynich manuscript', 'Recorded word positions'),
    ('gart_one_word_per_box', 'Historical text: one word per box', 'Gart der Gesundheit, 1487'),
    ('gart_character_budget', 'Historical text: line character budget', 'Gart der Gesundheit, 1487'),
    ('bigram_whole', 'Markov control', 'Whole-manuscript word bigrams'),
]


def font(size, bold=False):
    return ImageFont.truetype('C:/Windows/Fonts/' + ('segoeuib.ttf' if bold else 'segoeui.ttf'), size)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    inputs = json.loads((HERE / 'control_layout_inputs.json').read_text(encoding='utf-8'))
    captured = json.loads((HERE / 'control_layout_captures.json').read_text(encoding='utf-8'))
    pages, provenance = {}, []
    for item in captured['captures']:
        key = item['key']
        source = next(case for case in inputs['cases'] if case['key'] == key)
        bundle_path = CAPTURES / key / 'data/mattr_heatmap/words.json.gz'
        assert sha(bundle_path) == source['bundle_sha256']
        with gzip.open(bundle_path, 'rt', encoding='utf-8') as stream:
            bundle = json.load(stream)
        expected = [bundle['words'][i] for line in bundle['lines'] if line['page'] == 'f75r'
                    for i in range(line['start'], line['end']) if bundle['geometry'][i] is not None]
        # Every displayed word must be from the saved experimental text, in order.
        assert [label['text'] for label in item['labels']] == expected
        screenshot = CAPTURES / (key + '_app.png')
        image = Image.open(screenshot).convert('RGB')
        b = item['box']
        factor = image.width / item['viewport']['width']
        x = (b['x'] + item['scroll']['x']) * factor
        y = (b['y'] + item['scroll']['y']) * factor
        crop = (round(x), round(y), round(x + b['width'] * factor), round(y + b['height'] * factor))
        page = image.crop(crop)
        page.save(CAPTURES / (key + '_page.png'))
        pages[key] = page
        provenance.append(dict(key=key, screenshot_sha256=sha(screenshot), screenshot_crop=crop,
                               displayed_words=len(expected), bundle_sha256=sha(bundle_path)))

    def region(page, bounds):
        return tuple(round(v * (page.width / 1136 if i % 2 == 0 else page.height / 1500))
                     for i, v in enumerate(bounds))

    def paste_page(canvas, page, x, y, width, mark=False):
        shown = page.copy()
        if mark:
            ImageDraw.Draw(shown).rectangle(region(shown, DETAIL), outline=TEAL, width=3)
        height = round(width * shown.height / shown.width)
        canvas.paste(shown.resize((width, height), Image.Resampling.LANCZOS), (x, y))
        return height

    # Four full pages give the placement context without app controls or readouts.
    width, gap, margin = 438, 24, 28
    full = Image.new('RGB', (margin * 2 + 4 * width + 3 * gap, 738), PAPER)
    draw = ImageDraw.Draw(full)
    draw.text((margin, 12), 'The same f75r layout, with different words', font=font(28, True), fill=INK)
    for index, (key, title, subtitle) in enumerate(CASES):
        x = margin + index * (width + gap)
        draw.text((x, 62), title, font=font(21, True), fill=INK)
        draw.text((x, 91), subtitle, font=font(19), fill=MUTED)
        paste_page(full, pages[key], x, 125, width, mark=True)
    draw.text((margin, 699), 'Outlined areas are enlarged in the close-up view. Text is displayed by the heatmap app.',
              font=font(17), fill=MUTED)
    full.save(HERE / 'control_layout_f75r.png', optimize=True)

    # Same page coordinates in every close-up; no re-typesetting of screenshot text.
    width, gap, margin = 530, 30, 28
    height = round(width * (DETAIL[3] - DETAIL[1]) / (DETAIL[2] - DETAIL[0]))
    detail = Image.new('RGB', (margin * 2 + 2 * width + gap, 100 + 2 * (height + 80)), PAPER)
    draw = ImageDraw.Draw(detail)
    draw.text((margin, 15), 'The same part of f75r, enlarged', font=font(28, True), fill=INK)
    for index, (key, title, subtitle) in enumerate(CASES):
        x, y = margin + (index % 2) * (width + gap), 70 + (index // 2) * (height + 80)
        draw.text((x, y), title, font=font(22, True), fill=INK)
        draw.text((x, y + 30), subtitle, font=font(19), fill=MUTED)
        cropped = pages[key].crop(region(pages[key], DETAIL))
        detail.paste(cropped.resize((width, height), Image.Resampling.LANCZOS), (x, y + 61))
    detail.save(HERE / 'control_layout_f75r_detail.png', optimize=True)

    # Keep the printed-line variant available without crowding the main comparison.
    width, gap, margin = 480, 32, 28
    own = Image.new('RGB', (margin * 2 + width * 2 + gap, 790), PAPER)
    draw = ImageDraw.Draw(own)
    draw.text((margin, 15), 'Keeping the historical text’s printed lines', font=font(28, True), fill=INK)
    for index, (key, title, subtitle) in enumerate([
            CASES[0], ('gart_own_lines', 'Gart der Gesundheit, 1487', 'One printed line per manuscript line slot')]):
        x = margin + index * (width + gap)
        draw.text((x, 65), title, font=font(23, True), fill=INK)
        draw.text((x, 98), subtitle, font=font(20), fill=MUTED)
        paste_page(own, pages[key], x, 138, width)
    own.save(HERE / 'control_layout_f75r_printed_lines.png', optimize=True)
    (HERE / 'control_layout_figures.json').write_text(json.dumps(dict(
        page='f75r', screenshot_source='Actual heatmap app, Show words on, Boxes hidden, page image off',
        viewbox=[0, 0, 1136, 1500], closeup_coordinates=DETAIL, verified_captures=provenance,
        note='Screenshot crops and labels only; words and geometry are unchanged from the frozen study inputs.'),
        indent=2) + '\n', encoding='utf-8')
    print('Built 3 figures; all 1,921 displayed words match the frozen input bundles.')


if __name__ == '__main__':
    main()
