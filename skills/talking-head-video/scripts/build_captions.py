#!/usr/bin/env python3
"""timing.json + segments.json -> captions.json (word-level highlight blocks).

Each block <= caption_max_chars visible units, split at punctuation first.
Display text comes from segment 'text' (what the screen shows); keywords from
segment 'keywords' are flagged for accent colour.
"""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_config, load_json, save_json

PUNCT = '，。？！、；：,.?!;:—…'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default='config.json')
    ap.add_argument('--segments', default='segments.json')
    ap.add_argument('--timing', default='build/voice/timing.json')
    ap.add_argument('--out', default='build/captions.json')
    a = ap.parse_args()
    cfg = load_config(a.config); mx = cfg['caption_max_chars']
    tm = {t['id']: t for t in load_json(a.timing)}
    blocks = []
    for s in load_json(a.segments):
        units = tm[s['id']]['units']; k = 0; cur = []; n = 0
        kws = s.get('keywords', [])
        toks = re.findall(r'[A-Za-z0-9.%]+|\s+|.', s['text'])
        def flush():
            nonlocal cur, n
            if any(c.get('s') is not None for c in cur):
                txt = ''.join(c['t'] for c in cur).strip(PUNCT + ' ')
                hit = set()
                for kw in kws:
                    for m in re.finditer(re.escape(kw), ''.join(c['t'] for c in cur)):
                        hit.update(range(m.start(), m.end()))
                off = 0
                for c in cur:
                    c['kw'] = off in hit; off += len(c['t'])
                ts = [c for c in cur if c.get('s') is not None]
                blocks.append({'seg': s['id'], 'text': txt, 'start': ts[0]['s'], 'end': ts[-1]['e'], 'chars': cur})
            cur, n = [], 0
        for tk in toks:
            if tk.isspace():
                cur.append({'t': ' '}); continue
            if tk in PUNCT:
                cur.append({'t': tk}) if tk not in '，。,.' else None
                if n >= mx * 0.5 or tk in '。？！?!':
                    flush()
                continue
            if n >= mx:
                flush()
            u = units[k] if k < len(units) else {'s': None, 'e': None}; k += 1
            cur.append({'t': tk, 's': u['s'], 'e': u['e']}); n += 1
        flush()
    for i in range(len(blocks) - 1):  # hold each block until the next starts (no caption flicker)
        blocks[i]['end'] = max(blocks[i]['end'], blocks[i + 1]['start'])
    save_json(blocks, a.out)
    long = [b['text'] for b in blocks if len(b['text']) > mx + 2]
    print(len(blocks), 'caption blocks', '| over budget:', long or 'none')

if __name__ == '__main__':
    main()
