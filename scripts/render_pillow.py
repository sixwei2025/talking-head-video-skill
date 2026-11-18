#!/usr/bin/env python3
"""Multi-style talking-head renderer (Pillow -> ffmpeg pipe, zero Node/Chrome deps).

Supports 6 visual styles x 6 single-line caption styles across both 16:9 (1920x1080)
and 9:16 (1080x1920), optional circular avatar PIP, and cover-first-frame (frames 0..2).
"""
import argparse, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageOps
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_config, load_json
from styles import resolve_style, STYLES, CAPTION_STYLES


def find_font(pref):
    """Locate a CJK bold/sans font on the system."""
    if pref and os.path.exists(pref):
        return pref
    mac_candidates = [
        '/System/Library/Fonts/STHeiti Medium.ttc',
        '/System/Library/Fonts/PingFang.ttc',
        '/Library/Fonts/Arial Unicode.ttf',
    ]
    for p in mac_candidates:
        if os.path.exists(p):
            return p
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
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def blend(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def wrap(draw, text, font, width):
    lines, cur = [], ''
    for ch in text:
        if ch == '\n':
            lines.append(cur); cur = ''; continue
        if draw.textlength(cur + ch, font=font) > width and cur:
            lines.append(cur); cur = ch
        else:
            cur += ch
    return lines + ([cur] if cur else [])


def load_avatar(path, size):
    """Load an optional circular avatar image with transparent mask."""
    if not path or not os.path.exists(path):
        return None
    im = Image.open(path).convert('RGBA')
    im = ImageOps.fit(im, (size, size), method=Image.LANCZOS)
    mask = Image.new('L', (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    im.putalpha(mask)
    return im


def draw_background(im, d, W, H, t, st):
    """Draw style-specific background with subtle live motion to prevent freezedetect."""
    bg = hexrgb(st['bg'])
    bg_alt = hexrgb(st['bg_alt'])
    acc = hexrgb(st['accent'])
    pat = st['pattern']
    # Soft drifting ambient orb (subtle contrast, keeps frames alive)
    gx = int(W * (0.5 + 0.30 * math.cos(t * 0.55)))
    gy = int(H * (0.45 + 0.25 * math.sin(t * 0.80)))
    r = int(min(W, H) * 0.42)
    orb_col = blend(bg, bg_alt, 0.75)
    d.ellipse([gx - r, gy - r, gx + r, gy + r], fill=orb_col)
    if pat == 'grid':
        step = 64
        line_c = blend(bg, hexrgb(st['card_border']), 0.45)
        ox = int((t * 14) % step)
        for x in range(ox, W, step):
            d.line([(x, 0), (x, H)], fill=line_c, width=1)
        for y in range(0, H, step):
            d.line([(0, y), (W, y)], fill=line_c, width=1)
    elif pat == 'dots':
        step = 48
        dot_c = blend(bg, hexrgb(st['muted']), 0.30)
        for x in range(32, W, step):
            for y in range(32, H, step):
                d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=dot_c)
    elif pat == 'diagonal':
        stripe_c = blend(bg, bg_alt, 0.55)
        off = int((t * 36) % 160)
        for x in range(-H + off, W + H, 160):
            d.line([(x, H), (x + H // 2, 0)], fill=stripe_c, width=14)
    elif pat == 'editorial':
        rule_c = blend(bg, hexrgb(st['muted']), 0.28)
        d.line([(60, 118), (W - 60, 118)], fill=hexrgb(st['fg']), width=3)
        d.line([(60, H - 90), (W - 60, H - 90)], fill=rule_c, width=2)
    elif pat == 'glow':
        r2 = int(min(W, H) * 0.30)
        gx2 = int(W * (0.5 - 0.25 * math.sin(t * 0.45)))
        gy2 = int(H * (0.55 + 0.18 * math.cos(t * 0.65)))
        d.ellipse([gx2 - r2, gy2 - r2, gx2 + r2, gy2 + r2], fill=blend(bg, acc, 0.14))


def draw_visual_card(im, d, W, H, is_land, seg, seg_idx, total_segs, k, st, fonts, cfg):
    """Draw the main visual card according to style['card_mode']."""
    f_small, f_card, f_metric = fonts['small'], fonts['card'], fonts['metric']
    fg = hexrgb(st['fg'])
    muted = hexrgb(st['muted'])
    acc = hexrgb(st['accent'])
    cbg = hexrgb(st['card_bg'])
    cbd = hexrgb(st['card_border'])
    csh = hexrgb(st['card_shadow'])
    asoft = hexrgb(st['accent_soft'])
    mode = st['card_mode']

    ease = 1 - (1 - k) ** 3
    dx = int((1 - ease) * (90 if is_land else 110))
    pad_x = int(W * 0.08) if is_land else 80
    card_top = int(H * 0.18) if is_land else 340
    card_bot = int(H * 0.74) if is_land else 1240
    card_l, card_r = pad_x + dx, W - pad_x + dx
    chap = seg.get('chapter', '') or f'PART {seg_idx + 1:02d}'

    # Top header / chapter pill
    hy = int(H * 0.075) if is_land else 185
    if mode == 'swiss':
        brand = cfg.get('brand_label', 'HUIXIN · AI STUDIO')
        d.text((pad_x, 62), f'{brand}   /   {seg_idx + 1:02d} OF {total_segs:02d}', font=f_small, fill=muted)
        d.text((pad_x, 134 if is_land else 210), chap.upper(), font=f_small, fill=acc)
    else:
        pill_w = int(d.textlength(chap, font=f_small)) + 48
        d.rounded_rectangle([pad_x, hy, pad_x + pill_w, hy + 56], radius=28, fill=asoft, outline=acc, width=2)
        d.text((pad_x + 24, hy + 10), chap, font=f_small, fill=acc)

    # Card container
    if mode == 'elevated':
        d.rounded_rectangle([card_l + 10, card_top + 14, card_r + 10, card_bot + 14], radius=28, fill=csh)
        d.rounded_rectangle([card_l, card_top, card_r, card_bot], radius=28, fill=cbg, outline=cbd, width=2)
        d.rounded_rectangle([card_l, card_top + 40, card_l + 14, card_bot - 40], radius=7, fill=acc)
    elif mode == 'terminal':
        d.rounded_rectangle([card_l, card_top, card_r, card_bot], radius=22, fill=cbg, outline=cbd, width=2)
        d.rectangle([card_l + 2, card_top + 2, card_r - 2, card_top + 52], fill=blend(cbg, cbd, 0.45))
        for j, dc in enumerate([(239, 68, 68), (245, 158, 11), (34, 197, 94)]):
            d.ellipse([card_l + 26 + j * 28, card_top + 18, card_l + 42 + j * 28, card_top + 34], fill=dc)
    elif mode == 'impact':
        d.rounded_rectangle([card_l, card_top, card_r, card_bot], radius=16, fill=cbg, outline=cbd, width=4)
        d.rectangle([card_l, card_top, card_l + 22, card_bot], fill=acc)
    elif mode == 'sketch':
        d.rounded_rectangle([card_l + 12, card_top + 12, card_r + 12, card_bot + 12], radius=18, fill=csh)
        d.rounded_rectangle([card_l, card_top, card_r, card_bot], radius=18, fill=cbg, outline=cbd, width=5)
    elif mode == 'swiss':
        d.line([(card_l, card_top), (card_r, card_top)], fill=fg, width=4)
        d.line([(card_l, card_bot), (card_r, card_bot)], fill=cbd, width=2)
    elif mode == 'minimal':
        d.rounded_rectangle([card_l, card_top, card_r, card_bot], radius=32, fill=cbg, outline=cbd, width=1)

    # Optional metric badge (swiss/impact/elevated)
    metric = seg.get('metric') or (cfg.get('cover_metric') if seg_idx == 0 else '')
    if metric:
        mw = int(d.textlength(metric, font=f_metric)) + 44
        mx = card_r - mw - 44
        my = card_top + 36
        d.rounded_rectangle([mx, my, mx + mw, my + 78], radius=14, fill=asoft)
        d.text((mx + 22, my + 12), metric, font=f_metric, fill=acc)

    # Main visual text inside card
    vis = seg.get('visual', '') or seg.get('text', '')
    inner_l = card_l + (72 if is_land else 56)
    inner_w = (card_r - card_l) - (144 if is_land else 112)
    lines = wrap(d, vis, f_card, inner_w)[:4]
    lh = int(f_card.size * 1.35)
    block_h = len(lines) * lh
    ty = card_top + max(68, (card_bot - card_top - block_h) // 2)
    for idx_l, ln in enumerate(lines):
        if mode == 'sketch' and idx_l == 0:
            lw = int(d.textlength(ln, font=f_card))
            d.rectangle([inner_l - 8, ty + int(f_card.size * 0.55), inner_l + lw + 8, ty + f_card.size + 6], fill=asoft)
        d.text((inner_l, ty), ln, font=f_card, fill=fg)
        ty += lh

    # Animated keyword accent bar under visual text
    if seg.get('keywords'):
        bar_w = int(280 * ease)
        d.rounded_rectangle([inner_l, ty + 18, inner_l + max(24, bar_w), ty + 30], radius=6, fill=acc)


def draw_caption(d, W, H, is_land, t, cb, st, csid, f_cap, f_cap_sm):
    """Draw strictly single-line caption using one of the 6 caption styles."""
    if not cb:
        return
    chars = cb['chars']
    full_text = ''.join(c['t'] for c in chars)
    font = f_cap
    total = d.textlength(full_text, font=font)
    max_w = W - (240 if is_land else 100)
    if total > max_w:
        font = f_cap_sm
        total = d.textlength(full_text, font=font)

    cy = int(H * 0.835) if is_land else 1330
    x0 = (W - total) / 2
    ch_h = font.size

    fg = hexrgb(st['fg'])
    acc = hexrgb(st['accent'])
    muted = hexrgb(st['muted'])
    bg = hexrgb(st['bg'])
    is_dark = sum(bg) / 3 < 128

    if csid == 'pill-highlight':
        pill_bg = (24, 24, 29) if not is_dark else (250, 247, 242)
        text_on = (255, 255, 255) if not is_dark else (24, 24, 27)
        text_off = (160, 160, 170) if not is_dark else (130, 130, 140)
        d.rounded_rectangle([x0 - 36, cy - 16, x0 + total + 36, cy + ch_h + 22], radius=20, fill=pill_bg)
        x = x0
        for c in chars:
            on = c.get('s') is not None and c['s'] <= t
            col = acc if (on and c.get('kw')) else (text_on if on else text_off)
            d.text((x, cy), c['t'], font=font, fill=col)
            x += d.textlength(c['t'], font=font)

    elif csid == 'karaoke-glow':
        x = x0
        for c in chars:
            on = c.get('s') is not None and c['s'] <= t
            col = acc if (on and c.get('kw')) else (fg if on else muted)
            if on:
                d.text((x + 2, cy + 2), c['t'], font=font, fill=blend(bg, acc if c.get('kw') else fg, 0.35))
            d.text((x, cy), c['t'], font=font, fill=col)
            x += d.textlength(c['t'], font=font)

    elif csid == 'variety-bold':
        x = x0
        for c in chars:
            cw = d.textlength(c['t'], font=font)
            on = c.get('s') is not None and c['s'] <= t
            if on and c.get('kw'):
                d.rounded_rectangle([x - 4, cy - 8, x + cw + 4, cy + ch_h + 12], radius=10, fill=acc)
                col = (255, 255, 255)
            else:
                col = (232, 255, 0) if (on and is_dark) else (fg if on else muted)
                # thick outline for variety-show punch
                for ox, oy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
                    d.text((x + ox, cy + oy), c['t'], font=font, fill=(12, 12, 16))
            d.text((x, cy), c['t'], font=font, fill=col)
            x += cw

    elif csid == 'clean-underline':
        x = x0
        for c in chars:
            cw = d.textlength(c['t'], font=font)
            on = c.get('s') is not None and c['s'] <= t
            col = fg if on else muted
            d.text((x, cy), c['t'], font=font, fill=col)
            if on and c.get('kw'):
                d.rectangle([x, cy + ch_h + 10, x + cw, cy + ch_h + 16], fill=acc)
            x += cw

    elif csid == 'marker-box':
        x = x0
        for c in chars:
            cw = d.textlength(c['t'], font=font)
            on = c.get('s') is not None and c['s'] <= t
            if on and c.get('kw'):
                d.rectangle([x - 2, cy + int(ch_h * 0.45), x + cw + 2, cy + ch_h + 8], fill=(254, 240, 138))
                col = (200, 16, 46)
            else:
                col = fg if on else muted
            d.text((x, cy), c['t'], font=font, fill=col)
            x += cw

    elif csid == 'cinema-sub':
        d.rounded_rectangle([x0 - 32, cy - 14, x0 + total + 32, cy + ch_h + 18], radius=12, fill=(18, 19, 25))
        x = x0
        for c in chars:
            on = c.get('s') is not None and c['s'] <= t
            col = acc if (on and c.get('kw')) else ((248, 250, 252) if on else (140, 148, 165))
            d.text((x, cy), c['t'], font=font, fill=col)
            x += d.textlength(c['t'], font=font)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default='config.json')
    ap.add_argument('--segments', default='segments.json')
    ap.add_argument('--timing', default='build/voice/timing.json')
    ap.add_argument('--captions', default='build/captions.json')
    ap.add_argument('--audio', default='build/voice/voice.wav')
    ap.add_argument('--out', default='build/render.mp4')
    ap.add_argument('--style', default='', help=f'visual style: {", ".join(STYLES)}')
    ap.add_argument('--caption-style', default='', help=f'caption style: {", ".join(CAPTION_STYLES)}')
    ap.add_argument('--cover-frames', type=int, default=3)
    ap.add_argument('--max-seconds', type=float, default=0, help='render only the first N seconds (preview)')
    a = ap.parse_args()

    cfg = load_config(a.config)
    W, H, FPS = int(cfg['width']), int(cfg['height']), int(cfg['fps'])
    is_land = W >= H
    sid, st, csid = resolve_style(cfg, a.style, a.caption_style)
    print(f'[render_pillow] {W}x{H}@{FPS} style={sid} ({st["name"]}) caption={csid}')

    fp = find_font(cfg['font'])
    F = lambda s: ImageFont.truetype(fp, s)
    fonts = {
        'small': F(30 if is_land else 34),
        'card': F(72 if is_land else 84),
        'metric': F(46 if is_land else 54),
        'cover': F(116 if is_land else 140),
        'cap': F(54 if is_land else 60),
        'cap_sm': F(42 if is_land else 48),
    }

    segs = load_json(a.segments)
    tm = {t['id']: t for t in load_json(a.timing)}
    caps = load_json(a.captions)
    dur = max(t['end'] for t in tm.values()) + 0.15
    if a.max_seconds:
        dur = min(dur, a.max_seconds)
    n = int(round(dur * FPS))

    avatar_size = 112 if is_land else 128
    avatar_im = load_avatar(cfg.get('avatar', ''), avatar_size)

    title = cfg['cover_title'] or segs[0].get('cover', segs[0]['text'])
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           '-i', a.audio, '-t', f'{dur:.3f}', '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
           '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', a.out]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)

    cover_dir = os.path.join(os.path.dirname(os.path.abspath(a.out)), 'cover')
    opening_png = os.path.join(cover_dir, 'cover-opening.png')
    cover_3x4_png = os.path.join(cover_dir, 'cover-3x4.png')
    if not os.path.isfile(opening_png) or not os.path.isfile(cover_3x4_png):
        try:
            from render_video_cover import render_cover_pair
            t_lines = [x.strip() for x in str(title).replace('\n', '|').split('|') if x.strip()]
            if len(t_lines) == 1 and len(t_lines[0]) > 9:
                mid = len(t_lines[0]) // 2
                t_lines = [t_lines[0][:mid], t_lines[0][mid:]]
            brief = {
                'kicker': cfg.get('cover_kicker', 'HUIXIN · AI STUDIO'),
                'brand': cfg.get('cover_brand', ''),
                'title_lines': t_lines[:3],
                'subtitle': cfg.get('cover_sub', ''),
                'metric': cfg.get('cover_metric', ''),
                'theme': cfg.get('cover_theme') or st['cover_theme'],
                'layout': cfg.get('cover_layout', ''),
            }
            render_cover_pair(brief, cover_dir, dpr=2)
        except Exception as e:
            print('warn: render_video_cover fallback to pillow:', e, file=sys.stderr)

    bg = hexrgb(st['bg'])
    fg = hexrgb(st['fg'])
    acc = hexrgb(st['accent'])

    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    cover = None
    for i in range(n):
        t = i / FPS
        if i < a.cover_frames:
            if cover is None:
                src_cov = opening_png if (is_land and os.path.isfile(opening_png)) else (cover_3x4_png if os.path.isfile(cover_3x4_png) else None)
                if src_cov:
                    im = Image.open(src_cov).convert('RGB').resize((W, H), Image.LANCZOS)
                else:
                    im = Image.new('RGB', (W, H), bg); d = ImageDraw.Draw(im)
                    d.rectangle([80, int(H * 0.25), 102, int(H * 0.62)], fill=acc)
                    y = int(H * 0.27)
                    for ln in wrap(d, title, fonts['cover'], W - 260)[:3]:
                        d.text((140, y), ln, font=fonts['cover'], fill=fg); y += int(fonts['cover'].size * 1.25)
                cover = im.tobytes()
            p.stdin.write(cover)
            continue

        im = Image.new('RGB', (W, H), bg)
        d = ImageDraw.Draw(im)
        draw_background(im, d, W, H, t, st)

        # Top progress bar
        d.rectangle([0, 0, int(W * t / dur), 8], fill=acc)

        # Active segment lookup
        seg_idx = 0
        for idx_s, s in enumerate(segs):
            if tm[s['id']]['start'] <= t:
                seg_idx = idx_s
        seg = segs[seg_idx]
        k = min(1.0, (t - tm[seg['id']]['start']) * FPS / 10.0)

        draw_visual_card(im, d, W, H, is_land, seg, seg_idx, len(segs), k, st, fonts, cfg)

        # Optional circular avatar PIP badge
        if avatar_im is not None:
            ax = W - (int(W * 0.08) if is_land else 80) - avatar_size
            ay = int(H * 0.055) if is_land else 155
            pulse = int(4 + 3 * math.sin(t * 3.0))
            d.ellipse([ax - pulse, ay - pulse, ax + avatar_size + pulse, ay + avatar_size + pulse], outline=acc, width=4)
            im.paste(avatar_im, (ax, ay), avatar_im)

        cb = next((c for c in caps if c['start'] <= t < c['end']), None)
        draw_caption(d, W, H, is_land, t, cb, st, csid, fonts['cap'], fonts['cap_sm'])

        p.stdin.write(im.tobytes())

    p.stdin.close()
    sys.exit(p.wait())


if __name__ == '__main__':
    main()
