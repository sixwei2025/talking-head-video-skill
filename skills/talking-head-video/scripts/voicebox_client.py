#!/usr/bin/env python3
"""Minimal client for a local Voicebox-compatible TTS service.

Config (env overrides config.json):
  VOICEBOX_URL         default http://127.0.0.1:17493
  VOICEBOX_PROFILE_ID  voice profile id (list with --profiles); never commit it

Rules: each segment is generated ONCE; after ASR check, regenerate only the
segments listed with --only. Existing files are skipped unless --force.
"""
import argparse, json, os, sys, time, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_config, load_json

def req(url, method='GET', body=None, timeout=60, want_json=True):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if want_json else raw)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors='replace')

def synth(base, profile_id, text, language='zh', seed=None, timeout=600):
    body = {'profile_id': profile_id, 'text': text, 'language': language, 'normalize': True}
    if seed is not None:
        body['seed'] = seed
    code, res = req(base + '/generate/stream', 'POST', body, timeout=timeout, want_json=False)
    if code == 200:
        return res
    if code not in (400, 404, 405):
        raise RuntimeError(f'/generate/stream -> {code} {str(res)[:200]}')
    # async fallback: POST /generate, poll /history/{id}, fetch /audio/{id}
    code, job = req(base + '/generate', 'POST', body, timeout=120)
    if code != 200:
        raise RuntimeError(f'/generate -> {code} {job}')
    gid, t0 = job['id'], time.time()
    while time.time() - t0 < timeout:
        code, h = req(f'{base}/history/{gid}', timeout=30)
        st = (h or {}).get('status') if isinstance(h, dict) else None
        if st in ('completed', 'done', None) and code == 200:
            code, audio = req(f'{base}/audio/{gid}', timeout=120, want_json=False)
            if code == 200:
                return audio
        if st in ('failed', 'error'):
            raise RuntimeError(f'generation failed: {h}')
        time.sleep(2)
    raise TimeoutError('generation timed out')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', default='config.json')
    ap.add_argument('--segments', default='segments.json')
    ap.add_argument('--out', default='build/voice/takes')
    ap.add_argument('--profiles', action='store_true', help='list voice profiles and exit')
    ap.add_argument('--only', default='', help='comma separated segment ids to (re)generate')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--seed', type=int, default=None)
    ap.add_argument('--max-failures', type=int, default=3, help='stop after N consecutive failures')
    a = ap.parse_args()
    cfg = load_config(a.config); base = cfg['voicebox_url'].rstrip('/')
    code, h = req(base + '/health', timeout=10)
    if code != 200:
        sys.exit(f'Voicebox not reachable at {base} ({code}). Start the service or use make_placeholder_audio.py')
    if a.profiles:
        _, p = req(base + '/profiles')
        for x in p if isinstance(p, list) else p.get('profiles', []):
            print(x.get('id'), x.get('name'), x.get('language'))
        return
    pid = cfg['voicebox_profile_id']
    if not pid:
        sys.exit('Set VOICEBOX_PROFILE_ID (or voicebox_profile_id in config.json)')
    only = set(filter(None, a.only.split(',')))
    os.makedirs(a.out, exist_ok=True); fails = 0
    for s in load_json(a.segments):
        if only and s['id'] not in only:
            continue
        f = os.path.join(a.out, s['id'] + '.wav')
        if os.path.exists(f) and not (a.force or only):
            continue
        t0 = time.time()
        try:
            audio = synth(base, pid, s.get('tts', s['text']), cfg['language'], a.seed)
        except Exception as e:  # noqa
            fails += 1; print('FAIL', s['id'], e, flush=True)
            if fails >= a.max_failures:
                sys.exit('too many consecutive failures, stopping (check the service, do not hammer it)')
            continue
        fails = 0
        open(f, 'wb').write(audio)
        print('ok', s['id'], f'{time.time() - t0:.1f}s', flush=True)

if __name__ == '__main__':
    main()
