"""基于 st.md 生成《生态平衡 草-羊-狼》项目海报（宽幅多栏布局）：
灵感来源 / 构思过程 / 编程模拟(表格) / 运行截图 / 成功之处 / 遇到的问题 / 收获与总结。
正文统一字体(SC)与颜色，语言通俗，无页脚。"""
import os
import collections
from PIL import Image, ImageDraw, ImageFont

BASE = "/home/horde/isaac/haibao"
IMG_DIR = os.path.join(BASE, "images")
OUT = os.path.join(BASE, "03_生态平衡_海报.jpg")

W = 1720
MARGIN = 56
GAP = 30
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"

C_DEEP, C_GREEN, C_LIGHT, C_WARM = "#2d6a4f", "#40916c", "#74c69d", "#b9863b"
C_CARD, C_BORDER = "#ffffff", "#cfe3d4"
BODY = "#26402f"
TITLE_BG = "#2f7d5a"      # 各板块标题统一的绿色
BODY_SZ = 26
LEVELS = ["#2d6a4f", "#a7d3a0", "#ece9a8", "#c8a23a"]
LH = 1.45


def font(size, bold=False, serif=False):
    return ImageFont.truetype(FONT_SERIF if serif else (FONT_BOLD if bold else FONT_REG),
                              size, index=2)   # index=2 → 简体中文(SC)字形


def body_font():
    return font(BODY_SZ, bold=False)


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def vgrad(w, h, top, bot):
    top, bot = hex2rgb(top), hex2rgb(bot)
    im = Image.new("RGB", (w, h))
    px = im.load()
    for yy in range(h):
        t = yy / max(1, h - 1)
        c = tuple(int(top[i] * (1 - t) + bot[i] * t) for i in range(3))
        for xx in range(w):
            px[xx, yy] = c
    return im


NO_LEADING = "。，、；：！？）】》」』.,!?;:)"   # 这些标点不另起一行


def wrap(s, fnt, maxw):
    lines, cur = [], ""
    for ch in s:
        if ch == "\n":
            lines.append(cur); cur = ""; continue
        if d.textlength(cur + ch, font=fnt) <= maxw:
            cur += ch
        elif ch in NO_LEADING and cur:
            cur += ch                 # 收尾标点跟在当前行末（允许略微超宽），避免单独成行
            lines.append(cur); cur = ""
        else:
            lines.append(cur); cur = ch
    if cur:
        lines.append(cur)
    return lines


img = vgrad(W, 2600, "#eaf6ec", "#f8fcf6")
d = ImageDraw.Draw(img)


def text(s, x, yy, fill, maxw=None, fnt=None):
    fnt = fnt or body_font()
    for ln in (wrap(s, fnt, maxw) if maxw else [s]):
        d.text((x, yy), ln, font=fnt, fill=fill)
        yy += int(fnt.size * LH)
    return yy


def title_bar(x, top, w, title, accent, subtitle=None):
    d.rounded_rectangle([x, top, x + w, top + 64], radius=20, fill=hex2rgb(accent))
    d.rectangle([x, top + 36, x + w, top + 64], fill=hex2rgb(accent))
    d.text((x + 26, top + 12), title, font=font(34, bold=True), fill=(255, 255, 255))
    if subtitle:
        sw = d.textlength(subtitle, font=font(22))
        d.text((x + w - sw - 24, top + 22), subtitle, font=font(22), fill=(205, 232, 214))
    return top + 64


def card_h(w, paras):
    inner = w - 56
    fnt = body_font()
    body = sum(int(BODY_SZ * LH) * len(wrap(s, fnt, inner)) + 12 for s in paras)
    return 64 + 24 + body + 16


def card_at(x, top, w, title, paras, accent, min_h=0):
    h = max(card_h(w, paras), min_h)
    d.rounded_rectangle([x, top, x + w, top + h], radius=20, fill=hex2rgb(C_CARD),
                        outline=hex2rgb(C_BORDER), width=2)
    title_bar(x, top, w, title, accent)
    cy = top + 88
    for s in paras:
        cy = text(s, x + 28, cy, hex2rgb(BODY), maxw=w - 56) + 12
    return h


def intro_h(w, intro):
    return int(BODY_SZ * LH) * len(wrap(intro, body_font(), w - 56)) + 16 if intro else 0


def table_h(w, rows, intro=None):
    rc = (w - 48) - 270
    fnt = body_font()
    rhs = [max(int(BODY_SZ * LH) * len(wrap(rd, fnt, rc - 32)) + 28, 58) for _, rd in rows]
    return 64 + 18 + intro_h(w, intro) + 46 + sum(rhs) + 18


def table_at(x, top, w, title, header, rows, accent, intro=None):
    h = table_h(w, rows, intro)
    d.rounded_rectangle([x, top, x + w, top + h], radius=20, fill=hex2rgb(C_CARD),
                        outline=hex2rgb(C_BORDER), width=2)
    title_bar(x, top, w, title, accent)
    tl, tr = x + 24, x + w - 24
    tw = tr - tl
    lc = 270
    rc = tw - lc
    pad = 16
    fnt = body_font()
    ty = top + 84
    if intro:
        text(intro, x + 28, ty, hex2rgb(BODY), maxw=w - 56)
        ty += intro_h(w, intro)
    d.rectangle([tl, ty, tr, ty + 46], fill=hex2rgb(accent))
    d.text((tl + pad, ty + 9), header[0], font=font(24, bold=True), fill=(255, 255, 255))
    d.text((tl + lc + pad, ty + 9), header[1], font=font(24, bold=True), fill=(255, 255, 255))
    ry = ty + 46
    for k, (lcell, rcell) in enumerate(rows):
        rh = max(int(BODY_SZ * LH) * len(wrap(rcell, fnt, rc - 2 * pad)) + 28, 58)
        if k % 2 == 1:
            d.rectangle([tl, ry, tr, ry + rh], fill=hex2rgb("#f1f8f2"))
        d.line([tl + lc, ry, tl + lc, ry + rh], fill=hex2rgb(C_BORDER), width=1)
        text(lcell, tl + pad, ry + 14, hex2rgb(BODY), maxw=lc - 2 * pad)
        text(rcell, tl + lc + pad, ry + 14, hex2rgb(BODY), maxw=rc - 2 * pad)
        ry += rh
        d.line([tl, ry, tr, ry], fill=hex2rgb(C_BORDER), width=1)
    d.rounded_rectangle([tl, ty, tr, ry], radius=4, outline=hex2rgb(C_BORDER), width=2)
    return h


def paste_chase_scene(img_obj, draw_obj, ax, ay, aw, ah):
    """将 zzz.png 等比放大裁剪（cover），充满空白区域。"""
    scene = Image.open(os.path.join(IMG_DIR, "zzz.png")).convert("RGB")
    # cover：按较大比例缩放，使图片完全覆盖目标区域
    scale = max(aw / scene.width, ah / scene.height)
    sw = int(scene.width  * scale)
    sh = int(scene.height * scale)
    scene = scene.resize((sw, sh), Image.LANCZOS)
    # 居中裁剪到 (aw, ah)
    cx = (sw - aw) // 2
    cy = (sh - ah) // 2
    scene = scene.crop((cx, cy, cx + aw, cy + ah))
    img_obj.paste(scene, (ax, ay))



# ============ 顶部标题区 ============
HDR = 250
d.rectangle([0, 0, W, HDR], fill=hex2rgb(C_DEEP))
bw = W // 4
for i, c in enumerate(LEVELS):
    d.rectangle([i * bw, HDR - 14, (i + 1) * bw, HDR], fill=hex2rgb(c))
d.text((MARGIN, 44), "生态平衡", font=font(86, serif=True), fill=(255, 255, 255))
d.text((MARGIN, 156), "草 · 羊 · 狼   —   Scratch 生态系统模拟", font=font(34), fill=(202, 232, 212))

y = HDR + GAP
x0 = MARGIN
fullw = W - 2 * MARGIN

# ---- 行 A：灵感来源 | 构思过程（等高） ----
colw = (fullw - GAP) // 2
inspire = [
    "每年春天，北京总会刮几场沙尘暴，刮得鼻子、嘴巴里都是土。",
    "报道说，主要是因为我们的邻国蒙古过度放牧，导致草场严重退化、土地不断沙化。",
    "于是我想到做这样一个小程序，让大家亲眼看到：从动植物数量失衡，到生态平衡被打破，继而又慢慢"
    "恢复的过程——从而体会到，保持生态平衡，真的很重要。",
]
process = [
    "① 选了草场上最典型的食物链：草→羊→狼。羊吃草，狼又吃掉多出来的羊，草就有时间长回来——"
    "关键是要体现三者数量的平衡关系。",
    "② 第一版想让每只羊和狼真的在屏幕上跑动、追逐、吃掉对方，实现数量的精准增减，可这样太难控制："
    "狼跑快一点就把羊吃光，慢一点又把自己饿死，没法长期共存。",
    "③ 于是换个思路，建立数量增减逻辑『捕食 + 优胜劣汰』，每隔两秒运行一次；『碰到才吃』只是演示"
    "狼吃羊，捕食只是数量增减逻辑的一部分。",
    "④ 为增加趣味性，再加一个『裁判』(左下角的铃铛)：失衡时给出提示；右边两个按钮能让你随时加羊、"
    "加狼，尝试如何恢复平衡。",
]
inspire_nat_h = card_h(colw, inspire)
rowA_h = max(inspire_nat_h, card_h(colw, process))
card_at(x0, y, colw, "灵感来源", inspire, TITLE_BG, min_h=rowA_h)
card_at(x0 + colw + GAP, y, colw, "构思过程", process, TITLE_BG, min_h=rowA_h)
# 在灵感来源卡片底部空白区绘制追逐场景
blank_top = y + inspire_nat_h
blank_bot = y + rowA_h - 10
blank_h   = blank_bot - blank_top
if blank_h > 60:
    paste_chase_scene(img, d, x0 + 14, blank_top + 4, colw - 28, blank_h - 8)
y += rowA_h + GAP

# ---- 行 B：编程模拟（表格，整宽） ----
eco_intro = ("程序模拟『草→羊→狼』食物链生态：点绿旗启动后自动运行，每 2 秒刷新一次三者数量并更新画面"
             "（背景随草量由绿变黄）；点右侧『+羊』『+狼』按钮可手动投放（每次各加 50 / 10 只），"
             "左下角铃铛会随时提示「羊数量过多 / 狼数量过多 / 生态平衡被破坏」。")
y += table_at(x0, y, fullw, "编程模拟", ("用到的积木", "在模拟里做什么"), [
    ("角色 + 克隆体 + 变量",
     "一个克隆体就是一只羊/一只狼；变量记录草、羊、狼的数量，以及再生力、进食力、刷新间隔等可调参数。"),
    ("事件积木",
     "绿旗时做初始化；克隆体一出生就给数量+1；用『收到广播』让各角色配合；点按钮加羊、加狼。"),
    ("控制（永远 + 等待）",
     "『永远…等待 2 秒』形成心跳，每 2 秒结算一个时间步；用『等待直到』确保初始化完成才开始。"),
    ("运算 + 变量",
     "把公式直接拼成积木：四舍五入(再生力 × 数量) 来再生，(草 < 上限) 来封顶，实现按比例增减。"),
    ("广播 + 本地标记",
     "用『求最老→删最老』的广播，让克隆体按出生编号被精准、有序地删除（被吃的、最老的优先）。"),
    ("侦测 / 外观",
     "用『碰到狼?』判断捕食；用『说』弹出提示气泡；两帧造型来回切换做走路动画。"),
], TITLE_BG, intro=eco_intro) + GAP

# ---- 行 C：运行截图（5 张一行） ----
top = y
hbar = title_bar(x0, top, fullw, "运行截图", TITLE_BG, "草越多→背景越绿越密；草越少→越黄越稀")
caps = [
    "草丰茂：满屏浓绿，羊狼安然共存",
    "草仍充足，但羊开始变多 →「羊数量过多」",
    "浅绿：草渐少，羊狼数量一起攀升",
    "浅黄：草被啃掉一大半，背景泛黄",
    "深黄：草快没了 →「生态平衡被破坏」",
]
files = ["1.png", "2.png", "3.png", "4.png", "5.png"]
n = len(files)
igap = 18
iw = (fullw - igap * (n - 1)) // n
imgs = [Image.open(os.path.join(IMG_DIR, fn)).convert("RGB") for fn in files]
imgs = [im.resize((iw, int(im.height * iw / im.width))) for im in imgs]
ih = max(im.height for im in imgs)
cap_h = 96
gy = hbar + 16
for k, im in enumerate(imgs):
    cx = x0 + k * (iw + igap)
    d.rounded_rectangle([cx, gy, cx + iw, gy + ih + cap_h], radius=12,
                        fill=hex2rgb(C_CARD), outline=hex2rgb(C_BORDER), width=2)
    img.paste(im, (cx, gy))
    d.ellipse([cx + 8, gy + 8, cx + 36, gy + 36], fill=hex2rgb(LEVELS[min(k, 3)]))
    d.text((cx + 15, gy + 11), str(k + 1), font=font(20, bold=True), fill=(255, 255, 255))
    text(caps[k], cx + 12, gy + ih + 8, hex2rgb(BODY), maxw=iw - 24, fnt=font(19))
y = gy + ih + cap_h + GAP

# ---- 行 D：成功之处 | 遇到的问题 | 收获与总结（等高） ----
c3 = (fullw - 2 * GAP) // 3
success = [
    "· 了解学习了实际草场生态的运行规律(例如羊和狼的配比)，程序运行结果贴近生活认知。",
    "· 草的多少不靠克隆体数量体现，而是用背景颜色变化展示，更加直观清晰。",
    "· 失衡时铃铛提示「羊/狼过多、生态被破坏」。",
    "· 可点按钮加羊、加狼，亲手尝试恢复，增加互动。",
]
problems = [
    "· 起初按数学逻辑繁殖，克隆体『自己再克隆自己』，数量爆炸式增长，不符合现实规律。",
    "· 手动删多余的羊/狼时常删错对象，数量和记录对不上；后来定规则，靠『是否进食、年龄』判断删谁。",
    "· 用随机行走、碰到就捕食，可羊狼一多就互相挤在一起却又没被吃掉，看起来很奇怪。",
]
gains = [
    "· 复杂现象常能用简单『数量规则』概括，更好控制。",
    "· 编程要顺着工具脾气：摸清克隆与广播的特点。",
    "· 会『自我调节』(多减少补)的系统才稳得住。",
    "· 把数据变成颜色、配上互动，道理就看得见、玩得动。",
]
rowD_h = max(card_h(c3, success), card_h(c3, problems), card_h(c3, gains))
card_at(x0, y, c3, "成功之处", success, TITLE_BG, min_h=rowD_h)
card_at(x0 + c3 + GAP, y, c3, "遇到的问题", problems, TITLE_BG, min_h=rowD_h)
card_at(x0 + 2 * (c3 + GAP), y, c3, "收获与总结", gains, TITLE_BG, min_h=rowD_h)
y += rowD_h + GAP

img.crop((0, 0, W, y)).save(OUT, quality=92)
print("已生成海报:", OUT, "尺寸", (W, y))
