#!/usr/bin/env python3
"""ffmpeg-based QC: format, black frames, frozen frames, silence, loudness,
cover-first-frame. Writes a text report; exit code 1 if any hard check fails.

Defaults (override by flags):
  blackdetect   d>=0.10s pix_th=0.05 (keep backgrounds above ~#26262e)           -> fail
  freezedetect  n=-60dB d>=2.0s                -> fail (static talking-head shots: raise --freeze-d)
  silencedetect n=-40dB d>=0.30s (inside body) -> fail
  loudness      integrated -16..-12 LUFS, true peak <= -1.0 dBTP
  tail          last speech -> end <= 0.30s (warn)
"""
import argparse, json, re, subprocess, sys

def ff(args):
    return subprocess.run(['ffmpeg', '-hide_banner', '-nostats'] + args, capture_output=True, text=True).stderr

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('--report', default=None)
    ap.add_argument('--width', type=int, default=1080)
    ap.add_argument('--height', type=int, default=1920)
    ap.add_argument('--freeze-d', type=float, default=2.0)
    ap.add_argument('--silence-d', type=float, default=0.30)
    ap.add_argument('--lufs-min', type=float, default=-16.0)
    ap.add_argument('--lufs-max', type=float, default=-12.0)
    ap.add_argument('--skip-audio', action='store_true', help='placeholder/silent audio: only report audio checks')
    a = ap.parse_args()
    v = a.video; out = []; fail = []
    pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,codec_name,width,height,r_frame_rate',
                                    '-of', 'json', v], capture_output=True, text=True).stdout)
    dur = float(pr['format']['duration']); vs = [s for s in pr['streams'] if s['codec_type'] == 'video'][0]
    out.append(f"format: {vs['codec_name']} {vs['width']}x{vs['height']} {vs['r_frame_rate']} dur={dur:.2f}s audio={'yes' if any(s['codec_type']=='audio' for s in pr['streams']) else 'NO'}")
    if (vs['width'], vs['height']) != (a.width, a.height):
        fail.append('resolution')
    bl = re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', ff(['-i', v, '-vf', 'blackdetect=d=0.1:pix_th=0.05', '-an', '-f', 'null', '-']))
    out.append(f'blackdetect: {bl or "none"}'); fail += ['black'] if bl else []
    fr = ff(['-i', v, '-vf', f'freezedetect=n=-60dB:d={a.freeze_d}', '-an', '-f', 'null', '-'])
    fz = list(zip(re.findall(r'freeze_start: ([\d.]+)', fr), re.findall(r'freeze_end: ([\d.]+)', fr) + ['end']))
    out.append(f'freezedetect d>={a.freeze_d}: {fz or "none"}'); fail += ['freeze'] if fz else []
    si = ff(['-i', v, '-af', f'silencedetect=n=-40dB:d={a.silence_d}', '-vn', '-f', 'null', '-'])
    st = [float(x) for x in re.findall(r'silence_start: ([-\d.]+)', si)]; en = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', si)]
    body = [(round(s, 2), round(en[i], 2) if i < len(en) else 'end') for i, s in enumerate(st) if s > 0.15 and (i < len(en) and en[i] < dur - 0.05)]
    tail = [s for i, s in enumerate(st) if i >= len(en) or en[i] >= dur - 0.05]
    out.append(f'silencedetect -40dB d>={a.silence_d} (body): {body or "none"}')
    out.append(f'tail silence: {round(dur - tail[-1], 2) if tail else 0}s')
    ln = ff(['-i', v, '-af', 'loudnorm=print_format=json', '-vn', '-f', 'null', '-'])
    m = re.search(r'\{[^{}]*"input_i"[^{}]*\}', ln, re.S); I = tp = None
    if m:
        j = json.loads(m.group()); I = float(j['input_i']); tp = float(j['input_tp'])
    out.append(f'loudness: I={I} LUFS  TP={tp} dBTP (target {a.lufs_min}..{a.lufs_max}, TP<=-1)')
    if not a.skip_audio:
        fail += ['silence'] if body else []
        if I is None or not (a.lufs_min <= I <= a.lufs_max) or tp > -1.0:
            fail.append('loudness')
    # cover: first frame should differ strongly from the frame right after cover
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', v, '-vf', 'scale=108:192,format=gray', '-frames:v', '8', '-f', 'rawvideo', '-'],
                         capture_output=True).stdout
    fs = [raw[i:i + 108 * 192] for i in range(0, len(raw), 108 * 192)]
    if len(fs) >= 5:
        diff = sum(abs(x - y) for x, y in zip(fs[0], fs[4])) / len(fs[0])
        out.append(f'cover: frame0 vs frame4 mean diff {diff:.1f} (expect > 3: cover is a distinct first frame)')
    res = 'PASS' if not fail else 'FAIL: ' + ','.join(fail)
    out.append('RESULT: ' + res + (' (audio checks skipped)' if a.skip_audio else ''))
    txt = '\n'.join(out); print(txt)
    if a.report:
        open(a.report, 'w', encoding='utf-8').write(txt + '\n')
    sys.exit(0 if not fail else 1)

if __name__ == '__main__':
    main()
