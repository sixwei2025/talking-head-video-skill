"""Style & caption-style registry for talking-head-video (6 visual styles x 6 caption styles).

All dark backgrounds stay at or above ~#181820 with subtle motion/grid/glow elements
so ffmpeg blackdetect (pix_th=0.05) and freezedetect never falsely trigger.
"""

STYLES = {
    'huixin-red': {
        'name': '汇芯红白图解风',
        'desc': '宣纸米白底 + 汇芯品牌红主锚点 + 悬浮圆角白卡，高对比商业实战风格',
        'bg': '#FAF7F2',
        'bg_alt': '#F0EAE0',
        'card_bg': '#FFFFFF',
        'card_border': '#E6DDD0',
        'card_shadow': '#E2D8CA',
        'fg': '#18181B',
        'muted': '#6B6661',
        'accent': '#C8102E',
        'accent_soft': '#FCE8EC',
        'pattern': 'none',
        'card_mode': 'elevated',
        'default_caption': 'pill-highlight',
        'cover_theme': 'brand',
    },
    'dark-tech': {
        'name': '深色科技极客风',
        'desc': '深空暗夜底 + 微弱动态网格 + 磨砂终端卡片 + 赛博青/汇芯红双点缀',
        'bg': '#181C26',
        'bg_alt': '#222838',
        'card_bg': '#202636',
        'card_border': '#333D54',
        'card_shadow': '#12151E',
        'fg': '#F4F7FB',
        'muted': '#8E99B3',
        'accent': '#38BDF8',
        'accent_soft': '#1E3A5F',
        'pattern': 'grid',
        'card_mode': 'terminal',
        'default_caption': 'karaoke-glow',
        'cover_theme': 'swiss_dark',
    },
    'dazibao-impact': {
        'name': '黑底荧光黄大字报风',
        'desc': '深墨暗底 + 荧光黄巨型冲击字体 + 警示红删除线/角标认知反差',
        'bg': '#18181F',
        'bg_alt': '#262632',
        'card_bg': '#21212B',
        'card_border': '#E8FF00',
        'card_shadow': '#101016',
        'fg': '#E8FF00',
        'muted': '#A1A1AA',
        'accent': '#E5283A',
        'accent_soft': '#3B161E',
        'pattern': 'diagonal',
        'card_mode': 'impact',
        'default_caption': 'variety-bold',
        'cover_theme': 'swiss_dark',
    },
    'swiss-editorial': {
        'name': '瑞士杂志编辑风',
        'desc': '暖象牙纸底 + 顶部固定栏目条 + 粗黑排版 + 汇芯红数字锚点',
        'bg': '#F2EFE9',
        'bg_alt': '#E6E1D8',
        'card_bg': '#F2EFE9',
        'card_border': '#18181B',
        'card_shadow': '#D6D0C4',
        'fg': '#141416',
        'muted': '#64625E',
        'accent': '#C8102E',
        'accent_soft': '#F8E3E6',
        'pattern': 'editorial',
        'card_mode': 'swiss',
        'default_caption': 'clean-underline',
        'cover_theme': 'paper',
    },
    'paper-sketch': {
        'name': '白纸简笔手绘风',
        'desc': '纯白笔记本点阵底 + 硬阴影黑框卡片 + 荧光黄马克笔重点底条',
        'bg': '#FFFFFF',
        'bg_alt': '#F1F5F9',
        'card_bg': '#FFFFFF',
        'card_border': '#18181B',
        'card_shadow': '#18181B',
        'fg': '#18181B',
        'muted': '#64748B',
        'accent': '#C8102E',
        'accent_soft': '#FEF08A',
        'pattern': 'dots',
        'card_mode': 'sketch',
        'default_caption': 'marker-box',
        'cover_theme': 'paper',
    },
    'cinematic-apple': {
        'name': 'Apple 极简电影感风',
        'desc': '深炭黑渐变 + 柔和呼吸光斑 + 极细银灰标签 + 居中大留白高质感排版',
        'bg': '#1B1C24',
        'bg_alt': '#2B2838',
        'card_bg': '#232530',
        'card_border': '#383B4C',
        'card_shadow': '#14151C',
        'fg': '#F8FAFC',
        'muted': '#94A3B8',
        'accent': '#C8102E',
        'accent_soft': '#3E1C26',
        'pattern': 'glow',
        'card_mode': 'minimal',
        'default_caption': 'cinema-sub',
        'cover_theme': 'midnight',
    },
}

CAPTION_STYLES = {
    'pill-highlight': {
        'name': '圆角胶囊高亮',
        'desc': '高对比圆角底条 + 逐字点亮 + 关键词品牌红高亮',
    },
    'karaoke-glow': {
        'name': '逐字点亮发光',
        'desc': '已读字符亮白/青色、未读半透明、关键词高亮',
    },
    'variety-bold': {
        'name': '综艺大字描边',
        'desc': '粗体强描边白字 + 关键词荧光黄/红底突出',
    },
    'clean-underline': {
        'name': '极简杂志下划线',
        'desc': '无底框干净排印 + 关键词底部细红线标记',
    },
    'marker-box': {
        'name': '手绘马克笔底条',
        'desc': '关键词配荧光黄马克笔高亮块，适合笔记科普',
    },
    'cinema-sub': {
        'name': '电影感暗条字幕',
        'desc': '半透明深色电影字幕条 + 清晰白字，克制耐看',
    },
}


def resolve_style(cfg, style_override='', caption_override=''):
    """Return resolved (style_id, style_dict, caption_style_id) from config and overrides."""
    sid = (style_override or cfg.get('style') or 'huixin-red').strip()
    if sid not in STYLES:
        sid = 'huixin-red'
    st = dict(STYLES[sid])
    if cfg.get('accent') and sid == 'huixin-red':
        st['accent'] = cfg['accent']
    csid = (caption_override or cfg.get('caption_style') or st['default_caption']).strip()
    if csid not in CAPTION_STYLES:
        csid = st['default_caption']
    return sid, st, csid
