#!/usr/bin/env python3
"""Optional: transcribe each take with faster-whisper, compare with script text,
print segments whose error rate exceeds the threshold (regenerate only those),
and save word timestamps for caption alignment.

pip install faster-whisper pypinyin   (model downloads to $THV_MODEL_DIR or HF cache)
"""
import argparse, glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_json, save_json

def norm(s):
    return re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', s).lower()

def edit(a, b):
    d = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        p, d[0] = d[0], i
        for j, cb in enumerate(b, 1):
            p, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, p + (ca != cb))
    return d[-1] / max(1, len(b))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--segments', default='segments.json')
    ap.add_argument('--takes', default='build/voice/takes')
    ap.add_argument('--out', default='build/voice/asr.json')
    ap.add_argument('--model', default='small')
    ap.add_argument('--max-cer', type=float, default=0.05)
    a = ap.parse_args()
    from faster_whisper import WhisperModel
    try:
        from pypinyin import lazy_pinyin
        py = lambda s: lazy_pinyin(s)  # compare by pinyin: homophones are fine for TTS
    except ImportError:
        py = list
    m = WhisperModel(a.model, device='cpu', compute_type='int8', download_root=os.environ.get('THV_MODEL_DIR'))
    res, bad = {}, []
    for s in load_json(a.segments):
        f = os.path.join(a.takes, s['id'] + '.wav')
        if not os.path.exists(f):
            bad.append(s['id']); continue
        segs, _ = m.transcribe(f, language='zh', word_timestamps=True, condition_on_previous_text=False)
        words = [[w.word, round(w.start, 3), round(w.end, 3)] for g in segs for w in g.words]
        txt = ''.join(w[0] for w in words)
        cer = edit(py(norm(txt)), py(norm(s.get('tts', s['text']))))
        res[s['id']] = {'asr': txt, 'cer': round(cer, 3), 'words': words}
        flag = cer > a.max_cer
        if flag:
            bad.append(s['id'])
        print(('BAD ' if flag else 'ok  ') + s['id'], round(cer, 3), txt, flush=True)
    save_json(res, a.out)
    print('REGENERATE:', ','.join(bad) if bad else 'none')

if __name__ == '__main__':
    main()
