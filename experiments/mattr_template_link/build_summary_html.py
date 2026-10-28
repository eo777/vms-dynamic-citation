"""Build a portable, illustrated HTML report from SUMMARY.md and saved app captures.

Run: python build_summary_html.py
Requires markdown-it-py. No web requests or image resampling are performed.
"""
import base64
import html
import json
import mimetypes
import re
from pathlib import Path
from urllib.parse import urljoin

from markdown_it import MarkdownIt

HERE = Path(__file__).resolve().parent
REPO = 'https://github.com/eo777/vms-dynamic-citation/blob/main/experiments/mattr_template_link/'
MD = MarkdownIt('commonmark', {'html': True}).enable('table')


def data_uri(path):
    path = HERE / path
    mime = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
    return f'data:{mime};base64,' + base64.b64encode(path.read_bytes()).decode('ascii')


def marked_page():
    """Annotate the app capture in native image coordinates; leave its boxes intact."""
    examples = json.loads((HERE / 'summary_figures/component_examples.json').read_text())['examples']
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-55 0 755 900">',
           f'<image x="0" y="0" width="636" height="900" href="{data_uri("summary_figures/f75r_page.png")}"/>']
    for case, letter, color, cx in [(examples[0], 'A', '#177b79', 676),
                                    (examples[1], 'B', '#b95e2e', -31)]:
        x0, y0, x1, y1 = case['display_box']
        cy = (y0 + y1) / 2
        edge, end = (x1, cx - 18) if letter == 'A' else (x0, cx + 18)
        svg += [f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="none" stroke="{color}" stroke-width="3"/>',
                f'<path d="M{edge},{cy} H{end}" stroke="{color}" stroke-width="2.5"/>',
                f'<circle cx="{cx}" cy="{cy}" r="18" fill="{color}"/>',
                f'<text x="{cx}" y="{cy+7}" text-anchor="middle" font-family="sans-serif" font-size="22" font-weight="700" fill="white">{letter}</text>']
    svg.append('</svg>')
    return 'data:image/svg+xml;base64,' + base64.b64encode(''.join(svg).encode()).decode()


def figure(src, alt, caption='', cls=''):
    src = src if src.startswith('data:') else data_uri(src)
    return (f'<figure class="{cls}"><button class="figure-open" type="button" aria-label="Expand: {html.escape(alt, quote=True)}">'
            f'<img src="{src}" alt="{html.escape(alt, quote=True)}" decoding="async">'
            '<span class="expand-hint" aria-hidden="true">↗ Expand</span></button>'
            + (f'<figcaption>{caption}</figcaption>' if caption else '') + '</figure>')


def render(markdown):
    result = MD.render(markdown)
    # Every chart is bounded in the article and opens at full size on demand.
    pattern = r'<p><img src="([^"]+)" alt="([^"]*)"\s*/?></p>\s*(?:<p><em>(.*?)</em></p>)?'
    result = re.sub(pattern, lambda m: figure(html.unescape(m[1]), html.unescape(m[2]), m[3] or ''),
                    result, flags=re.S)
    result = re.sub(r'href="(?!https?://|#)([^"]+)"',
                    lambda m: 'href="' + urljoin(REPO, html.unescape(m[1])) + '"', result)
    return result


def mattr_gallery(rendered, *, kind='mattr'):
    """Collect a set of figures into one main image and a thumbnail strip."""
    figures = re.findall(r'<figure\b[^>]*>.*?</figure>', rendered, flags=re.S)
    labels = {'mattr': [('Copying models', 'Bifolium view'),
              ('Copying + Markov', 'Group averages'), ('Governed models', 'Group averages')],
              'historical': [('Historical texts', 'Late bifolia'), ('Historical texts', 'All 50 bifolia'),
                             ('Historical texts', 'Group averages')],
              'controls': [('Page layout', 'f75r'), ('Word close-ups', 'Same page area'),
                           ('Printed-line control', 'Gart 1487')],
              'groups': [('Illustration sections', 'Herbal A and B separated'),
                         ('Golf groups', 'Golf 2.1')],
              }[kind]
    name = {'mattr': 'MATTR', 'historical': 'Historical MATTR',
            'controls': 'Control placement', 'groups': 'Section comparison'}[kind]
    identifier = f'{kind}-gallery-main'
    assert len(figures) == len(labels)
    items, thumbnails, captions = [], [], []
    for index, (fig, (title, scope)) in enumerate(zip(figures, labels)):
        match = re.search(r'<img src="([^"]+)" alt="([^"]*)"', fig)
        assert match
        caption_match = re.search(r'<figcaption>(.*?)</figcaption>', fig, flags=re.S)
        assert caption_match, f'Missing caption in {kind} figure {index + 1}'
        caption = caption_match[1]
        items.append((match[1], match[2], caption))
        label = html.escape(f'{title} · {scope}', quote=True)
        thumbnails.append(
            f'<button class="gallery-thumb" type="button" data-gallery-index="{index}" '
            f'data-gallery-title="{label}" aria-label="Show: {label}" '
            f'aria-pressed="{str(index == 0).lower()}" aria-controls="{identifier}">'
            f'<img src="{match[1]}" alt="{match[2]}" decoding="async">'
            f'<span>{title}</span><small>{scope}</small></button>')
        captions.append(f'<template data-gallery-caption="{index}">{caption}</template>')
    src, alt, caption = items[0]
    gallery = (f'<div class="figure-gallery {kind}-gallery" aria-label="{name} figure gallery">'
               f'<div class="gallery-heading"><h4 data-gallery-title>{labels[0][0]} · {labels[0][1]}</h4>'
               f'<span data-gallery-count aria-live="polite">1 / {len(labels)}</span></div>'
               f'<figure class="gallery-main" id="{identifier}"><button class="figure-open" type="button" '
               f'aria-label="Expand: {alt}"><img src="{src}" alt="{alt}" decoding="async">'
               '<span class="expand-hint" aria-hidden="true">↗ Expand</span></button>'
               f'<figcaption>{caption}</figcaption></figure>'
               '<div class="gallery-choices"><p>Choose a comparison</p>'
               f'<div class="gallery-strip" role="group" aria-label="Choose a {name} figure">'
               + ''.join(thumbnails) + '</div></div>' + ''.join(captions) + '</div>')
    replaced = 0

    def replace_figure(match):
        nonlocal replaced
        replaced += 1
        return gallery if replaced == 1 else ''

    result = re.sub(r'<figure\b[^>]*>.*?</figure>', replace_figure, rendered, flags=re.S)
    result = re.sub(r'<details>\s*<summary>[^<]+</summary>\s*</details>', '', result)
    return result


CSS = r'''
:root{--ink:#243231;--muted:#5d6d68;--teal:#177b79;--orange:#a85326;--line:#dce4de;--paper:#fffefb;--wash:#f2f5f0}
*{box-sizing:border-box}html{scroll-padding-top:20px}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.65 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a{color:var(--teal);text-underline-offset:3px}a:hover{color:#104e4d}
button{font:inherit}button:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid var(--teal);outline-offset:4px}
.wrap{max-width:1080px;margin:auto;padding:36px 36px 70px}
header{border-top:5px solid var(--teal);padding-top:20px}.eyebrow{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);font-weight:700;margin:0 0 7px}
h1{font-family:Georgia,"Times New Roman",serif;font-size:clamp(30px,4vw,43px);line-height:1.15;font-weight:500;letter-spacing:-.025em;margin:0 0 20px}
h2{font-family:Georgia,"Times New Roman",serif;font-size:32px;font-weight:500;line-height:1.22;margin:0 0 18px;letter-spacing:-.015em}
h3{font-size:21px;line-height:1.35;margin:0 0 16px}h4{font-size:16px;line-height:1.35;margin:0 0 12px}p{margin:0 0 15px}strong{font-weight:650}em{font-style:italic}
.finding{font-size:17px;line-height:1.65;max-width:920px}.finding strong{font-weight:600}.finding p{margin-bottom:12px}
header .figure-open img{max-height:350px}header figcaption{font-size:12px}
nav{display:flex;gap:10px 22px;flex-wrap:wrap;border-top:1px solid var(--line);padding:13px 0 0;margin-top:22px;font-size:13px}
nav a{text-decoration:none}section{padding-top:30px;margin-top:30px;border-top:1px solid var(--line)}section:first-of-type{margin-top:24px}
.test>section{margin-top:32px;padding-top:24px}.test>section:first-of-type{margin-top:22px;padding-top:0;border-top:0}
.context{display:grid;grid-template-columns:300px minmax(0,1fr);gap:30px;align-items:center}
.context figure{margin:0}.context .figure-open img{height:300px;width:100%;object-fit:contain}
.context .figure-open{background:#f1f0e9}.context-text{font-size:15px}.context-text p:last-child{margin-bottom:0}
.context-caption{font-size:12px;line-height:1.5;color:var(--muted);margin:10px 0 0}.legend{height:8px;border-radius:8px;margin:9px 0 4px}
.legend-labels{display:flex;justify-content:space-between;font-size:11px;color:var(--muted)}
.score-pair{display:flex;gap:22px;margin:17px 0}.score-pair>div{border-left:3px solid currentColor;padding-left:12px;line-height:1.3}.score-pair b{font-size:25px;display:block;font-weight:600}.score-pair small{font-size:12px}
.high{color:var(--teal)}.low{color:var(--orange)}.metrics{margin:20px 0}.metrics summary{font-size:14px}
ul{padding-left:23px;margin:12px 0}li{margin:7px 0}
.examples{margin-top:26px}.example-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.example-card{background:var(--wash);border:1px solid var(--line);border-radius:9px;padding:16px;min-width:0}
.example-card h5{font-size:14px;margin:0 0 3px}.example-card .score{font-size:24px;line-height:1.2;margin-bottom:12px}.score span{font-size:13px;font-weight:400}
.example-card figure{margin:0}.example-card .figure-open{background:transparent;border:0}.example-card img{height:auto;max-height:none}
.example-card figcaption{padding:10px 0 0;font-size:13px}.settings{font-size:12px;color:var(--muted);margin:11px 0 22px}
.controls{margin-top:27px}
.controls-gallery .gallery-main .figure-open img{max-height:540px}
.controls-gallery .gallery-thumb{flex:0 1 180px}
.historical-gallery .gallery-thumb,.mattr-gallery .gallery-thumb{flex:0 1 180px}
.groups-gallery .gallery-main .figure-open img{height:600px;max-height:600px}
.groups-gallery .gallery-thumb{flex:0 1 220px}
figure{margin:22px 0}.figure-open{display:block;position:relative;width:100%;padding:10px;border:1px solid var(--line);border-radius:7px;background:white;cursor:zoom-in;overflow:hidden;color:var(--ink)}
.figure-open img{display:block;max-width:100%;width:100%;height:auto;max-height:430px;object-fit:contain;margin:auto}
.expand-hint{position:absolute;bottom:8px;right:9px;padding:2px 8px;border:1px solid #dae2dc;border-radius:4px;background:#fffefbeF;color:#465953;font-size:11px;line-height:1.6}
figcaption{font-size:13px;line-height:1.5;color:var(--muted);padding:9px 2px 0}
.group-layout{display:grid;grid-template-columns:1.05fr 1fr;gap:26px;align-items:start}.group-layout figure{margin:0}.group-layout img{max-height:450px}
#groups>figure .figure-open img{max-height:620px}
#swings .figure-open img,#historical .figure-open img{max-height:650px}
#markov>.figure-open img,#markov>figure .figure-open img{max-height:500px}
.figure-gallery{margin:22px 0;border:1px solid var(--line);border-radius:9px;padding:16px;background:white}
.gallery-heading{display:flex;align-items:center;gap:12px;margin-bottom:12px}.gallery-heading h4{font-size:15px;margin:0;flex:1}.gallery-heading>span{font-size:12px;color:var(--muted);white-space:nowrap}
.gallery-main{margin:0}.gallery-main .figure-open{border:0;padding:0}.gallery-main figcaption{min-height:58px;padding:12px 0;font-size:12px}
#swings .gallery-main .figure-open img,#historical .gallery-main .figure-open img{height:500px;max-height:500px}
.gallery-choices{border-top:1px solid var(--line);padding-top:12px}.gallery-choices>p{font-size:12px;color:var(--muted);margin:0 0 8px}
.gallery-strip{display:flex;gap:8px;overflow-x:auto;padding:3px 3px 8px;scrollbar-width:thin}
.gallery-thumb{flex:1 0 115px;min-width:0;padding:7px 5px 8px;border:1px solid var(--line);border-radius:5px;background:var(--paper);color:var(--ink);cursor:pointer;text-align:left;line-height:1.3}
.gallery-thumb:hover{border-color:#91b4a5}.gallery-thumb[aria-pressed="true"]{border-color:var(--teal);box-shadow:0 0 0 1px var(--teal);background:#edf5f1}
.gallery-thumb img{display:block;width:100%;height:68px;object-fit:contain;background:white;margin-bottom:7px}.gallery-thumb span,.gallery-thumb small{display:block;padding:0 3px}.gallery-thumb span{font-size:11px;font-weight:650}.gallery-thumb small{font-size:10px;color:var(--muted);margin-top:3px}
details{border:1px solid var(--line);border-radius:7px;padding:12px 16px;margin:18px 0;background:#fafbf7}summary{font-weight:600;cursor:pointer;line-height:1.45}details[open]>summary{margin-bottom:16px}details p:last-child{margin-bottom:0}
details figure{margin:0}details table{margin-bottom:0}table{border-collapse:collapse;width:100%;font-size:13px;line-height:1.5;margin:18px 0}th,td{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left}th{background:#eaf0ea;font-weight:600}td:not(:first-child),th:not(:first-child){text-align:right}tbody tr:first-child{font-weight:700;background:#f0f6ef}
.table-scroll{overflow-x:auto}.conclusion{border-left:3px solid var(--teal);padding:6px 0 6px 20px}.conclusion p{margin:0}
.notes{font-size:13px}.notes code{overflow-wrap:anywhere}footer{font-size:12px;color:var(--muted);margin-top:30px;padding-top:16px;border-top:1px solid var(--line)}
dialog{width:calc(100vw - 32px);max-width:1800px;height:calc(100dvh - 32px);max-height:none;padding:0;border:1px solid #cbd6cd;border-radius:10px;background:var(--paper);color:var(--ink);overflow:hidden}
dialog::backdrop{background:#15211eda;backdrop-filter:blur(3px)}.viewer{height:100%;display:flex;flex-direction:column}.viewer-bar{display:flex;align-items:center;gap:10px;border-bottom:1px solid var(--line);padding:12px 16px}.viewer-bar p{font-size:13px;line-height:1.4;margin:0;flex:1}.viewer-bar button{border:1px solid #c9d5ce;border-radius:5px;background:white;padding:6px 12px;cursor:pointer;font-size:13px;white-space:nowrap}
.viewer-image{min-height:0;flex:1;overflow:auto;padding:16px;display:flex;align-items:center;justify-content:center}.viewer-image img{max-width:100%;max-height:100%;object-fit:contain}.viewer-image.actual{display:block}.viewer-image.actual img{max-width:none;max-height:none}.viewer-image.actual img[src^="data:image/svg"]{width:755px;height:900px}body:has(dialog[open]){overflow:hidden}
@media(min-width:1200px){.context{grid-template-columns:330px minmax(0,1fr)}}
@media(max-width:740px){.wrap{padding:22px 22px 45px}.context{grid-template-columns:230px minmax(0,1fr);gap:20px}.context img{height:290px}.context-text{font-size:14px}.score-pair{gap:14px}.group-layout{grid-template-columns:1fr}.group-layout figure{max-width:480px;margin:auto}.finding{font-size:16px}.example-card{padding:12px}}
@media(max-width:560px){.wrap{padding:18px 18px 40px}h1{font-size:32px}h2{font-size:25px}section{padding-top:24px;margin-top:24px}.context{grid-template-columns:1fr;gap:18px}.context figure{max-width:340px;width:100%;margin:auto}.context img{height:290px}.context-text{font-size:15px}.example-grid{grid-template-columns:1fr}.example-card img{max-height:300px}.figure-open{padding:4px}.expand-hint{bottom:5px;right:5px}.viewer-bar{padding:10px;flex-wrap:wrap}.viewer-bar p{flex-basis:100%;font-size:12px}.viewer-image{padding:6px}nav{gap:10px 18px}.score-pair{gap:25px}table{font-size:12px}}
@media(max-width:560px){.figure-gallery{padding:10px}.gallery-heading h4{font-size:13px}#swings .gallery-main .figure-open img,#historical .gallery-main .figure-open img{height:300px;max-height:300px}.groups-gallery .gallery-main .figure-open img{height:330px;max-height:330px}.gallery-thumb{flex-basis:115px}.gallery-main figcaption{min-height:0}}
@media print{.gallery-choices{display:none}.figure-gallery{border:0;padding:0}#swings .gallery-main .figure-open img,#historical .gallery-main .figure-open img{height:auto;max-height:440px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{body{font-size:10pt;background:white}.wrap{max-width:none;padding:0}nav,.expand-hint,dialog{display:none!important}header{padding-top:10px}h1{font-size:27pt}h2{font-size:18pt}.finding{font-size:11pt}section{margin-top:18px;padding-top:18px}.context{grid-template-columns:240px 1fr}.context img{height:280px}.context-text{font-size:10pt}.figure-open{border:0}figure,.example-card,table{break-inside:avoid}.figure-open img{max-height:340px}details{background:none}details:not([open]){display:none}a{color:inherit}.group-layout{grid-template-columns:1fr 1fr}}
'''

JS = r'''
const dialog = document.querySelector('#figure-viewer');
const viewerImage = dialog.querySelector('img');
const viewerTitle = dialog.querySelector('#viewer-title');
const viewport = dialog.querySelector('.viewer-image');
const sizeButton = dialog.querySelector('[data-size]');
document.querySelectorAll('.figure-gallery').forEach(gallery => {
  const choices = [...gallery.querySelectorAll('.gallery-thumb')];
  const main = gallery.querySelector('.gallery-main');
  function select(index) {
    const choice = choices[index];
    const source = choice.querySelector('img');
    const image = main.querySelector('img');
    image.src = source.src;
    image.alt = source.alt;
    main.querySelector('button').setAttribute('aria-label', 'Expand: ' + source.alt);
    main.querySelector('figcaption').replaceChildren(
      gallery.querySelector(`[data-gallery-caption="${index}"]`).content.cloneNode(true));
    gallery.querySelector('.gallery-heading [data-gallery-title]').textContent = choice.dataset.galleryTitle;
    gallery.querySelector('[data-gallery-count]').textContent = `${index + 1} / ${choices.length}`;
    choices.forEach((button, i) => button.setAttribute('aria-pressed', String(i === index)));
  }
  choices.forEach((button, index) => {
    button.addEventListener('click', () => select(index));
    button.addEventListener('keydown', event => {
      let next;
      if (event.key === 'ArrowRight') next = (index + 1) % choices.length;
      else if (event.key === 'ArrowLeft') next = (index + choices.length - 1) % choices.length;
      else if (event.key === 'Home') next = 0;
      else if (event.key === 'End') next = choices.length - 1;
      else return;
      event.preventDefault();
      choices[next].focus();
      select(next);
    });
  });
});
document.querySelectorAll('.figure-open').forEach(button => {
  button.addEventListener('click', () => {
    const source = button.querySelector('img');
    viewerImage.src = source.src;
    viewerImage.alt = source.alt;
    viewerTitle.textContent = source.alt;
    viewport.classList.remove('actual');
    sizeButton.textContent = 'Actual size';
    sizeButton.setAttribute('aria-pressed', 'false');
    dialog.showModal();
    viewport.scrollTo(0, 0);
  });
});
dialog.querySelector('[data-close]').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
sizeButton.addEventListener('click', () => {
  const actual = viewport.classList.toggle('actual');
  sizeButton.textContent = actual ? 'Fit to screen' : 'Actual size';
  sizeButton.setAttribute('aria-pressed', String(actual));
  viewport.scrollTo(0, 0);
});
'''


def main():
    source = (HERE / 'SUMMARY.md').read_text(encoding='utf-8')
    notes_marker = '<details>\n<summary>Numbers, definitions, and reproduction</summary>'
    article, notes_body = source.split(notes_marker, 1)
    notes = render('<details class="notes">\n<summary>Numbers, definitions, and reproduction</summary>' + notes_body)
    parts = re.split(r'^#{2,3} (.+)$', article, flags=re.M)
    sections = dict(zip(parts[1::2], parts[2::2]))
    titles = {
        'test1': 'Test 1: Can changes in page layout explain the MATTR swings?',
        'controls': 'Method: historical texts and models in the same layout',
        'historical': 'Natural-language controls do not show the same broad MATTR swings',
        'markov': 'Markov controls do not predict the swings from layout alone',
        'swings': 'Self-citation predicts some broad MATTR swings from layout alone',
        'test2': 'Test 2: Could local copying help explain the MATTR shifts?',
        'method': 'Method: the spatial window and diversity score',
        'repetition': 'Words with less diverse source material are more often repeats',
        'groups': 'Herbal B does not show the same association',
        'mattr': 'Source diversity also tracks MATTR',
        'conclusion': 'Conclusion',
    }

    def section_body(key):
        return sections.pop(titles[key])

    intro = parts[0].split('\n\n', 1)[1].strip()
    method = section_body('method').strip().split('\n\n')
    # These checks prevent silently dropping prose when the Markdown structure changes.
    assert len(method) >= 8 and method[1].startswith('![Full page')
    assert method[4].startswith('- **Component diversity:') and method[5].startswith('Here are the two')
    assert method[7].startswith('*Both close-ups')
    # Locate prose by content, keeping the Markdown as the source of the explanation.
    settings = next(x for x in method if x.startswith('*Both close-ups')).strip('*')
    method_tail = render('\n\n'.join(method[8:]))
    palette = json.loads((HERE / 'summary_figures/component_examples.json').read_text())['palette']
    colors = ','.join(palette[::max(1, len(palette)//20)])
    overview = figure(marked_page(), 'f75r: component diversity over the actual manuscript, with examples A and B marked', cls='page-overview')
    legend = (f'<div class="legend" style="background:linear-gradient(90deg,{colors})"></div>'
              '<div class="legend-labels"><span>9.5 · lower</span><span>27.3 · higher</span></div>')
    method_html = f'''<section id="method"><h3>{titles['method']}</h3>
    <div class="context"><div>{overview}{legend}<p class="context-caption">Component diversity · effective pairs<br>Each box describes its source window. A and B locate the two <i>qokeedy</i> examples below.</p></div>
    <div class="context-text">{render(method[0])}
    <p><strong>Component diversity</strong> is the effective number of different adjacent glyph-unit pairs in those source words. A varied, evenly used mix gives a higher score.</p>
    <div class="score-pair"><div class="high"><b>A · 22.1</b><small>higher diversity</small></div><div class="low"><b>B · 13.6</b><small>lower diversity</small></div></div>
    <p>The translucent colors show how this varies across the actual page. Warm colors are lower; teal is higher.</p></div></div>
    <div class="examples"><h4>Example: 2 different qokeedy's on f75r</h4>{render(method[5])}
    <div class="example-grid"><div class="example-card"><h5 class="high">A · Higher component diversity</h5><div class="score high">22.1 <span>effective pairs</span></div>
    {figure('summary_figures/f75r_high.png', 'A: higher-diversity source window around qokeedy on f75r', 'lor, sain, checthy and other forms supply a wider mix of glyph pairs.')}</div>
    <div class="example-card"><h5 class="low">B · Lower component diversity</h5><div class="score low">13.6 <span>effective pairs</span></div>
    {figure('summary_figures/f75r_low.png', 'B: lower-diversity source window around qokeedy on f75r', 'Repeated qokeedy / qokedy forms keep reusing q·o, o·k and d·y.')}</div></div>
    <p class="settings">Both windows: 8 line spacings up · 45° half-angle · 3 word widths left. The target is at the point of each cone. {html.escape(settings)}</p></div>
    <details class="metrics"><summary>The three diversity measurements</summary>{render(method[3] + chr(10)*2 + method[4])}</details>
    {method_tail}</section>'''

    test1 = render(section_body('test1'))
    controls = mattr_gallery(render(section_body('controls')), kind='controls')
    historical = mattr_gallery(render(section_body('historical')), kind='historical')
    markov = render(section_body('markov'))
    test2 = render(section_body('test2'))
    repetition = render(section_body('repetition'))
    repetition = re.sub(r'(<table>.*?</table>)', r'<div class="table-scroll">\1</div>', repetition, flags=re.S)
    groups = mattr_gallery(render(section_body('groups')), kind='groups')
    mattr = render(section_body('mattr'))
    swings = mattr_gallery(render(section_body('swings')))
    conclusion = render(section_body('conclusion'))
    assert not sections
    document = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="An illustrated explanation of spatial component diversity, repetition, and MATTR in the Voynich manuscript.">
<title>Spatial diversity, repetition, and MATTR</title><style>{CSS}</style></head>
<body><main class="wrap"><header id="overview"><p class="eyebrow">Voynich manuscript · analysis notes · October 2026</p>
<h1>Spatial diversity, repetition, and MATTR</h1><div class="finding">{render(intro)}</div>
<nav aria-label="Sections"><a href="#test1">Test 1 · Layout</a><a href="#historical">Historical controls</a><a href="#markov">Markov controls</a><a href="#swings">Copying models</a><a href="#test2">Test 2 · Local copying</a><a href="#method">Spatial window</a><a href="#repetition">Results</a><a href="#groups">By section</a><a href="#mattr">MATTR correlation</a><a href="#conclusion">Conclusion</a></nav></header>
<section class="test" id="test1"><h2>{titles['test1']}</h2>{test1}
<section id="controls"><h3>{titles['controls']}</h3>{controls}</section>
<section id="historical"><h3>{titles['historical']}</h3>{historical}</section>
<section id="markov"><h3>{titles['markov']}</h3>{markov}</section>
<section id="swings"><h3>{titles['swings']}</h3>{swings}</section>
</section>
<section class="test" id="test2"><h2>{titles['test2']}</h2>{test2}
{method_html}
<section id="repetition"><h3>{titles['repetition']}</h3>{repetition}</section>
<section id="groups"><h3>{titles['groups']}</h3>{groups}</section>
<section id="mattr"><h3>{titles['mattr']}</h3>{mattr}</section>
</section>
<section id="conclusion"><h2>{titles['conclusion']}</h2>{conclusion}</section>
{notes}
<footer>Figures open at full size when selected. All images are embedded in this file.<br>
Page image and word coordinates: The Voynichese Project. <a href="{REPO}RESULTS.md">Full results and sources</a></footer></main>
<dialog id="figure-viewer" aria-labelledby="viewer-title"><div class="viewer"><div class="viewer-bar"><p id="viewer-title"></p><button type="button" data-size aria-pressed="false">Actual size</button><button type="button" data-close autofocus>Close</button></div><div class="viewer-image"><img alt=""></div></div></dialog>
<script>{JS}</script></body></html>'''
    output = HERE / 'SUMMARY.html'
    output.write_text(document, encoding='utf-8')
    print(f'Built {output.name}: {output.stat().st_size / 1_000_000:.2f} MB, all figures embedded.')


if __name__ == '__main__':
    main()
