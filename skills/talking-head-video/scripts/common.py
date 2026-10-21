"""Shared helpers: config loading, wav IO via ffmpeg, simple silence analysis."""
import json, os, subprocess, wave
import numpy as np

SR = 48000

def load_json(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)

def save_json(obj, p):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)

def load_config(path=None):
    """Read project config.json; environment variables override file values."""
    cfg = {
        'width': 1080, 'height': 1920, 'fps': 30,
        'voicebox_url': 'http://127.0.0.1:17493', 'voicebox_profile_id': '', 'language': 'zh',
        'min_gap': 0.28, 'max_gap': 0.45, 'seg_gap': 0.20, 'chars_per_sec': 5.5,
        'caption_max_chars': 14, 'font': '', 'accent': '#E5283A', 'cover_title': '',
        'loudness_target': -14.0,
    }
    if path and os.path.exists(path):
        cfg.update(load_json(path))
    env = {'VOICEBOX_URL': 'voicebox_url', 'VOICEBOX_PROFILE_ID': 'voicebox_profile_id',
           'THV_FONT': 'font', 'THV_FPS': 'fps'}
    for k, v in env.items():
        if os.environ.get(k):
            cfg[v] = type(cfg[v])(os.environ[k]) if not isinstance(cfg[v], str) else os.environ[k]
    return cfg

def read_audio(path, sr=SR):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 's16le', '-ac', '1', '-ar', str(sr), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768

def write_wav(path, x, sr=SR):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

def quiet_runs(x, sr=SR, thresh_db=-40.0, min_len=0.1):
    """Return [(start_s, end_s)] of runs quieter than thresh_db (10 ms RMS windows)."""
    hop = int(sr * 0.01)
    n = len(x) // hop
    if n == 0:
        return []
    rms = np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    q = 20 * np.log10(rms) < thresh_db
    runs, i = [], 0
    while i < n:
        if q[i]:
            j = i
            while j < n and q[j]:
                j += 1
            if (j - i) * 0.01 >= min_len:
                runs.append((i * 0.01, j * 0.01))
            i = j
        else:
            i += 1
    return runs

def visible_chars(text):
    """Units that get a timestamp: each CJK char, each latin word / number."""
    import re
    return re.findall(r'[A-Za-z0-9.%]+|[\u4e00-\u9fff]', text)
