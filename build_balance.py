"""主题03 生态系统：草—羊—狼食物链（寻路觅食版）

三个角色：草、羊、狼，均用克隆体表示个体。

核心改动：羊/狼不再随机游走，而是【检测最近的食物，朝它移动】。
  由于 Scratch 的「面向角色 / 到角色的距离」对克隆体只认本体，
  这里用全局列表记录所有个体坐标实现“找最近”：
    · 草本体周期性清空 [草X][草Y] 并广播[报草位]，每株草把自身坐标写入
    · 羊本体周期性清空 [羊X][羊Y] 并广播[报羊位]，每只羊把自身坐标写入
    · 羊遍历 [草X][草Y] 找最近的草、狼遍历 [羊X][羊Y] 找最近的羊，朝目标移动

其余规则：
  · 开局只随机生成草；羊、狼由「新增羊/新增狼」按钮投放
  · [草再生间隔]=3s 周期随机长草；[羊繁衍间隔]=6s、[狼繁衍间隔]=9s 按各自数量一半繁衍(>2才繁衍)
  · 草碰到羊→草消失；羊碰到狼→羊消失
  · [羊饿死间隔]=10s / [狼饿死间隔]=10s：超时没吃到食物则死亡
  · [羊行动间隔]/[狼行动间隔]：平时1秒，吃到食物后下一次3秒再变回1秒
"""
from sb3lib import (B, N, WH, PN, T, C, R, RN, BOOL, SUB, MENU,
                    Assets, make_stage, make_sprite, monitor, package)

OUT = "/home/horde/isaac/haibao/生态平衡.sb3"
# 目标比例 草:羊:狼 = 150:75:5。不用调节器，靠“食物驱动繁殖 + 饥饿/捕食死亡 +
# 承载力上限(到上限就不再繁殖)”这套规则自然平衡。参数由 search_150.py 寻优。
SPEED_S = 12      # 羊移动速度
SPEED_W = 16      # 狼略快，才能偶尔抓到羊

# ---- 全局变量 ----
V_GRASS, V_SHEEP, V_WOLF = "v-grass", "v-sheep", "v-wolf"
V_GINT, V_SBREED, V_WBREED = "v-gint", "v-sint", "v-wint"
V_SSTV, V_WSTV = "v-sstv", "v-wstv"
V_RS, V_RW = "v-rs", "v-rw"   # 草羊比、羊狼比（决定 150:75:5）
VARS = {
    V_GRASS: "草数量", V_SHEEP: "羊数量", V_WOLF: "狼数量",
    V_GINT: "草再生间隔",        # 默认1：每秒长一批草
    V_SBREED: "羊繁殖食量",      # 默认1：羊每吃1株草生1只小羊
    V_WBREED: "狼繁殖食量",      # 默认3：狼每吃3只羊生1只小狼
    V_SSTV: "羊饿死间隔", V_WSTV: "狼饿死间隔",
    V_RS: "草羊比", V_RW: "羊狼比",   # 草:羊=草羊比:1(=2)，羊:狼=羊狼比:1(=15)
}
# ---- 全局列表（个体坐标）----
LX_G, LY_G = ["草X", "l-gx"], ["草Y", "l-gy"]
LX_S, LY_S = ["羊X", "l-sx"], ["羊Y", "l-sy"]
LX_W, LY_W = ["狼X", "l-wx"], ["狼Y", "l-wy"]
LISTS = {l[1]: l[0] for l in (LX_G, LY_G, LX_S, LY_S, LX_W, LY_W)}

# ---- 每克隆体本地变量 ----
SHEEP_EAT, SHEEP_ACT = ("v-sheepeat", "羊进食时刻"), ("v-sact", "羊行动间隔")
WOLF_EAT, WOLF_ACT = ("v-wolfeat", "狼进食时刻"), ("v-wact", "狼行动间隔")
SHEEP_EN, WOLF_EN = ("v-sen", "羊能量"), ("v-wen", "狼能量")   # 累计进食量，达到繁殖食量即繁殖
# 寻路用本地变量 (目标x, 目标y, 最近距, 临时距, 序号)
SHEEP_SEEK = [("s-tx", "羊目标x"), ("s-ty", "羊目标y"), ("s-min", "羊最近距"),
              ("s-d", "羊距"), ("s-i", "羊序")]
# 羊用来“找最近的狼”以躲避
SHEEP_AVOID = [("sa-tx", "近狼x"), ("sa-ty", "近狼y"), ("sa-min", "近狼距"),
               ("sa-d", "狼距临时"), ("sa-i", "狼序")]
WOLF_SEEK = [("w-tx", "狼目标x"), ("w-ty", "狼目标y"), ("w-min", "狼最近距"),
             ("w-d", "狼距"), ("w-i", "狼序")]

# ---- 广播 ----
BC_ADDS, BC_ADDW = "bc-adds", "bc-addw"
BC_REPG, BC_REPS, BC_REPW = "bc-repg", "bc-reps", "bc-repw"
BC = {BC_ADDS: "新增羊", BC_ADDW: "新增狼",
      BC_REPG: "报草位", BC_REPS: "报羊位", BC_REPW: "报狼位"}

# 承载力上限即目标比例 150:75:5（到上限就不再繁殖——这是“密度规则”，不是调节器）
CAP_GRASS, CAP_SHEEP, CAP_WOLF = 150, 75, 5
DANGER2 = 71 * 71     # 羊的避狼半径（平方）


def vf(v):
    return {"VARIABLE": [VARS[v], v]}


def lf(loc):
    return {"VARIABLE": [loc[1], loc[0]]}


def var(b, loc):
    return b.new("data_variable", fields=lf(loc))


def gvar(b, v):
    return b.new("data_variable", fields=vf(v))


# ---- 列表/坐标 积木助手 ----
def L_add(b, lst, item):
    return b.new("data_addtolist", {"ITEM": item}, {"LIST": lst})


def L_delall(b, lst):
    return b.new("data_deletealloflist", fields={"LIST": lst})


def L_item(b, lst, idx):
    return b.new("data_itemoflist", {"INDEX": idx}, {"LIST": lst})


def L_len(b, lst):
    return b.new("data_lengthoflist", fields={"LIST": lst})


def xpos(b):
    return b.new("motion_xposition")


def ypos(b):
    return b.new("motion_yposition")


def clone_self(b):
    c = b.new("control_create_clone_of", {"CLONE_OPTION": MENU(0)})
    b.d[c]["inputs"]["CLONE_OPTION"] = MENU(b.clone_menu("_myself_"))
    return c


def repeat_clone(b, times_input):
    rep = b.new("control_repeat", {"TIMES": times_input})
    b.d[rep]["inputs"]["SUBSTACK"] = SUB(clone_self(b))
    return rep


def goto_random(b):
    sx = b.new("operator_random", {"FROM": N(-220), "TO": N(200)})
    sy = b.new("operator_random", {"FROM": N(-150), "TO": N(150)})
    return b.new("motion_gotoxy", {"X": RN(sx), "Y": RN(sy)})


def timer(b):
    return b.new("sensing_timer")


def touching(b, name):
    t = b.new("sensing_touchingobject", {"TOUCHINGOBJECTMENU": MENU(0)})
    b.d[t]["inputs"]["TOUCHINGOBJECTMENU"] = MENU(b.touch_menu(name))
    return t


def report_handler(b, bc_id, lx, ly):
    """收到[报X位]→把自身坐标写入列表（克隆体执行）"""
    ha = b.new("event_whenbroadcastreceived",
               fields={"BROADCAST_OPTION": [BC[bc_id], bc_id]}, top=True, x=900)
    ax = L_add(b, lx, RN(xpos(b)))
    ay = L_add(b, ly, RN(ypos(b)))
    b.link([ha, ax, ay])


def rebuild_loop(b, bc_id, lx, ly):
    """本体周期性重建坐标列表：清空→广播并等待各克隆上报→稍候"""
    hat = b.new("event_whenflagclicked", top=True, x=1100)
    fa = b.new("control_forever")
    d1 = L_delall(b, lx)
    d2 = L_delall(b, ly)
    bcast = b.new("event_broadcastandwait",
                  {"BROADCAST_INPUT": [1, [11, BC[bc_id], bc_id]]})
    w = b.new("control_wait", {"DURATION": PN(0.3)})
    b.link([hat, fa])
    b.d[fa]["inputs"]["SUBSTACK"] = SUB(d1)
    b.link([d1, d2, bcast, w])


def find_nearest(b, sk, lx, ly):
    """遍历坐标列表，找最近的目标写入 sk 的(目标x,目标y,最近距)。
    返回(首块, 末块=repeat)。若列表为空，目标默认为自身、最近距=999999。"""
    tx, ty, mn, dd, idx = sk
    setmin = b.new("data_setvariableto", {"VALUE": T(999999)}, lf(mn))
    settx = b.new("data_setvariableto", {"VALUE": RN(xpos(b))}, lf(tx))
    setty = b.new("data_setvariableto", {"VALUE": RN(ypos(b))}, lf(ty))
    seti = b.new("data_setvariableto", {"VALUE": T(1)}, lf(idx))
    rep = b.new("control_repeat", {"TIMES": RN(L_len(b, lx))})

    def diff(lst, pos):
        return b.new("operator_subtract",
                     {"NUM1": RN(L_item(b, lst, RN(var(b, idx)))), "NUM2": RN(pos(b))})
    sqx = b.new("operator_multiply", {"NUM1": RN(diff(lx, xpos)), "NUM2": RN(diff(lx, xpos))})
    sqy = b.new("operator_multiply", {"NUM1": RN(diff(ly, ypos)), "NUM2": RN(diff(ly, ypos))})
    dsum = b.new("operator_add", {"NUM1": RN(sqx), "NUM2": RN(sqy)})
    setdd = b.new("data_setvariableto", {"VALUE": RN(dsum)}, lf(dd))
    cond = b.new("operator_lt", {"OPERAND1": RN(var(b, dd)), "OPERAND2": RN(var(b, mn))})
    iff = b.new("control_if")
    m1 = b.new("data_setvariableto", {"VALUE": RN(var(b, dd))}, lf(mn))
    m2 = b.new("data_setvariableto", {"VALUE": RN(L_item(b, lx, RN(var(b, idx))))}, lf(tx))
    m3 = b.new("data_setvariableto", {"VALUE": RN(L_item(b, ly, RN(var(b, idx))))}, lf(ty))
    b.link([m1, m2, m3])
    b.d[iff]["inputs"]["CONDITION"] = BOOL(cond)
    b.d[iff]["inputs"]["SUBSTACK"] = SUB(m1)
    chgi = b.new("data_changevariableby", {"VALUE": N(1)}, lf(idx))
    b.d[rep]["inputs"]["SUBSTACK"] = SUB(setdd)
    b.link([setdd, iff, chgi])
    b.link([setmin, settx, setty, seti, rep])
    return setmin, rep


def _step(b, target, away, speed):
    """朝 target(本地变量元组) 移动一步；away=True 则反向（逃离）。返回(首,尾)。"""
    tx, ty = target
    near, far = (N(-speed), N(speed)) if away else (N(speed), N(-speed))
    cx = b.new("operator_lt", {"OPERAND1": RN(xpos(b)), "OPERAND2": RN(var(b, tx))})
    ifx = b.new("control_if_else")
    px = b.new("motion_changexby", {"DX": near})
    nx = b.new("motion_changexby", {"DX": far})
    b.d[ifx]["inputs"]["CONDITION"] = BOOL(cx)
    b.d[ifx]["inputs"]["SUBSTACK"] = SUB(px)
    b.d[ifx]["inputs"]["SUBSTACK2"] = SUB(nx)
    cy = b.new("operator_lt", {"OPERAND1": RN(ypos(b)), "OPERAND2": RN(var(b, ty))})
    ify = b.new("control_if_else")
    py = b.new("motion_changeyby", {"DY": near})
    ny = b.new("motion_changeyby", {"DY": far})
    b.d[ify]["inputs"]["CONDITION"] = BOOL(cy)
    b.d[ify]["inputs"]["SUBSTACK"] = SUB(py)
    b.d[ify]["inputs"]["SUBSTACK2"] = SUB(ny)
    b.link([ifx, ify])
    return ifx, ify


def move_chase(b, sk, lx, ly, speed):
    """狼用：找最近食物 → 朝它移动 → 切换造型。返回(首,尾)。"""
    f, last = find_nearest(b, sk, lx, ly)
    mf, ml = _step(b, (sk[0], sk[1]), away=False, speed=speed)
    nc = b.new("looks_nextcostume")
    b.link([last, mf])
    b.link([ml, nc])
    return f, nc


def move_flee_or_chase(b, food_sk, food_lx, food_ly, wolf_sk, wlx, wly):
    """羊用：找最近草 + 找最近狼；若狼在危险半径内则逃离，否则走向草。"""
    f1, l1 = find_nearest(b, food_sk, food_lx, food_ly)
    f2, l2 = find_nearest(b, wolf_sk, wlx, wly)
    danger = b.new("operator_lt",
                   {"OPERAND1": RN(var(b, wolf_sk[2])), "OPERAND2": T(DANGER2)})
    ife = b.new("control_if_else")
    flee_f, flee_l = _step(b, (wolf_sk[0], wolf_sk[1]), away=True, speed=SPEED_S)
    chase_f, chase_l = _step(b, (food_sk[0], food_sk[1]), away=False, speed=SPEED_S)
    b.d[ife]["inputs"]["CONDITION"] = BOOL(danger)
    b.d[ife]["inputs"]["SUBSTACK"] = SUB(flee_f)
    b.d[ife]["inputs"]["SUBSTACK2"] = SUB(chase_f)
    nc = b.new("looks_nextcostume")
    b.link([l1, f2])     # 草搜索 → 狼搜索
    b.link([l2, ife, nc])
    return f1, nc


# ==================== 草 ====================
def grass():
    b = B()
    # 脚本1：绿旗 → 初始化参数 + 随机初始草 + 周期再生
    hat = b.new("event_whenflagclicked", top=True)
    hide = b.new("looks_hide")
    inits = [b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_GRASS))]
    # 食物驱动平衡参数（search_150 寻优）：羊吃1株草生1、狼吃3只羊生1、饿死22/10
    for vid, val in [(V_GINT, 1), (V_SBREED, 1), (V_WBREED, 3), (V_SSTV, 22),
                     (V_WSTV, 11), (V_RS, 2), (V_RW, 15)]:
        inits.append(b.new("data_setvariableto", {"VALUE": T(val)}, vf(vid)))
    rst = b.new("sensing_resettimer")
    n0 = b.new("operator_random", {"FROM": N(140), "TO": N(150)})   # 草初始≈承载力150
    rep0 = repeat_clone(b, RN(n0))
    fa = b.new("control_forever")
    waitg = b.new("control_wait", {"DURATION": RN(gvar(b, V_GINT))})
    capic = b.new("operator_lt", {"OPERAND1": R(gvar(b, V_GRASS)), "OPERAND2": T(CAP_GRASS)})
    ifcap = b.new("control_if")
    nn = b.new("operator_random", {"FROM": N(5), "TO": N(19)})
    repg = repeat_clone(b, RN(nn))
    b.d[ifcap]["inputs"]["CONDITION"] = BOOL(capic)
    b.d[ifcap]["inputs"]["SUBSTACK"] = SUB(repg)
    b.link([hat, hide] + inits + [rst, rep0, fa])
    b.d[fa]["inputs"]["SUBSTACK"] = SUB(waitg)
    b.link([waitg, ifcap])

    # 脚本2：作为克隆体 → 随机散布；碰到羊被吃
    chat = b.new("control_start_as_clone", top=True, x=300)
    goto = goto_random(b)
    show = b.new("looks_show")
    addg = b.new("data_changevariableby", {"VALUE": N(1)}, vf(V_GRASS))
    cfa = b.new("control_forever")
    teat = touching(b, "羊")
    ife = b.new("control_if")
    subg = b.new("data_changevariableby", {"VALUE": N(-1)}, vf(V_GRASS))
    delc = b.new("control_delete_this_clone")
    b.link([subg, delc])
    b.d[ife]["inputs"]["CONDITION"] = BOOL(teat)
    b.d[ife]["inputs"]["SUBSTACK"] = SUB(subg)
    cw = b.new("control_wait", {"DURATION": PN(0.1)})
    b.link([chat, goto, show, addg, cfa])
    b.d[cfa]["inputs"]["SUBSTACK"] = SUB(ife)
    b.link([ife, cw])

    # 脚本：坐标列表维护
    rebuild_loop(b, BC_REPG, LX_G, LY_G)   # 本体重建
    report_handler(b, BC_REPG, LX_G, LY_G)  # 克隆上报
    return b


# ==================== 通用动物（羊/狼） ====================
def animal(count_var, eat_local, act_local, en_local, breed_var, move_builder,
           food, predator, report_bc, report_lists, food_count, ratio_var,
           add_bc, add_lo, add_hi, init_lo, init_hi):
    b = B()
    # 脚本1：绿旗 → 数量清零 + 按平衡数量初始生成
    hat = b.new("event_whenflagclicked", top=True)
    hide = b.new("looks_hide")
    c0 = b.new("data_setvariableto", {"VALUE": T(0)}, vf(count_var))
    n0 = b.new("operator_random", {"FROM": N(init_lo), "TO": N(init_hi)})
    rep0 = repeat_clone(b, RN(n0))
    b.link([hat, hide, c0, rep0])

    # 脚本2：新增按钮 → 随机新增若干（手动扰动）
    ha = b.new("event_whenbroadcastreceived",
               fields={"BROADCAST_OPTION": [BC[add_bc], add_bc]}, top=True, x=300)
    na = b.new("operator_random", {"FROM": N(add_lo), "TO": N(add_hi)})
    repa = repeat_clone(b, RN(na))
    b.link([ha, repa])

    # 脚本3：作为克隆体
    chat = b.new("control_start_as_clone", top=True, x=600)
    goto = goto_random(b)
    show = b.new("looks_show")
    chgcnt = b.new("data_changevariableby", {"VALUE": N(1)}, vf(count_var))
    set_eat0 = b.new("data_setvariableto", {"VALUE": RN(timer(b))}, lf(eat_local))
    set_act0 = b.new("data_setvariableto", {"VALUE": T(1)}, lf(act_local))
    set_en0 = b.new("data_setvariableto", {"VALUE": T(0)}, lf(en_local))
    fa2 = b.new("control_forever")
    sfirst, slast = move_builder(b)   # 寻路觅食（羊会避狼）
    # 碰到食物 → 刷新进食时刻 + 行动间隔3秒 + 能量+1 + 够食量则繁殖
    tfood = touching(b, food)
    if_food = b.new("control_if")
    set_eat = b.new("data_setvariableto", {"VALUE": RN(timer(b))}, lf(eat_local))
    set_act3 = b.new("data_setvariableto", {"VALUE": T(3)}, lf(act_local))
    en_inc = b.new("data_changevariableby", {"VALUE": N(1)}, lf(en_local))
    # 能量 >= 繁殖食量 → 克隆自己（无数量上限封顶），能量清零
    en_ge = b.new("operator_not",
                  {"OPERAND": BOOL(b.new("operator_lt",
                                         {"OPERAND1": RN(var(b, en_local)),
                                          "OPERAND2": RN(gvar(b, breed_var))}))})
    if_breed = b.new("control_if")
    bclone = clone_self(b)
    reset_en = b.new("data_setvariableto", {"VALUE": T(0)}, lf(en_local))
    b.link([bclone, reset_en])
    b.d[if_breed]["inputs"]["CONDITION"] = BOOL(en_ge)
    b.d[if_breed]["inputs"]["SUBSTACK"] = SUB(bclone)
    b.link([set_eat, set_act3, en_inc, if_breed])
    b.d[if_food]["inputs"]["CONDITION"] = BOOL(tfood)
    b.d[if_food]["inputs"]["SUBSTACK"] = SUB(set_eat)
    body = [if_food]
    # 密度/比例制约死亡（非封顶）：随机(0,数量) > 食物/比例 → 个体死亡
    #   羊：随机(0,羊数量) > 草数量/草羊比 ；狼：随机(0,狼数量) > 羊数量/羊狼比
    rnd = b.new("operator_random", {"FROM": N(0), "TO": R(gvar(b, count_var))})
    tgt = b.new("operator_divide", {"NUM1": RN(gvar(b, food_count)), "NUM2": RN(gvar(b, ratio_var))})
    over_d = b.new("operator_gt", {"OPERAND1": RN(rnd), "OPERAND2": RN(tgt)})
    if_dense = b.new("control_if")
    dd_ = b.new("data_changevariableby", {"VALUE": N(-1)}, vf(count_var))
    ddel = b.new("control_delete_this_clone")
    b.link([dd_, ddel])
    b.d[if_dense]["inputs"]["CONDITION"] = BOOL(over_d)
    b.d[if_dense]["inputs"]["SUBSTACK"] = SUB(dd_)
    body.append(if_dense)
    # 被天敌吃
    if predator:
        tpred = touching(b, predator)
        if_pred = b.new("control_if")
        dp = b.new("data_changevariableby", {"VALUE": N(-1)}, vf(count_var))
        delp = b.new("control_delete_this_clone")
        b.link([dp, delp])
        b.d[if_pred]["inputs"]["CONDITION"] = BOOL(tpred)
        b.d[if_pred]["inputs"]["SUBSTACK"] = SUB(dp)
        body.append(if_pred)
    # 饿死
    starve_var = V_SSTV if count_var == V_SHEEP else V_WSTV
    hunger = b.new("operator_subtract",
                   {"NUM1": RN(timer(b)), "NUM2": RN(var(b, eat_local))})
    over = b.new("operator_gt", {"OPERAND1": RN(hunger), "OPERAND2": RN(gvar(b, starve_var))})
    if_st = b.new("control_if")
    ds = b.new("data_changevariableby", {"VALUE": N(-1)}, vf(count_var))
    dels = b.new("control_delete_this_clone")
    b.link([ds, dels])
    b.d[if_st]["inputs"]["CONDITION"] = BOOL(over)
    b.d[if_st]["inputs"]["SUBSTACK"] = SUB(ds)
    body.append(if_st)
    # 等待行动间隔后重置回 1 秒
    w = b.new("control_wait", {"DURATION": RN(var(b, act_local))})
    reset_act = b.new("data_setvariableto", {"VALUE": T(1)}, lf(act_local))
    body += [w, reset_act]
    b.link([chat, goto, show, chgcnt, set_eat0, set_act0, set_en0, fa2])
    b.d[fa2]["inputs"]["SUBSTACK"] = SUB(sfirst)
    b.link([slast] + body)

    # 脚本4+5：若是猎物，维护自身坐标列表供天敌寻路
    if report_bc and report_lists:
        rebuild_loop(b, report_bc, report_lists[0], report_lists[1])
        report_handler(b, report_bc, report_lists[0], report_lists[1])
    return b


def sheep():
    # 羊：走向最近的草，但若危险半径内有狼则逃离；吃够草(羊繁殖食量)生小羊
    def mv(b):
        return move_flee_or_chase(b, SHEEP_SEEK, LX_G, LY_G,
                                  SHEEP_AVOID, LX_W, LY_W)
    return animal(V_SHEEP, SHEEP_EAT, SHEEP_ACT, SHEEP_EN, V_SBREED, mv,
                  food="草", predator="狼",
                  report_bc=BC_REPS, report_lists=(LX_S, LY_S),
                  food_count=V_GRASS, ratio_var=V_RS,   # 羊死亡阈值=草数量/草羊比
                  add_bc=BC_ADDS, add_lo=4, add_hi=7,
                  init_lo=70, init_hi=75)   # 羊初始≈75


def wolf():
    # 狼：追向最近的羊；吃够羊(狼繁殖食量)生小狼；并上报坐标供羊躲避
    def mv(b):
        return move_chase(b, WOLF_SEEK, LX_S, LY_S, SPEED_W)
    return animal(V_WOLF, WOLF_EAT, WOLF_ACT, WOLF_EN, V_WBREED, mv,
                  food="羊", predator=None,
                  report_bc=BC_REPW, report_lists=(LX_W, LY_W),
                  food_count=V_SHEEP, ratio_var=V_RW,   # 狼死亡阈值=羊数量/羊狼比
                  add_bc=BC_ADDW, add_lo=1, add_hi=2,
                  init_lo=5, init_hi=5)   # 狼初始=5


# ==================== 画笔三柱 ====================
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
        mul = b.new("operator_multiply", {"NUM1": RN(gvar(b, vid)), "NUM2": N(scale)})
        add = b.new("operator_add", {"NUM1": N(-150), "NUM2": RN(mul)})
        g2 = b.new("motion_gotoxy", {"X": N(x), "Y": RN(add)})
        pu = b.new("pen_penUp")
        seq.extend([col, g1, pd, g2, pu])

    bar(120, V_GRASS, "#80ed99", 1.6)
    bar(175, V_SHEEP, "#f1f1f1", 2.2)
    bar(230, V_WOLF, "#9aa0a6", 3.2)
    b.link([hat, hide, fa])
    b.d[fa]["inputs"]["SUBSTACK"] = SUB(clr)
    b.link(seq)
    return b


def btn(msg):
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    show = b.new("looks_show")
    b.link([hat, show])
    cl = b.new("event_whenthisspriteclicked", top=True, x=300)
    bc = b.new("event_broadcast", {"BROADCAST_INPUT": [1, [11, BC[msg], msg]]})
    b.link([cl, bc])
    return b


# ==================== SVG ====================
def bg():
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360">'
            '<rect width="480" height="360" fill="#a8d5a2"/>'
            '<rect y="250" width="480" height="110" fill="#7cb274"/>'
            '<text x="240" y="30" font-family="sans-serif" font-size="22" '
            'font-weight="bold" fill="#1b4332" text-anchor="middle">'
            '生态平衡 草:羊:狼 = 150:75:5</text></svg>')


def grass_svg():
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="30" height="32">'
            '<path d="M15 31 Q9 18 6 4 Q14 16 15 31 Z" fill="#52b788"/>'
            '<path d="M15 31 Q15 16 15 2 Q19 16 15 31 Z" fill="#40916c"/>'
            '<path d="M15 31 Q21 18 24 4 Q16 16 15 31 Z" fill="#52b788"/></svg>')


def sheep_svg(step=0):
    lx1, lx2 = 16 + step, 30 - step
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="48" height="40">'
            f'<rect x="{lx1}" y="28" width="4" height="9" fill="#6b6b6b"/>'
            f'<rect x="{lx2}" y="28" width="4" height="9" fill="#6b6b6b"/>'
            '<ellipse cx="24" cy="22" rx="16" ry="12" fill="#f3f3f3"/>'
            '<circle cx="13" cy="16" r="6" fill="#f3f3f3"/>'
            '<circle cx="22" cy="13" r="7" fill="#f3f3f3"/>'
            '<circle cx="32" cy="15" r="6" fill="#f3f3f3"/>'
            '<ellipse cx="9" cy="20" rx="5" ry="6" fill="#444"/>'
            '<ellipse cx="5" cy="17" rx="2" ry="3" fill="#444"/>'
            '<circle cx="8" cy="19" r="1.3" fill="#fff"/></svg>')


def wolf_svg(step=0):
    lx1, lx2 = 16 + step, 32 - step
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="52" height="40">'
            f'<rect x="{lx1}" y="27" width="4" height="10" fill="#6f767c"/>'
            f'<rect x="{lx2}" y="27" width="4" height="10" fill="#6f767c"/>'
            '<polygon points="6,20 -2,28 8,26" fill="#9aa0a6"/>'
            '<ellipse cx="26" cy="20" rx="17" ry="11" fill="#9aa0a6"/>'
            '<circle cx="40" cy="15" r="8" fill="#9aa0a6"/>'
            '<polygon points="35,8 37,-1 42,8" fill="#7c8288"/>'
            '<polygon points="43,8 48,-1 49,9" fill="#7c8288"/>'
            '<polygon points="46,15 56,17 46,20" fill="#b6bbbf"/>'
            '<circle cx="42" cy="14" r="1.4" fill="#000"/></svg>')


def button_svg(label, fill):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="150" height="50">'
            f'<rect x="2" y="2" width="146" height="46" rx="23" fill="{fill}" '
            'stroke="#fff" stroke-width="3"/>'
            f'<text x="75" y="33" font-family="sans-serif" font-size="20" '
            f'fill="#fff" text-anchor="middle">{label}</text></svg>')


def build():
    a = Assets()
    stage = make_stage([a.costume("草原", bg(), 240, 180)],
                       {v: [VARS[v], 0] for v in VARS}, {k: BC[k] for k in BC})
    stage["lists"] = {lid: [LISTS[lid], []] for lid in LISTS}

    gr = make_sprite("草", grass(), [a.costume("草丛", grass_svg(), 15, 31)],
                     1, 0, 0, visible=False, size=70)

    sh = make_sprite("羊", sheep(),
                     [a.costume("羊a", sheep_svg(0), 24, 20),
                      a.costume("羊b", sheep_svg(4), 24, 20)],
                     4, 0, 0, visible=False, size=70)
    sh["rotationStyle"] = "left-right"
    sh["variables"] = {t[0]: [t[1], 0] for t in
                       [SHEEP_EAT, SHEEP_EN] + SHEEP_SEEK + SHEEP_AVOID} | {SHEEP_ACT[0]: [SHEEP_ACT[1], 1]}

    wo = make_sprite("狼", wolf(),
                     [a.costume("狼a", wolf_svg(0), 26, 20),
                      a.costume("狼b", wolf_svg(4), 26, 20)],
                     5, 0, 0, visible=False, size=70)
    wo["rotationStyle"] = "left-right"
    wo["variables"] = {t[0]: [t[1], 0] for t in
                       [WOLF_EAT, WOLF_EN] + WOLF_SEEK} | {WOLF_ACT[0]: [WOLF_ACT[1], 1]}

    bd = make_sprite("数据板", board(), [a.costume("点", grass_svg(), 15, 31)],
                     2, 0, 0, visible=False)
    # 右上角两个按钮：新增羊 / 新增狼（手动扰动，用于检验规则会把比例拉回）
    bs = make_sprite("新增羊", btn(BC_ADDS),
                     [a.costume("加羊", button_svg("+ 羊", "#52b788"), 75, 25)],
                     6, 150, 150, size=85)
    bw = make_sprite("新增狼", btn(BC_ADDW),
                     [a.costume("加狼", button_svg("+ 狼", "#6f767c"), 75, 25)],
                     7, 150, 112, size=85)

    # 显示三个数量变量（左上角）
    mons = [monitor(V_GRASS, VARS[V_GRASS], 5, 5, 0, CAP_GRASS),
            monitor(V_SHEEP, VARS[V_SHEEP], 5, 32, 0, CAP_SHEEP),
            monitor(V_WOLF, VARS[V_WOLF], 5, 59, 0, CAP_WOLF)]
    info = package(OUT, [stage, gr, sh, wo, bd, bs, bw], mons, a, extensions=["pen"])
    print(f"已生成: {OUT}  角色{info['targets']} 积木{info['blocks']} {info['extensions']}")


if __name__ == "__main__":
    build()
