# 口播视觉风格与字幕样式指南（6 × 6 矩阵）

本 Skill 的统一渲染引擎（`scripts/render_pillow.py` 与 `templates/studio.html`）内置 **6 大口播视觉风格** 与 **6 大单行字幕样式**，同时支持 **16:9 横屏（`1920×1080`，默认）** 与 **9:16 竖屏（`1080×1920`）** 自适应排版，以及可选的**圆形画中画头像（`avatar`）**。

## 一、6 大口播视觉风格（`style`）

| 风格 ID (`--style` / `STYLE`) | 中文名称 | 视觉特征与配色 | 默认字幕样式 | 适用场景 |
| :--- | :--- | :--- | :--- | :--- |
| `huixin-red` | **汇芯红白图解风** | 宣纸米白 `#FAF7F2` + 汇芯红 `#C8102E` + 悬浮圆角白卡 | `pill-highlight` | 商业实战、方法论拆解、品牌主号口播（默认） |
| `dark-tech` | **深色科技极客风** | 深空暗夜 `#181C26` + 动态网格 + 磨砂终端窗 + 赛博青 `#38BDF8` | `karaoke-glow` | AI 工具实测、技术架构、SaaS 实操演示 |
| `dazibao-impact` | **黑底荧光黄大字报风** | 深墨底 `#18181F` + 荧光黄 `#E8FF00` + 警示红 `#E5283A` 角标 | `variety-bold` | 15–30s 强观点、认知反转、痛点暴击 |
| `swiss-editorial` | **瑞士杂志编辑风** | 暖象牙纸 `#F2EFE9` + 顶部固定刊号栏目条 + 粗黑排版 + 红数字锚点 | `clean-underline` | 深度商业评论、行业趋势、案例复盘 |
| `paper-sketch` | **白纸简笔手绘风** | 纯白点阵笔记本 `#FFFFFF` + 硬阴影黑框卡片 + 荧光黄马克笔高亮 | `marker-box` | 知识科普、读书笔记、避坑清单 |
| `cinematic-apple` | **Apple 极简电影感风** | 深炭黑 `#1B1C24` + 柔和呼吸光斑 + 极细银灰标签 + 居中大留白 | `cinema-sub` | 个人故事、品牌理念、年度总结 |

## 二、6 大单行字幕样式（`caption_style`）

默认随主风格自动匹配，也可在 `config.json` 中单独指定 `"caption_style"` 或通过 `CAPTION_STYLE=...` 覆盖：

1. `pill-highlight`：圆角胶囊高亮（高对比底条 + 逐字点亮 + 关键词品牌红高亮）
2. `karaoke-glow`：逐字点亮发光（已读亮白/青色、未读弱化、关键词高亮）
3. `variety-bold`：综艺大字描边（粗体强描边 + 关键词红底反白块）
4. `clean-underline`：极简杂志下划线（无底框干净排印 + 关键词底部细红线）
5. `marker-box`：手绘马克笔底条（关键词配荧光黄马克笔高亮块）
6. `cinema-sub`：电影感暗条字幕（半透明深色电影字幕条 + 清晰白字）

## 三、快速切换方式

```bash
# 方式 1：环境变量一键切换风格跑全流程
STYLE=dark-tech bash ../scripts/run_all.sh

# 方式 2：混搭风格与字幕样式（例如：瑞士杂志风 + 胶囊高亮字幕）
STYLE=swiss-editorial CAPTION_STYLE=pill-highlight bash ../scripts/run_all.sh

# 方式 3：使用 headless Chrome 渲染 HTML5 模板（templates/studio.html）
RENDERER=html CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" STYLE=paper-sketch bash ../scripts/run_all.sh
```
