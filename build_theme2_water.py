"""主题02 水资源培育：森林涵养水源对比模拟（增强版）
动态：云朵来回飘移 + 下雨动画；雨滴克隆体不断下落，落到左山/右山分别给
      “裸山地下水 / 森林地下水”加水（森林吸水更多）；画笔实时绘制两根水柱；
      「种树」让森林变茂密；「暴雨」加快雨速并使裸山水土流失抖动变色；
      空格键「重来」清零；监视器显示两山地下水与森林领先差。
"""
from sb3lib import (B, N, WH, PN, T, C, R, RN, BOOL, SUB, MENU,
                    Assets, make_stage, make_sprite, monitor, package)

OUT = "/home/horde/isaac/haibao/02_森林涵养水源.sb3"

V_BARE = "v-bare"
V_FOREST = "v-forest"
V_SPEED = "v-speed"
V_DIFF = "v-diff"
VARS = {V_BARE: "裸山地下水", V_FOREST: "森林地下水", V_SPEED: "雨速",
        V_DIFF: "森林比裸山多存"}
BC_PLANT = "bc-plant"
BC_STORM = "bc-storm"
BC_RESET = "bc-reset"
BC = {BC_PLANT: "种树了", BC_STORM: "暴雨", BC_RESET: "重来"}


def vf(v):
    return {"VARIABLE": [VARS[v], v]}


# ---------------- 雨云 ----------------
def cloud():
    b = B()
    # 脚本1：初始化 + 来回飘
    hat1 = b.new("event_whenflagclicked", top=True)
    s1 = b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_BARE))
    s2 = b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_FOREST))
    s3 = b.new("data_setvariableto", {"VALUE": T(4)}, vf(V_SPEED))
    show = b.new("looks_show")
    fa = b.new("control_forever")
    g1 = b.new("motion_glidesecstoxy", {"SECS": N(2.5), "X": N(-150), "Y": N(140)})
    g2 = b.new("motion_glidesecstoxy", {"SECS": N(2.5), "X": N(150), "Y": N(140)})
    b.link([hat1, s1, s2, s3, show, fa])
    b.d[fa]["inputs"]["SUBSTACK"] = SUB(g1)
    b.link([g1, g2])

    # 脚本2：下雨动画（造型切换）
    hat2 = b.new("event_whenflagclicked", top=True, x=300)
    fa2 = b.new("control_forever")
    nc = b.new("looks_nextcostume")
    wa = b.new("control_wait", {"DURATION": PN(0.3)})
    b.link([hat2, fa2])
    b.d[fa2]["inputs"]["SUBSTACK"] = SUB(nc)
    b.link([nc, wa])

    # 脚本3：按空格 → 重来
    hat3 = b.new("event_whenkeypressed", fields={"KEY_OPTION": ["space", None]},
                 top=True, x=600)
    r1 = b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_BARE))
    r2 = b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_FOREST))
    r3 = b.new("data_setvariableto", {"VALUE": T(4)}, vf(V_SPEED))
    bcast = b.new("event_broadcast",
                  {"BROADCAST_INPUT": [1, [11, BC[BC_RESET], BC_RESET]]})
    b.link([hat3, r1, r2, r3, bcast])
    return b


# ---------------- 雨滴 ----------------
def raindrop():
    b = B()
    # 脚本1：隐藏本体，循环造雨
    hat = b.new("event_whenflagclicked", top=True)
    hide = b.new("looks_hide")
    setsize = b.new("looks_setsizeto", {"SIZE": N(60)})
    fa = b.new("control_forever")
    clone = b.new("control_create_clone_of", {"CLONE_OPTION": MENU(0)})
    menu = b.clone_menu("_myself_")
    b.d[clone]["inputs"]["CLONE_OPTION"] = MENU(menu)
    rnd = b.new("operator_random", {"FROM": N(0.1), "TO": N(0.4)})
    wait = b.new("control_wait", {"DURATION": [3, rnd, [5, "0.2"]]})  # 5=正数兜底
    b.link([hat, hide, setsize, fa])
    b.d[fa]["inputs"]["SUBSTACK"] = SUB(clone)
    b.link([clone, wait])

    # 脚本2：作为克隆体 → 下落 + 落地加水
    chat = b.new("control_start_as_clone", top=True, x=300)
    randx = b.new("operator_random", {"FROM": N(-220), "TO": N(220)})
    goto = b.new("motion_gotoxy", {"X": RN(randx), "Y": N(160)})
    shown = b.new("looks_show")
    # 重复直到 y<-120：change y by -(雨速)
    runtil = b.new("control_repeat_until")
    ypos = b.new("motion_yposition")
    lt = b.new("operator_lt", {"OPERAND1": R(ypos), "OPERAND2": T(-120)})
    negspeed = b.new("operator_subtract",
                     {"NUM1": N(0),
                      "NUM2": RN(b.new("data_variable", fields=vf(V_SPEED)))})
    chy = b.new("motion_changeyby", {"DY": RN(negspeed)})
    b.d[runtil]["inputs"]["CONDITION"] = BOOL(lt)
    b.d[runtil]["inputs"]["SUBSTACK"] = SUB(chy)
    # 落地：判断左右
    xpos = b.new("motion_xposition")
    isleft = b.new("operator_lt", {"OPERAND1": R(xpos), "OPERAND2": T(0)})
    ifelse = b.new("control_if_else")
    b.d[ifelse]["inputs"]["CONDITION"] = BOOL(isleft)
    # 左：裸山+1（<100）
    bare_lt = b.new("operator_lt",
                    {"OPERAND1": R(b.new("data_variable", fields=vf(V_BARE))),
                     "OPERAND2": T(100)})
    if_bare = b.new("control_if")
    chg_bare = b.new("data_changevariableby", {"VALUE": N(1)}, vf(V_BARE))
    b.d[if_bare]["inputs"]["CONDITION"] = BOOL(bare_lt)
    b.d[if_bare]["inputs"]["SUBSTACK"] = SUB(chg_bare)
    # 右：森林+3（<100）
    for_lt = b.new("operator_lt",
                   {"OPERAND1": R(b.new("data_variable", fields=vf(V_FOREST))),
                    "OPERAND2": T(100)})
    if_for = b.new("control_if")
    chg_for = b.new("data_changevariableby", {"VALUE": N(3)}, vf(V_FOREST))
    b.d[if_for]["inputs"]["CONDITION"] = BOOL(for_lt)
    b.d[if_for]["inputs"]["SUBSTACK"] = SUB(chg_for)
    b.d[ifelse]["inputs"]["SUBSTACK"] = SUB(if_bare)
    b.d[ifelse]["inputs"]["SUBSTACK2"] = SUB(if_for)
    delete = b.new("control_delete_this_clone")
    b.link([chat, goto, shown, runtil, ifelse, delete])
    return b


# ---------------- 数据板：画笔双水柱 + 领先差 ----------------
def databoard():
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    hide = b.new("looks_hide")
    fa = b.new("control_forever")
    clear = b.new("pen_clear")
    psize = b.new("pen_setPenSizeTo", {"SIZE": N(46)})
    seq = [clear, psize]

    def bar(x, vid, hexc):
        col = b.new("pen_setPenColorToColor", {"COLOR": C(hexc)})
        g1 = b.new("motion_gotoxy", {"X": N(x), "Y": N(-150)})
        pd = b.new("pen_penDown")
        mul = b.new("operator_multiply",
                    {"NUM1": RN(b.new("data_variable", fields=vf(vid))), "NUM2": N(2)})
        add = b.new("operator_add", {"NUM1": N(-150), "NUM2": RN(mul)})
        g2 = b.new("motion_gotoxy", {"X": N(x), "Y": RN(add)})
        pu = b.new("pen_penUp")
        seq.extend([col, g1, pd, g2, pu])

    bar(-90, V_BARE, "#4a90d9")
    bar(90, V_FOREST, "#2eb086")
    b.link([hat, hide, fa])
    b.d[fa]["inputs"]["SUBSTACK"] = SUB(clear)
    b.link(seq)

    # 脚本2：持续算领先差
    hat2 = b.new("event_whenflagclicked", top=True, x=300)
    fa2 = b.new("control_forever")
    sub = b.new("operator_subtract",
                {"NUM1": RN(b.new("data_variable", fields=vf(V_FOREST))),
                 "NUM2": RN(b.new("data_variable", fields=vf(V_BARE)))})
    setdiff = b.new("data_setvariableto", {"VALUE": RN(sub)}, vf(V_DIFF))
    b.link([hat2, fa2])
    b.d[fa2]["inputs"]["SUBSTACK"] = SUB(setdiff)
    return b


# ---------------- 裸山 ----------------
def bare():
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    go = b.new("motion_gotoxy", {"X": N(-120), "Y": N(-70)})
    cle = b.new("looks_cleargraphiceffects")
    b.link([hat, go, cle])

    # 暴雨 → 抖动 10 次 + 变红
    hs = b.new("event_whenbroadcastreceived",
               fields={"BROADCAST_OPTION": [BC[BC_STORM], BC_STORM]}, top=True, x=300)
    rep10 = b.new("control_repeat", {"TIMES": WH(10)})
    e1 = b.new("looks_changeeffectby", {"CHANGE": N(8)},
               fields={"EFFECT": ["COLOR", None]})
    cx1 = b.new("motion_changexby", {"DX": N(5)})
    w1 = b.new("control_wait", {"DURATION": PN(0.05)})
    cx2 = b.new("motion_changexby", {"DX": N(-5)})
    w2 = b.new("control_wait", {"DURATION": PN(0.05)})
    b.link([hs, rep10])
    b.d[rep10]["inputs"]["SUBSTACK"] = SUB(e1)
    b.link([e1, cx1, w1, cx2, w2])

    # 重来 → 复原
    hr = b.new("event_whenbroadcastreceived",
               fields={"BROADCAST_OPTION": [BC[BC_RESET], BC_RESET]}, top=True, x=600)
    cle2 = b.new("looks_cleargraphiceffects")
    go2 = b.new("motion_gotoxy", {"X": N(-120), "Y": N(-70)})
    b.link([hr, cle2, go2])
    return b


# ---------------- 森林 ----------------
def forest():
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    sw = b.new("looks_switchcostumeto", {"COSTUME": MENU(0)})
    menu = b.costume_menu("森林")
    b.d[sw]["inputs"]["COSTUME"] = MENU(menu)
    go = b.new("motion_gotoxy", {"X": N(120), "Y": N(-70)})
    b.link([hat, sw, go])

    # 种树 → 下一个造型 + 说
    hp = b.new("event_whenbroadcastreceived",
               fields={"BROADCAST_OPTION": [BC[BC_PLANT], BC_PLANT]}, top=True, x=300)
    nc = b.new("looks_nextcostume")
    say = b.new("looks_sayforsecs", {"MESSAGE": T("树多了，蓄水更强！"), "SECS": N(1.5)})
    b.link([hp, nc, say])

    # 重来 → 复原造型
    hr = b.new("event_whenbroadcastreceived",
               fields={"BROADCAST_OPTION": [BC[BC_RESET], BC_RESET]}, top=True, x=600)
    sw2 = b.new("looks_switchcostumeto", {"COSTUME": MENU(0)})
    menu2 = b.costume_menu("森林")
    b.d[sw2]["inputs"]["COSTUME"] = MENU(menu2)
    b.link([hr, sw2])
    return b


# ---------------- 通用按钮 ----------------
def button(msg_id, set_speed=None):
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    show = b.new("looks_show")
    b.link([hat, show])
    clicked = b.new("event_whenthisspriteclicked", top=True, x=300)
    chain = [clicked]
    if set_speed is not None:
        sp = b.new("data_setvariableto", {"VALUE": T(set_speed)}, vf(V_SPEED))
        chain.append(sp)
    bc = b.new("event_broadcast", {"BROADCAST_INPUT": [1, [11, BC[msg_id], msg_id]]})
    chain.append(bc)
    b.link(chain)
    return b


# ---------------- SVG 素材 ----------------
def svg_backdrop():
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360">'
            '<defs><linearGradient id="s" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0" stop-color="#9fd8ef"/>'
            '<stop offset="1" stop-color="#d8f0e0"/></linearGradient></defs>'
            '<rect width="480" height="360" fill="url(#s)"/>'
            '<rect y="300" width="480" height="60" fill="#cbb89d"/>'
            '<line x1="240" y1="120" x2="240" y2="300" stroke="#ffffff" '
            'stroke-width="2" stroke-dasharray="6 6"/>'
            '<text x="60" y="150" font-family="sans-serif" font-size="20" '
            'fill="#8a5a44">裸山</text>'
            '<text x="360" y="150" font-family="sans-serif" font-size="20" '
            'fill="#2d6a4f">森林</text>'
            '<text x="120" y="36" font-family="sans-serif" font-size="22" '
            'fill="#013a63">森林涵养水源对比模拟</text></svg>')


def svg_cloud(rain=False):
    drops = ""
    if rain:
        for i in range(5):
            xx = 18 + i * 16
            drops += (f'<line x1="{xx}" y1="50" x2="{xx-4}" y2="66" '
                      'stroke="#48cae4" stroke-width="3"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="110" height="75">'
            '<ellipse cx="38" cy="34" rx="30" ry="21" fill="#ffffff"/>'
            '<ellipse cx="66" cy="28" rx="32" ry="23" fill="#ffffff"/>'
            '<ellipse cx="82" cy="40" rx="24" ry="17" fill="#eef3f6"/>'
            f'{drops}</svg>')


def svg_raindrop():
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="12" height="20">'
            '<path d="M6 0 C9 8 12 12 12 15 A6 6 0 1 1 0 15 C0 12 3 8 6 0 Z" '
            'fill="#48cae4"/></svg>')


def svg_bare_mountain():
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="180" height="130">'
            '<polygon points="12,122 90,16 168,122" fill="#b08968"/>'
            '<polygon points="90,16 108,52 72,52" fill="#9c6644"/>'
            '<path d="M70 90 q12 8 24 0" stroke="#8a5a44" stroke-width="3" '
            'fill="none"/></svg>')


def svg_forest(dense=False):
    trees = ""
    xs = (50, 78, 106, 134) if dense else (60, 90, 120)
    for tx in xs:
        ty = 72 if tx in (78, 90) else 88
        trees += (f'<polygon points="{tx},{ty-34} {tx-16},{ty} {tx+16},{ty}" '
                  'fill="#2d6a4f"/>'
                  f'<rect x="{tx-3}" y="{ty}" width="6" height="13" '
                  'fill="#6f4518"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="180" height="130">'
            '<polygon points="12,122 90,16 168,122" fill="#4a6741"/>'
            f'{trees}</svg>')


def svg_button(label, fill):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="140" height="50">'
            f'<rect x="2" y="2" width="136" height="46" rx="23" fill="{fill}" '
            'stroke="#ffffff" stroke-width="3"/>'
            f'<text x="70" y="33" font-family="sans-serif" font-size="22" '
            f'fill="#ffffff" text-anchor="middle">{label}</text></svg>')


def build():
    a = Assets()
    stage = make_stage([a.costume("背景", svg_backdrop(), 240, 180)],
                       {v: [VARS[v], 0] for v in VARS}, {k: BC[k] for k in BC})
    cl = make_sprite("雨云", cloud(),
                     [a.costume("云", svg_cloud(False), 55, 37),
                      a.costume("云带雨", svg_cloud(True), 55, 37)],
                     6, 0, 140)
    rd = make_sprite("雨滴", raindrop(), [a.costume("水滴", svg_raindrop(), 6, 10)],
                     5, 0, 160, visible=False)
    bd = make_sprite("数据板", databoard(), [a.costume("点", svg_raindrop(), 6, 10)],
                     1, 0, 0, visible=False)
    ba = make_sprite("裸山", bare(), [a.costume("裸山", svg_bare_mountain(), 90, 65)],
                     2, -120, -70)
    fo = make_sprite("森林", forest(),
                     [a.costume("森林", svg_forest(False), 90, 65),
                      a.costume("茂密森林", svg_forest(True), 90, 65)],
                     3, 120, -70)
    bp = make_sprite("种树按钮", button(BC_PLANT),
                     [a.costume("种树", svg_button("🌱 种树", "#2eb086"), 70, 25)],
                     7, -150, 150)
    bs = make_sprite("暴雨按钮", button(BC_STORM, set_speed=10),
                     [a.costume("暴雨", svg_button("⛈ 暴雨", "#e07a3f"), 70, 25)],
                     8, 150, 150)

    mons = [monitor(V_BARE, VARS[V_BARE], 5, 5),
            monitor(V_FOREST, VARS[V_FOREST], 5, 40),
            monitor(V_DIFF, VARS[V_DIFF], 5, 75)]
    info = package(OUT, [stage, cl, rd, bd, ba, fo, bp, bs], mons, a,
                   extensions=["pen"])
    print(f"已生成: {OUT}  角色{info['targets']} 积木{info['blocks']} {info['extensions']}")


if __name__ == "__main__":
    build()
