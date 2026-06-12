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
import os
import random
from sb3lib import (B, N, WH, PN, T, R, RN, BOOL, SUB, MENU,
                    Assets, make_stage, make_sprite, monitor, package, fix_parents)

AST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scratch_assets")


def load_asset(md5):
    with open(os.path.join(AST, f"{md5}.svg"), "rb") as f:
        return f.read()


BELL = ("8c0234fe1bfd36f5a72e975fbbc18bfd", 59, 69)   # Scratch 内置 Bell 造型

OUT = "/home/horde/isaac/haibao/03_生态平衡.sb3"

# ---- 全局变量 ----
V_GRASS, V_SHEEP, V_WOLF = "v-grass", "v-sheep", "v-wolf"
V_GROW, V_SGROW, V_WGROW = "v-grow", "v-sgrow", "v-wgrow"  # 草/羊/狼 再生能力
V_REFRESH = "v-refresh"                                  # 刷新间隔（统一管理草羊狼定期变化）
V_SEAT, V_WEAT = "v-seat", "v-weat"                      # 羊进食能力/狼进食能力
V_WCUT, V_SCUT = "v-wcut", "v-scut"                     # 待删狼/待删羊
V_SSEQ, V_WSEQ = "v-sseq", "v-wseq"   # 羊/狼 出生编号计数器（越小越老）
V_OLD = "v-old"                       # 求“最老”时的临时最小编号
VARS = {
    V_GRASS: "草数量", V_SHEEP: "羊数量", V_WOLF: "狼数量",
    V_GROW: "草再生能力",        # 刷新时 草增加 = 草再生能力 × 草数量（上限150）
    V_SGROW: "羊再生能力",       # 刷新时 羊增加 = 羊再生能力 × 羊数量
    V_WGROW: "狼再生能力",       # 刷新时 狼增加 = 狼再生能力 × 狼数量
    V_REFRESH: "刷新间隔",       # 每隔此秒统一刷新（再生/消耗/检查）
    V_SEAT: "羊进食能力",        # 草定期减少 = 羊进食能力 × 羊数量
    V_WEAT: "狼进食能力",        # 羊定期减少 = 狼进食能力 × 狼数量
    V_WCUT: "待删狼", V_SCUT: "待删羊",
    V_SSEQ: "羊编号", V_WSEQ: "狼编号", V_OLD: "最老编号",
}
# ---- 全局列表：仅羊坐标(供狼找最近的羊)----
LX_S, LY_S = ["羊X", "l-sx"], ["羊Y", "l-sy"]

# ---- 狼寻路用的每克隆体本地变量（找最近的羊）----
WOLF_SEEK = [("w-tx", "狼目标x"), ("w-ty", "狼目标y"), ("w-min", "狼最近距"),
             ("w-d", "狼距"), ("w-i", "狼序")]

# ---- 广播 ----
# 草为纯数值(控制器直接增减)，不再广播。羊/狼：按出生编号“最老优先”删除——
#   先广播[求最老X]让所有克隆把最小编号写入[最老编号]，再广播[删最老X]
#   让编号等于该值（即最先创建）的那一只删除自己，重复 N 次即删最老的 N 只。
BC_OLDS, BC_DELS = "bc-olds", "bc-dels"   # 求待删羊 / 删待删羊（被吃优先，其次最老）
BC_OLDW, BC_DELW = "bc-oldw", "bc-delw"   # 求最老狼 / 删最老狼
BC_REPS = "bc-reps"                       # 羊上报坐标（重建羊位置列表）
BC_WMOVE = "bc-wmove"                     # 狼朝最近的羊移动（刷新时捕食）
BC_MARK = "bc-mark"                       # 羊根据是否碰到狼标记“被吃”
BC_WEAT = "bc-weat"                       # 狼根据是否碰到羊标记“吃过”
BC = {BC_OLDS: "求待删羊", BC_DELS: "删待删羊",
      BC_OLDW: "求最老狼", BC_DELW: "删最老狼",
      BC_REPS: "报羊位", BC_WMOVE: "狼移动", BC_MARK: "标记被吃", BC_WEAT: "狼进食"}

# 初始数量 + 稳定参数（乘法再生数值模型，标定到 20:10:1）
INIT_GRASS, INIT_SHEEP, INIT_WOLF = 100, 50, 5
CAP_GRASS = 105                 # 草地承载力 → 草稳定在 ≈100（配合羊50、狼5）
SAFE_SHEEP, SAFE_WOLF = 100, 20   # 羊上限（峰值）；狼安全阈值
GROW_DEF = 0.25                 # 草再生能力（需 > 羊进食能力，草才不枯竭）
SGROW_DEF, WGROW_DEF = 0.08, 0.3  # 羊/狼 再生能力（刷新时按 数量×再生能力 增加）
SEAT_DEF, WEAT_DEF = 0.10, 0.5   # 羊进食能力 / 狼进食能力
REFRESH_DEF = 2                 # 刷新间隔默认 2 秒
WOLF_RATIO = 10                 # 删狼目标：羊/狼 达到 10（仅当 草≥2×羊 时执行）
MOVE_W = 10                     # 狼每次刷新朝最近的羊移动的固定距离(像素)


def vf(v):
    return {"VARIABLE": [VARS[v], v]}


def lf(loc):
    return {"VARIABLE": [loc[1], loc[0]]}


def var(b, loc):
    return b.new("data_variable", fields=lf(loc))


def gvar(b, v):
    return b.new("data_variable", fields=vf(v))


# ---- 每角色「是否克隆体」本地变量 ----
# 删减用令牌广播时，本体也会收到广播；本体执行“删除此克隆”无效却照样
# 把计数减 1、令牌减 1 → 真正的克隆少删一个、计数却被多减 → 舞台上越积越多。
# 用本地变量区分本体(0)与克隆(1)，只让克隆执行删除，彻底修复。
ISCL = {"羊": "s-iscl", "狼": "w-iscl"}


def iscl_field(slug):
    return {"VARIABLE": ["克隆标记", slug]}


def set_iscl(b, slug, val):
    return b.new("data_setvariableto", {"VALUE": T(val)}, iscl_field(slug))


def is_clone(b, slug):
    return b.new("operator_equals",
                 {"OPERAND1": R(b.new("data_variable", fields=iscl_field(slug))),
                  "OPERAND2": T(1)})


# ---- 「最老优先」删除：每个克隆带出生编号(本地变量)，编号越小越老 ----
# name -> (本体/克隆标记 slug, 出生编号本地变量 slug+名, 全局编号计数器, 数量变量)
ORD = {"羊": ("s-ord", "羊出生编号"), "狼": ("w-ord", "狼出生编号")}
SEQ = {"羊": V_SSEQ, "狼": V_WSEQ}
CNTV = {"羊": V_SHEEP, "狼": V_WOLF}


def ord_field(name):
    return {"VARIABLE": [ORD[name][1], ORD[name][0]]}


def ord_var(b, name):
    return b.new("data_variable", fields=ord_field(name))


# ---- 羊「被吃」/ 狼「吃过」「原地」本地标记 ----
EAT = ("s-eat", "被吃")       # 羊：刷新时被狼碰到则=1
WEAT = ("w-eat", "狼吃过")     # 狼：本轮碰到羊则=1
WREST = ("w-rest", "狼原地")   # 狼：被裁狼放过后原地不动的剩余轮数(1→本轮歇)


def eat_field():
    return {"VARIABLE": [EAT[1], EAT[0]]}


def eat_var(b):
    return b.new("data_variable", fields=eat_field())


def weat_field():
    return {"VARIABLE": [WEAT[1], WEAT[0]]}


def weat_var(b):
    return b.new("data_variable", fields=weat_field())


def wrest_field():
    return {"VARIABLE": [WREST[1], WREST[0]]}


def wrest_var(b):
    return b.new("data_variable", fields=wrest_field())


def prio_key(b, name):
    """删除优先级键（越小越先删）：
       羊 = 出生编号 − 被吃×1e6（被吃的键极小→最先删，其次按编号即最老）；
       狼 = 出生编号 + 原地×1e6（已被放过、正在原地歇的狼键极大→不会被重复选中）。"""
    if name == "羊":
        big = b.new("operator_multiply", {"NUM1": RN(eat_var(b)), "NUM2": N(1000000)})
        return b.new("operator_subtract", {"NUM1": RN(ord_var(b, name)), "NUM2": RN(big)})
    big = b.new("operator_multiply", {"NUM1": RN(wrest_var(b)), "NUM2": N(1000000)})
    return b.new("operator_add", {"NUM1": RN(ord_var(b, name)), "NUM2": RN(big)})


def assign_serial(b, name, slug):
    """克隆体启动时领取一个递增的出生编号（在不让出的两步内原子完成）。"""
    inc = b.new("data_changevariableby", {"VALUE": N(1)}, vf(SEQ[name]))
    setv = b.new("data_setvariableto", {"VALUE": R(gvar(b, SEQ[name]))}, ord_field(name))
    b.link([inc, setv])
    return inc, setv


def find_oldest_handler(b, name, slug, bc_find, x):
    """收到[求待删X]：克隆体若自身优先级键 < 最老编号 则刷新它（求最小键=最先删的那只）。"""
    ha = b.new("event_whenbroadcastreceived",
               fields={"BROADCAST_OPTION": [BC[bc_find], bc_find]}, top=True, x=x)
    younger = b.new("operator_lt",
                    {"OPERAND1": RN(prio_key(b, name)), "OPERAND2": R(gvar(b, V_OLD))})
    cond = b.new("operator_and",
                 {"OPERAND1": BOOL(is_clone(b, slug)), "OPERAND2": BOOL(younger)})
    iff = b.new("control_if")
    setv = b.new("data_setvariableto", {"VALUE": RN(prio_key(b, name))}, vf(V_OLD))
    b.d[iff]["inputs"]["CONDITION"] = BOOL(cond)
    b.d[iff]["inputs"]["SUBSTACK"] = SUB(setv)
    b.link([ha, iff])


def del_oldest_handler(b, name, slug, bc_del, x):
    """收到[删待删X]：优先级键等于[最老编号]的那一只删除自己、数量-1。"""
    ha = b.new("event_whenbroadcastreceived",
               fields={"BROADCAST_OPTION": [BC[bc_del], bc_del]}, top=True, x=x)
    match = b.new("operator_equals",
                  {"OPERAND1": RN(prio_key(b, name)), "OPERAND2": R(gvar(b, V_OLD))})
    cond = b.new("operator_and",
                 {"OPERAND1": BOOL(is_clone(b, slug)), "OPERAND2": BOOL(match)})
    iff = b.new("control_if")
    dec = b.new("data_changevariableby", {"VALUE": N(-1)}, vf(CNTV[name]))
    dele = b.new("control_delete_this_clone")
    b.link([dec, dele])
    b.d[iff]["inputs"]["CONDITION"] = BOOL(cond)
    b.d[iff]["inputs"]["SUBSTACK"] = SUB(dec)
    b.link([ha, iff])


def delete_oldest_loop(b, count_input, bc_find, bc_del):
    """控制器侧：重复 count 次「求最老→删最老」，即删除最老的 count 只。"""
    rep = b.new("control_repeat", {"TIMES": count_input})
    setmax = b.new("data_setvariableto", {"VALUE": T(999999)}, vf(V_OLD))
    bfind = b.new("event_broadcastandwait",
                  {"BROADCAST_INPUT": [1, [11, BC[bc_find], bc_find]]})
    bdel = b.new("event_broadcastandwait",
                 {"BROADCAST_INPUT": [1, [11, BC[bc_del], bc_del]]})
    b.link([setmax, bfind, bdel])
    b.d[rep]["inputs"]["SUBSTACK"] = SUB(setmax)
    return rep


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


def clone_other(b, name):
    """克隆指定角色（由单一角色调用，避免克隆体重复繁殖）。"""
    c = b.new("control_create_clone_of", {"CLONE_OPTION": MENU(0)})
    b.d[c]["inputs"]["CLONE_OPTION"] = MENU(b.clone_menu(name))
    return c


def repeat_clone(b, times_input):
    rep = b.new("control_repeat", {"TIMES": times_input})
    b.d[rep]["inputs"]["SUBSTACK"] = SUB(clone_self(b))
    return rep


def repeat_clone_other(b, times_input, name):
    rep = b.new("control_repeat", {"TIMES": times_input})
    b.d[rep]["inputs"]["SUBSTACK"] = SUB(clone_other(b, name))
    return rep


def goto_random(b):
    # y 上限压到 110，避免盖住顶部标题（标题在 y≈150 处）
    sx = b.new("operator_random", {"FROM": N(-220), "TO": N(200)})
    sy = b.new("operator_random", {"FROM": N(-150), "TO": N(110)})
    return b.new("motion_gotoxy", {"X": RN(sx), "Y": RN(sy)})


def idle_anim(b):
    """原地动画：每 1 秒切换下一个造型。返回 forever 块。"""
    fa = b.new("control_forever")
    nc = b.new("looks_nextcostume")
    w = b.new("control_wait", {"DURATION": PN(1)})
    b.d[fa]["inputs"]["SUBSTACK"] = SUB(nc)
    b.link([nc, w])
    return fa


def touching(b, name):
    t = b.new("sensing_touchingobject", {"TOUCHINGOBJECTMENU": MENU(0)})
    b.d[t]["inputs"]["TOUCHINGOBJECTMENU"] = MENU(b.touch_menu(name))
    return t


def report_handler(b, bc_id, lx, ly, slug):
    """收到[报X位]→克隆体把自身坐标写入列表（本体不上报，避免出现(0,0)幽灵目标）"""
    ha = b.new("event_whenbroadcastreceived",
               fields={"BROADCAST_OPTION": [BC[bc_id], bc_id]}, top=True, x=900)
    iff = b.new("control_if")
    ax = L_add(b, lx, RN(xpos(b)))
    ay = L_add(b, ly, RN(ypos(b)))
    b.link([ax, ay])
    b.d[iff]["inputs"]["CONDITION"] = BOOL(is_clone(b, slug))
    b.d[iff]["inputs"]["SUBSTACK"] = SUB(ax)
    b.link([ha, iff])


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


# （草角色已删除：草数量为纯数值，由控制器管理，草由背景呈现）


# ==================== 羊 ====================
def sheep():
    b = B()
    # 脚本1：绿旗 → 数量清零 + 初始生成 50 只
    hat = b.new("event_whenflagclicked", top=True)
    hide = b.new("looks_hide")
    iscl0 = set_iscl(b, "羊", 0)
    c0 = b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_SHEEP))
    seq0 = b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_SSEQ))   # 出生编号归零
    rep0 = repeat_clone(b, WH(INIT_SHEEP))
    b.link([hat, hide, iscl0, c0, seq0, rep0])
    # 注：繁殖(克隆)统一由“控制器”执行；“+羊”按钮直接克隆，避免克隆体重复繁殖

    # 脚本2：作为克隆体 → 领出生编号、清被吃、计数、随机散布、显示、动画（不再判断与狼是否重叠）
    chat = b.new("control_start_as_clone", top=True, x=860)
    setcl = set_iscl(b, "羊", 1)
    sinc, sset = assign_serial(b, "羊", "s-ord")   # 领取递增出生编号(越小越老)
    eat0 = b.new("data_setvariableto", {"VALUE": T(0)}, eat_field())   # 被吃标记清零
    cnt = b.new("data_changevariableby", {"VALUE": N(1)}, vf(V_SHEEP))
    goto = goto_random(b)
    show = b.new("looks_show")
    b.link([chat, setcl, sinc])
    b.link([sset, eat0, cnt, goto, show, idle_anim(b)])

    # 脚本：收到[报羊位] → 克隆体把自身坐标写入 羊X/羊Y（供狼找最近的羊）
    report_handler(b, BC_REPS, LX_S, LY_S, "羊")

    # 脚本：收到[标记被吃] → 碰到狼则被吃=1，否则=0（每次刷新狼移动后重判）
    hm = b.new("event_whenbroadcastreceived",
               fields={"BROADCAST_OPTION": [BC[BC_MARK], BC_MARK]}, top=True, x=1700)
    mcond = b.new("operator_and",
                  {"OPERAND1": BOOL(is_clone(b, "羊")), "OPERAND2": BOOL(touching(b, "狼"))})
    mif = b.new("control_if_else")
    seat1 = b.new("data_setvariableto", {"VALUE": T(1)}, eat_field())
    seat0 = b.new("data_setvariableto", {"VALUE": T(0)}, eat_field())
    b.d[mif]["inputs"]["CONDITION"] = BOOL(mcond)
    b.d[mif]["inputs"]["SUBSTACK"] = SUB(seat1)
    b.d[mif]["inputs"]["SUBSTACK2"] = SUB(seat0)
    b.link([hm, mif])

    # 脚本：待删羊删除（被吃优先，其次最老）
    find_oldest_handler(b, "羊", "羊", BC_OLDS, x=1100)
    del_oldest_handler(b, "羊", "羊", BC_DELS, x=1400)
    return b


# ==================== 狼 ====================
def wolf():
    b = B()
    # 脚本1：绿旗 → 数量清零 + 初始生成 2 头
    hat = b.new("event_whenflagclicked", top=True)
    hide = b.new("looks_hide")
    iscl0 = set_iscl(b, "狼", 0)
    c0 = b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_WOLF))
    seq0 = b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_WSEQ))   # 出生编号归零
    rep0 = repeat_clone(b, WH(INIT_WOLF))
    b.link([hat, hide, iscl0, c0, seq0, rep0])
    # 注：繁殖(克隆)统一由“控制器”执行；“+狼”按钮直接克隆，避免克隆体重复繁殖

    # 脚本：求最老狼（用 出生编号+原地×1e6 作键，正在原地歇的不参与）
    find_oldest_handler(b, "狼", "狼", BC_OLDW, x=860)

    # 脚本：删最老狼——若该狼本轮吃过羊，则不删，改回“没吃过”并原地歇一轮；否则删除
    hdel = b.new("event_whenbroadcastreceived",
                 fields={"BROADCAST_OPTION": [BC[BC_DELW], BC_DELW]}, top=True, x=1160)
    match = b.new("operator_equals",
                  {"OPERAND1": RN(prio_key(b, "狼")), "OPERAND2": R(gvar(b, V_OLD))})
    dcond = b.new("operator_and",
                  {"OPERAND1": BOOL(is_clone(b, "狼")), "OPERAND2": BOOL(match)})
    dif = b.new("control_if")
    ate = b.new("operator_equals", {"OPERAND1": R(weat_var(b)), "OPERAND2": T(1)})
    sif = b.new("control_if_else")
    spare_e = b.new("data_setvariableto", {"VALUE": T(0)}, weat_field())   # 改回没吃过
    spare_r = b.new("data_setvariableto", {"VALUE": T(1)}, wrest_field())  # 原地歇一轮
    b.link([spare_e, spare_r])
    kill_c = b.new("data_changevariableby", {"VALUE": N(-1)}, vf(V_WOLF))
    kill_d = b.new("control_delete_this_clone")
    b.link([kill_c, kill_d])
    b.d[sif]["inputs"]["CONDITION"] = BOOL(ate)
    b.d[sif]["inputs"]["SUBSTACK"] = SUB(spare_e)
    b.d[sif]["inputs"]["SUBSTACK2"] = SUB(kill_c)
    b.d[dif]["inputs"]["CONDITION"] = BOOL(dcond)
    b.d[dif]["inputs"]["SUBSTACK"] = SUB(sif)
    b.link([hdel, dif])

    # 脚本：收到[狼移动] → 原地歇的狼消耗一轮不动；否则找最近的羊朝它移动固定距离 MOVE_W
    hmv = b.new("event_whenbroadcastreceived",
                fields={"BROADCAST_OPTION": [BC[BC_WMOVE], BC_WMOVE]}, top=True, x=1760)
    mvif = b.new("control_if")
    b.d[mvif]["inputs"]["CONDITION"] = BOOL(is_clone(b, "狼"))
    # 遍历 羊X/羊Y 求最近的羊 → 写入 狼目标x/狼目标y/狼最近距(平方距)
    seek_first, seek_last = find_nearest(b, WOLF_SEEK, LX_S, LY_S)
    tx, ty, mn = WOLF_SEEK[0], WOLF_SEEK[1], WOLF_SEEK[2]

    def step_axis(tloc, pos):
        # pos + MOVE_W × (目标 − pos) / √最近距
        delta = b.new("operator_subtract", {"NUM1": RN(var(b, tloc)), "NUM2": RN(pos(b))})
        num = b.new("operator_multiply", {"NUM1": N(MOVE_W), "NUM2": RN(delta)})
        dist = b.new("operator_mathop", {"NUM": RN(var(b, mn))}, fields={"OPERATOR": ["sqrt", None]})
        div = b.new("operator_divide", {"NUM1": RN(num), "NUM2": RN(dist)})
        return b.new("operator_add", {"NUM1": RN(pos(b)), "NUM2": RN(div)})

    goto = b.new("motion_gotoxy", {"X": RN(step_axis(tx, xpos)), "Y": RN(step_axis(ty, ypos))})
    # 仅当确有羊(最近距 < 999999)且不在原地(>0) 才移动
    has = b.new("operator_and",
                {"OPERAND1": BOOL(b.new("operator_gt", {"OPERAND1": R(var(b, mn)), "OPERAND2": T(0)})),
                 "OPERAND2": BOOL(b.new("operator_lt", {"OPERAND1": R(var(b, mn)), "OPERAND2": T(999999)}))})
    mvgo = b.new("control_if")
    b.d[mvgo]["inputs"]["CONDITION"] = BOOL(has)
    b.d[mvgo]["inputs"]["SUBSTACK"] = SUB(goto)
    b.link([seek_last, mvgo])              # 求最近后再判断移动
    # 原地歇：若 原地>0 则消耗一轮、不动；否则觅食移动
    resting = b.new("operator_gt", {"OPERAND1": R(wrest_var(b)), "OPERAND2": T(0)})
    restif = b.new("control_if_else")
    rdec = b.new("data_changevariableby", {"VALUE": N(-1)}, wrest_field())
    b.d[restif]["inputs"]["CONDITION"] = BOOL(resting)
    b.d[restif]["inputs"]["SUBSTACK"] = SUB(rdec)
    b.d[restif]["inputs"]["SUBSTACK2"] = SUB(seek_first)
    b.d[mvif]["inputs"]["SUBSTACK"] = SUB(restif)
    b.link([hmv, mvif])

    # 脚本：收到[狼进食] → 本轮是否碰到羊 → 吃过=1 / 0
    hwe = b.new("event_whenbroadcastreceived",
                fields={"BROADCAST_OPTION": [BC[BC_WEAT], BC_WEAT]}, top=True, x=2200)
    we_if = b.new("control_if_else")
    we_set1 = b.new("data_setvariableto", {"VALUE": T(1)}, weat_field())
    we_set0 = b.new("data_setvariableto", {"VALUE": T(0)}, weat_field())
    we_cond = b.new("operator_and",
                    {"OPERAND1": BOOL(is_clone(b, "狼")), "OPERAND2": BOOL(touching(b, "羊"))})
    b.d[we_if]["inputs"]["CONDITION"] = BOOL(we_cond)
    b.d[we_if]["inputs"]["SUBSTACK"] = SUB(we_set1)
    b.d[we_if]["inputs"]["SUBSTACK2"] = SUB(we_set0)
    b.link([hwe, we_if])

    # 脚本5：作为克隆体 → 领出生编号、清吃过/原地、计数、随机定位、显示、动画（不再判断与羊是否重叠）
    chat = b.new("control_start_as_clone", top=True, x=1460)
    setcl = set_iscl(b, "狼", 1)
    winc, wset = assign_serial(b, "狼", "w-ord")
    weat0 = b.new("data_setvariableto", {"VALUE": T(0)}, weat_field())
    wrest0 = b.new("data_setvariableto", {"VALUE": T(0)}, wrest_field())
    cnt = b.new("data_changevariableby", {"VALUE": N(1)}, vf(V_WOLF))
    goto = goto_random(b)
    show = b.new("looks_show")
    b.link([chat, setcl, winc])
    b.link([wset, weat0, wrest0, cnt, goto, show, idle_anim(b)])
    return b


# ==================== 控制器：定期检查比例、提示、裁狼 ====================
def controller():
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    # 用 Bell 造型，显示在右上角，靠“说”给出提示（不再用变量）
    sw = b.new("looks_switchcostumeto", {"COSTUME": MENU(0)})
    bm = b.costume_menu("bell1")
    b.d[sw]["inputs"]["COSTUME"] = MENU(bm)
    go = b.new("motion_gotoxy", {"X": N(-190), "Y": N(-140)})   # 左下角
    show = b.new("looks_show")
    front = b.new("looks_gotofrontback", fields={"FRONT_BACK": ["front", None]})  # 置于最前，不被盖住

    # —— 初始化（原在草角色里，现统一由控制器完成）——
    # 草为纯数值：直接置初值；各能力/间隔参数也在此设定。羊/狼数量由各自克隆维护。
    init_blocks = [
        b.new("data_setvariableto", {"VALUE": T(INIT_GRASS)}, vf(V_GRASS)),
        b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_WCUT)),
        b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_SCUT)),
        b.new("data_setvariableto", {"VALUE": T(GROW_DEF)}, vf(V_GROW)),
        b.new("data_setvariableto", {"VALUE": T(SGROW_DEF)}, vf(V_SGROW)),
        b.new("data_setvariableto", {"VALUE": T(WGROW_DEF)}, vf(V_WGROW)),
        b.new("data_setvariableto", {"VALUE": T(SEAT_DEF)}, vf(V_SEAT)),
        b.new("data_setvariableto", {"VALUE": T(WEAT_DEF)}, vf(V_WEAT)),
        b.new("data_setvariableto", {"VALUE": T(REFRESH_DEF)}, vf(V_REFRESH)),
    ]

    # —— 等羊/狼初始化完成后再启动循环（草由控制器直接置好）——
    # 各角色初始克隆体启动时才把数量 +1，故数量达到初始值即代表初始克隆全部就位。
    def ge(v, init):   # 数量 ≥ 初始值，即 not(数量 < 初始值)
        lt = b.new("operator_lt", {"OPERAND1": R(gvar(b, v)), "OPERAND2": T(init)})
        return b.new("operator_not", {"OPERAND": BOOL(lt)})
    ready = b.new("operator_and",
                  {"OPERAND1": BOOL(b.new("operator_and",
                                          {"OPERAND1": BOOL(ge(V_GRASS, INIT_GRASS)),
                                           "OPERAND2": BOOL(ge(V_SHEEP, INIT_SHEEP))})),
                   "OPERAND2": BOOL(ge(V_WOLF, INIT_WOLF))})
    wready = b.new("control_wait_until")
    b.d[wready]["inputs"]["CONDITION"] = BOOL(ready)

    fa = b.new("control_forever")
    wt = b.new("control_wait", {"DURATION": RN(gvar(b, V_REFRESH))})

    # —— 草再生（纯数值，不再克隆草）——
    # 草=0 → 补 20；否则 草数量 += round(草再生能力×草数量)，并封顶到 CAP_GRASS
    g_zero = b.new("operator_equals", {"OPERAND1": R(gvar(b, V_GRASS)), "OPERAND2": T(0)})
    grow_if = b.new("control_if_else")
    revive = b.new("data_setvariableto", {"VALUE": T(20)}, vf(V_GRASS))   # 草=0：补 20
    grow_inc = b.new("data_changevariableby",
                     {"VALUE": RN(b.new("operator_round",
                                        {"NUM": RN(b.new("operator_multiply",
                                                         {"NUM1": RN(gvar(b, V_GROW)),
                                                          "NUM2": RN(gvar(b, V_GRASS))}))}))},
                     vf(V_GRASS))
    over_cap = b.new("operator_gt", {"OPERAND1": R(gvar(b, V_GRASS)), "OPERAND2": T(CAP_GRASS)})
    cap_if = b.new("control_if")
    cap_set = b.new("data_setvariableto", {"VALUE": T(CAP_GRASS)}, vf(V_GRASS))
    b.d[cap_if]["inputs"]["CONDITION"] = BOOL(over_cap)
    b.d[cap_if]["inputs"]["SUBSTACK"] = SUB(cap_set)
    b.link([grow_inc, cap_if])
    b.d[grow_if]["inputs"]["CONDITION"] = BOOL(g_zero)
    b.d[grow_if]["inputs"]["SUBSTACK"] = SUB(revive)
    b.d[grow_if]["inputs"]["SUBSTACK2"] = SUB(grow_inc)
    # 羊再生 = round(羊再生能力×羊数量)，羊<上限 才繁殖
    s_safe = b.new("operator_lt", {"OPERAND1": R(gvar(b, V_SHEEP)), "OPERAND2": T(SAFE_SHEEP)})
    if_srep = b.new("control_if")
    s_n = b.new("operator_round",
                {"NUM": RN(b.new("operator_multiply",
                                 {"NUM1": RN(gvar(b, V_SGROW)), "NUM2": RN(gvar(b, V_SHEEP))}))})
    b.d[if_srep]["inputs"]["CONDITION"] = BOOL(s_safe)
    b.d[if_srep]["inputs"]["SUBSTACK"] = SUB(repeat_clone_other(b, RN(s_n), "羊"))
    # 狼再生 = round(狼再生能力×狼数量)，狼<上限 才繁殖
    w_safe = b.new("operator_lt", {"OPERAND1": R(gvar(b, V_WOLF)), "OPERAND2": T(SAFE_WOLF)})
    if_wrep = b.new("control_if")
    w_n = b.new("operator_round",
                {"NUM": RN(b.new("operator_multiply",
                                 {"NUM1": RN(gvar(b, V_WGROW)), "NUM2": RN(gvar(b, V_WOLF))}))})
    b.d[if_wrep]["inputs"]["CONDITION"] = BOOL(w_safe)
    b.d[if_wrep]["inputs"]["SUBSTACK"] = SUB(repeat_clone_other(b, RN(w_n), "狼"))
    # 再生顺序(狼→羊→草)由下方 forever 主链统一串联

    # 草:羊 检查 —— 草<10 → 破坏；否则 草<羊 → 羊过多；否则 ↓
    g_lt10 = b.new("operator_lt", {"OPERAND1": R(gvar(b, V_GRASS)), "OPERAND2": T(10)})
    if_g = b.new("control_if_else")
    tip_break = b.new("looks_say", {"MESSAGE": T("生态平衡被破坏！")})
    # else: 草 < 羊 ?
    gs_lt2 = b.new("operator_lt", {"OPERAND1": R(gvar(b, V_GRASS)), "OPERAND2": RN(gvar(b, V_SHEEP))})
    if_gs = b.new("control_if_else")
    tip_many = b.new("looks_say", {"MESSAGE": T("羊数量过多")})
    # else: 羊 < 2×狼 → 狼数量过多；否则 清空气泡
    ten_w2 = b.new("operator_multiply", {"NUM1": N(2), "NUM2": RN(gvar(b, V_WOLF))})
    sw_lt10 = b.new("operator_lt", {"OPERAND1": R(gvar(b, V_SHEEP)), "OPERAND2": RN(ten_w2)})
    if_sw = b.new("control_if_else")
    tip_wmany = b.new("looks_say", {"MESSAGE": T("狼数量过多")})
    tip_ok = b.new("looks_say", {"MESSAGE": T("")})   # 否则：清空气泡（不提示）
    b.d[if_sw]["inputs"]["CONDITION"] = BOOL(sw_lt10)
    b.d[if_sw]["inputs"]["SUBSTACK"] = SUB(tip_wmany)
    b.d[if_sw]["inputs"]["SUBSTACK2"] = SUB(tip_ok)
    b.d[if_gs]["inputs"]["CONDITION"] = BOOL(gs_lt2)
    b.d[if_gs]["inputs"]["SUBSTACK"] = SUB(tip_many)
    b.d[if_gs]["inputs"]["SUBSTACK2"] = SUB(if_sw)
    b.d[if_g]["inputs"]["CONDITION"] = BOOL(g_lt10)
    b.d[if_g]["inputs"]["SUBSTACK"] = SUB(tip_break)
    b.d[if_g]["inputs"]["SUBSTACK2"] = SUB(if_gs)

    # 羊:狼 检查 —— 狼>0 且 羊<10×狼(羊/狼<10) 且 草/羊≥2 时才删狼
    #   即：当 草/羊<2（羊过多）时，不再减少狼，让狼去压制过多的羊
    w_pos = b.new("operator_gt", {"OPERAND1": R(gvar(b, V_WOLF)), "OPERAND2": T(0)})
    ten_w = b.new("operator_multiply", {"NUM1": N(10), "NUM2": RN(gvar(b, V_WOLF))})
    sw_lt10 = b.new("operator_lt", {"OPERAND1": R(gvar(b, V_SHEEP)), "OPERAND2": RN(ten_w)})
    # 草 ≥ 2×羊（草/羊 不小于2）才允许删狼
    two_s2 = b.new("operator_multiply", {"NUM1": N(2), "NUM2": RN(gvar(b, V_SHEEP))})
    not_crowd = b.new("operator_not",
                      {"OPERAND": BOOL(b.new("operator_lt",
                                             {"OPERAND1": R(gvar(b, V_GRASS)),
                                              "OPERAND2": RN(two_s2)}))})
    cw1 = b.new("operator_and", {"OPERAND1": BOOL(w_pos), "OPERAND2": BOOL(sw_lt10)})
    cond_w = b.new("operator_and", {"OPERAND1": BOOL(cw1), "OPERAND2": BOOL(not_crowd)})
    if_w = b.new("control_if")
    # 待裁狼 = 狼数量 - round(羊数量 / 8)
    tgt = b.new("operator_round",
                {"NUM": RN(b.new("operator_divide", {"NUM1": RN(gvar(b, V_SHEEP)), "NUM2": N(WOLF_RATIO)}))})
    setcut = b.new("data_setvariableto",
                   {"VALUE": RN(b.new("operator_subtract", {"NUM1": RN(gvar(b, V_WOLF)), "NUM2": RN(tgt)}))},
                   vf(V_WCUT))
    # 删最老的 (待删狼) 只狼
    loop_w = delete_oldest_loop(b, RN(gvar(b, V_WCUT)), BC_OLDW, BC_DELW)
    b.link([setcut, loop_w])
    b.d[if_w]["inputs"]["CONDITION"] = BOOL(cond_w)
    b.d[if_w]["inputs"]["SUBSTACK"] = SUB(setcut)

    # 定期消耗：草减少 = round(羊进食能力×羊数量)（纯数值，封底到 0）；羊减少 = round(狼进食能力×狼数量)
    eat_g = b.new("data_changevariableby",
                  {"VALUE": RN(b.new("operator_multiply",
                                     {"NUM1": N(-1),
                                      "NUM2": RN(b.new("operator_round",
                                                       {"NUM": RN(b.new("operator_multiply",
                                                                        {"NUM1": RN(gvar(b, V_SEAT)),
                                                                         "NUM2": RN(gvar(b, V_SHEEP))}))}))}))},
                  vf(V_GRASS))
    g_neg = b.new("operator_lt", {"OPERAND1": R(gvar(b, V_GRASS)), "OPERAND2": T(0)})
    floor_if = b.new("control_if")
    floor_set = b.new("data_setvariableto", {"VALUE": T(0)}, vf(V_GRASS))
    b.d[floor_if]["inputs"]["CONDITION"] = BOOL(g_neg)
    b.d[floor_if]["inputs"]["SUBSTACK"] = SUB(floor_set)   # 草消耗后不小于 0（在主链中 eat_g→floor_if）
    set_scut = b.new("data_setvariableto",
                     {"VALUE": RN(b.new("operator_round",
                                        {"NUM": RN(b.new("operator_multiply",
                                                         {"NUM1": RN(gvar(b, V_WEAT)),
                                                          "NUM2": RN(gvar(b, V_WOLF))}))}))},
                     vf(V_SCUT))
    # 捕食：重建羊位置列表 → 狼朝最近的羊移动 → 羊重判是否被吃
    clr_sx = L_delall(b, LX_S)
    clr_sy = L_delall(b, LY_S)
    bc_reps = b.new("event_broadcastandwait",
                    {"BROADCAST_INPUT": [1, [11, BC[BC_REPS], BC_REPS]]})
    bc_wmove = b.new("event_broadcastandwait",
                     {"BROADCAST_INPUT": [1, [11, BC[BC_WMOVE], BC_WMOVE]]})
    bc_mark = b.new("event_broadcastandwait",
                    {"BROADCAST_INPUT": [1, [11, BC[BC_MARK], BC_MARK]]})
    bc_weat = b.new("event_broadcastandwait",      # 狼判断本轮是否碰到羊(吃过)，供裁狼放过
                    {"BROADCAST_INPUT": [1, [11, BC[BC_WEAT], BC_WEAT]]})
    # 羊减少：删 (待删羊) 只羊——被吃的优先，其次最老
    loop_s = delete_oldest_loop(b, RN(gvar(b, V_SCUT)), BC_OLDS, BC_DELS)

    # 初始化(含草数值) → 等羊/狼就位 → 进入循环。
    # 每刷新：等待 → 再生 → 草消耗(数值) → 狼觅食捕食 → 羊消耗 → 检查(含放过吃过的狼)
    b.link([hat, sw, go, show, front] + init_blocks + [wready, fa])
    b.d[fa]["inputs"]["SUBSTACK"] = SUB(wt)
    b.link([wt, if_wrep, if_srep, grow_if, eat_g, floor_if,
            clr_sx, clr_sy, bc_reps, bc_wmove, bc_mark, bc_weat, set_scut, loop_s, if_g, if_w])
    return b


def btn(target, count):
    # 被点击时由按钮(单一角色)直接克隆固定 count 个 target，避免克隆体重复繁殖
    b = B()
    hat = b.new("event_whenflagclicked", top=True)
    show = b.new("looks_show")
    b.link([hat, show])
    cl = b.new("event_whenthisspriteclicked", top=True, x=300)
    b.link([cl, repeat_clone_other(b, N(count), target)])
    return b


# ==================== SVG ====================
# —— 四种背景：草越多→越绿、草越密；草越少→越黄、草越稀 ——
# (名称, 底色, 草数量档) ；草丛用“草角色”的造型，随机位置与大小；切换阈值见 bg_script()
BG_LEVELS = [
    ("深绿铺满", "#2d6a4f", "full"),     # 草多：深绿 + 铺满草
    ("浅绿一半", "#a7d3a0", "half"),     # 草中：浅绿 + 一半草
    ("浅黄四一", "#ece9a8", "quarter"),  # 草少：浅黄 + 四分之一草
    ("深黄零星", "#c8a23a", "sparse"),   # 草很少：深黄 + 零星草
]
DENSITY_N = {"full": 500, "half": 200, "quarter": 50, "sparse": 10}   # 各档草棵数
GREENS = ["#52b788", "#40916c", "#74c69d", "#2d6a4f", "#95d5b2", "#1b7a4f", "#5fa777"]
FLOWERS = ["#ffd166", "#ff8fab", "#ffffff", "#fcbf49", "#e76f51", "#c77dff"]


def _grass_shape(sway, vseed):
    """一棵更丰富的草（30×32 坐标，基部 (15,31)）：4~6 片不同绿的叶，偶有小花。
    叶形与配色由 vseed 决定，两帧只随 sway 摆动而形态不变。"""
    rng = random.Random(vseed)
    nb = rng.randint(4, 6)
    out = []
    for k in range(nb):
        t = (k / (nb - 1)) * 2 - 1 if nb > 1 else 0.0   # 叶子展开方向 -1..1
        h = rng.uniform(18, 30)                          # 叶高
        bw = rng.uniform(1.6, 2.8)                       # 叶基半宽
        tipy = 31 - h
        midy = 31 - h * 0.55
        tipx = 15 + t * 13 + sway                        # 叶尖随风(sway)平移
        ctrlx = 15 + t * 6 + sway * 0.6
        col = rng.choice(GREENS)
        out.append(f'<path d="M{15-bw:.1f} 31 Q{ctrlx:.1f} {midy:.1f} {tipx:.1f} {tipy:.1f} '
                   f'Q{ctrlx:.1f} {midy:.1f} {15+bw:.1f} 31 Z" fill="{col}"/>')
    if rng.random() < 0.22:                              # 偶尔点缀一朵小花
        fx, fy = 15 + rng.uniform(-7, 7), rng.uniform(3, 12)
        out.append(f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="2.3" fill="{rng.choice(FLOWERS)}"/>')
    return "".join(out)


def _grass_layout(density, seed):
    """随机散布若干棵草的 (x, y, 大小10~20, 形态种子)，按 y 排序使下方后画更自然。"""
    rng = random.Random(seed)
    pts = [(rng.uniform(4, 476), rng.uniform(52, 354),
            rng.uniform(10, 20), rng.randint(1, 10**9))
           for _ in range(DENSITY_N[density])]
    pts.sort(key=lambda p: p[1])
    return pts


def _title_banner():
    return ('<rect x="118" y="7" width="244" height="34" rx="17" fill="#ffffff" opacity="0.78"/>'
            '<text x="240" y="31" font-family="sans-serif" font-size="20" font-weight="bold" '
            'fill="#1b4332" text-anchor="middle">生态平衡 草-羊-狼</text>')


def bg_level(bg_color, sway, layout):
    """生成一张 480×360 背景：纯色底 + 用草角色造型按 layout 随机铺草(大小5~20) + 顶部标题。"""
    blades = []
    for x, y, size, vseed in layout:
        s = size / 30.0                                   # 大小(px) → 造型缩放
        blades.append(f'<g transform="translate({x-15*s:.1f},{y-31*s:.1f}) scale({s:.3f})">'
                      f'{_grass_shape(sway, vseed)}</g>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360">'
            f'<rect width="480" height="360" fill="{bg_color}"/>'
            + "".join(blades) + _title_banner() + '</svg>')


def bg_costumes(a):
    """为四档背景各做 a/b 两帧（同一随机布局与形态、仅草叶摆动），共 8 个造型。"""
    cos = []
    for idx, (zh, bgc, dens) in enumerate(BG_LEVELS):
        layout = _grass_layout(dens, seed=idx + 1)   # 固定种子→可复现
        cos.append(a.costume(zh + "a", bg_level(bgc, -3, layout), 240, 180))
        cos.append(a.costume(zh + "b", bg_level(bgc, 3, layout), 240, 180))
    return cos


def bg_script():
    """舞台脚本：初始化完成后，按草数量选档(深绿>74 / 浅绿>49 / 浅黄>24 / 深黄)，并在该档 a/b 两帧间切换做摆动。"""
    b = B()
    hat = b.new("event_whenflagclicked", top=True)

    # 等草/羊/狼初始化完成后再开始切换背景（与控制器一致）
    def ge(v, init):
        lt = b.new("operator_lt", {"OPERAND1": R(gvar(b, v)), "OPERAND2": T(init)})
        return b.new("operator_not", {"OPERAND": BOOL(lt)})
    ready = b.new("operator_and",
                  {"OPERAND1": BOOL(b.new("operator_and",
                                          {"OPERAND1": BOOL(ge(V_GRASS, INIT_GRASS)),
                                           "OPERAND2": BOOL(ge(V_SHEEP, INIT_SHEEP))})),
                   "OPERAND2": BOOL(ge(V_WOLF, INIT_WOLF))})
    wready = b.new("control_wait_until")
    b.d[wready]["inputs"]["CONDITION"] = BOOL(ready)

    fa = b.new("control_forever")

    def switch(name):   # 舞台用“换成背景”(switchbackdrop) 而非造型
        sw = b.new("looks_switchbackdropto", {"BACKDROP": MENU(0)})
        menu = b.new("looks_backdrops", fields={"BACKDROP": [name, None]}, shadow=True)
        b.d[sw]["inputs"]["BACKDROP"] = MENU(menu)
        return sw

    def two_frames(zh):
        sa = switch(zh + "a")
        wa = b.new("control_wait", {"DURATION": PN(0.4)})
        sb = switch(zh + "b")
        wb = b.new("control_wait", {"DURATION": PN(0.4)})
        b.link([sa, wa, sb, wb])
        return sa

    def gt(thr):
        return b.new("operator_gt", {"OPERAND1": R(gvar(b, V_GRASS)), "OPERAND2": T(thr)})

    if3 = b.new("control_if_else")            # >24 浅黄 否则 深黄
    b.d[if3]["inputs"]["CONDITION"] = BOOL(gt(24))
    b.d[if3]["inputs"]["SUBSTACK"] = SUB(two_frames("浅黄四一"))
    b.d[if3]["inputs"]["SUBSTACK2"] = SUB(two_frames("深黄零星"))
    if2 = b.new("control_if_else")            # >49 浅绿 否则 ↓
    b.d[if2]["inputs"]["CONDITION"] = BOOL(gt(49))
    b.d[if2]["inputs"]["SUBSTACK"] = SUB(two_frames("浅绿一半"))
    b.d[if2]["inputs"]["SUBSTACK2"] = SUB(if3)
    if1 = b.new("control_if_else")            # >74 深绿 否则 ↓
    b.d[if1]["inputs"]["CONDITION"] = BOOL(gt(74))
    b.d[if1]["inputs"]["SUBSTACK"] = SUB(two_frames("深绿铺满"))
    b.d[if1]["inputs"]["SUBSTACK2"] = SUB(if2)
    b.d[fa]["inputs"]["SUBSTACK"] = SUB(if1)
    b.link([hat, wready, fa])
    return b


def sheep_svg(step=0):
    """白色蓬松圆身的羊；两帧间身子前后摆 + 上下颠、四腿交替迈步。"""
    bx = -3 if step == 0 else 3       # 身子前后
    by = -1 if step == 0 else 1       # 身子上下
    f1 = 15 if step == 0 else 19      # 前腿
    f2 = 33 if step == 0 else 29      # 后腿
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="48" height="40">'
            f'<rect x="{f1}" y="27" width="4.5" height="11" rx="2" fill="#777"/>'
            f'<rect x="{f2}" y="27" width="4.5" height="11" rx="2" fill="#777"/>'
            f'<g transform="translate({bx},{by})">'
            '<ellipse cx="25" cy="21" rx="16" ry="12.5" fill="#f6f6f6"/>'   # 蓬松身体
            '<circle cx="14" cy="15" r="6.5" fill="#f6f6f6"/>'
            '<circle cx="24" cy="11" r="7.5" fill="#f6f6f6"/>'
            '<circle cx="34" cy="14" r="6.5" fill="#f6f6f6"/>'
            '<circle cx="33" cy="25" r="6.5" fill="#f6f6f6"/>'
            '<ellipse cx="9" cy="19" rx="5.5" ry="6.5" fill="#3a3a3a"/>'    # 黑脸
            '<ellipse cx="5" cy="14" rx="2.4" ry="3.2" fill="#3a3a3a"/>'    # 耳
            '<circle cx="8" cy="18" r="1.5" fill="#fff"/></g></svg>')        # 眼


def wolf_svg(step=0):
    """灰色瘦长身、尖耳尖吻、蓬尾的狼；两帧间身子前后摆 + 上下颠、四腿交替迈步。"""
    bx = -3 if step == 0 else 3
    by = -1 if step == 0 else 1
    f1 = 16 if step == 0 else 20
    f2 = 35 if step == 0 else 31
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="54" height="40">'
            f'<rect x="{f1}" y="26" width="4" height="12" rx="1.5" fill="#5d646b"/>'
            f'<rect x="{f2}" y="26" width="4" height="12" rx="1.5" fill="#5d646b"/>'
            f'<g transform="translate({bx},{by})">'
            '<path d="M44 18 Q57 9 52 23 Q49 25 44 22 Z" fill="#8a9097"/>'  # 蓬尾
            '<ellipse cx="27" cy="20" rx="18" ry="9.5" fill="#9aa0a6"/>'    # 瘦长身体
            '<circle cx="12" cy="16" r="8" fill="#9aa0a6"/>'               # 头
            '<polygon points="1,18 11,14 11,21" fill="#9aa0a6"/>'          # 尖吻
            '<polygon points="8,9 5,0 13,7" fill="#7c8288"/>'              # 尖耳
            '<polygon points="14,7 19,0 18,9" fill="#7c8288"/>'
            '<circle cx="10" cy="14" r="1.5" fill="#000"/>'               # 眼
            '<circle cx="2.5" cy="18" r="1.2" fill="#1a1a1a"/></g></svg>')  # 鼻


def button_svg(label, fill):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="150" height="50">'
            f'<rect x="2" y="2" width="146" height="46" rx="23" fill="{fill}" '
            'stroke="#fff" stroke-width="3"/>'
            f'<text x="75" y="33" font-family="sans-serif" font-size="20" '
            f'fill="#fff" text-anchor="middle">{label}</text></svg>')


def build():
    a = Assets()
    stage = make_stage(bg_costumes(a),
                       {v: [VARS[v], 0] for v in VARS}, {k: BC[k] for k in BC})
    # 羊位置列表：刷新时由羊上报、供狼找最近的羊
    stage["lists"] = {LX_S[1]: [LX_S[0], []], LY_S[1]: [LY_S[0], []]}
    # 舞台脚本：按草数量切换四档背景并做草丛摆动
    _sb = bg_script()
    fix_parents(_sb.d)
    stage["blocks"] = _sb.d

    # 狼层级(5)高于羊(3) → 狼不会被羊盖住
    sh = make_sprite("羊", sheep(),
                     [a.costume("羊a", sheep_svg(0), 24, 20),
                      a.costume("羊b", sheep_svg(4), 24, 20)],
                     3, 0, 0, visible=False, size=50)

    wo = make_sprite("狼", wolf(),
                     [a.costume("狼a", wolf_svg(0), 27, 20),
                      a.costume("狼b", wolf_svg(4), 27, 20)],
                     5, 0, 0, visible=False, size=60)

    # 每角色本地变量「克隆标记」：本体=0、克隆=1，令删减只作用于克隆
    sh["variables"] = {"s-iscl": ["克隆标记", 0], "s-ord": ["羊出生编号", 0],
                       "s-eat": ["被吃", 0]}
    wo["variables"] = {"w-iscl": ["克隆标记", 0], "w-ord": ["狼出生编号", 0],
                       "w-eat": ["狼吃过", 0], "w-rest": ["狼原地", 0],
                       **{slug: [name, 0] for slug, name in WOLF_SEEK}}

    # 控制器层级设为最高(8)，并在脚本里“移到最前”，确保不被草/羊/狼盖住
    ctl = make_sprite("控制器", controller(),
                      [a.raw_costume("bell1", load_asset(BELL[0]), BELL[1], BELL[2])],
                      8, -190, -140, visible=True, size=70)   # 左下角
    # 右侧边缘两个按钮：新增羊 / 新增狼（手动扰动）
    bs = make_sprite("新增羊", btn("羊", 50),
                     [a.costume("加羊", button_svg("+ 羊", "#52b788"), 75, 25)],
                     6, 185, 150, size=70)
    bw = make_sprite("新增狼", btn("狼", 10),
                     [a.costume("加狼", button_svg("+ 狼", "#6f767c"), 75, 25)],
                     7, 185, 112, size=70)

    # 左上角：三个数量（提示由控制器 Bell 角色“说”出，不再用变量）
    mons = [monitor(V_GRASS, VARS[V_GRASS], 5, 5, 0, CAP_GRASS),
            monitor(V_SHEEP, VARS[V_SHEEP], 5, 32, 0, 150),
            monitor(V_WOLF, VARS[V_WOLF], 5, 59, 0, SAFE_WOLF)]
    info = package(OUT, [stage, sh, wo, ctl, bs, bw], mons, a, extensions=[])
    print(f"已生成: {OUT}  角色{info['targets']} 积木{info['blocks']} {info['extensions']}")


if __name__ == "__main__":
    build()
