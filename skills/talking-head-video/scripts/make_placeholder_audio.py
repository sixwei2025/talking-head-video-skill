#!/usr/bin/env python3
"""No-TTS path: build a silent (or quiet tone) narration track and an estimated
timing.json from character counts, so captions + render can be tested end to end.
"""
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import SR, load_config, load_json, save_json, write_wav, visible_chars

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default='config.json')
    ap.add_argument('--segments', default='segments.json')
    ap.add_argument('--out', default='build/voice')
    ap.add_argument('--tone', action='store_true', help='quiet 220 Hz tone instead of silence (lets silencedetect pass)')
    a = ap.parse_args()
    cfg = load_config(a.config); cps = cfg['chars_per_sec']
    pos = 0.08; timing = []
    for s in load_json(a.segments):
        units = visible_chars(s['text'])
        L = max(0.6, len(units) / cps); b = np.linspace(pos, pos + L, len(units) + 1)
        timing.append({'id': s['id'], 'start': round(pos, 3), 'end': round(pos + L, 3),
                       'units': [{'t': u, 's': round(b[i], 3), 'e': round(b[i + 1], 3)} for i, u in enumerate(units)]})
        pos += L + cfg['seg_gap']
    dur = pos - cfg['seg_gap'] + 0.15
    t = np.arange(int(dur * SR)) / SR
    y = 0.05 * np.sin(2 * np.pi * 220 * t) if a.tone else np.zeros_like(t)
    write_wav(os.path.join(a.out, 'voice.wav'), y.astype(np.float32))
    save_json(timing, os.path.join(a.out, 'timing.json'))
    print('placeholder', round(dur, 2), 's')

if __name__ == '__main__':
    main()
