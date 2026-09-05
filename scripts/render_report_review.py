"""Rend toutes les pages pour la relecture visuelle, sans toucher au PDF."""
from pathlib import Path
import fitz
from PIL import Image, ImageOps, ImageDraw
root = Path(__file__).resolve().parents[1]
out = root / 'report/review'
out.mkdir(exist_ok=True)
doc = fitz.open(root / 'report/rapport.pdf')
print(f'{len(doc)} pages')
thumbs = []
for i, page in enumerate(doc):
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
    pix.save(out / f'page-{i+1:02}.png')
    im = Image.open(out / f'page-{i+1:02}.png').convert('RGB')
    im.thumbnail((445, 630))
    thumb = Image.new('RGB', (465, 665), 'white')
    thumb.paste(im, (10, 25))
    ImageDraw.Draw(thumb).text((10, 5), f'Page {i+1}', fill='black')
    thumbs.append(thumb)
    text = page.get_text()
    print(i+1, len(text), text[:70].replace('\n', ' '), '| END:', text[-80:].replace('\n', ' '))
    for b in page.get_text('blocks'):
        if b[0] < 20 or b[2] > page.rect.width-20:
            print('  horizontal margin warning', b[:4])
for start in range(0, len(thumbs), 4):
    sheet = Image.new('RGB', (930, 1330), '#cccccc')
    for j, thumb in enumerate(thumbs[start:start+4]):
        sheet.paste(thumb, ((j%2)*465, (j//2)*665))
    sheet.save(out / f'sheet-{start//4+1}.jpg')
