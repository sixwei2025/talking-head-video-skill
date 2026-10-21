# 依赖

| 组件 | 版本 | 用途 | 必需 |
|---|---|---|---|
| Python | ≥ 3.10（在 3.13 上测试） | 全部 `scripts/*.py` | 是 |
| numpy、Pillow | 见 `requirements.txt` | 音频处理、逐帧绘制 | 是 |
| ffmpeg / ffprobe | ≥ 5.0（需 libx264、aac、loudnorm、blackdetect、freezedetect、silencedetect） | 编码、响度、质检 | 是 |
| CJK 字体 | 例如 Noto Sans CJK SC Bold | 字幕和画面文字；`fc-list` 自动查找或设 `THV_FONT` | 是 |
| Node.js | ≥ 18（在 20 上测试） | `render_html.mjs`、`upload_channels_cdp.mjs` | 否 |
| puppeteer-core | ^23（`npm install`） | 控制 Chrome | 否 |
| Chrome / Chromium | 近期稳定版，`CHROME_PATH` 指向可执行文件 | HTML 渲染；上传脚本连接已登录浏览器 | 否 |
| faster-whisper、pypinyin | ≥ 1.0 / ≥ 0.50 | `asr_check.py` 配音校对（首次会下载模型，可设 `THV_MODEL_DIR`） | 否 |
| Voicebox（本地服务，默认 127.0.0.1:17493）或任意 TTS | — | 克隆声配音；没有则用占位音轨或其他 TTS 输出 wav | 否 |
| Remotion | ≥ 4（自备工程） | 想要更复杂动效时替换内置渲染器 | 否 |

安装：
```bash
python3 -m pip install -r requirements.txt          # 可选再装 faster-whisper pypinyin
npm install                                          # 只在用 HTML 渲染/上传脚本时需要
```
