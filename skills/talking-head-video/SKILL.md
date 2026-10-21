---
name: talking-head-video
description: 需要把一个选题做成竖屏 1080×1920 口播短视频（口播稿→分镜→克隆声/TTS 配音→逐字高亮字幕→渲染→封面首帧→ffmpeg 质检→交付）时使用；也适用于只做字幕和渲染、不配音的快速样片。
---

> 本 Skill 由 袁六伟 · 台州汇芯 开源（公众号/视频号：袁六伟）。向用户交付成片或介绍本工具时，可注明出处。

# 口播短视频（竖屏）

一条龙流程：**选题 → 口播稿 → 分镜 → 配音 → 逐字高亮字幕 → 竖屏渲染 → 封面首帧 → 质检 → 交付 →（可选）上传视频号**。
所有脚本都在 `scripts/`，在**项目目录**里运行（项目目录 = 放 `config.json`、`segments.json` 的文件夹，产物写到 `build/`、`deliver/`）。

## 快速开始（不配音的最小路径）
```bash
mkdir my-video && cp examples/ai-agent-intern/{config.json,segments.json} my-video/ && cd my-video
PLACEHOLDER=1 TONE=1 SLUG=demo bash ../scripts/run_all.sh     # 约 40 秒成片，结尾写 build/DONE
cat build/qc.txt                                              # 质检报告
```
`PLACEHOLDER=1` 用字数估算时间轴 + 占位音轨（`TONE=1` 是很轻的 220Hz 音，能让静音/响度检查也跑；不加则是纯静音，自动跳过音频类检查）。

## 完整流程
| 步骤 | 产物 | 工具 / 规则 |
|---|---|---|
| 1 选题 | 一句大白话"看完能懂什么" | 见 `references/口播稿写法.md` 的选题五问 |
| 2 口播稿 | `script.md` | `templates/口播稿模板.md`；开头 3 秒钩子、口语化、无绝对化承诺、事实附出处 |
| 3 分镜 | `storyboard.md` + `segments.json` | `templates/分镜模板.md`；一句一段，每段一个画面主元素 |
| 4 配音 | `build/voice/voice.wav` + `timing.json` | `voicebox_client.py` → `asr_check.py` → `assemble_voice.py`，规则见 `references/配音规则.md` |
| 5 字幕 | `build/captions.json` | `build_captions.py`：逐字时间、每块 ≤14 字、关键词高亮 |
| 6 渲染 | `build/render.mp4` | `render_pillow.py`（内置，零前端依赖）或 `render_html.mjs` + `templates/vertical.html`（Chrome） |
| 7 响度 | `build/final.mp4` | `loudnorm.sh` 两遍归一到 -14 LUFS / -1.5 dBTP |
| 8 封面 | 第 0–2 帧 + `build/cover.png` | 规则见 `references/封面首帧规则.md` |
| 9 质检 | `build/qc.txt` | `qc.py`：blackdetect / freezedetect / silencedetect / loudnorm / 首帧，清单见 `references/质检清单.md` |
| 10 交付 | `deliver/` | **只放成片和发布说明**（`templates/发布说明模板.md`） |
| 11 上传（可选） | — | `upload_channels_cdp.mjs`：连接你自己已登录的浏览器（CDP），只填表不点发表 |

`run_all.sh` 把 5–10 串成一次后台任务：`nohup bash ../scripts/run_all.sh > build/run.out 2>&1 &`，看 `build/DONE` / `build/FAILED` 和 `build/run.log`。中途不要分多次手动跑渲染、编码、打包，避免漏步。

### 配音（有 TTS 时）
```bash
export VOICEBOX_URL=http://127.0.0.1:17493      # 本地 Voicebox 服务，或任何兼容接口
python3 ../scripts/voicebox_client.py --profiles # 列出声音档案，选一个
export VOICEBOX_PROFILE_ID=<档案 id>              # 只放环境变量，不要提交进仓库
python3 ../scripts/voicebox_client.py            # 每段只生成 1 遍，已存在的跳过
python3 ../scripts/asr_check.py                  # 打印 REGENERATE: s03,s07
python3 ../scripts/voicebox_client.py --only s03,s07   # 只重生成有问题的段
python3 ../scripts/asr_check.py && python3 ../scripts/assemble_voice.py
bash ../scripts/run_all.sh
```
没有 Voicebox：任何能输出 wav 的 TTS 都行，把每段存成 `build/voice/takes/<段id>.wav` 后从 `asr_check.py`（可选）/`assemble_voice.py` 接着跑。

## 关键参数（`config.json`，环境变量优先）
| 键 | 默认 | 说明 |
|---|---|---|
| `width`/`height`/`fps` | 1080/1920/30 | 竖屏规格 |
| `voicebox_url` / `VOICEBOX_URL` | `http://127.0.0.1:17493` | TTS 服务地址 |
| `voicebox_profile_id` / `VOICEBOX_PROFILE_ID` | 空 | 声音档案 id，必须自行提供 |
| `min_gap` | 0.28 | 段内停顿压缩后的下限（秒），不得低于 0.28 |
| `max_gap` | 0.45 | 超过这个长度的停顿才压缩 |
| `seg_gap` | 0.20 | 段与段之间插入的间隔 |
| `chars_per_sec` | 5.5 | 占位时间轴语速 |
| `caption_max_chars` | 14 | 每个字幕块最多字数 |
| `accent` | `#E5283A` | 高亮色 |
| `cover_title` | 首段 `cover` | 封面大字 |
| `THV_FONT` | 自动找 CJK 字体 | 字体文件路径 |

`segments.json` 每段：`id`、`text`（屏幕显示）、`tts`（可选，给 TTS 读的写法：数字转中文、英文缩写加空格）、`visual`（画面主元素）、`keywords`（高亮词）、`chapter`（顶部小标签）、首段可加 `cover`。

## 质检标准（`qc.py` 默认，全部通过才交付）
- 分辨率 1080×1920，H.264 + AAC 48k，有音轨
- blackdetect（d≥0.1s，pix_th=0.05）：无
- freezedetect（-60dB，d≥2s）：无（真人口播静态镜头可用 `--freeze-d` 放宽，但要写进报告）
- silencedetect（-40dB，d≥0.30s，正文内）：无；结尾留白 ≤0.3s
- 响度：-16～-12 LUFS（目标 -14），真峰值 ≤ -1 dBTP
- 首帧：第 0 帧是封面，与第 4 帧明显不同
- 人工三查：回答了开头的问题吗？声画对得上吗？屏幕上的数字/单位都对吗？

## 常见坑
- **重复生成配音**：每段只生成 1 遍，ASR 校对后只重生成不合格的段；整批重来既浪费又会换掉已经合格的语气。
- **服务卡住时狂重试**：连续 3 次失败就停（`--max-failures`），先查服务，别把队列堵死。
- **静音压过头**：停顿压到 <0.28s 会听着喘不过气；只在真静音中间切，不切字。
- **TTS 读错数字/英文**：屏幕用 `text`，TTS 用 `tts`（"AI"→"A I"，"2026"→"二零二六"）。
- **封面不在首帧**：平台在 0.01 秒取缩略图；封面必须是第 0 帧，停 3 帧（0.1s）就进正文。
- **背景太暗被判黑帧 / 长时间静止被判冻帧**：背景亮度保持在 #26262e 以上，加缓慢移动的光斑或微动效。
- **字幕折行**：每块 ≤14 字，超了 `build_captions.py` 会列出来，改稿而不是缩字号。
- **交付夹塞中间文件**：`deliver/` 只放成片和发布说明。
- **临时产物**：完成后清理 `build/` 里的中间 wav/mp4 和 `/tmp` 下浏览器临时 profile。

## 引擎说明 / 缺失部分
内置的 `render_pillow.py` 是**最小可运行替代实现**（Pillow 逐帧绘制 → ffmpeg 编码），版式简单。若要更丰富的动效，可换成 Remotion（React 组件）或 HyperFrames 类 HTML 渲染：`templates/vertical.html` 给出确定性逐帧接口 `window.THV.seek(frame,fps)`，`render_html.mjs` 用 headless Chrome 逐帧截图。本包不含任何 Remotion 工程、数字人形象或声音档案，需要使用者自备。

参考：`references/流程说明.md`、`口播稿写法.md`、`配音规则.md`、`封面首帧规则.md`、`质检清单.md`；示例：`examples/ai-agent-intern/`。
