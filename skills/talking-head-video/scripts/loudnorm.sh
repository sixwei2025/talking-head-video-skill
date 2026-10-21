#!/usr/bin/env bash
# Two-pass loudness normalisation to -14 LUFS / -1.5 dBTP, video stream copied.
# usage: scripts/loudnorm.sh in.mp4 out.mp4 [target_lufs]
set -euo pipefail
IN=$1; OUT=$2; T=${3:--14}
J=$(ffmpeg -hide_banner -nostats -i "$IN" -af "loudnorm=I=$T:TP=-1.5:LRA=11:print_format=json" -vn -f null - 2>&1 | sed -n '/^{/,/^}/p')
g(){ echo "$J" | python3 -c "import json,sys;print(json.load(sys.stdin)['$1'])"; }
ffmpeg -y -v error -i "$IN" -c:v copy -af "loudnorm=I=$T:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true" -c:a aac -b:a 192k -ar 48000 -movflags +faststart "$OUT"
