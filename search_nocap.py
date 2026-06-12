"""不使用上限封顶：靠 食物驱动繁殖 + 饥饿/捕食 + 密度制约死亡 自然平衡到 150:75:5。
羊/狼无数量上限(cap 设极大)；草受草地面积约束(资源，非动物封顶)。"""
import numpy as np
from sim_balance import simulate

TG, TS, TW = 150, 75, 5
BASE = dict(mode="food", g_lo=5, g_int=1, cap_g=150,
            cap_s=99999, cap_w=99999,         # 动物无封顶
            s_speed=12, s0=72, w0=5, g0=150)


def score(P, seeds=(0, 1, 2, 3)):
    sc = 0.0
    for sd in seeds:
        h = simulate(P, sd, T=600)
        S, W = h[:, 1], h[:, 2]
        bad = np.where((S == 0) | (W == 0))[0]
        if len(bad):
            sc += -1000 - (600 - bad[0]); continue
        tl = h[300:]
        gm, sm, wm = tl[:, 0].mean(), tl[:, 1].mean(), tl[:, 2].mean()
        dev = abs(gm - TG) / TG + abs(sm - TS) / TS + abs(wm - TW) / TW
        # 振幅惩罚（鼓励稳）
        amp = tl[:, 1].std() / max(sm, 1) + tl[:, 2].std() / max(wm, 1)
        sc += -(dev + 0.3 * amp)
    return sc / len(seeds)


def search(n=260):
    rng = np.random.default_rng(5)
    best, bsc = None, -1e18
    print(f"无封顶搜索 {n} 组（密度制约死亡，目标150:75:5）...")
    for i in range(n):
        P = dict(BASE)
        P.update(
            g_hi=int(rng.integers(8, 22)),
            s_breed=int(rng.integers(1, 3)),
            w_breed=int(rng.integers(3, 9)),
            s_starve=int(rng.integers(12, 26)),
            w_starve=int(rng.integers(8, 18)),
            w_speed=int(rng.integers(13, 19)),
            danger=int(rng.integers(45, 100)),
            s_crowd=float(rng.uniform(0.001, 0.010)),
            w_crowd=float(rng.uniform(0.005, 0.060)),
        )
        s = score(P)
        if s > bsc:
            bsc, best = s, P
            print(f"  [{i}] score={s:.3f} g_hi={P['g_hi']} s_breed={P['s_breed']} "
                  f"w_breed={P['w_breed']} s_stv={P['s_starve']} w_stv={P['w_starve']} "
                  f"w_spd={P['w_speed']} danger={P['danger']} "
                  f"s_crowd={P['s_crowd']:.4f} w_crowd={P['w_crowd']:.4f}")
    return best, bsc


if __name__ == "__main__":
    best, sc = search()
    print("\n最优:", {k: (round(best[k], 4) if isinstance(best[k], float) else best[k])
          for k in ('g_hi', 's_breed', 'w_breed', 's_starve', 'w_starve',
                    'w_speed', 'danger', 's_crowd', 'w_crowd')}, "score=", round(sc, 3))
    print("\n轨迹（每60s 草/羊/狼）+ 均值:")
    for sd in range(5):
        h = simulate(best, sd, T=600)
        tl = h[300:]
        pts = "  ".join(f"{h[k][0]}/{h[k][1]}/{h[k][2]}" for k in range(0, len(h), 60))
        print(f"  seed{sd}: {pts}  | 均值 {tl[:,0].mean():.0f}/{tl[:,1].mean():.0f}/{tl[:,2].mean():.1f}")
