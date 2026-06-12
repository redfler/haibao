"""
轻量 Scratch 3 (.sb3) 构造库。
核心思路：
  - B 类负责创建积木、自动编号；脚本用 link() 串联 next。
  - 所有积木的 parent 由 fix_parents() 在最后根据 inputs 自动回填，
    避免手工设置 parent 出错。
  - Project 负责打包成 zip 并做结构自检。
"""
import os
import json
import hashlib
import zipfile

# 输入原语类型码
NUM, POS, WHOLE, INT, ANGLE, COLOR_T, TEXT = 4, 5, 6, 7, 8, 9, 10


# ---------- 输入构造助手 ----------
def N(v):                      # 数字
    return [1, [NUM, str(v)]]


def WH(v):                     # 整数（如重复次数）
    return [1, [WHOLE, str(v)]]


def PN(v):                     # 正数（如等待秒数）
    return [1, [POS, str(v)]]


def T(v):                      # 文本
    return [1, [TEXT, str(v)]]


def C(hexv):                   # 颜色
    return [1, [COLOR_T, hexv]]


def R(bid):                    # reporter 放进文本/数字槽（文本兜底）
    return [3, bid, [TEXT, ""]]


def RN(bid):                   # reporter 放进数字槽（数字兜底）
    return [3, bid, [NUM, ""]]


def BOOL(bid):                 # 布尔输入
    return [2, bid]


def SUB(bid):                  # 子栈
    return [2, bid]


def MENU(bid):                 # 下拉菜单 shadow
    return [1, bid]


class B:
    def __init__(self):
        self.d = {}
        self.i = 0

    def new(self, opcode, inputs=None, fields=None, shadow=False,
            top=False, x=0, y=0):
        self.i += 1
        bid = f"b{self.i}"
        blk = {"opcode": opcode, "next": None, "parent": None,
               "inputs": inputs or {}, "fields": fields or {},
               "shadow": shadow, "topLevel": top}
        if top:
            blk["x"], blk["y"] = x, y
        self.d[bid] = blk
        return bid

    def link(self, seq):
        for a, c in zip(seq, seq[1:]):
            self.d[a]["next"] = c
        return seq[0] if seq else None

    # ---- 常用菜单/造型 shadow ----
    def clone_menu(self, target="_myself_"):
        return self.new("control_create_clone_of_menu",
                        fields={"CLONE_OPTION": [target, None]}, shadow=True)

    def touch_menu(self, target):
        return self.new("sensing_touchingobjectmenu",
                        fields={"TOUCHINGOBJECTMENU": [target, None]},
                        shadow=True)

    def dist_menu(self, target):
        return self.new("sensing_distancetomenu",
                        fields={"DISTANCETOMENU": [target, None]}, shadow=True)

    def point_menu(self, target):
        return self.new("motion_pointtowards_menu",
                        fields={"TOWARDS": [target, None]}, shadow=True)

    def goto_menu(self, target):
        return self.new("motion_goto_menu",
                        fields={"TO": [target, None]}, shadow=True)

    def costume_menu(self, name):
        return self.new("looks_costume", fields={"COSTUME": [name, None]},
                        shadow=True)

    def key_menu(self, key):
        return self.new("sensing_keyoptions", fields={"KEY_OPTION": [key, None]},
                        shadow=True)


def fix_parents(blocks):
    """根据 inputs 中出现的块 id 自动回填 parent。"""
    for bid, blk in blocks.items():
        for name, inp in blk.get("inputs", {}).items():
            if not isinstance(inp, list):
                continue
            for elem in inp[1:]:
                if isinstance(elem, str) and elem in blocks:
                    blocks[elem]["parent"] = bid


# ---------- 素材 ----------
class Assets:
    def __init__(self):
        self.files = {}

    def costume(self, name, svg, cx, cy):
        data = svg.encode("utf-8")
        md5 = hashlib.md5(data).hexdigest()
        md5ext = f"{md5}.svg"
        self.files[md5ext] = data
        return {"assetId": md5, "name": name, "md5ext": md5ext,
                "dataFormat": "svg", "rotationCenterX": cx,
                "rotationCenterY": cy}

    def raw_costume(self, name, data, cx, cy, fmt="svg"):
        """使用现成的素材字节（如 Scratch 内置造型）。md5 由内容计算，
        与官方 md5ext 一致，故可离线打开。"""
        md5 = hashlib.md5(data).hexdigest()
        md5ext = f"{md5}.{fmt}"
        self.files[md5ext] = data
        return {"assetId": md5, "name": name, "md5ext": md5ext,
                "dataFormat": fmt, "bitmapResolution": 1,
                "rotationCenterX": cx, "rotationCenterY": cy}


def base_target():
    return {"variables": {}, "lists": {}, "broadcasts": {}, "blocks": {},
            "comments": {}, "currentCostume": 0, "sounds": [], "volume": 100}


def make_stage(costumes, variables, broadcasts):
    t = base_target()
    t.update({"isStage": True, "name": "Stage",
              "variables": variables, "broadcasts": broadcasts,
              "costumes": costumes, "layerOrder": 0, "tempo": 60,
              "videoTransparency": 50, "videoState": "off",
              "textToSpeechLanguage": None})
    return t


def make_sprite(name, builder, costumes, layer, x, y, visible=True,
                size=100, current=0):
    fix_parents(builder.d)
    t = base_target()
    t.update({"isStage": False, "name": name, "blocks": builder.d,
              "costumes": costumes, "currentCostume": current,
              "layerOrder": layer, "visible": visible, "x": x, "y": y,
              "size": size, "direction": 90, "draggable": False,
              "rotationStyle": "all around"})
    return t


def monitor(vid, name, x, y, smin=0, smax=100):
    return {"id": vid, "mode": "default", "opcode": "data_variable",
            "params": {"VARIABLE": name}, "spriteName": None, "value": 0,
            "width": 0, "height": 0, "x": x, "y": y, "visible": True,
            "sliderMin": smin, "sliderMax": smax, "isDiscrete": True}


def package(out_path, targets, monitors, assets, extensions=None):
    project = {"targets": targets, "monitors": monitors,
               "extensions": extensions or [],
               "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": ""}}
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.json", json.dumps(project, ensure_ascii=False))
        for nm, data in assets.files.items():
            z.writestr(nm, data)
    return validate(out_path)


def validate(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None, "zip 损坏"
        p = json.loads(z.read("project.json"))
        files = set(z.namelist())

    errs = []
    # 造型素材
    for t in p["targets"]:
        for c in t["costumes"]:
            if c["md5ext"] not in files:
                errs.append(f"{t['name']} 缺造型 {c['md5ext']}")
    # 引用自洽
    for t in p["targets"]:
        ids = set(t["blocks"])
        for bid, blk in t["blocks"].items():
            for key in ("next", "parent"):
                v = blk.get(key)
                if v is not None and v not in ids:
                    errs.append(f"{t['name']}:{bid}.{key}->{v}")
            for k, inp in blk.get("inputs", {}).items():
                if not isinstance(inp, list):
                    continue
                for elem in inp[1:]:
                    if isinstance(elem, str) and elem not in ids:
                        errs.append(f"{t['name']}:{bid}.{k}->{elem}")
            if blk.get("topLevel") and ("x" not in blk or "y" not in blk):
                errs.append(f"{t['name']}:{bid} 顶层缺坐标")
    # 广播一致
    stage_bc = p["targets"][0]["broadcasts"]
    for t in p["targets"]:
        for bid, blk in t["blocks"].items():
            if blk["opcode"] == "event_whenbroadcastreceived":
                _id = blk["fields"]["BROADCAST_OPTION"][1]
                if _id not in stage_bc:
                    errs.append(f"{t['name']} 收到未定义广播 {_id}")
            if blk["opcode"] in ("event_broadcast", "event_broadcastandwait"):
                prim = blk["inputs"]["BROADCAST_INPUT"][1]
                if isinstance(prim, list) and prim[2] not in stage_bc:
                    errs.append(f"{t['name']} 发送未定义广播 {prim[2]}")
    # 监视器
    sv = p["targets"][0]["variables"]
    for m in p["monitors"]:
        if m["id"] not in sv:
            errs.append(f"监视器 {m['id']} 无变量")

    if errs:
        raise AssertionError("校验失败:\n" + "\n".join(errs))
    total = sum(len(t["blocks"]) for t in p["targets"])
    return {"targets": len(p["targets"]), "blocks": total,
            "extensions": p["extensions"]}
