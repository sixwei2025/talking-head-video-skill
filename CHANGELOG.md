# 更新日志

## v1.2.0 · 2026-11-21

- **Otsu 自适应双阈值与标点语义分级停顿**：升级 `scripts/common.py`（新增 `otsu_quiet_runs`）与 `scripts/assemble_voice.py`，保护轻声起音与尾音余韵，按逗号/句号/换段自动分级压缩停顿，支持 `segments.json` 单段 `pause_after` 配置。
- **动态开头预审与分轨逃生舱**：`scripts/run_all.sh` 新增 `EXPORT_STEMS=1`（同步导出纯净画面轨 + 独立人声 WAV + 时间轴 JSON 供剪映二次精修），并强化 `PREVIEW_SECONDS=10` 动态开头预审闭环。
- **表格化改片与实拍避坑**：新增 `templates/剪辑意见模板.md`（时间码 + 截图 + 局部/全局标签），补充真人口播调色参考图、克隆音色少堆语气词与数字人首帧照三铁律。

## v1.1.0 · 2026-11-18

- 新增统一多风格渲染引擎（`scripts/styles.py`、`scripts/render_pillow.py` 与 `templates/studio.html`），支持 **6 大口播视觉风格 × 6 大单行字幕样式**（`huixin-red` / `dark-tech` / `dazibao-impact` / `swiss-editorial` / `paper-sketch` / `cinematic-apple`）。
- 原生支持 **16:9 横屏（`1920×1080`）** 与 **9:16 竖屏（`1080×1920`）** 自适应排版，新增可选右上角圆形头像画中画（`avatar`）。
- `run_all.sh` 与 `render_html.mjs` 支持通过 `STYLE` / `CAPTION_STYLE` / `RENDERER=html` 一键切换风格与渲染引擎。

## v1.0.1 · 2026-11-15

- `generate_video_covers.py` 与 `render_video_cover.py` 移除 Homebrew Python 与个人绝对路径依赖，支持 Windows / macOS / Linux 跨平台运行。

## v1.0.0 · 2026-11-13

- 建立可追踪的版本记录，README、Skill 文件和 Git 标签保持一致。
- 后续功能变化、修复和兼容性调整会持续记录在本文件。

