#!/usr/bin/env python3
"""Minimal, dependency-light vertical renderer (Pillow -> ffmpeg pipe).

A stand-in for a Remotion / HyperFrames composition: draws a 1080x1920 frame per
tick with a per-segment visual card, word-by-word highlighted captions, and the
cover as the very first frames (cover_frames, default 3 = 0.1 s @30fps), so the
platform thumbnail taken at 0.01 s is the cover.

Layout (safe zones): content y300-1290, captions ~y1330, nothing below y1500.
"""
import argparse, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_config, load_json

def find_font(pref):
    if pref and os.path.exists(pref):
        return pref
    try:
        files = subprocess.run(['fc-list', ':lang=zh', 'file'], capture_output=True, text=True).stdout.split('\n')
        files = [f.strip().rstrip(':') for f in files if f.strip()]
        rank = lambda f: (('CJK' not in f) and ('Hei' not in f) and ('Han' not in f), 'Bold' not in f and 'Black' not in f, f)
        for f in sorted(files, key=rank):
            if os.path.exists(f):
                return f
    except FileNotFoundError:
        pass
    sys.exit('No CJK font found: set THV_FONT=/path/to/NotoSansCJK-Bold.ttc')

def hexrgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def wrap(draw, text, font, width):
    lines, cur = [], ''
    for ch in text:
        if draw.textlength(cur + ch, font=font) > width and cur:
            lines.append(cur); cur = ch
        else:
            cur += ch
    return lines + ([cur] if cur else [])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default='config.json')
    ap.add_argument('--segments', default='segments.json')
    ap.add_argument('--timing', default='build/voice/timing.json')
    ap.add_argument('--captions', default='build/captions.json')
    ap.add_argument('--audio', default='build/voice/voice.wav')
    ap.add_argument('--out', default='build/render.mp4')
    ap.add_argument('--cover-frames', type=int, default=3)
    ap.add_argument('--max-seconds', type=float, default=0, help='render only the first N seconds (preview)')
    a = ap.parse_args()
    cfg = load_config(a.config); W, H, FPS = cfg['width'], cfg['height'], int(cfg['fps'])
    fp = find_font(cfg['font']); F = lambda s: ImageFont.truetype(fp, s)
    f_cap, f_card, f_cover, f_small = F(64), F(96), F(150), F(40)
    acc = hexrgb(cfg['accent']); bg = (38, 38, 46); white = (245, 245, 245); grey = (120, 120, 130)
    segs = load_json(a.segments); tm = {t['id']: t for t in load_json(a.timing)}; caps = load_json(a.captions)
    dur = max(t['end'] for t in tm.values()) + 0.15
    if a.max_seconds:
        dur = min(dur, a.max_seconds)
    n = int(round(dur * FPS))
    title = cfg['cover_title'] or segs[0].get('cover', segs[0]['text'])
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           '-i', a.audio, '-t', f'{dur:.3f}', '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
           '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', a.out]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    cover = None
    for i in range(n):
        t = i / FPS
        if i < a.cover_frames:
            if cover is None:
                im = Image.new('RGB', (W, H), bg); d = ImageDraw.Draw(im)
                d.rectangle([80, 520, 100, 1060], fill=acc)
                y = 520
                for ln in wrap(d, title, f_cover, W - 260)[:4]:
                    d.text((140, y), ln, font=f_cover, fill=white); y += 180
                cover = im.tobytes()
            p.stdin.write(cover); continue
        im = Image.new('RGB', (W, H), bg); d = ImageDraw.Draw(im)
        # slow drifting glow keeps the background alive (avoids freezedetect on long holds)
        gy = int(300 + 500 * (0.5 + 0.5 * math.sin(t * 0.9))); gx = int(W * (0.5 + 0.35 * math.cos(t * 0.6)))
        d.ellipse([gx - 420, gy - 420, gx + 420, gy + 420], fill=(52, 44, 54))
        # progress bar + HUD
        d.rectangle([0, 0, int(W * t / dur), 8], fill=acc)
        seg = next((s for s in reversed(segs) if tm[s['id']]['start'] <= t), segs[0])
        d.text((80, 200), seg.get('chapter', ''), font=f_small, fill=grey)
        # visual card: slide in over 8 frames from segment start
        k = min(1.0, (t - tm[seg['id']]['start']) * FPS / 8)
        dx = int((1 - k) ** 2 * 120)
        vis = seg.get('visual', '')
        y = 520
        for ln in wrap(d, vis, f_card, W - 200)[:5]:
            d.text((100 + dx, y), ln, font=f_card, fill=white); y += 130
        if seg.get('keywords'):
            d.rectangle([100 + dx, y + 20, 100 + dx + int(260 * k), y + 32], fill=acc)
        # captions with word-by-word highlight
        cb = next((c for c in caps if c['start'] <= t < c['end']), None)
        if cb:
            chars = [c for c in cb['chars'] if c['t'] != ' ' or True]
            total = sum(d.textlength(c['t'], font=f_cap) for c in chars)
            x = (W - total) / 2
            for c in chars:
                said = c.get('s') is not None and c['s'] <= t
                col = acc if (said and c.get('kw')) else (white if said else grey)
                d.text((x, 1330), c['t'], font=f_cap, fill=col); x += d.textlength(c['t'], font=f_cap)
        p.stdin.write(im.tobytes())
    p.stdin.close()
    if p.wait() != 0:
        sys.exit('ffmpeg encode failed')
    print('rendered', a.out, f'{dur:.2f}s', n, 'frames')

if __name__ == '__main__':
    main()
