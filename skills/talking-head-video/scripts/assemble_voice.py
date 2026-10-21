#!/usr/bin/env python3
"""Concatenate segment takes into one narration track.

- trims leading/trailing silence of each take
- compresses internal pauses longer than max_gap down to min_gap (>=0.28 s, never shorter)
- inserts seg_gap between segments
- writes voice.wav + timing.json (per-unit timestamps; from asr.json if present,
  otherwise distributed by voiced duration)
"""
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import SR, load_config, load_json, save_json, read_audio, write_wav, quiet_runs, visible_chars

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default='config.json')
    ap.add_argument('--segments', default='segments.json')
    ap.add_argument('--takes', default='build/voice/takes')
    ap.add_argument('--asr', default='build/voice/asr.json')
    ap.add_argument('--out', default='build/voice')
    a = ap.parse_args()
    cfg = load_config(a.config); mn = max(0.28, cfg['min_gap']); mx = max(mn, cfg['max_gap'])
    asr = load_json(a.asr) if os.path.exists(a.asr) else {}
    out = [np.zeros(int(0.08 * SR), np.float32)]; pos = 0.08; timing = []
    for s in load_json(a.segments):
        x = read_audio(os.path.join(a.takes, s['id'] + '.wav'))
        runs = quiet_runs(x, min_len=0.05)
        st = runs[0][1] if runs and runs[0][0] == 0 else 0.0
        en = runs[-1][0] if runs and runs[-1][1] >= len(x) / SR - 0.011 else len(x) / SR
        st = max(0, st - 0.03); en = min(len(x) / SR, en + 0.06)
        cuts = []
        for r0, r1 in runs:
            if r0 > st and r1 < en and r1 - r0 > mx:
                m, h = (r0 + r1) / 2, (r1 - r0 - mn) / 2
                cuts.append((m - h, m + h))
        keep, prev = [], st
        for c0, c1 in cuts:
            keep.append((prev, c0)); prev = c1
        keep.append((prev, en))
        seg = np.concatenate([x[int(p * SR):int(q * SR)] for p, q in keep])
        fl = int(0.01 * SR); seg[:fl] *= np.linspace(0, 1, fl); seg[-fl:] *= np.linspace(1, 0, fl)
        L = len(seg) / SR
        def tmap(t):
            r = sum((c1 - c0) if t >= c1 else max(0, t - c0) for c0, c1 in cuts)
            return min(max(pos + t - st - r, pos), pos + L)
        units = visible_chars(s['text'])
        if s['id'] in asr and asr[s['id']]['words']:
            # spread ASR word spans over script units in order (robust, approximate)
            ws = asr[s['id']]['words']; t0s = np.linspace(0, 1, len(units) + 1)
            spans = np.interp(t0s, np.linspace(0, 1, len(ws) + 1), [ws[0][1]] + [w[2] for w in ws])
            times = [(tmap(spans[i]), tmap(spans[i + 1])) for i in range(len(units))]
        else:
            b = np.linspace(pos, pos + L, len(units) + 1)
            times = [(b[i], b[i + 1]) for i in range(len(units))]
        timing.append({'id': s['id'], 'start': round(pos, 3), 'end': round(pos + L, 3),
                       'units': [{'t': u, 's': round(p, 3), 'e': round(q, 3)} for u, (p, q) in zip(units, times)]})
        out += [seg, np.zeros(int(cfg['seg_gap'] * SR), np.float32)]; pos += L + cfg['seg_gap']
    y = np.concatenate(out)
    y = y[:int((pos - cfg['seg_gap'] + 0.15) * SR)]
    y *= 0.89 / max(1e-6, np.abs(y).max())
    write_wav(os.path.join(a.out, 'voice.wav'), y)
    save_json(timing, os.path.join(a.out, 'timing.json'))
    print('voice.wav', round(len(y) / SR, 2), 's,', len(timing), 'segments')

if __name__ == '__main__':
    main()
