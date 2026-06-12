"""主题01 大气环境治理：蓝天保卫战
动态：工厂冒烟(克隆体上升) → PM2.5上升、雾霾层变浓 → 启动净化塔吸收粒子 →
      PM下降、天空变蓝；画笔绘制PM2.5柱；起风按钮加大粒子横向漂移。
"""
import os
from sb3lib import (B, N, WH, PN, T, C, R, RN, BOOL, SUB, MENU,
                    Assets, make_stage, make_sprite, monitor, package)

OUT = "/home/horde/isaac/haibao/01_蓝天保卫战.sb3"

V_PM = "v-pm"
V_CLEAN = "v-clean"
V_PURIFY = "v-purify"   # 净化塔是否开启 0/1
V_WIND = "v-wind"
VARS = {V_PM: "PM2.5浓度", V_CLEAN: "已净化", V_PURIFY: "净化开关", V_WIND: "风力"}
BC_PURIFY = "bc-purify"
BC_RESET = "bc-reset"
BC = {BC_PURIFY: "启动净化", BC_RESET: "重来"}


def vf(v):
    return {"VARIABLE": [VARS[v], v]}


# ---------------- 烟雾粒子 ----------------
def smoke():
    b = B()
    # 绿旗：隐藏，循环造烟
    hat = b.new("event_whenflagclicked", top=True)
    hide = b.new("looks_hide")
    setpm = b.new("data_setvariableto", {"VALUE": T(20)}, vf(V_PM))
    setcl = b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_CLEAN))
    setpur = b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_PURIFY))
    setwind = b.new("data_setvariableto", {"VALUE": T(1)}, vf(V_WIND))
    fa = b.new("control_forever")
    cl = b.new("control_create_clone_of", {"CLONE_OPTION": MENU(0)})
    menu = b.clone_menu("_myself_")
    b.d[cl]["inputs"]["CLONE_OPTION"] = MENU(menu)
    wait = b.new("control_wait", {"DURATION": PN(0.4)})
    b.link([hat, hide, setpm, setcl, setpur, setwind, fa])
    b.d[fa]["inputs"]["SUBSTACK"] = SUB(cl)
    b.link([cl, wait])

    # 作为克隆体：从烟囱升起
    chat = b.new("control_start_as_clone", top=True, x=300)
    rx = b.new("operator_random", {"FROM": N(-180), "TO": N(-60)})
    goto = b.new("motion_gotoxy", {"X": RN(rx), "Y": N(-120)})
    show = b.new("looks_show")
    setsz = b.new("looks_setsizeto", {"SIZE": N(50)})
    # PM 上升（封顶100）
    pmlt = b.new("operator_lt", {"OPERAND1": R(b.new("data_variable", fields=vf(V_PM))),
                                 "OPERAND2": T(100)})
    ifpm = b.new("control_if")
    chgpm = b.new("data_changevariableby", {"VALUE": N(2)}, vf(V_PM))
    b.d[ifpm]["inputs"]["CONDITION"] = BOOL(pmlt)
    b.d[ifpm]["inputs"]["SUBSTACK"] = SUB(chgpm)
    # 上升直到顶端 或 被净化塔吸收
    runtil = b.new("control_repeat_until")
    ytop = b.new("operator_gt", {"OPERAND1": R(b.new("motion_yposition")),
                                 "OPERAND2": T(150)})
    # drift: 横向随风
    driftrand = b.new("operator_random", {"FROM": N(-1), "TO": N(1)})
    driftmul = b.new("operator_multiply",
                     {"NUM1": RN(driftrand),
                      "NUM2": RN(b.new("data_variable", fields=vf(V_WIND)))})
    chx = b.new("motion_changexby", {"DX": RN(driftmul)})
    chy = b.new("motion_changeyby", {"DY": N(3)})
    # 若净化塔开 且 碰到净化塔 → 净化
    puron = b.new("operator_equals",
                  {"OPERAND1": R(b.new("data_variable", fields=vf(V_PURIFY))),
                   "OPERAND2": T(1)})
    touch = b.new("sensing_touchingobject", {"TOUCHINGOBJECTMENU": MENU(0)})
    tmenu = b.touch_menu("净化塔")
    b.d[touch]["inputs"]["TOUCHINGOBJECTMENU"] = MENU(tmenu)
    andc = b.new("operator_and", {"OPERAND1": BOOL(puron), "OPERAND2": BOOL(touch)})
    ifclean = b.new("control_if")
    chgpm2 = b.new("data_changevariableby", {"VALUE": N(-4)}, vf(V_PM))
    chgcl = b.new("data_changevariableby", {"VALUE": N(1)}, vf(V_CLEAN))
    delc = b.new("control_delete_this_clone")
    b.d[ifclean]["inputs"]["CONDITION"] = BOOL(andc)
    b.link([chgpm2, chgcl, delc])
    b.d[ifclean]["inputs"]["SUBSTACK"] = SUB(chgpm2)
    b.d[runtil]["inputs"]["CONDITION"] = BOOL(ytop)
    b.link([chx, chy, ifclean])
    b.d[runtil]["inputs"]["SUBSTACK"] = SUB(chx)
    deltop = b.new("control_delete_this_clone")
    b.link([chat, goto, show, setsz, ifpm, runtil, deltop])
    return b


# ---------------- 雾霾层（半透明灰，随PM变浓） ----------------
def haze():
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    fa = b.new("control_forever")
    # ghost = 100 - PM  → PM越高越不透明
    sub = b.new("operator_subtract",
                {"NUM1": N(100),
                 "NUM2": RN(b.new("data_variable", fields=vf(V_PM)))})
    seteff = b.new("looks_seteffectto", {"VALUE": RN(sub)},
                   fields={"EFFECT": ["GHOST", None]})
    b.link([hat, fa])
    b.d[fa]["inputs"]["SUBSTACK"] = SUB(seteff)
    return b


# ---------------- 净化塔 ----------------
def tower():
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    go = b.new("motion_gotoxy", {"X": N(150), "Y": N(-60)})
    eff = b.new("looks_seteffectto", {"VALUE": N(40)},
                fields={"EFFECT": ["GHOST", None]})
    b.link([hat, go, eff])
    # 启动净化 → 开关置1，亮起
    hp = b.new("event_whenbroadcastreceived",
               fields={"BROADCAST_OPTION": [BC[BC_PURIFY], BC_PURIFY]}, top=True, x=300)
    setp = b.new("data_setvariableto", {"VALUE": T(1)}, vf(V_PURIFY))
    eff2 = b.new("looks_seteffectto", {"VALUE": N(0)},
                 fields={"EFFECT": ["GHOST", None]})
    say = b.new("looks_sayforsecs", {"MESSAGE": T("净化塔启动！"), "SECS": N(1.5)})
    b.link([hp, setp, eff2, say])
    # 重来
    hr = b.new("event_whenbroadcastreceived",
               fields={"BROADCAST_OPTION": [BC[BC_RESET], BC_RESET]}, top=True, x=600)
    setp0 = b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_PURIFY))
    eff3 = b.new("looks_seteffectto", {"VALUE": N(40)},
                 fields={"EFFECT": ["GHOST", None]})
    b.link([hr, setp0, eff3])
    return b


# ---------------- 画笔数据板：PM2.5 柱 ----------------
def board():
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    hide = b.new("looks_hide")
    fa = b.new("control_forever")
    clr = b.new("pen_clear")
    psz = b.new("pen_setPenSizeTo", {"SIZE": N(50)})
    # 颜色随PM：直接用红色
    col = b.new("pen_setPenColorToColor", {"COLOR": C("#e63946")})
    g1 = b.new("motion_gotoxy", {"X": N(-210), "Y": N(-150)})
    pd = b.new("pen_penDown")
    mul = b.new("operator_multiply",
                {"NUM1": RN(b.new("data_variable", fields=vf(V_PM))), "NUM2": N(2.4)})
    add = b.new("operator_add", {"NUM1": N(-150), "NUM2": RN(mul)})
    g2 = b.new("motion_gotoxy", {"X": N(-210), "Y": RN(add)})
    pu = b.new("pen_penUp")
    b.link([hat, hide, fa])
    b.d[fa]["inputs"]["SUBSTACK"] = SUB(clr)
    b.link([clr, psz, col, g1, pd, g2, pu])
    return b


# ---------------- 按钮 ----------------
def btn(msg, addwind=False):
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    show = b.new("looks_show")
    b.link([hat, show])
    cl = b.new("event_whenthisspriteclicked", top=True, x=300)
    chain = [cl]
    if addwind:
        chw = b.new("data_changevariableby", {"VALUE": N(2)}, vf(V_WIND))
        say = b.new("looks_sayforsecs", {"MESSAGE": T("风力加大！"), "SECS": N(1)})
        chain += [chw, say]
    if msg:
        bc = b.new("event_broadcast",
                   {"BROADCAST_INPUT": [1, [11, BC[msg], msg]]})
        chain.append(bc)
    b.link(chain)
    return b


# ---------------- SVG ----------------
def bg():
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360">'
            '<rect width="480" height="360" fill="#5ea9dd"/>'
            '<rect y="300" width="480" height="60" fill="#7a8a99"/>'
            '<text x="110" y="34" font-family="sans-serif" font-size="22" '
            'fill="#ffffff">蓝天保卫战 · 大气治理</text></svg>')


def smoke_svg():
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40">'
            '<circle cx="20" cy="20" r="16" fill="#6b6b6b"/></svg>')


def haze_svg():
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="300">'
            '<rect width="480" height="300" fill="#9a9a9a"/></svg>')


def factory_svg():
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="160" height="90">'
            '<rect x="10" y="40" width="140" height="50" fill="#5b6770"/>'
            '<rect x="40" y="10" width="22" height="40" fill="#3d4750"/>'
            '<rect x="90" y="20" width="22" height="30" fill="#3d4750"/></svg>')


def tower_svg():
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="70" height="150">'
            '<rect x="20" y="20" width="30" height="130" fill="#48cae4"/>'
            '<polygon points="35,0 15,25 55,25" fill="#0096c7"/>'
            '<circle cx="35" cy="60" r="8" fill="#caf0f8"/>'
            '<circle cx="35" cy="95" r="8" fill="#caf0f8"/></svg>')


def button_svg(label, fill):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="150" height="50">'
            f'<rect x="2" y="2" width="146" height="46" rx="23" fill="{fill}" '
            'stroke="#fff" stroke-width="3"/>'
            f'<text x="75" y="33" font-family="sans-serif" font-size="20" '
            f'fill="#fff" text-anchor="middle">{label}</text></svg>')


def point_svg():
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="6" height="6">'
            '<circle cx="3" cy="3" r="3" fill="#000"/></svg>')


def build():
    a = Assets()
    stage = make_stage([a.costume("天空", bg(), 240, 180)],
                       {v: [VARS[v], 0] for v in VARS},
                       {k: BC[k] for k in BC})
    # 工厂(本体只装饰，不冒烟逻辑放烟雾)
    fb = B()
    fhat = fb.new("event_whenflagclicked", top=True)
    fgo = fb.new("motion_gotoxy", {"X": N(-120), "Y": N(-110)})
    fb.link([fhat, fgo])
    factory = make_sprite("工厂", fb, [a.costume("工厂", factory_svg(), 80, 45)],
                          2, -120, -110)

    sm = make_sprite("烟雾", smoke(), [a.costume("烟", smoke_svg(), 20, 20)],
                     5, 0, 0, visible=False)
    hz = make_sprite("雾霾层", haze(), [a.costume("霾", haze_svg(), 240, 150)],
                     6, 0, 30)
    tw = make_sprite("净化塔", tower(), [a.costume("塔", tower_svg(), 35, 75)],
                     3, 150, -60)
    bd = make_sprite("数据板", board(), [a.costume("点", point_svg(), 3, 3)],
                     1, 0, 0, visible=False)
    bp = make_sprite("启动净化", btn(BC_PURIFY),
                     [a.costume("净化", button_svg("启动净化", "#0096c7"), 75, 25)],
                     7, -150, 150)
    bw = make_sprite("起风按钮", btn(None, addwind=True),
                     [a.costume("起风", button_svg("起风 →", "#48cae4"), 75, 25)],
                     8, 150, 150)

    mons = [monitor(V_PM, VARS[V_PM], 5, 5),
            monitor(V_CLEAN, VARS[V_CLEAN], 5, 40),
            monitor(V_WIND, VARS[V_WIND], 5, 75, 0, 10)]
    info = package(OUT, [stage, factory, sm, hz, tw, bd, bp, bw], mons, a,
                   extensions=["pen"])
    print(f"已生成: {OUT}  角色{info['targets']} 积木{info['blocks']} {info['extensions']}")


if __name__ == "__main__":
    build()
