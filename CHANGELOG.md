# 更新日志

## v1.1.0 · 2026-11-18

- 新增统一多风格渲染引擎（`scripts/styles.py`、`scripts/render_pillow.py` 与 `templates/studio.html`），支持 **6 大口播视觉风格 × 6 大单行字幕样式**（`huixin-red` / `dark-tech` / `dazibao-impact` / `swiss-editorial` / `paper-sketch` / `cinematic-apple`）。
- 原生支持 **16:9 横屏（`1920×1080`）** 与 **9:16 竖屏（`1080×1920`）** 自适应排版，新增可选右上角圆形头像画中画（`avatar`）。
- `run_all.sh` 与 `render_html.mjs` 支持通过 `STYLE` / `CAPTION_STYLE` / `RENDERER=html` 一键切换风格与渲染引擎。

## v1.0.1 · 2026-11-15

- `generate_video_covers.py` 与 `render_video_cover.py` 移除 Homebrew Python 与个人绝对路径依赖，支持 Windows / macOS / Linux 跨平台运行。

## v1.0.0 · 2026-11-13

- 建立可追踪的版本记录，README、Skill 文件和 Git 标签保持一致。
- 后续功能变化、修复和兼容性调整会持续记录在本文件。

