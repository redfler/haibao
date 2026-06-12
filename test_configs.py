"""验证：直接以平衡数量初始化（草~100,羊~80,狼~6）是否稳定。"""
from sim_balance import simulate
import numpy as np

best = dict(mode="food", g_lo=5, g_hi=23, g_int=1, cap_g=126,
            cap_s=85, w_int=11, cap_w=23, s_starve=22, w_starve=11,
            danger=77, s_speed=12, w_speed=14, s_breed=1, w_breed=6)
CONFIGS = {
    "init 草100/羊80/狼6": dict(best, g0=100, s0=80, w0=6),
    "init 草90/羊70/狼5": dict(best, g0=90, s0=70, w0=5),
    "init 草110/羊82/狼7": dict(best, g0=110, s0=82, w0=7),
}
for name, P in CONFIGS.items():
    print(f"\n=== {name} ===")
    surv = 0
    for sd in range(8):
        h = simulate(P, sd, T=600)
        S, W = h[:, 1], h[:, 2]
        bad = np.where((S == 0) | (W == 0))[0]
        co = int(bad[0]) if len(bad) else 600
        surv += co >= 600
        tail = h[300:]
        print(f"  seed{sd}: 共存{co}s 末段 草{tail[:,0].min()}-{tail[:,0].max()} "
              f"羊{tail[:,1].min()}-{tail[:,1].max()} 狼{tail[:,2].min()}-{tail[:,2].max()}")
    print(f"  → 8种子 {surv} 个全程600s共存")
