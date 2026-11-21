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
        'width': 1920, 'height': 1080, 'fps': 30,
        'style': 'huixin-red', 'caption_style': '', 'avatar': '',
        'brand_label': 'HUIXIN · AI STUDIO',
        'voicebox_url': 'http://127.0.0.1:17493', 'voicebox_profile_id': '', 'language': 'zh',
        'min_gap': 0.28, 'max_gap': 0.45, 'seg_gap': 0.20, 'chars_per_sec': 5.5,
        'adaptive_vad': True, 'semantic_pauses': True,
        'caption_max_chars': 14, 'font': '', 'accent': '#C8102E', 'cover_title': '',
        'cover_kicker': 'HUIXIN · AI STUDIO', 'cover_brand': '', 'cover_sub': '',
        'cover_metric': '', 'cover_theme': 'swiss_dark', 'cover_layout': '',
        'loudness_target': -14.0,
    }
    if path and os.path.exists(path):
        cfg.update(load_json(path))
    env = {'VOICEBOX_URL': 'voicebox_url', 'VOICEBOX_PROFILE_ID': 'voicebox_profile_id',
           'THV_FONT': 'font', 'THV_FPS': 'fps',
           'THV_STYLE': 'style', 'STYLE': 'style',
           'THV_CAPTION_STYLE': 'caption_style', 'CAPTION_STYLE': 'caption_style'}
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


def otsu_quiet_runs(x, sr=SR, margin_db=10.0, min_len=0.05):
    """Otsu 自适应双阈值静音检测：保住轻声起音与尾音余韵，不随长停顿比例漂移。"""
    hop = int(sr * 0.01)
    n = len(x) // hop
    if n < 10:
        return quiet_runs(x, sr=sr, min_len=min_len)
    rms = np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    db = 20.0 * np.log10(rms + 1e-9)
    p_lo, p_hi = np.percentile(db, 1), np.percentile(db, 99.5)
    if p_hi - p_lo < 3.0:
        return quiet_runs(x, sr=sr, min_len=min_len)
    clipped = np.clip(db, p_lo, p_hi)
    hist, edges = np.histogram(clipped, bins=100, range=(p_lo, p_hi))
    centers = 0.5 * (edges[:-1] + edges[1:])
    w0 = np.cumsum(hist).astype(np.float64)
    w1 = w0[-1] - w0
    s_all = float(np.sum(hist * centers))
    s0 = np.cumsum(hist * centers)
    m0 = s0 / np.maximum(w0, 1.0)
    m1 = (s_all - s0) / np.maximum(w1, 1.0)
    otsu = float(centers[int(np.argmax(w0 * w1 * (m0 - m1) ** 2))])
    q_frames = db[db <= otsu]
    floor = float(np.median(q_frames)) if len(q_frames) else float(p_lo)
    high_thr = max(otsu, floor + margin_db)
    low_thr = max(high_thr - 6.0, floor + 6.0)

    # 先找有声帧，再向两侧按 low_thr 外延（连续 3 帧低于 low_thr 才止步）
    voiced = (db > high_thr).copy()
    i = 0
    while i < n:
        if voiced[i]:
            j = i
            while j < n and voiced[j]:
                j += 1
            # 左外延
            p, streak = i - 1, 0
            while p >= 0 and streak < 3:
                if db[p] > low_thr:
                    voiced[p] = True
                    streak = 0
                else:
                    streak += 1
                p -= 1
            # 右外延
            p, streak = j, 0
            while p < n and streak < 3:
                if db[p] > low_thr:
                    voiced[p] = True
                    streak = 0
                else:
                    streak += 1
                p += 1
            i = max(j, p)
        else:
            i += 1

    runs, i = [], 0
    while i < n:
        if not voiced[i]:
            j = i
            while j < n and not voiced[j]:
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
