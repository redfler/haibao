"""草–羊–狼 生态参数寻优模拟器（近似复现 03_生态平衡.sb3 的机制）。
目的：扫描参数，找到三者长期共存、数量有界波动的配置。

近似规则（每 1 秒一个 tick）：
  · 草：每 g_int 秒，若 <cap_g 则新增 randint(g_lo,g_hi) 株（随机位置）
  · 羊：每 s_int 秒，若 2<羊<cap_s 则新增 round(羊/2)
  · 狼：每 w_int 秒，若 2<狼<cap_w 则新增 round(狼/2)
  · 羊每行动：若 danger 内有狼→远离最近狼；否则走向最近草；之后若与某株草距离<er_sg→吃掉(草-1)、刷新进食
  · 狼每行动：走向最近羊；若与某只羊距离<er_ws→吃掉(羊-1)、刷新进食；同时该羊被捕食移除
  · 行动间隔：平时1s，吃到食物后下一次3s（用 next_act 控制）
  · 饥饿：羊/狼超过 starve 秒没进食→死亡
舞台：x∈[-240,240], y∈[-180,180]
"""
import numpy as np

XMIN, XMAX, YMIN, YMAX = -240, 240, -180, 180
ER_SG = 28    # 羊-草 接触半径
ER_WS = 34    # 狼-羊 接触半径


def rand_pos(n, rng):
    x = rng.uniform(-220, 200, n)
    y = rng.uniform(-150, 150, n)
    return np.stack([x, y], 1)


def nearest(points, targets):
    """对每个 point 返回最近 target 的 (索引, 距离平方)；targets 空则 (-1, inf)"""
    if len(targets) == 0:
        return np.full(len(points), -1), np.full(len(points), np.inf)
    d2 = ((points[:, None, :] - targets[None, :, :]) ** 2).sum(2)
    idx = d2.argmin(1)
    return idx, d2[np.arange(len(points)), idx]


def clamp(p):
    p[:, 0] = np.clip(p[:, 0], XMIN, XMAX)
    p[:, 1] = np.clip(p[:, 1], YMIN, YMAX)
    return p


def simulate(P, seed=0, T=420):
    rng = np.random.default_rng(seed)
    g = rand_pos(P.get("g0", rng.integers(8, 13)), rng)
    s = rand_pos(P["s0"], rng)
    w = rand_pos(P["w0"], rng)
    s_eat = np.zeros(len(s)); s_next = np.zeros(len(s))
    w_eat = np.zeros(len(w)); w_next = np.zeros(len(w))
    s_en = np.zeros(len(s)); w_en = np.zeros(len(w))   # 进食能量（食物驱动模式）
    food_mode = P.get("mode") == "food"
    danger2 = P["danger"] ** 2
    hist = []
    for t in range(1, T + 1):
        # —— 繁殖/再生 ——
        if t % P["g_int"] == 0 and len(g) < P["cap_g"]:
            add = rng.integers(P["g_lo"], P["g_hi"] + 1)
            add = min(add, P["cap_g"] - len(g))
            if add > 0:
                g = np.vstack([g, rand_pos(add, rng)])
        rfl = P.get("rfloor", 2)
        if not food_mode:   # 定时半数繁殖（原规则）
            if t % P["s_int"] == 0 and rfl < len(s) < P["cap_s"]:
                add = min(round(len(s) / 2), P["cap_s"] - len(s))
                if add > 0:
                    s = np.vstack([s, rand_pos(add, rng)])
                    s_eat = np.concatenate([s_eat, np.full(add, t)])
                    s_next = np.concatenate([s_next, np.full(add, t)])
                    s_en = np.concatenate([s_en, np.zeros(add)])
            if t % P["w_int"] == 0 and rfl < len(w) < P["cap_w"]:
                add = min(round(len(w) / 2), P["cap_w"] - len(w))
                if add > 0:
                    w = np.vstack([w, rand_pos(add, rng)])
                    w_eat = np.concatenate([w_eat, np.full(add, t)])
                    w_next = np.concatenate([w_next, np.full(add, t)])
                    w_en = np.concatenate([w_en, np.zeros(add)])

        # —— 羊行动 ——
        if len(s):
            act = s_next <= t
            if act.any():
                widx, wd2 = nearest(s, w)
                gidx, gd2 = nearest(s, g)
                flee = (wd2 < danger2) & (widx >= 0)
                mv = s[act].copy()
                ai = np.where(act)[0]
                for k, i in enumerate(ai):
                    if flee[i]:
                        tgt = w[widx[i]]; d = mv[k] - tgt          # 远离
                    elif gidx[i] >= 0:
                        tgt = g[gidx[i]]; d = tgt - mv[k]          # 走向草
                    else:
                        d = np.zeros(2)
                    n = np.hypot(*d)
                    if n > 1e-6:
                        mv[k] += P["s_speed"] * d / n
                s[ai] = clamp(mv)
                # 吃草
                gidx2, gd2b = nearest(s[ai], g)
                ate = (gidx2 >= 0) & (gd2b < ER_SG ** 2)
                eaten = set(); lambs = []
                for k, i in enumerate(ai):
                    if ate[k] and gidx2[k] not in eaten:
                        eaten.add(int(gidx2[k]))
                        s_eat[i] = t; s_next[i] = t + 3            # 吃到→下次隔3s
                        if food_mode:
                            s_en[i] += 1
                            if s_en[i] >= P["s_breed"] and len(s) + len(lambs) < P["cap_s"]:
                                s_en[i] = 0; lambs.append(s[i].copy())
                    else:
                        s_next[i] = t + 1
                if eaten:
                    keep = np.ones(len(g), bool)
                    keep[list(eaten)] = False
                    g = g[keep]
                if lambs:
                    s = np.vstack([s, np.array(lambs)])
                    s_eat = np.concatenate([s_eat, np.full(len(lambs), t)])
                    s_next = np.concatenate([s_next, np.full(len(lambs), t)])
                    s_en = np.concatenate([s_en, np.zeros(len(lambs))])

        # —— 狼行动 ——
        if len(w):
            act = w_next <= t
            if act.any():
                sidx, sd2 = nearest(w, s)
                ai = np.where(act)[0]
                mv = w[ai].copy()
                for k, i in enumerate(ai):
                    if sidx[i] >= 0:
                        d = s[sidx[i]] - mv[k]; n = np.hypot(*d)
                        if n > 1e-6:
                            mv[k] += P["w_speed"] * d / n
                w[ai] = clamp(mv)
                sidx2, sd2b = nearest(w[ai], s)
                ate = (sidx2 >= 0) & (sd2b < ER_WS ** 2)
                eaten = set(); pups = []
                for k, i in enumerate(ai):
                    if ate[k] and sidx2[k] not in eaten:
                        eaten.add(int(sidx2[k]))
                        w_eat[i] = t; w_next[i] = t + 3
                        if food_mode:
                            w_en[i] += 1
                            if w_en[i] >= P["w_breed"] and len(w) + len(pups) < P["cap_w"]:
                                w_en[i] = 0; pups.append(w[i].copy())
                    else:
                        w_next[i] = t + 1
                if eaten:
                    keep = np.ones(len(s), bool)
                    keep[list(eaten)] = False
                    s = s[keep]; s_eat = s_eat[keep]; s_next = s_next[keep]; s_en = s_en[keep]
                if pups:
                    w = np.vstack([w, np.array(pups)])
                    w_eat = np.concatenate([w_eat, np.full(len(pups), t)])
                    w_next = np.concatenate([w_next, np.full(len(pups), t)])
                    w_en = np.concatenate([w_en, np.zeros(len(pups))])

        # —— 饥饿死亡 ——
        if len(s):
            alive = (t - s_eat) <= P["s_starve"]
            s, s_eat, s_next, s_en = s[alive], s_eat[alive], s_next[alive], s_en[alive]
        if len(w):
            alive = (t - w_eat) <= P["w_starve"]
            w, w_eat, w_next, w_en = w[alive], w_eat[alive], w_next[alive], w_en[alive]

        # —— 密度制约死亡（拥挤致死；越多死亡概率越高，非硬封顶）——
        sc = P.get("s_crowd", 0.0)
        if sc and len(s):
            keep = rng.random(len(s)) >= min(0.95, sc * len(s))
            s, s_eat, s_next, s_en = s[keep], s_eat[keep], s_next[keep], s_en[keep]
        wc = P.get("w_crowd", 0.0)
        if wc and len(w):
            keep = rng.random(len(w)) >= min(0.95, wc * len(w))
            w, w_eat, w_next, w_en = w[keep], w_eat[keep], w_next[keep], w_en[keep]

        hist.append((len(g), len(s), len(w)))
    return np.array(hist)


T_SIM = 600


def score(P, seeds=(0, 1, 2, 3, 4)):
    """主目标：羊、狼共存的时长越长越好；全程共存再加奖励 + 鼓励种群处于中位。"""
    sc = 0.0
    for sd in seeds:
        h = simulate(P, sd, T=T_SIM)
        S, W = h[:, 1], h[:, 2]
        bad = np.where((S == 0) | (W == 0))[0]
        coexist = int(bad[0]) if len(bad) else T_SIM
        sc += coexist
        if coexist >= T_SIM:
            tail = h[T_SIM // 4:]
            # 奖励：全程都把羊、狼维持在“繁衍下限3”之上（越稳越高）
            sc += 800 + 10 * tail[:, 2].min() + 6 * tail[:, 1].min()
            if tail[:, 1].max() >= P["cap_s"]:
                sc -= 80          # 罚羊贴满上限（说明失衡爆发）
            if tail[:, 2].max() >= P["cap_w"]:
                sc -= 40
    return sc / len(seeds)


# 食物驱动繁殖：羊每吃 s_breed 株草生 1 羊；狼每吃 w_breed 只羊生 1 狼
BASE = dict(mode="food", g_lo=5, g_hi=20, g_int=1, cap_g=120,
            s_int=8, cap_s=80, w_int=11, cap_w=30,
            s_starve=20, w_starve=12, danger=60,
            s_speed=12, w_speed=15, s_breed=1, w_breed=3, s0=20, w0=5)


def search():
    rng = np.random.default_rng(7)
    best, best_sc = None, -1e18
    N = 220
    print(f"食物驱动·随机搜索 {N} 组（每组 5 个种子，T={T_SIM}s）...")
    for i in range(N):
        P = dict(BASE)
        P.update(
            w_speed=int(rng.integers(13, 18)),
            s_breed=int(rng.integers(1, 3)),
            w_breed=int(rng.integers(2, 7)),
            s_starve=int(rng.integers(16, 24)),
            w_starve=int(rng.integers(8, 16)),
            g_int=int(rng.integers(1, 3)),
            g_hi=int(rng.integers(14, 26)),
            cap_g=int(rng.integers(100, 151)),
            cap_s=int(rng.integers(60, 95)),
            cap_w=int(rng.integers(22, 38)),
            danger=int(rng.integers(35, 95)),
            s0=int(rng.integers(16, 26)),
            w0=int(rng.integers(4, 8)),
        )
        sc = score(P)
        if sc > best_sc:
            best_sc, best = sc, P
            print(f"  [{i}] score={sc:.0f} :: w_spd={P['w_speed']} s_breed={P['s_breed']} "
                  f"w_breed={P['w_breed']} s_stv={P['s_starve']} w_stv={P['w_starve']} "
                  f"g_int={P['g_int']} g_hi={P['g_hi']} capG={P['cap_g']} capS={P['cap_s']} "
                  f"capW={P['cap_w']} danger={P['danger']} s0={P['s0']} w0={P['w0']}")
    return best, best_sc


if __name__ == "__main__":
    best, sc = search()
    print("\n最优参数:", best, "score=", round(sc, 1))
    print("\n该配置 4 个种子的种群轨迹（每50秒采样 草/羊/狼）：")
    for sd in (0, 1, 2, 3):
        h = simulate(best, sd, T=T_SIM)
        pts = [f"{h[k][0]}/{h[k][1]}/{h[k][2]}" for k in range(0, len(h), 50)]
        print(f"  seed{sd}: " + "  ".join(pts))
