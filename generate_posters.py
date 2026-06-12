"""
生成5张主题海报：
1. 大气环境治理
2. 水资源培育
3. 大自然生态系统搭建
4. 能源供给
5. 人类居住场景规划
"""
import os
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT_DIR = "/home/horde/isaac/haibao"
os.makedirs(OUT_DIR, exist_ok=True)

# 海报尺寸（加大纵向以容纳详细 Scratch 代码）
W, H = 1240, 1900

# 字体路径
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"


def font(size, bold=True, serif=False):
    path = FONT_SERIF if serif else (FONT_BOLD if bold else FONT_REG)
    return ImageFont.truetype(path, size, index=0)


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def vertical_gradient(w, h, top, bottom):
    img = Image.new("RGB", (w, h), top)
    top = hex2rgb(top) if isinstance(top, str) else top
    bottom = hex2rgb(bottom) if isinstance(bottom, str) else bottom
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        for x in range(w):
            px[x, y] = (r, g, b)
    return img


def diagonal_gradient(w, h, c1, c2):
    img = Image.new("RGB", (w, h))
    c1 = hex2rgb(c1) if isinstance(c1, str) else c1
    c2 = hex2rgb(c2) if isinstance(c2, str) else c2
    px = img.load()
    for y in range(h):
        for x in range(w):
            t = (x + y) / (w + h)
            r = int(c1[0] * (1 - t) + c2[0] * t)
            g = int(c1[1] * (1 - t) + c2[1] * t)
            b = int(c1[2] * (1 - t) + c2[2] * t)
            px[x, y] = (r, g, b)
    return img


def wrap_text(text, fnt, max_w):
    """按字符宽度分行（中文）"""
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        cur = ""
        for ch in paragraph:
            test = cur + ch
            bbox = fnt.getbbox(test)
            if bbox[2] - bbox[0] > max_w and cur:
                lines.append(cur)
                cur = ch
            else:
                cur = test
        if cur:
            lines.append(cur)
    return lines


def draw_text_block(draw, x, y, text, fnt, fill, max_w, line_height=None):
    lines = wrap_text(text, fnt, max_w)
    lh = line_height if line_height else int(fnt.size * 1.55)
    for i, line in enumerate(lines):
        draw.text((x, y + i * lh), line, font=fnt, fill=fill)
    return y + len(lines) * lh


def rounded_panel(img, box, fill, radius=24, alpha=255):
    """绘制半透明圆角面板"""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    if isinstance(fill, str):
        fill = hex2rgb(fill)
    d.rounded_rectangle(box, radius=radius, fill=(*fill, alpha))
    img.alpha_composite(overlay)


def draw_section_header(draw, x, y, num, title, accent, text_color="#ffffff"):
    """绘制章节编号 + 标题"""
    num_font = font(50, bold=True, serif=True)
    title_font = font(34, bold=True)
    # 编号方块
    box = (x, y, x + 70, y + 70)
    draw.rounded_rectangle(box, radius=12, fill=accent)
    bbox = num_font.getbbox(num)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((x + (70 - tw) / 2 - bbox[0], y + (70 - th) / 2 - bbox[1]), num,
              font=num_font, fill="#ffffff")
    # 标题
    draw.text((x + 90, y + 15), title, font=title_font, fill=text_color)
    # 装饰底线
    draw.rectangle((x + 90, y + 62, x + 90 + 200, y + 65), fill=accent)
    return y + 95


# ============================================================
# 海报 1：大气环境治理
# ============================================================
def poster_atmosphere():
    bg = vertical_gradient(W, H, "#0b3d91", "#7ec8e3")
    img = bg.convert("RGBA")
    draw = ImageDraw.Draw(img)

    # 顶部云层装饰
    cloud_layer = Image.new("RGBA", (W, 350), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cloud_layer)
    random.seed(1)
    for _ in range(40):
        cx = random.randint(-50, W + 50)
        cy = random.randint(20, 280)
        cr = random.randint(40, 120)
        a = random.randint(30, 90)
        cd.ellipse((cx - cr, cy - cr * 0.6, cx + cr, cy + cr * 0.6),
                   fill=(255, 255, 255, a))
    cloud_layer = cloud_layer.filter(ImageFilter.GaussianBlur(8))
    img.alpha_composite(cloud_layer)

    # 标题区
    title_font = font(86, serif=True)
    subtitle_font = font(34, bold=False)
    draw.text((80, 110), "蔚蓝呼吸", font=title_font, fill="#ffffff")
    draw.text((80, 215), "—— 大气环境治理可视化模拟", font=subtitle_font,
              fill="#e6f4ff")
    # 顶部右侧标签
    tag_box = (W - 280, 130, W - 80, 180)
    draw.rounded_rectangle(tag_box, radius=25, fill="#ffd166")
    draw.text((W - 260, 138), "主题 01 · 大气", font=font(26), fill="#1a1a1a")

    # 内容面板
    panel_top = 310
    panel_box = (60, panel_top, W - 60, H - 320)
    rounded_panel(img, panel_box, "#ffffff", radius=30, alpha=235)
    draw = ImageDraw.Draw(img)

    x = 100
    y = panel_top + 40

    # 1 灵感来源
    y = draw_section_header(draw, x, y, "1", "灵感来源与构思过程", "#0b3d91",
                            text_color="#0b3d91")
    inspiration = (
        "项目最初源于冬季雾霾天气中孩子戴着口罩上学的画面。"
        "我们思考：能否用图形化编程，让看不见的污染物变成可视的粒子？"
        "构思阶段经历了三次方向调整——从单一PM2.5浓度地图，"
        "到加入风场与扩散模拟，最终确定为"
        "“污染源-气象-治理措施”三层联动的动态沙盘。"
    )
    y = draw_text_block(draw, x, y, inspiration, font(24, bold=False),
                        "#1a1a1a", W - 220, line_height=40)
    y += 30

    # 2 图形化编程模拟
    y = draw_section_header(draw, x, y, "2", "图形化编程模拟方法", "#0b3d91",
                            text_color="#0b3d91")
    code_text = (
        "[Scratch 项目：城市污染扩散沙盘]\n"
        "当 ▶ 被点击：\n"
        "  设 [污染源数量 ▼] 为 (滑杆1.值)\n"
        "  设 [风速 ▼] 为 (滑杆2.值)\n"
        "  克隆 [PM2.5粒子] (污染源数量 × 50) 次\n"
        "当 [PM2.5粒子] 作为克隆体启动时：\n"
        "  重复执行：\n"
        "    将 x 增加 ((风速) × cos(风向) + 在-2和2间取随机数)\n"
        "    将 [浓度 ▼] 设为 ([浓度] × 0.97)   // 扩散衰减\n"
        "    如果 <碰到 [净化塔 ▼]?> 那么 → 删除此克隆体\n"
        "    如果 <[浓度] < 5> 那么 → 将 [颜色特效] 设为 绿色\n"
        "    落笔 → 在地图上记录粒子轨迹\n"
        "当接收到 [刷新热力图 ▼]（每 10 帧）：\n"
        "  对 50×50 网格每格：统计粒子数 → 涂热力色"
    )
    lines = code_text.split("\n")
    code_h = 25 + len(lines) * 28
    code_box = (x, y, W - 100, y + code_h)
    draw.rounded_rectangle(code_box, radius=14, fill="#0b3d91")
    code_font = font(20, bold=False)
    for i, line in enumerate(lines):
        draw.text((x + 24, y + 15 + i * 28), line, font=code_font,
                  fill="#a8d8ff" if "//" in line else "#ffffff")
    y += code_h + 25

    # 3 实践总结
    y = draw_section_header(draw, x, y, "3", "成功 · 问题 · 收获", "#0b3d91",
                            text_color="#0b3d91")

    # 三栏总结
    col_w = (W - 200) // 3
    col_titles = ["✓ 成功之处", "✗ 遇到的问题", "★ 收获与改进"]
    col_colors = ["#06a77d", "#e63946", "#ffb703"]
    col_texts = [
        "粒子扩散算法稳定运行；\n"
        "新增净化塔后，浓度热力图\n"
        "在300帧内由红转绿，直观\n"
        "展现治理效果。",
        "初版粒子过万导致卡顿；\n"
        "未考虑昼夜温差导致的\n"
        "逆温层现象，模拟与真实\n"
        "数据偏差较大。",
        "改用网格采样替代逐粒子\n"
        "渲染，性能提升5倍；\n"
        "下一步将接入真实API\n"
        "数据，做城市级仿真。"
    ]
    for i in range(3):
        cx = x + i * (col_w + 20)
        draw.rounded_rectangle((cx, y, cx + col_w, y + 230), radius=18,
                               outline=col_colors[i], width=4)
        draw.rectangle((cx, y, cx + col_w, y + 50), fill=col_colors[i])
        draw.text((cx + 20, y + 10), col_titles[i], font=font(24),
                  fill="#ffffff")
        draw_text_block(draw, cx + 20, y + 70, col_texts[i],
                        font(20, bold=False), "#1a1a1a", col_w - 40,
                        line_height=32)
    y += 310

    # 底部：作品展示 - 简化的污染扩散可视化
    chart_top = H - 290
    draw.rounded_rectangle((60, chart_top, W - 60, H - 50), radius=24,
                           fill="#0b3d91")
    draw.text((90, chart_top + 20), "作品展示：城市污染扩散热力沙盘",
              font=font(28), fill="#ffd166")
    # 模拟热力图
    grid_w = W - 200
    grid_h = 160
    gx = 100
    gy = chart_top + 75
    cols, rows = 30, 10
    cw = grid_w // cols
    ch = grid_h // rows
    random.seed(5)
    for r in range(rows):
        for c in range(cols):
            # 模拟从左到右的污染源 + 扩散
            dist = math.sqrt((c - 4) ** 2 + (r - 5) ** 2)
            intensity = max(0, 1 - dist / 14) + random.uniform(-0.1, 0.1)
            intensity = max(0, min(1, intensity))
            if intensity > 0.7:
                col = (230, 57, 70)
            elif intensity > 0.45:
                col = (255, 183, 3)
            elif intensity > 0.2:
                col = (255, 214, 102)
            else:
                col = (6, 167, 125)
            draw.rectangle((gx + c * cw, gy + r * ch,
                            gx + (c + 1) * cw - 2, gy + (r + 1) * ch - 2),
                           fill=col)
    # 图例
    legend_y = H - 80
    legend_items = [("污染严重", (230, 57, 70)), ("中度", (255, 183, 3)),
                    ("轻度", (255, 214, 102)), ("清洁", (6, 167, 125))]
    lx = 100
    for name, col in legend_items:
        draw.rectangle((lx, legend_y, lx + 30, legend_y + 24), fill=col)
        draw.text((lx + 40, legend_y), name, font=font(22, bold=False),
                  fill="#ffffff")
        lx += 200

    img.convert("RGB").save(os.path.join(OUT_DIR, "01_大气环境治理.jpg"),
                            quality=92)
    print("已生成: 01_大气环境治理.jpg")


# ============================================================
# 海报 2：水资源培育
# ============================================================
def poster_water():
    bg = vertical_gradient(W, H, "#013a63", "#61a5c2")
    img = bg.convert("RGBA")
    draw = ImageDraw.Draw(img)

    # 顶部水波纹装饰
    wave_layer = Image.new("RGBA", (W, 350), (0, 0, 0, 0))
    wd = ImageDraw.Draw(wave_layer)
    for amp, freq, y0, color, alpha in [
        (30, 0.012, 180, (135, 206, 235), 70),
        (40, 0.008, 220, (173, 216, 230), 60),
        (50, 0.006, 270, (224, 247, 250), 80),
    ]:
        points = []
        for x in range(0, W + 5, 5):
            y = y0 + amp * math.sin(freq * x)
            points.append((x, y))
        points += [(W, 350), (0, 350)]
        wd.polygon(points, fill=(*color, alpha))
    img.alpha_composite(wave_layer)

    # 标题
    draw.text((80, 110), "青山涵水", font=font(86, serif=True), fill="#ffffff")
    draw.text((80, 215), "—— 森林涵养水源对比模拟", font=font(34, bold=False),
              fill="#caf0f8")
    tag_box = (W - 280, 130, W - 80, 180)
    draw.rounded_rectangle(tag_box, radius=25, fill="#90e0ef")
    draw.text((W - 260, 138), "主题 02 · 水脉", font=font(26),
              fill="#013a63")

    # 内容面板
    panel_top = 310
    rounded_panel(img, (60, panel_top, W - 60, H - 320), "#ffffff",
                  radius=30, alpha=235)
    draw = ImageDraw.Draw(img)
    x = 100
    y = panel_top + 40

    y = draw_section_header(draw, x, y, "1", "灵感来源与构思过程", "#013a63",
                            text_color="#013a63")
    inspiration = (
        "课本上说“绿水青山就是金山银山”，可森林到底怎么“养”水？"
        "我们想做一个看得见的对比：同样下一场雨，光秃的山和有树的山，"
        "谁能把水留住、补进地下水。起初想模拟整条河流，发现太复杂；"
        "于是聚焦“两座山的较量”——裸山水土流失、森林树根蓄水，"
        "只用两个变量和柱状图，就把“植树涵养水源”讲清楚了。"
    )
    y = draw_text_block(draw, x, y, inspiration, font(24, bold=False),
                        "#1a1a1a", W - 220, line_height=40)
    y += 30

    y = draw_section_header(draw, x, y, "2", "图形化编程模拟方法", "#013a63",
                            text_color="#013a63")
    code_text = (
        "[Scratch 项目：裸山 VS 森林 · 只用基础积木]\n"
        "当 ▶ 被点击：\n"
        "  将 [裸山地下水 ▼] 设为 0\n"
        "  将 [森林地下水 ▼] 设为 0\n"
        "  重复 (20) 次：           （模拟下 20 滴雨）\n"
        "    等待 0.3 秒             下一个造型（雨在飘）\n"
        "    将 [裸山地下水 ▼] 增加 1     （只渗进一点）\n"
        "    将 [森林地下水 ▼] 增加 3     （树根多存水）\n"
        "    将 [裸山柱.高度 ▼] 设为 (裸山地下水)\n"
        "    将 [森林柱.高度 ▼] 设为 (森林地下水)\n"
        "  说 (连接 [森林比裸山多存水 ]\n"
        "      ((森林地下水) - (裸山地下水))) 2 秒\n"
        "当点击 [种树 ▼] 按钮：    （把裸山变成森林）\n"
        "  将左山 换成 [绿树造型 ▼]   播放声音 [鸟鸣 ▼]"
    )
    lines = code_text.split("\n")
    code_h = 25 + len(lines) * 28
    code_box = (x, y, W - 100, y + code_h)
    draw.rounded_rectangle(code_box, radius=14, fill="#013a63")
    code_font = font(20, bold=False)
    for i, line in enumerate(lines):
        draw.text((x + 24, y + 15 + i * 28), line, font=code_font,
                  fill="#caf0f8")
    y += code_h + 25

    y = draw_section_header(draw, x, y, "3", "成功 · 问题 · 收获", "#013a63",
                            text_color="#013a63")
    col_w = (W - 200) // 3
    col_titles = ["✓ 成功之处", "✗ 遇到的问题", "★ 收获与改进"]
    col_colors = ["#06a77d", "#e63946", "#ffb703"]
    col_texts = [
        "两根柱子边涨边对比，\n"
        "森林明显存水更多；\n"
        "点“种树”按钮让裸山\n"
        "变绿，对比一目了然。",
        "起初两山加水一样多，\n"
        "看不出差别；又忘了\n"
        "把变量数值同步到\n"
        "柱子高度，柱子不动。",
        "把森林渗水率调成裸山\n"
        "的 3 倍，差距立现；\n"
        "下一步想加“暴雨”按钮，\n"
        "演示裸山水土流失。"
    ]
    for i in range(3):
        cx = x + i * (col_w + 20)
        draw.rounded_rectangle((cx, y, cx + col_w, y + 230), radius=18,
                               outline=col_colors[i], width=4)
        draw.rectangle((cx, y, cx + col_w, y + 50), fill=col_colors[i])
        draw.text((cx + 20, y + 10), col_titles[i], font=font(24),
                  fill="#ffffff")
        draw_text_block(draw, cx + 20, y + 70, col_texts[i],
                        font(20, bold=False), "#1a1a1a", col_w - 40,
                        line_height=32)

    # 底部：裸山 vs 森林对比舞台
    chart_top = H - 290
    draw.rounded_rectangle((60, chart_top, W - 60, H - 50), radius=24,
                           fill="#013a63")
    draw.text((90, chart_top + 20), "作品展示：裸山 VS 森林涵养水源对比（Scratch 运行画面）",
              font=font(26), fill="#90e0ef")

    base_y = H - 90          # 地面线
    mid_x = W // 2
    draw.line((90, base_y, W - 90, base_y), fill="#90e0ef", width=2)

    # ---- 左半：裸山 ----
    # 雨
    for i in range(6):
        rx = 200 + i * 26
        draw.line((rx, chart_top + 70, rx - 5, chart_top + 100),
                  fill="#90e0ef", width=3)
    # 光秃山坡（土黄）
    draw.polygon([(140, base_y), (300, base_y - 110), (440, base_y)],
                 fill="#b08968")
    # 流失的水（向下箭头/径流）
    draw.text((150, base_y - 70), "水土流失↘", font=font(20, bold=False),
              fill="#ff8fa3")
    # 裸山地下水柱（少）
    bar_bare_h = 40
    draw.rectangle((mid_x - 200, base_y - bar_bare_h, mid_x - 130, base_y),
                   fill="#48cae4")
    draw.text((mid_x - 215, base_y - bar_bare_h - 30), "地下水 20",
              font=font(20), fill="#ffffff")
    draw.text((220, chart_top + 50), "裸山", font=font(26), fill="#ffd166")

    # 分隔线
    draw.line((mid_x, chart_top + 60, mid_x, base_y), fill="#90e0ef", width=2)

    # ---- 右半：森林 ----
    for i in range(6):
        rx = mid_x + 120 + i * 26
        draw.line((rx, chart_top + 70, rx - 5, chart_top + 100),
                  fill="#90e0ef", width=3)
    # 绿色山坡
    draw.polygon([(mid_x + 60, base_y), (mid_x + 220, base_y - 110),
                  (mid_x + 380, base_y)], fill="#4a6741")
    # 山上的树
    for tx in [mid_x + 150, mid_x + 220, mid_x + 290]:
        ty = base_y - 60 if tx == mid_x + 220 else base_y - 35
        draw.polygon([(tx, ty - 40), (tx - 18, ty), (tx + 18, ty)],
                     fill="#2d6a4f")
        draw.rectangle((tx - 4, ty, tx + 4, ty + 14), fill="#6f4518")
    # 森林地下水柱（多）
    bar_forest_h = 110
    draw.rectangle((mid_x + 420, base_y - bar_forest_h, mid_x + 490, base_y),
                   fill="#48cae4")
    draw.text((mid_x + 405, base_y - bar_forest_h - 30), "地下水 60",
              font=font(20), fill="#ffffff")
    draw.text((mid_x + 130, chart_top + 50), "森林", font=font(26),
              fill="#80ed99")

    img.convert("RGB").save(os.path.join(OUT_DIR, "02_水资源培育.jpg"),
                            quality=92)
    print("已生成: 02_水资源培育.jpg")


# ============================================================
# 海报 3：大自然生态系统搭建
# ============================================================
def poster_ecosystem():
    bg = vertical_gradient(W, H, "#1b4332", "#95d5b2")
    img = bg.convert("RGBA")
    draw = ImageDraw.Draw(img)

    # 顶部树叶装饰
    leaf_layer = Image.new("RGBA", (W, 350), (0, 0, 0, 0))
    ld = ImageDraw.Draw(leaf_layer)
    random.seed(3)
    for _ in range(60):
        cx = random.randint(0, W)
        cy = random.randint(20, 320)
        cr = random.randint(20, 60)
        a = random.randint(60, 140)
        green = random.choice([(82, 121, 70), (104, 146, 79), (130, 163, 93)])
        ld.ellipse((cx - cr, cy - cr * 0.55, cx + cr, cy + cr * 0.55),
                   fill=(*green, a))
    leaf_layer = leaf_layer.filter(ImageFilter.GaussianBlur(4))
    img.alpha_composite(leaf_layer)

    draw.text((80, 110), "万物共生", font=font(86, serif=True), fill="#ffffff")
    draw.text((80, 215), "—— 大自然生态系统搭建", font=font(34, bold=False),
              fill="#d8f3dc")
    draw.rounded_rectangle((W - 280, 130, W - 80, 180), radius=25,
                           fill="#ffb703")
    draw.text((W - 245, 138), "主题 · 生态", font=font(26),
              fill="#1b4332")

    panel_top = 310
    rounded_panel(img, (60, panel_top, W - 60, H - 320), "#ffffff",
                  radius=30, alpha=235)
    draw = ImageDraw.Draw(img)
    x = 100
    y = panel_top + 40

    y = draw_section_header(draw, x, y, "1", "灵感来源与构思过程", "#1b4332",
                            text_color="#1b4332")
    inspiration = (
        "草养羊、羊喂狼——这条“草—羊—狼”食物链里，谁多谁少都牵一发动全身。"
        "我们想做一个会自我维持的生态沙盘：个体会寻路觅食、被捕食、饿死、繁殖。"
        "项目几经迭代：从随机游走→检测最近食物寻路、羊会避狼；"
        "最关键的一次转变是——发现“定时按数量繁殖”怎么调参都会让狼灭绝，"
        "于是改成“吃够食物才繁殖”，才让捕食者与猎物真正耦合、产生持续震荡，"
        "并以平衡态数量初始化、加“平衡”按钮一键复位。"
    )
    y = draw_text_block(draw, x, y, inspiration, font(24, bold=False),
                        "#1a1a1a", W - 220, line_height=40)
    y += 30

    y = draw_section_header(draw, x, y, "2", "图形化编程模拟方法", "#1b4332",
                            text_color="#1b4332")
    code_text = (
        "[Scratch 项目：草–羊–狼 食物链平衡（食物驱动繁殖）]\n"
        "当 ▶ 被点击：重置计时器；草初始~100，羊/狼数量设为 0\n"
        "寻路：用列表[草X/Y][羊X/Y][狼X/Y]记录各克隆坐标(广播上报)\n"
        "  羊→遍历列表找最近的草并走向；若<最近狼距²<避狼半径²>则逃离\n"
        "  狼→找最近的羊追击\n"
        "进食/繁殖(食物驱动)：\n"
        "  羊碰到草→草消失、[羊能量]+1；能量≥[羊繁殖食量]→克隆小羊\n"
        "  狼碰到羊→羊消失、[狼能量]+1；能量≥[狼繁殖食量]→克隆小狼\n"
        "死亡：碰到天敌→消失；计时器-[进食时刻]>[饿死间隔]→饿死\n"
        "按钮：⚖平衡→把草/羊/狼补齐到平衡态(100/80/6)；+羊 +狼\n"
        "画笔：草 / 羊 / 狼 三根数量柱实时绘制"
    )
    lines = code_text.split("\n")
    code_h = 25 + len(lines) * 28
    code_box = (x, y, W - 100, y + code_h)
    draw.rounded_rectangle(code_box, radius=14, fill="#1b4332")
    code_font = font(20, bold=False)
    for i, line in enumerate(lines):
        draw.text((x + 24, y + 15 + i * 28), line, font=code_font,
                  fill="#d8f3dc")
    y += code_h + 25

    y = draw_section_header(draw, x, y, "3", "成功 · 问题 · 收获", "#1b4332",
                            text_color="#1b4332")
    col_w = (W - 200) // 3
    col_titles = ["✓ 成功之处", "✗ 遇到的问题", "★ 收获与改进"]
    col_colors = ["#06a77d", "#e63946", "#ffb703"]
    col_texts = [
        "克隆体寻路觅食、避敌；\n"
        "用坐标列表破解“找最近”\n"
        "难题；写 Python 模拟器\n"
        "扫了上千组参数，最终\n"
        "实现长期共存震荡。",
        "原“定时半数繁殖+>2”\n"
        "规则下狼必灭绝：羊会逃\n"
        "抓不到、≤2 无法恢复、\n"
        "繁殖与进食脱钩，调参\n"
        "无解。",
        "改“吃够食物才繁殖”使\n"
        "捕食者-猎物真正耦合；\n"
        "从平衡态初始化最稳。\n"
        "改进：加避难所、概率化\n"
        "捕食、空间分区提性能。"
    ]
    for i in range(3):
        cx = x + i * (col_w + 20)
        draw.rounded_rectangle((cx, y, cx + col_w, y + 230), radius=18,
                               outline=col_colors[i], width=4)
        draw.rectangle((cx, y, cx + col_w, y + 50), fill=col_colors[i])
        draw.text((cx + 20, y + 10), col_titles[i], font=font(24),
                  fill="#ffffff")
        draw_text_block(draw, cx + 20, y + 70, col_texts[i],
                        font(20, bold=False), "#1a1a1a", col_w - 40,
                        line_height=32)

    # 底部：草–羊–狼食物链（Scratch 运行画面）
    chart_top = H - 290
    draw.rounded_rectangle((60, chart_top, W - 60, H - 50), radius=24,
                           fill="#1b4332")
    draw.text((90, chart_top + 18),
              "作品展示：草–羊–狼食物链（Scratch 运行画面）",
              font=font(25), fill="#ffb703")
    # 模拟舞台 UI：标题正上方居中
    tt = "生态平衡 草-羊-狼"
    bb = font(22).getbbox(tt)
    draw.text(((W - (bb[2] - bb[0])) / 2, chart_top + 54), tt, font=font(22),
              fill="#d8f3dc")
    # 左上角三个数量读数
    for j, (lab, col) in enumerate([("草 100", "#80ed99"), ("羊 80", "#f1f1f1"),
                                    ("狼 6", "#9aa0a6")]):
        draw.text((90, chart_top + 86 + j * 26), lab, font=font(20), fill=col)
    # 右上角三个按钮（⚖平衡 / +羊 / +狼）
    for j, (lab, col) in enumerate([("⚖ 平衡", "#3a86ff"), ("+ 羊", "#52b788"),
                                    ("+ 狼", "#6f767c")]):
        bxr = W - 200
        by = chart_top + 50 + j * 40
        draw.rounded_rectangle((bxr, by, bxr + 110, by + 34),
                               radius=16, fill=col, outline="#ffffff", width=2)
        draw.text((bxr + 16, by + 5), lab, font=font(22), fill="#ffffff")

    base_y = H - 95          # 基线
    # 草丛随机散布（对应克隆体随机分布）
    random.seed(11)
    for _ in range(22):
        gx = random.randint(95, 700)
        gy = random.randint(chart_top + 95, base_y)
        h = random.randint(14, 24)
        draw.line((gx, gy, gx - 3, gy - h), fill="#52b788", width=3)
        draw.line((gx + 4, gy, gx + 4, gy - h + 3), fill="#40916c", width=3)
        draw.line((gx + 8, gy, gx + 11, gy - h), fill="#52b788", width=3)

    # 简易羊：白色绒毛身 + 深色头
    sx, sy = 250, base_y - 36
    draw.rectangle((sx - 8, sy + 14, sx - 4, sy + 24), fill="#6b6b6b")
    draw.rectangle((sx + 8, sy + 14, sx + 12, sy + 24), fill="#6b6b6b")
    draw.ellipse((sx - 16, sy - 2, sx + 16, sy + 20), fill="#f3f3f3")
    draw.ellipse((sx - 14, sy - 10, sx - 2, sy + 2), fill="#f3f3f3")
    draw.ellipse((sx + 0, sy - 12, sx + 14, sy + 2), fill="#f3f3f3")
    draw.ellipse((sx + 12, sy - 2, sx + 24, sy + 12), fill="#444")   # 头
    draw.ellipse((sx + 19, sy + 1, sx + 23, sy + 5), fill="#fff")

    # 简易狼：灰色身 + 尖耳大尾
    wx, wy = 560, base_y - 36
    draw.rectangle((wx - 6, wy + 14, wx - 2, wy + 24), fill="#6f767c")
    draw.rectangle((wx + 10, wy + 14, wx + 14, wy + 24), fill="#6f767c")
    draw.polygon([(wx - 18, wy + 14), (wx - 30, wy + 20), (wx - 16, wy + 4)],
                 fill="#9aa0a6")                       # 尾
    draw.ellipse((wx - 18, wy - 2, wx + 18, wy + 18), fill="#9aa0a6")
    draw.ellipse((wx + 8, wy - 12, wx + 30, wy + 8), fill="#9aa0a6")   # 头
    draw.polygon([(wx + 11, wy - 10), (wx + 13, wy - 22), (wx + 19, wy - 10)],
                 fill="#7c8288")
    draw.polygon([(wx + 22, wy - 10), (wx + 24, wy - 22), (wx + 30, wy - 10)],
                 fill="#7c8288")
    draw.polygon([(wx + 26, wy - 2), (wx + 38, wy + 0), (wx + 26, wy + 6)],
                 fill="#b6bbbf")                        # 吻
    draw.ellipse((wx + 22, wy - 4, wx + 26, wy), fill="#000")

    # 右侧：草/羊/狼 三根数量柱（画笔效果）
    bx0 = 770
    bars = [("草", 72, "#80ed99"), ("羊", 40, "#f1f1f1"), ("狼", 18, "#9aa0a6")]
    bw, gap = 66, 38
    for i, (name, val, col) in enumerate(bars):
        cx0 = bx0 + i * (bw + gap)
        bh = int(val / 100 * 150)
        draw.rectangle((cx0, base_y - bh, cx0 + bw, base_y), fill=col)
        draw.text((cx0 + 8, base_y - bh - 30), str(val), font=font(22),
                  fill="#ffffff")
        draw.text((cx0 + 20, base_y + 6), name, font=font(24), fill="#ffffff")

    # 图例
    legend = [("草", "#80ed99"), ("羊", "#f1f1f1"), ("狼", "#9aa0a6")]
    lx = 100
    for name, c in legend:
        draw.rectangle((lx, H - 78, lx + 28, H - 60), fill=c)
        draw.text((lx + 36, H - 82), name, font=font(22, bold=False),
                  fill="#ffffff")
        lx += 150

    img.convert("RGB").save(os.path.join(OUT_DIR, "03_大自然生态系统搭建.jpg"),
                            quality=92)
    print("已生成: 03_大自然生态系统搭建.jpg")


# ============================================================
# 海报 4：能源供给
# ============================================================
def poster_energy():
    bg = vertical_gradient(W, H, "#6a040f", "#ffb703")
    img = bg.convert("RGBA")
    draw = ImageDraw.Draw(img)

    # 顶部能量光线
    ray_layer = Image.new("RGBA", (W, 350), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ray_layer)
    cx, cy = W // 2, 80
    for ang in range(0, 360, 6):
        rad = math.radians(ang)
        x2 = cx + int(900 * math.cos(rad))
        y2 = cy + int(900 * math.sin(rad))
        rd.line((cx, cy, x2, y2), fill=(255, 214, 102, 30), width=2)
    ray_layer = ray_layer.filter(ImageFilter.GaussianBlur(3))
    img.alpha_composite(ray_layer)

    draw.text((80, 110), "光耀新能", font=font(86, serif=True), fill="#ffffff")
    draw.text((80, 215), "—— 清洁能源供给与调度", font=font(34, bold=False),
              fill="#ffe8a3")
    draw.rounded_rectangle((W - 280, 130, W - 80, 180), radius=25,
                           fill="#80ed99")
    draw.text((W - 260, 138), "主题 04 · 能源", font=font(26),
              fill="#6a040f")

    panel_top = 310
    rounded_panel(img, (60, panel_top, W - 60, H - 320), "#ffffff",
                  radius=30, alpha=235)
    draw = ImageDraw.Draw(img)
    x = 100
    y = panel_top + 40

    y = draw_section_header(draw, x, y, "1", "灵感来源与构思过程", "#6a040f",
                            text_color="#6a040f")
    inspiration = (
        "一次野外露营，太阳能板白天发电充足，到了夜晚却只能依赖小柴油机。"
        "这种“能量过剩”与“能量短缺”交替出现的体验，"
        "让我们思考：能不能搭建一个微型多源调度系统？"
        "项目从单一光伏，扩展到“光伏+风电+储能+用电”四节点；"
        "在构思中我们一度想加核能，因复杂度过高最终选择更直观的可再生组合。"
    )
    y = draw_text_block(draw, x, y, inspiration, font(24, bold=False),
                        "#1a1a1a", W - 220, line_height=40)
    y += 30

    y = draw_section_header(draw, x, y, "2", "图形化编程模拟方法", "#6a040f",
                            text_color="#6a040f")
    code_text = (
        "[Scratch 项目：微电网 24 小时调度]\n"
        "当 ▶ 被点击：\n"
        "  设 [电池储能 ▼] 为 50；设 [当前小时 ▼] 为 0\n"
        "  重复 24 次（每次代表 1 小时）：\n"
        "    [光伏] ← 装机 × sin(π × 当前小时 / 24) × 天气系数\n"
        "    [风电] ← 装机 × ([风速] / 12)\n"
        "    [发电] ← [光伏] + [风电]\n"
        "    [用电] ← 基础负荷 + 高峰加权(当前小时)\n"
        "    如果 <[发电] > [用电]> 那么：\n"
        "      [电池储能] ← [电池储能] + ([发电]-[用电]) × 0.9\n"
        "    否则：\n"
        "      [电池储能] ← [电池储能] - ([用电]-[发电]) / 0.9\n"
        "      若 <[电池储能] < 0> → 广播 [启动备用 ▼]\n"
        "    画笔绘制：当前小时柱状图（光伏/风电/储能/用电）\n"
        "    [当前小时] ← [当前小时] + 1"
    )
    lines = code_text.split("\n")
    code_h = 25 + len(lines) * 28
    code_box = (x, y, W - 100, y + code_h)
    draw.rounded_rectangle(code_box, radius=14, fill="#6a040f")
    code_font = font(20, bold=False)
    for i, line in enumerate(lines):
        draw.text((x + 24, y + 15 + i * 28), line, font=code_font,
                  fill="#ffe8a3")
    y += code_h + 25

    y = draw_section_header(draw, x, y, "3", "成功 · 问题 · 收获", "#6a040f",
                            text_color="#6a040f")
    col_w = (W - 200) // 3
    col_titles = ["✓ 成功之处", "✗ 遇到的问题", "★ 收获与改进"]
    col_colors = ["#06a77d", "#e63946", "#ffb703"]
    col_texts = [
        "实现24小时发用储\n"
        "动态平衡可视化；\n"
        "新能源占比达到85%\n"
        "时系统仍稳定。",
        "夜间用电峰值与\n"
        "光伏低谷叠加，\n"
        "导致备用电源频繁\n"
        "启动，体验不佳。",
        "加入“分时电价”\n"
        "与“可调节负载”，\n"
        "把电热水器移到白天\n"
        "充足时段，成功削峰。"
    ]
    for i in range(3):
        cx = x + i * (col_w + 20)
        draw.rounded_rectangle((cx, y, cx + col_w, y + 230), radius=18,
                               outline=col_colors[i], width=4)
        draw.rectangle((cx, y, cx + col_w, y + 50), fill=col_colors[i])
        draw.text((cx + 20, y + 10), col_titles[i], font=font(24),
                  fill="#ffffff")
        draw_text_block(draw, cx + 20, y + 70, col_texts[i],
                        font(20, bold=False), "#1a1a1a", col_w - 40,
                        line_height=32)

    # 底部：24小时柱状图
    chart_top = H - 290
    draw.rounded_rectangle((60, chart_top, W - 60, H - 50), radius=24,
                           fill="#6a040f")
    draw.text((90, chart_top + 20), "作品展示：24小时多源发电与用电曲线",
              font=font(28), fill="#80ed99")

    ax_x0, ax_y0 = 130, chart_top + 220
    ax_x1, ax_y1 = W - 110, chart_top + 80
    draw.line((ax_x0, ax_y0, ax_x1, ax_y0), fill="#ffe8a3", width=2)
    draw.line((ax_x0, ax_y0, ax_x0, ax_y1), fill="#ffe8a3", width=2)

    # 24个时段
    bar_w = (ax_x1 - ax_x0) / 24
    for h in range(24):
        # 光伏
        solar = max(0, math.sin(math.pi * h / 24)) * 0.9
        # 风电
        wind = 0.3 + 0.2 * math.sin(h * 0.6 + 1)
        # 用电
        load = 0.4 + 0.5 * (1 if 6 <= h <= 9 or 18 <= h <= 22 else 0.4)
        bx = ax_x0 + h * bar_w
        # 堆叠柱：光伏（金）+风电（绿）
        s_h = solar * (ax_y0 - ax_y1)
        w_h = wind * (ax_y0 - ax_y1)
        draw.rectangle((bx + 2, ax_y0 - s_h, bx + bar_w - 4, ax_y0),
                       fill="#ffd166")
        draw.rectangle((bx + 2, ax_y0 - s_h - w_h, bx + bar_w - 4,
                        ax_y0 - s_h), fill="#80ed99")
        # 用电曲线点
        ly = ax_y0 - load * (ax_y0 - ax_y1)
        if h > 0:
            prev_load = 0.4 + 0.5 * (1 if 6 <= h - 1 <= 9 or
                                     18 <= h - 1 <= 22 else 0.4)
            prev_ly = ax_y0 - prev_load * (ax_y0 - ax_y1)
            draw.line((bx + bar_w / 2 - bar_w, prev_ly,
                       bx + bar_w / 2, ly), fill="#e63946", width=3)
    # 图例
    legend = [("光伏", "#ffd166"), ("风电", "#80ed99"),
              ("用电曲线", "#e63946")]
    lx = 130
    for name, c in legend:
        draw.rectangle((lx, H - 75, lx + 30, H - 60), fill=c)
        draw.text((lx + 40, H - 80), name, font=font(22, bold=False),
                  fill="#ffffff")
        lx += 250

    img.convert("RGB").save(os.path.join(OUT_DIR, "04_能源供给.jpg"),
                            quality=92)
    print("已生成: 04_能源供给.jpg")


# ============================================================
# 海报 5：人类居住场景规划
# ============================================================
def poster_habitat():
    bg = vertical_gradient(W, H, "#3a0ca3", "#f72585")
    img = bg.convert("RGBA")
    draw = ImageDraw.Draw(img)

    # 顶部建筑剪影
    sky_layer = Image.new("RGBA", (W, 350), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sky_layer)
    random.seed(7)
    bx = 0
    while bx < W:
        bw = random.randint(40, 110)
        bh = random.randint(80, 230)
        sd.rectangle((bx, 350 - bh, bx + bw, 350), fill=(20, 20, 60, 180))
        # 窗户
        for wy in range(350 - bh + 15, 340, 25):
            for wx in range(bx + 8, bx + bw - 8, 18):
                if random.random() > 0.4:
                    sd.rectangle((wx, wy, wx + 8, wy + 12),
                                 fill=(255, 214, 102, 200))
        bx += bw + random.randint(5, 15)
    img.alpha_composite(sky_layer)

    draw.text((80, 110), "未来之家", font=font(86, serif=True), fill="#ffffff")
    draw.text((80, 215), "—— 智慧低碳人居场景规划", font=font(34, bold=False),
              fill="#ffd6e7")
    draw.rounded_rectangle((W - 280, 130, W - 80, 180), radius=25,
                           fill="#80ed99")
    draw.text((W - 260, 138), "主题 05 · 人居", font=font(26),
              fill="#3a0ca3")

    panel_top = 310
    rounded_panel(img, (60, panel_top, W - 60, H - 320), "#ffffff",
                  radius=30, alpha=235)
    draw = ImageDraw.Draw(img)
    x = 100
    y = panel_top + 40

    y = draw_section_header(draw, x, y, "1", "灵感来源与构思过程", "#3a0ca3",
                            text_color="#3a0ca3")
    inspiration = (
        "夏天回家，发现小区里没有一棵能遮阴的大树，"
        "通勤花两小时却看不到公园，孩子们只能在马路边玩耍。"
        "我们意识到：好的居住，不仅是房子，而是“15分钟生活圈”。"
        "构思过程中先做了纯住宅小区，发现过于单调；"
        "随后加入步行、绿地、新能源、社区中心，"
        "最终落定为“职-住-绿-行”一体化的社区方案。"
    )
    y = draw_text_block(draw, x, y, inspiration, font(24, bold=False),
                        "#1a1a1a", W - 220, line_height=40)
    y += 30

    y = draw_section_header(draw, x, y, "2", "图形化编程模拟方法", "#3a0ca3",
                            text_color="#3a0ca3")
    code_text = (
        "[Scratch 项目：15分钟生活圈仿真]\n"
        "当 ▶ 被点击：\n"
        "  克隆 [居民] 100 次，初始位置=[住宅 ▼]\n"
        "  随机分布 [学校/公园/超市/办公] 角色于 30×30 地图\n"
        "  广播 [开始一天 ▼]\n"
        "当 [居民] 接收到 [开始一天 ▼]（每天循环）：\n"
        "  设 [目标 ▼] 为 在 (学校, 公园, 超市, 公司) 中随机选\n"
        "  [路径] ← A*寻路(起点=住宅, 终点=[目标])\n"
        "  [步行时间] ← 长度([路径]) / [步速]\n"
        "  如果 <[步行时间] ≤ 15> 那么：\n"
        "    [满意度] ← [满意度] + 1\n"
        "    沿路径移动 → 播放走路动画\n"
        "  否则：\n"
        "    [碳排] ← [碳排] + 0.4 × [距离]   // 机动车出行\n"
        "  [社区评分] ← [满意度] / 居民数 × 100\n"
        "广播 [刷新仪表盘 ▼]：绘制 人流热力图 + 评分仪表"
    )
    lines = code_text.split("\n")
    code_h = 25 + len(lines) * 28
    code_box = (x, y, W - 100, y + code_h)
    draw.rounded_rectangle(code_box, radius=14, fill="#3a0ca3")
    code_font = font(20, bold=False)
    for i, line in enumerate(lines):
        draw.text((x + 24, y + 15 + i * 28), line, font=code_font,
                  fill="#ffd6e7")
    y += code_h + 25

    y = draw_section_header(draw, x, y, "3", "成功 · 问题 · 收获", "#3a0ca3",
                            text_color="#3a0ca3")
    col_w = (W - 200) // 3
    col_titles = ["✓ 成功之处", "✗ 遇到的问题", "★ 收获与改进"]
    col_colors = ["#06a77d", "#e63946", "#ffb703"]
    col_texts = [
        "完成2km×2km社区沙盘；\n"
        "92%居民步行15分钟内\n"
        "可达学校与商业，\n"
        "碳排降低38%。",
        "初版功能区过于集中，\n"
        "造成高峰拥堵；\n"
        "未考虑老年人步行\n"
        "速度差异。",
        "采用多中心组团布局，\n"
        "增加无障碍坡道；\n"
        "引入分时段人流仿真，\n"
        "拥堵指数下降一半。"
    ]
    for i in range(3):
        cx = x + i * (col_w + 20)
        draw.rounded_rectangle((cx, y, cx + col_w, y + 230), radius=18,
                               outline=col_colors[i], width=4)
        draw.rectangle((cx, y, cx + col_w, y + 50), fill=col_colors[i])
        draw.text((cx + 20, y + 10), col_titles[i], font=font(24),
                  fill="#ffffff")
        draw_text_block(draw, cx + 20, y + 70, col_texts[i],
                        font(20, bold=False), "#1a1a1a", col_w - 40,
                        line_height=32)

    # 底部：社区平面示意图
    chart_top = H - 290
    draw.rounded_rectangle((60, chart_top, W - 60, H - 50), radius=24,
                           fill="#3a0ca3")
    draw.text((90, chart_top + 20), "作品展示：15分钟生活圈社区平面示意",
              font=font(28), fill="#80ed99")

    # 绘制 8x4 网格示意
    gx0 = 130
    gy0 = chart_top + 70
    grid_w = W - 260
    grid_h = 120
    cols, rows = 10, 4
    cw = grid_w / cols
    rh = grid_h / rows
    # 配置：H=住宅，S=学校，P=公园，M=超市，O=办公，T=交通
    layout = [
        list("HHGHHGPHHO"),
        list("HHGHHGMHHO"),
        list("THHSHHGHHO"),
        list("HHGHHGPHHO"),
    ]
    colors_map = {
        "H": ("#caf0f8", "住"),
        "G": ("#80ed99", "绿"),
        "S": ("#ffd166", "校"),
        "P": ("#06a77d", "园"),
        "M": ("#f72585", "商"),
        "O": ("#3a0ca3", "办"),
        "T": ("#e63946", "通"),
    }
    cell_font = font(20)
    for r in range(rows):
        for c in range(cols):
            kind = layout[r][c]
            col, label = colors_map[kind]
            cx0 = gx0 + c * cw
            cy0 = gy0 + r * rh
            draw.rectangle((cx0 + 2, cy0 + 2, cx0 + cw - 4, cy0 + rh - 4),
                           fill=col)
            text_col = "#ffffff" if kind in "OPMT" else "#1a1a1a"
            bbox = cell_font.getbbox(label)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text((cx0 + (cw - tw) / 2 - bbox[0],
                       cy0 + (rh - th) / 2 - bbox[1]),
                      label, font=cell_font, fill=text_col)

    # 图例
    legend_items = [("住宅", "#caf0f8"), ("绿地", "#80ed99"),
                    ("学校", "#ffd166"), ("公园", "#06a77d"),
                    ("商业", "#f72585"), ("办公", "#3a0ca3")]
    legend_y = gy0 + grid_h + 25
    lx = 130
    for name, c in legend_items:
        draw.rectangle((lx, legend_y, lx + 28, legend_y + 22), fill=c)
        draw.text((lx + 36, legend_y - 4), name, font=font(20, bold=False),
                  fill="#ffffff")
        lx += 160

    img.convert("RGB").save(os.path.join(OUT_DIR, "05_人类居住场景规划.jpg"),
                            quality=92)
    print("已生成: 05_人类居住场景规划.jpg")


if __name__ == "__main__":
    poster_atmosphere()
    poster_water()
    poster_ecosystem()
    poster_energy()
    poster_habitat()
    print("\n全部完成。输出目录：", OUT_DIR)
