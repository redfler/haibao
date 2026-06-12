"""搜索食物驱动参数，使草/羊/狼自然稳定在 150:75:5 附近（不用调节器）。"""
import numpy as np
from sim_balance import simulate

TG, TS, TW = 150, 75, 5   # 目标
# 把“承载力上限”定在目标比例：到上限就不再繁殖（密度规则），靠捕食/饥饿提供动态
BASE = dict(mode="food", g_lo=5, g_int=1, cap_g=150,
            cap_s=75, cap_w=5, s_speed=12, danger=70, s0=75, w0=5, g0=150)


def score(P, seeds=(0, 1, 2, 3)):
    sc = 0.0
    for sd in seeds:
        h = simulate(P, sd, T=500)
        S, W = h[:, 1], h[:, 2]
        bad = np.where((S == 0) | (W == 0))[0]
        if len(bad):                       # 灭绝重罚（越早越差）
            sc += -1000 - (500 - bad[0])
            continue
        tail = h[250:]
        gm, sm, wm = tail[:, 0].mean(), tail[:, 1].mean(), tail[:, 2].mean()
        # 与目标的相对偏差（越小越好），取负作为分数
        dev = abs(gm - TG) / TG + abs(sm - TS) / TS + abs(wm - TW) / TW
        sc += -dev
    return sc / len(seeds)


def search(n=240):
    rng = np.random.default_rng(20)
    best, bsc = None, -1e18
    print(f"搜索 {n} 组（目标 150:75:5）...")
    for i in range(n):
        P = dict(BASE)
        P.update(
            g_hi=int(rng.integers(8, 24)),
            s_breed=int(rng.integers(1, 4)),
            w_breed=int(rng.integers(3, 9)),
            s_starve=int(rng.integers(10, 24)),
            w_starve=int(rng.integers(8, 18)),
            w_speed=int(rng.integers(13, 19)),
            danger=int(rng.integers(40, 100)),
        )
        s = score(P)
        if s > bsc:
            bsc, best = s, P
            print(f"  [{i}] score={s:.3f} g_hi={P['g_hi']} s_breed={P['s_breed']} "
                  f"w_breed={P['w_breed']} s_stv={P['s_starve']} w_stv={P['w_starve']} "
                  f"w_spd={P['w_speed']} danger={P['danger']}")
    return best, bsc


if __name__ == "__main__":
    best, sc = search()
    print("\n最优:", {k: best[k] for k in ('g_hi', 's_breed', 'w_breed', 's_starve',
          'w_starve', 'w_speed', 'danger')}, "score=", round(sc, 3))
    print("\n轨迹（每50s 草/羊/狼）:")
    for sd in range(5):
        h = simulate(best, sd, T=500)
        print(f"  seed{sd}: " + "  ".join(
            f"{h[k][0]}/{h[k][1]}/{h[k][2]}" for k in range(0, len(h), 50)))
