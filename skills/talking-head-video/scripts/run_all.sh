#!/usr/bin/env bash
# One-shot pipeline, safe to run in the background:
#   (voice | placeholder) -> captions -> render -> loudnorm -> cover png -> QC -> deliver/
# Writes build/DONE or build/FAILED.  Run from the project directory:
#   bash path/to/scripts/run_all.sh            # uses existing build/voice or takes
#   PLACEHOLDER=1 bash path/to/scripts/run_all.sh   # no TTS, silent track
# Env: SLUG (output name), PREVIEW_SECONDS (render only first N s), PY (python)
set -eEuo pipefail
S="$(cd "$(dirname "$0")" && pwd)"; PY=${PY:-python3}; SLUG=${SLUG:-video}
mkdir -p build deliver; rm -f build/DONE build/FAILED
trap 'echo "failed at line $LINENO" > build/FAILED' ERR
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a build/run.log; }
if [ "${PLACEHOLDER:-0}" = 1 ]; then
  log placeholder audio; $PY "$S/make_placeholder_audio.py" ${TONE:+--tone}
elif [ ! -f build/voice/voice.wav ]; then
  log assemble voice; $PY "$S/assemble_voice.py"
fi
log captions; $PY "$S/build_captions.py"
log render; $PY "$S/render_pillow.py" --out build/render.mp4 ${PREVIEW_SECONDS:+--max-seconds $PREVIEW_SECONDS} 2>>build/run.log
if [ "${PLACEHOLDER:-0}" = 1 ] && [ -z "${TONE:-}" ]; then cp build/render.mp4 build/final.mp4; QCF=--skip-audio
else log loudnorm; bash "$S/loudnorm.sh" build/render.mp4 build/final.mp4; QCF=; fi
if [ -f build/cover/cover-3x4.jpg ]; then
  cp build/cover/cover-3x4.jpg build/cover-3x4.jpg
  cp build/cover/cover-3x4.png build/cover.png
  cp build/cover/cover-3x4.jpg "deliver/$SLUG-cover-3x4.jpg"
else
  ffmpeg -y -v error -i build/final.mp4 -frames:v 1 build/cover.png
fi
[ -f build/cover/cover-opening.png ] && cp build/cover/cover-opening.png "deliver/$SLUG-cover-16x9.png" || true
log qc; $PY "$S/qc.py" build/final.mp4 --report build/qc.txt $QCF || { log "QC failed, see build/qc.txt"; false; }
cp build/final.mp4 "deliver/$SLUG.mp4"
[ -f 发布说明.md ] && cp 发布说明.md deliver/ || true
log "done -> deliver/"; touch build/DONE
