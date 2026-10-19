"""Hook card (2560x1440) and Short frame 0 (1080x1920) from the real cause-2 log (evidence/c2-localhost/nginx.log,
19 Oct 2026). The log line is split across rows only; nothing is reworded. Runs in Docker:
  docker run --rm -v <lab>:/lab -w /lab python:3.12-slim sh -c "apt-get -qq update && apt-get -qq install -y fonts-dejavu-core && pip -q install pillow && python video/make_frames.py"
"""
from PIL import Image, ImageDraw, ImageFont

MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'
SANS = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
RED, INK, MUTED, BG = '#c62828', '#1a2230', '#5b6678', '#f6f7f9'

line = open('evidence/c2-localhost/nginx.log', encoding='utf8').read()
first = next(l for l in line.splitlines() if 'connect() failed (111: Connection refused)' in l)
assert 'upstream: "http://127.0.0.1:8080/"' in first


def window(d, box, title):
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, 28, fill='#ffffff', outline='#d8dde5', width=4)
    d.rectangle((x0, y0, x1, y0 + 80), fill='#e3e7ee')
    for i, c in enumerate(('#e5534b', '#d9a400', '#2da44e')):
        d.ellipse((x0 + 40 + i * 50, y0 + 25, x0 + 70 + i * 50, y0 + 55), fill=c)
    d.text((x0 + 220, y0 + 20), title, font=ImageFont.truetype(BOLD, 36), fill=INK)


def hook():
    W, H = 2560, 1440
    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    d.text((120, 70), '502 Bad Gateway', font=ImageFont.truetype(SANS, 64), fill=MUTED)
    window(d, (120, 190, W - 120, H - 190), 'NGINX 1.30.6 error log · proxy_pass http://localhost:8080')
    rows = ['2026/10/19 14:24:13 [error] 35#35: *1 connect() failed',
            '(111: Connection refused) while connecting to upstream,',
            'client: 10.199.33.4, server: , request: "GET / HTTP/1.1",',
            'upstream: "http://127.0.0.1:8080/", host: "nginx"']
    f = ImageFont.truetype(MONO, 56)
    y = 340
    for i, r in enumerate(rows):
        d.text((200, y), r, font=f, fill=RED if i in (1, 3) else INK); y += 110
    d.text((200, y + 40), 'localhost inside the NGINX container is NGINX itself', font=ImageFont.truetype(SANS, 54), fill=INK)
    d.text((140, H - 140), 'Real NGINX log line from the lab (19 Oct 2026), split across rows, unchanged',
           font=ImageFont.truetype(MONO, 32), fill=MUTED)
    im.save('video/hook-landscape.png')


def short():
    W, H = 1080, 1920
    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    d.text((60, 230), '502 Bad Gateway', font=ImageFont.truetype(SANS, 60), fill=MUTED)
    window(d, (40, 340, W - 40, 1250), 'NGINX error log')
    rows = ['[error] connect() failed', '(111: Connection refused)', 'while connecting to', 'upstream,',
            'upstream:', '"http://127.0.0.1:8080/"']
    f = ImageFont.truetype(MONO, 52)
    y = 480
    for i, r in enumerate(rows):
        d.text((90, y), r, font=f, fill=RED if i in (1, 5) else INK); y += 112
    d.text((60, 1310), 'Real log line; middle fields left out', font=ImageFont.truetype(MONO, 30), fill=MUTED)
    im.save('video/short-frame0.png')


hook(); short(); print('ok')
