"""主题04 能源供给：光伏微电网
动态：太阳沿天空弧线运动(昼夜循环)，光伏随太阳高度变化；风车转速随风电变化；
      电网控制器逐小时计算 发电/用电/电池储能；房子电量不足变暗；
      画笔绘制 光伏/风电/电池 三柱实时变化。按钮：节能模式。
"""
from sb3lib import (B, N, WH, PN, T, C, R, RN, BOOL, SUB, MENU,
                    Assets, make_stage, make_sprite, monitor, package)

OUT = "/home/horde/isaac/haibao/04_光伏微电网.sb3"

V_HOUR = "v-hour"
V_SOLAR = "v-solar"
V_WIND = "v-wind"
V_BAT = "v-bat"
V_LOAD = "v-load"
VARS = {V_HOUR: "小时", V_SOLAR: "光伏", V_WIND: "风电", V_BAT: "电池储能",
        V_LOAD: "用电"}
BC_SAVE = "bc-save"
BC = {BC_SAVE: "节能模式"}


def vf(v):
    return {"VARIABLE": [VARS[v], v]}


# ---------------- 电网控制器（核心逻辑） ----------------
def controller():
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    h0 = b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_HOUR))
    bat0 = b.new("data_setvariableto", {"VALUE": T(40)}, vf(V_BAT))
    base0 = b.new("data_setvariableto", {"VALUE": T(30)}, vf(V_LOAD))
    fa = b.new("control_forever")

    # 小时 +1，超过23归0
    chgh = b.new("data_changevariableby", {"VALUE": N(1)}, vf(V_HOUR))
    hgt = b.new("operator_gt", {"OPERAND1": R(b.new("data_variable", fields=vf(V_HOUR))),
                                "OPERAND2": T(23)})
    ifh = b.new("control_if")
    seth = b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_HOUR))
    b.d[ifh]["inputs"]["CONDITION"] = BOOL(hgt)
    b.d[ifh]["inputs"]["SUBSTACK"] = SUB(seth)

    # 光伏 = round( 60 * sin(小时*15) )，夜间为负则置0
    mulang = b.new("operator_multiply",
                   {"NUM1": RN(b.new("data_variable", fields=vf(V_HOUR))), "NUM2": N(15)})
    sin = b.new("operator_mathop", {"NUM": RN(mulang)}, fields={"OPERATOR": ["sin", None]})
    mul60 = b.new("operator_multiply", {"NUM1": RN(sin), "NUM2": N(60)})
    rnd = b.new("operator_round", {"NUM": RN(mul60)})
    setsolar = b.new("data_setvariableto", {"VALUE": RN(rnd)}, vf(V_SOLAR))
    slt = b.new("operator_lt", {"OPERAND1": R(b.new("data_variable", fields=vf(V_SOLAR))),
                                "OPERAND2": T(0)})
    ifs = b.new("control_if")
    s0 = b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_SOLAR))
    b.d[ifs]["inputs"]["CONDITION"] = BOOL(slt)
    b.d[ifs]["inputs"]["SUBSTACK"] = SUB(s0)

    # 风电 = 随机 10..40
    wr = b.new("operator_random", {"FROM": N(10), "TO": N(40)})
    setwind = b.new("data_setvariableto", {"VALUE": RN(wr)}, vf(V_WIND))

    # 电池储能 += 光伏 + 风电 - 用电（夹在0..100）
    gen = b.new("operator_add",
                {"NUM1": RN(b.new("data_variable", fields=vf(V_SOLAR))),
                 "NUM2": RN(b.new("data_variable", fields=vf(V_WIND)))})
    net = b.new("operator_subtract",
                {"NUM1": RN(gen),
                 "NUM2": RN(b.new("data_variable", fields=vf(V_LOAD)))})
    # 缩放后加到电池：net/10
    div = b.new("operator_divide", {"NUM1": RN(net), "NUM2": N(10)})
    chgbat = b.new("data_changevariableby", {"VALUE": RN(div)}, vf(V_BAT))
    # 上限100
    bgt = b.new("operator_gt", {"OPERAND1": R(b.new("data_variable", fields=vf(V_BAT))),
                                "OPERAND2": T(100)})
    ifbg = b.new("control_if")
    b100 = b.new("data_setvariableto", {"VALUE": T(100)}, vf(V_BAT))
    b.d[ifbg]["inputs"]["CONDITION"] = BOOL(bgt)
    b.d[ifbg]["inputs"]["SUBSTACK"] = SUB(b100)
    # 下限0
    blt = b.new("operator_lt", {"OPERAND1": R(b.new("data_variable", fields=vf(V_BAT))),
                                "OPERAND2": T(0)})
    ifbl = b.new("control_if")
    b0 = b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_BAT))
    b.d[ifbl]["inputs"]["CONDITION"] = BOOL(blt)
    b.d[ifbl]["inputs"]["SUBSTACK"] = SUB(b0)

    wait = b.new("control_wait", {"DURATION": PN(0.5)})
    b.link([hat, h0, bat0, base0, fa])
    b.d[fa]["inputs"]["SUBSTACK"] = SUB(chgh)
    # 循环体顺序：改时→归零判断→算光伏→夜间归零→算风电→更新电池→上下限
    b.link([chgh, ifh, setsolar, ifs, setwind, chgbat, ifbg, ifbl, wait])
    return b


# ---------------- 太阳：沿弧线运动 ----------------
def sun():
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    fa = b.new("control_forever")
    # x = 小时*20 - 230
    mulx = b.new("operator_multiply",
                 {"NUM1": RN(b.new("data_variable", fields=vf(V_HOUR))), "NUM2": N(20)})
    addx = b.new("operator_subtract", {"NUM1": RN(mulx), "NUM2": N(230)})
    # y = 光伏*1.8 - 60 （白天高，夜里落下）
    muly = b.new("operator_multiply",
                 {"NUM1": RN(b.new("data_variable", fields=vf(V_SOLAR))), "NUM2": N(1.8)})
    addy = b.new("operator_subtract", {"NUM1": RN(muly), "NUM2": N(60)})
    goto = b.new("motion_gotoxy", {"X": RN(addx), "Y": RN(addy)})
    wait = b.new("control_wait", {"DURATION": PN(0.1)})
    b.link([hat, fa])
    b.d[fa]["inputs"]["SUBSTACK"] = SUB(goto)
    b.link([goto, wait])
    return b


# ---------------- 风车：随风电旋转 ----------------
def windmill():
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    go = b.new("motion_gotoxy", {"X": N(-150), "Y": N(40)})
    fa = b.new("control_forever")
    # 转速 = 风电/4 度
    div = b.new("operator_divide",
                {"NUM1": RN(b.new("data_variable", fields=vf(V_WIND))), "NUM2": N(4)})
    turn = b.new("motion_turnright", {"DEGREES": RN(div)})
    b.link([hat, go, fa])
    b.d[fa]["inputs"]["SUBSTACK"] = SUB(turn)
    return b


# ---------------- 房子：电量低变暗 ----------------
def house():
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    go = b.new("motion_gotoxy", {"X": N(120), "Y": N(-90)})
    fa = b.new("control_forever")
    # 电池>10 → 亮(ghost0) 否则 暗(ghost60)
    bgt = b.new("operator_gt", {"OPERAND1": R(b.new("data_variable", fields=vf(V_BAT))),
                                "OPERAND2": T(10)})
    ife = b.new("control_if_else")
    bright = b.new("looks_seteffectto", {"VALUE": N(0)},
                   fields={"EFFECT": ["BRIGHTNESS", None]})
    dark = b.new("looks_seteffectto", {"VALUE": N(-40)},
                 fields={"EFFECT": ["BRIGHTNESS", None]})
    b.d[ife]["inputs"]["CONDITION"] = BOOL(bgt)
    b.d[ife]["inputs"]["SUBSTACK"] = SUB(bright)
    b.d[ife]["inputs"]["SUBSTACK2"] = SUB(dark)
    b.link([hat, go, fa])
    b.d[fa]["inputs"]["SUBSTACK"] = SUB(ife)
    return b


# ---------------- 画笔三柱 ----------------
def board():
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    hide = b.new("looks_hide")
    fa = b.new("control_forever")
    clr = b.new("pen_clear")
    psz = b.new("pen_setPenSizeTo", {"SIZE": N(36)})
    seq = [clr, psz]

    def bar(x, vid, hexc, scale):
        col = b.new("pen_setPenColorToColor", {"COLOR": C(hexc)})
        g1 = b.new("motion_gotoxy", {"X": N(x), "Y": N(-150)})
        pd = b.new("pen_penDown")
        mul = b.new("operator_multiply",
                    {"NUM1": RN(b.new("data_variable", fields=vf(vid))), "NUM2": N(scale)})
        add = b.new("operator_add", {"NUM1": N(-150), "NUM2": RN(mul)})
        g2 = b.new("motion_gotoxy", {"X": N(x), "Y": RN(add)})
        pu = b.new("pen_penUp")
        seq.extend([col, g1, pd, g2, pu])

    bar(120, V_SOLAR, "#ffd166", 1.6)
    bar(170, V_WIND, "#80ed99", 2.4)
    bar(220, V_BAT, "#48cae4", 1.6)
    b.link([hat, hide, fa])
    b.d[fa]["inputs"]["SUBSTACK"] = SUB(clr)
    b.link(seq)
    return b


def btn():
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    show = b.new("looks_show")
    b.link([hat, show])
    cl = b.new("event_whenthisspriteclicked", top=True, x=300)
    setload = b.new("data_setvariableto", {"VALUE": T(18)}, vf(V_LOAD))
    say = b.new("looks_sayforsecs", {"MESSAGE": T("已开启节能模式，用电下降！"),
                                     "SECS": N(1.5)})
    b.link([cl, setload, say])
    return b


# ---------------- SVG ----------------
def bg():
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360">'
            '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0" stop-color="#1d3557"/>'
            '<stop offset="0.6" stop-color="#fca311"/>'
            '<stop offset="1" stop-color="#e5e5e5"/></linearGradient></defs>'
            '<rect width="480" height="360" fill="url(#g)"/>'
            '<rect y="300" width="480" height="60" fill="#6b705c"/>'
            '<text x="120" y="34" font-family="sans-serif" font-size="22" '
            'fill="#fff">光伏微电网 · 能源调度</text></svg>')


def sun_svg():
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="70" height="70">'
            '<circle cx="35" cy="35" r="20" fill="#ffd60a"/>'
            + "".join(f'<line x1="35" y1="35" x2="{35+30*__import__("math").cos(a)}" '
                      f'y2="{35+30*__import__("math").sin(a)}" stroke="#ffd60a" '
                      'stroke-width="3"/>'
                      for a in [i*0.785 for i in range(8)])
            + '</svg>')


def windmill_svg():
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80">'
            '<circle cx="40" cy="40" r="6" fill="#495057"/>'
            '<polygon points="40,40 44,4 36,4" fill="#e9ecef"/>'
            '<polygon points="40,40 76,44 76,36" fill="#e9ecef"/>'
            '<polygon points="40,40 36,76 44,76" fill="#e9ecef"/></svg>')


def house_svg():
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="90" height="80">'
            '<rect x="15" y="35" width="60" height="40" fill="#e9c46a"/>'
            '<polygon points="10,35 45,5 80,35" fill="#e76f51"/>'
            '<rect x="38" y="50" width="16" height="25" fill="#6f4518"/>'
            '<rect x="22" y="44" width="12" height="12" fill="#fff3b0"/></svg>')


def point_svg():
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="6" height="6">'
            '<circle cx="3" cy="3" r="3" fill="#000"/></svg>')


def button_svg(label, fill):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="160" height="50">'
            f'<rect x="2" y="2" width="156" height="46" rx="23" fill="{fill}" '
            'stroke="#fff" stroke-width="3"/>'
            f'<text x="80" y="33" font-family="sans-serif" font-size="20" '
            f'fill="#fff" text-anchor="middle">{label}</text></svg>')


def build():
    a = Assets()
    stage = make_stage([a.costume("天空", bg(), 240, 180)],
                       {v: [VARS[v], 0] for v in VARS}, {k: BC[k] for k in BC})
    ctl = make_sprite("电网控制器", controller(),
                      [a.costume("点", point_svg(), 3, 3)], 1, 0, 0, visible=False)
    su = make_sprite("太阳", sun(), [a.costume("日", sun_svg(), 35, 35)],
                     3, -200, 80)
    wm = make_sprite("风车", windmill(), [a.costume("风车", windmill_svg(), 40, 40)],
                     4, -150, 40)
    ho = make_sprite("房子", house(), [a.costume("家", house_svg(), 45, 40)],
                     2, 120, -90)
    bd = make_sprite("数据板", board(), [a.costume("点", point_svg(), 3, 3)],
                     5, 0, 0, visible=False)
    bs = make_sprite("节能按钮", btn(),
                     [a.costume("节能", button_svg("节能模式", "#2a9d8f"), 80, 25)],
                     6, -150, 150)
    mons = [monitor(V_HOUR, VARS[V_HOUR], 5, 5, 0, 23),
            monitor(V_SOLAR, VARS[V_SOLAR], 5, 40, 0, 60),
            monitor(V_WIND, VARS[V_WIND], 5, 75, 0, 40),
            monitor(V_BAT, VARS[V_BAT], 5, 110),
            monitor(V_LOAD, VARS[V_LOAD], 5, 145, 0, 60)]
    info = package(OUT, [stage, ctl, su, wm, ho, bd, bs], mons, a,
                   extensions=["pen"])
    print(f"已生成: {OUT}  角色{info['targets']} 积木{info['blocks']} {info['extensions']}")


if __name__ == "__main__":
    build()
