"""阶段4：假设检验与回归分析。

输入：data/battles_detailed.json
输出：
  results/analysis_results.json   全部数值结果
  results/分析报告_数据结果.md     人读版结果
  figures/*.png                   可视化
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
plt.rcParams["font.sans-serif"] = ["WenQuanYi Zen Hei"]
plt.rcParams["axes.unicode_minus"] = False

# ---------- 读入 ----------
rows = json.load(open(os.path.join(BASE, "data", "battles_detailed.json"), encoding="utf-8"))
df = pd.DataFrame(rows).sort_values("datetime").reset_index(drop=True)  # 时间正序
N = len(df)
win = df[df.win == 1]
lose = df[df.win == 0]
results = {"n": N, "wins": int(df.win.sum()), "losses": int((1 - df.win).sum())}


# ---------- 1. 描述统计 ----------
metrics = ["kills", "deaths", "assists", "kda_ratio", "headshot_rate",
           "adr", "damage", "economy_score", "clutches", "rr_earned"]
desc = df.groupby("win")[metrics].mean().round(2).T
desc.columns = ["负场均值", "胜场均值"]
results["describe"] = desc.to_dict()


# ---------- 2. Welch 两样本 t 检验（胜负组差异）----------
def cohens_d(a, b):
    na, nb = len(a), len(b)
    sp = np.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    return (a.mean() - b.mean()) / sp


ttests = {}
for m in ["kda_ratio", "kills", "deaths", "adr", "headshot_rate", "economy_score"]:
    t, p = stats.ttest_ind(win[m], lose[m], equal_var=False)
    ttests[m] = {"t": round(float(t), 3), "p": round(float(p), 5),
                 "d": round(float(cohens_d(win[m], lose[m])), 3)}
results["ttest"] = ttests


# ---------- 3. 卡方：高击杀 vs 胜负 ----------
med_kill = df.kills.median()
df["high_kill"] = (df.kills >= med_kill).astype(int)
ct = pd.crosstab(df.high_kill, df.win)
chi2, p_chi, dof, _ = stats.chi2_contingency(ct, correction=True)
odds = (ct.iloc[1, 1] * ct.iloc[0, 0]) / max(ct.iloc[1, 0] * ct.iloc[0, 1], 1)
results["chi_square"] = {
    "threshold": float(med_kill), "table": ct.values.tolist(),
    "chi2": round(float(chi2), 3), "p": round(float(p_chi), 5),
    "odds_ratio": round(float(odds), 2)}


# ---------- 4. 游程检验（连胜连败是否随机）----------
seq = df.win.values
n1, n2 = int(seq.sum()), int((1 - seq).sum())
runs = 1 + int((seq[1:] != seq[:-1]).sum())
mu_r = 2 * n1 * n2 / N + 1
var_r = (2 * n1 * n2 * (2 * n1 * n2 - N)) / (N ** 2 * (N - 1))
z_r = (runs - mu_r) / np.sqrt(var_r)
p_r = 2 * (1 - stats.norm.cdf(abs(z_r)))
# 最长连胜/连败
max_w = max_l = cur = 0
prev = seq[0]
for v in seq:
    if v == prev:
        cur += 1
    else:
        cur, prev = 1, v
    if v == 1: max_w = max(max_w, cur)
    else: max_l = max(max_l, cur)
results["runs_test"] = {"runs": runs, "expected": round(mu_r, 2),
                        "z": round(float(z_r), 3), "p": round(float(p_r), 4),
                        "max_win_streak": max_w, "max_lose_streak": max_l}


# ---------- 5. 相关性 ----------
corr_cols = ["win", "kda_ratio", "kills", "deaths", "headshot_rate",
             "adr", "economy_score", "clutches", "rr_earned"]
corr = df[corr_cols].corr().round(3)
results["corr_with_rr"] = corr["rr_earned"].drop("rr_earned").to_dict()


# ---------- 6. OLS：RR 增减对表现因素回归 ----------
X1 = sm.add_constant(df[["win"]])
X2 = sm.add_constant(df[["win", "kda_ratio", "headshot_rate", "adr", "clutches"]])
m1 = sm.OLS(df.rr_earned, X1).fit()
m2 = sm.OLS(df.rr_earned, X2).fit()
# 模型1 vs 模型2 增量 F 检验
rss1, rss2 = m1.ssr, m2.ssr
df_diff = m2.df_model - m1.df_model
f_inc = ((rss1 - rss2) / df_diff) / (rss2 / m2.df_resid)
p_finc = 1 - stats.f.cdf(f_inc, df_diff, m2.df_resid)

def model_pack(m):
    return {"coef": {k: round(float(v), 3) for k, v in m.params.items()},
            "pvalues": {k: round(float(v), 4) for k, v in m.pvalues.items()},
            "r2": round(float(m.rsquared), 3),
            "r2_adj": round(float(m.rsquared_adj), 3)}
results["ols"] = {"model1_win_only": model_pack(m1),
                  "model2_full": model_pack(m2),
                  "incremental_F": round(float(f_inc), 3),
                  "incremental_p": round(float(p_finc), 5)}

# ---------- 7. 地图/特工胜率（描述性）----------
map_wr = df.groupby("map_name").agg(
    场次=("win", "size"), 胜=("win", "sum")).reset_index()
map_wr["胜率"] = (map_wr.胜 / map_wr.场次).round(2)
agent_wr = df.groupby("agent").agg(
    场次=("win", "size"), 胜=("win", "sum")).reset_index()
agent_wr["胜率"] = (agent_wr.胜 / agent_wr.场次).round(2)
results["map_winrate"] = map_wr.to_dict("records")
results["agent_winrate"] = agent_wr[agent_wr.场次 >= 3].to_dict("records")


# ================= 可视化 =================
figdir = os.path.join(BASE, "figures")
os.makedirs(figdir, exist_ok=True)

# 图1：胜负组核心指标均值对比
fig, axes = plt.subplots(1, 4, figsize=(13, 3.4))
for ax, m, title in zip(axes, ["kda_ratio", "kills", "adr", "headshot_rate"],
                        ["KDA比率", "击杀", "回合均伤ADR", "爆头率"]):
    means = [lose[m].mean(), win[m].mean()]
    bars = ax.bar(["负场", "胜场"], means, color=["#ef4444", "#22c55e"])
    ax.bar_label(bars, fmt="%.2f", padding=2)
    ax.set_title(title)
fig.suptitle("胜场 vs 负场：核心表现指标均值对比")
fig.tight_layout()
fig.savefig(os.path.join(figdir, "01_胜负组指标对比.png"), dpi=130)
plt.close(fig)

# 图2：RR 随时间变化（胜负着色）
fig, ax = plt.subplots(figsize=(12, 3.6))
colors = df.win.map({1: "#16a34a", 0: "#dc2626"})
ax.bar(range(N), df.rr_earned, color=colors)
ax.axhline(0, color="#333", lw=0.8)
ax.set_title("每场 RR（段位评分）增减，绿=胜 红=负（时间从左到右）")
ax.set_xlabel("对局序号")
ax.set_ylabel("RR 增减")
fig.tight_layout()
fig.savefig(os.path.join(figdir, "02_RR时间序列.png"), dpi=130)
plt.close(fig)

# 图3：地图胜率
fig, ax = plt.subplots(figsize=(9, 3.8))
mw = map_wr.sort_values("胜率")
bars = ax.barh(mw.map_name, mw.胜率, color="#3b82f6")
ax.bar_label(bars, labels=[f"{r:.0%}（{n}场）" for r, n in zip(mw.胜率, mw.场次)], padding=3)
ax.set_xlim(0, 1)
ax.set_title("各地图胜率")
fig.tight_layout()
fig.savefig(os.path.join(figdir, "03_地图胜率.png"), dpi=130)
plt.close(fig)

# 图4：相关性热力图
fig, ax = plt.subplots(figsize=(7.5, 6))
im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
ax.set_xticks(range(len(corr_cols)), corr_cols, rotation=45, ha="right")
ax.set_yticks(range(len(corr_cols)), corr_cols)
for i in range(len(corr_cols)):
    for j in range(len(corr_cols)):
        ax.text(j, i, corr.iloc[i, j], ha="center", va="center", fontsize=8)
fig.colorbar(im)
ax.set_title("核心指标相关系数矩阵")
fig.tight_layout()
fig.savefig(os.path.join(figdir, "04_相关性热力图.png"), dpi=130)
plt.close(fig)

# 图5：RR 回归 实测 vs 预测
fig, ax = plt.subplots(figsize=(6.5, 5))
ax.scatter(m2.predict(), df.rr_earned, c=colors, s=45)
lims = [-32, 42]
ax.plot(lims, lims, "--", color="#888")
ax.set_xlim(lims); ax.set_ylim(lims)
ax.set_xlabel("模型预测 RR")
ax.set_ylabel("实际 RR")
ax.set_title(f"OLS 模型2：实测 vs 预测 RR（R²={m2.rsquared:.3f}）")
fig.tight_layout()
fig.savefig(os.path.join(figdir, "05_RR回归预测.png"), dpi=130)
plt.close(fig)


# ================= 保存结果 =================
os.makedirs(os.path.join(BASE, "results"), exist_ok=True)
json.dump(results, open(os.path.join(BASE, "results", "analysis_results.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=1)
print("分析完成，n =", N)
print(json.dumps({k: results[k] for k in
      ["ttest", "chi_square", "runs_test", "ols"]}, ensure_ascii=False, indent=1))
