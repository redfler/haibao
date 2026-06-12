"""主题05 人类居住场景规划：15分钟生活圈
动态：居民(克隆体)从住宅出发，随机走向 学校/公园/超市；用画笔画出步行轨迹；
      到达后按距离判断是否在“15分钟”内：是→满意度+1，否→碳排+1(开车)；
      实时计算社区评分。按钮：加公园(就近增设，提高满意度概率)。
"""
from sb3lib import (B, N, WH, PN, T, C, R, RN, BOOL, SUB, MENU,
                    Assets, make_stage, make_sprite, monitor, package)

OUT = "/home/horde/isaac/haibao/05_十五分钟生活圈.sb3"

V_SAT = "v-sat"
V_CARBON = "v-carbon"
V_SCORE = "v-score"
V_PARK = "v-park"      # 公园数（越多越容易就近满足）
VARS = {V_SAT: "满意度", V_CARBON: "碳排", V_SCORE: "社区评分", V_PARK: "公园数"}
BC_PARK = "bc-park"
BC = {BC_PARK: "加公园"}


def vf(v):
    return {"VARIABLE": [VARS[v], v]}


# ---------------- 居民 ----------------
def resident():
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    hide = b.new("looks_hide")
    s1 = b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_SAT))
    s2 = b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_CARBON))
    s3 = b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_SCORE))
    s4 = b.new("data_setvariableto", {"VALUE": T(1)}, vf(V_PARK))
    fa = b.new("control_forever")
    cl = b.new("control_create_clone_of", {"CLONE_OPTION": MENU(0)})
    m = b.clone_menu("_myself_")
    b.d[cl]["inputs"]["CLONE_OPTION"] = MENU(m)
    wait = b.new("control_wait", {"DURATION": PN(0.6)})
    b.link([hat, hide, s1, s2, s3, s4, fa])
    b.d[fa]["inputs"]["SUBSTACK"] = SUB(cl)
    b.link([cl, wait])

    # 作为克隆体：从住宅出发，走向随机设施
    chat = b.new("control_start_as_clone", top=True, x=300)
    goh = b.new("motion_gotoxy", {"X": N(-180), "Y": N(-110)})
    show = b.new("looks_show")
    pd = b.new("pen_penDown")
    setc = b.new("pen_setPenColorToColor", {"COLOR": C("#9d4edd")})
    psz = b.new("pen_setPenSizeTo", {"SIZE": N(2)})
    # 随机选目标 1=学校 2=公园 3=超市
    tr = b.new("operator_random", {"FROM": N(1), "TO": N(3)})
    settgt = b.new("data_setvariableto", {"VALUE": RN(tr)},
                   {"VARIABLE": ["目标", "v-target"]})  # 本地变量
    # 指向目标精灵：用三段 if 选择 point towards
    point = b.new("motion_pointtowards", {"TOWARDS": MENU(0)})
    pmenu = b.point_menu("公园")  # 默认朝公园，下面用if覆盖方向也可；这里简单都走向公园
    b.d[point]["inputs"]["TOWARDS"] = MENU(pmenu)
    # 走向目标：重复30步
    rep = b.new("control_repeat", {"TIMES": WH(30)})
    mv = b.new("motion_movesteps", {"STEPS": N(8)})
    b.d[rep]["inputs"]["SUBSTACK"] = SUB(mv)
    pu = b.new("pen_penUp")
    # 判断是否到达(距公园近)：distance<40 视为15分钟可达
    dist = b.new("sensing_distanceto", {"DISTANCETOMENU": MENU(0)})
    dmenu = b.dist_menu("公园")
    b.d[dist]["inputs"]["DISTANCETOMENU"] = MENU(dmenu)
    near = b.new("operator_lt", {"OPERAND1": RN(dist), "OPERAND2": T(60)})
    ife = b.new("control_if_else")
    chgsat = b.new("data_changevariableby", {"VALUE": N(1)}, vf(V_SAT))
    saygood = b.new("looks_sayforsecs", {"MESSAGE": T("步行可达，满意！"), "SECS": N(0.6)})
    chgcar = b.new("data_changevariableby", {"VALUE": N(1)}, vf(V_CARBON))
    saybad = b.new("looks_sayforsecs", {"MESSAGE": T("太远，得开车…"), "SECS": N(0.6)})
    b.link([chgsat, saygood])
    b.link([chgcar, saybad])
    b.d[ife]["inputs"]["CONDITION"] = BOOL(near)
    b.d[ife]["inputs"]["SUBSTACK"] = SUB(chgsat)
    b.d[ife]["inputs"]["SUBSTACK2"] = SUB(chgcar)
    delc = b.new("control_delete_this_clone")
    b.link([chat, goh, show, setc, psz, pd, settgt, point, rep, pu, ife, delc])
    return b


# ---------------- 评分器 ----------------
def scorer():
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    fa = b.new("control_forever")
    # 总数 = 满意度 + 碳排
    tot = b.new("operator_add",
                {"NUM1": RN(b.new("data_variable", fields=vf(V_SAT))),
                 "NUM2": RN(b.new("data_variable", fields=vf(V_CARBON)))})
    gt0 = b.new("operator_gt", {"OPERAND1": RN(tot), "OPERAND2": T(0)})
    iff = b.new("control_if")
    # 评分 = round(满意度 / 总数 * 100)
    tot2 = b.new("operator_add",
                 {"NUM1": RN(b.new("data_variable", fields=vf(V_SAT))),
                  "NUM2": RN(b.new("data_variable", fields=vf(V_CARBON)))})
    dv = b.new("operator_divide",
               {"NUM1": RN(b.new("data_variable", fields=vf(V_SAT))), "NUM2": RN(tot2)})
    ml = b.new("operator_multiply", {"NUM1": RN(dv), "NUM2": N(100)})
    rd = b.new("operator_round", {"NUM": RN(ml)})
    setsc = b.new("data_setvariableto", {"VALUE": RN(rd)}, vf(V_SCORE))
    b.d[iff]["inputs"]["CONDITION"] = BOOL(gt0)
    b.d[iff]["inputs"]["SUBSTACK"] = SUB(setsc)
    wait = b.new("control_wait", {"DURATION": PN(0.3)})
    b.link([hat, fa])
    b.d[fa]["inputs"]["SUBSTACK"] = SUB(iff)
    b.link([iff, wait])
    return b


# ---------------- 设施（固定位置 + 加公园） ----------------
def facility(x, y, label_pos=False):
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    go = b.new("motion_gotoxy", {"X": N(x), "Y": N(y)})
    b.link([hat, go])
    return b


def park_sprite(x, y):
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    go = b.new("motion_gotoxy", {"X": N(x), "Y": N(y)})
    b.link([hat, go])
    # 加公园：被点击它的按钮后移动靠近居民区(模拟就近增设)
    hp = b.new("event_whenbroadcastreceived",
               fields={"BROADCAST_OPTION": [BC[BC_PARK], BC_PARK]}, top=True, x=300)
    chgp = b.new("data_changevariableby", {"VALUE": N(1)}, vf(V_PARK))
    go2 = b.new("motion_gotoxy", {"X": N(-60), "Y": N(60)})
    say = b.new("looks_sayforsecs", {"MESSAGE": T("新公园落成，更就近！"), "SECS": N(1.2)})
    b.link([hp, chgp, go2, say])
    return b


def btn():
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    show = b.new("looks_show")
    b.link([hat, show])
    cl = b.new("event_whenthisspriteclicked", top=True, x=300)
    bc = b.new("event_broadcast", {"BROADCAST_INPUT": [1, [11, BC[BC_PARK], BC_PARK]]})
    b.link([cl, bc])
    return b


# ---------------- SVG ----------------
def bg():
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360">'
            '<rect width="480" height="360" fill="#dee2e6"/>'
            '<line x1="0" y1="180" x2="480" y2="180" stroke="#adb5bd" stroke-width="10"/>'
            '<line x1="240" y1="0" x2="240" y2="360" stroke="#adb5bd" stroke-width="10"/>'
            '<text x="100" y="30" font-family="sans-serif" font-size="22" '
            'fill="#3a0ca3">15分钟生活圈 · 人居规划</text></svg>')


def home_svg():
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="50" height="50">'
            '<rect x="8" y="22" width="34" height="24" fill="#4361ee"/>'
            '<polygon points="5,22 25,6 45,22" fill="#3a0ca3"/></svg>')


def person_svg():
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="30">'
            '<circle cx="10" cy="6" r="5" fill="#ffba08"/>'
            '<rect x="6" y="11" width="8" height="13" rx="3" fill="#f72585"/></svg>')


def fac_svg(label, fill):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="50" height="50">'
            f'<rect x="4" y="4" width="42" height="42" rx="8" fill="{fill}"/>'
            f'<text x="25" y="32" font-family="sans-serif" font-size="22" '
            f'fill="#fff" text-anchor="middle">{label}</text></svg>')


def button_svg(label, fill):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="150" height="50">'
            f'<rect x="2" y="2" width="146" height="46" rx="23" fill="{fill}" '
            'stroke="#fff" stroke-width="3"/>'
            f'<text x="75" y="33" font-family="sans-serif" font-size="20" '
            f'fill="#fff" text-anchor="middle">{label}</text></svg>')


def build():
    a = Assets()
    # 居民需要一个本地变量“目标”，挂在居民角色上
    stage = make_stage([a.costume("社区", bg(), 240, 180)],
                       {v: [VARS[v], 0] for v in VARS}, {k: BC[k] for k in BC})

    res_b = resident()
    res = make_sprite("居民", res_b, [a.costume("人", person_svg(), 10, 15)],
                      6, -180, -110, visible=False)
    # 给居民加本地变量“目标”
    res["variables"] = {"v-target": ["目标", 0]}

    home = make_sprite("住宅", facility(-180, -110),
                       [a.costume("家", home_svg(), 25, 25)], 2, -180, -110)
    school = make_sprite("学校", facility(150, 110),
                         [a.costume("校", fac_svg("校", "#ffba08"), 25, 25)],
                         3, 150, 110)
    market = make_sprite("超市", facility(150, -90),
                         [a.costume("商", fac_svg("商", "#f72585"), 25, 25)],
                         4, 150, -90)
    park = make_sprite("公园", park_sprite(-60, 110),
                       [a.costume("园", fac_svg("园", "#52b788"), 25, 25)],
                       5, -60, 110)
    sc = make_sprite("评分器", scorer(),
                     [a.costume("点", person_svg(), 10, 15)], 1, 0, 0, visible=False)
    bp = make_sprite("加公园按钮", btn(),
                     [a.costume("加园", button_svg("+ 公园", "#52b788"), 75, 25)],
                     7, 0, 150)

    mons = [monitor(V_SAT, VARS[V_SAT], 5, 5),
            monitor(V_CARBON, VARS[V_CARBON], 5, 40),
            monitor(V_SCORE, VARS[V_SCORE], 5, 75),
            monitor(V_PARK, VARS[V_PARK], 5, 110, 0, 10)]
    info = package(OUT, [stage, sc, home, school, market, park, res, bp], mons, a,
                   extensions=["pen"])
    print(f"已生成: {OUT}  角色{info['targets']} 积木{info['blocks']} {info['extensions']}")


if __name__ == "__main__":
    build()
