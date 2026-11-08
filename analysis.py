"""
Project 2: County food environment (Food Environment Index) vs adult diabetes prevalence, U.S. counties.
Reproducible script.  Run:  python3 analysis.py      Needs: pandas, numpy, scipy, matplotlib.
(statsmodels was unavailable, so OLS, HC3 and cluster-robust SEs, VIF and Breusch-Pagan are implemented below with numpy.)

Inputs (data_raw/), all from County Health Rankings & Roadmaps (CHR&R):
  chr_analytic_data2025_v3.csv           2025 Annual Data Release, analytic file
  chr_analytic_supplement_20260325.csv   Supplemental Release (March 25, 2026): updated FEI, diabetes, inactivity, uninsured, obesity (2023 data)
Outputs (outputs/): cleaned_county_dataset.csv, results.json, results.csv, figure1_food_environment_diabetes.png, diagnostics_residuals.png
"""
import json, os
import numpy as np, pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__)); RAW = os.path.join(HERE, "data_raw"); OUT = os.path.join(HERE, "outputs")
os.makedirs(OUT, exist_ok=True)
R = {}

# ------------------------------------------------------------------ load + clean
ann = pd.read_csv(os.path.join(RAW, "chr_analytic_data2025_v3.csv"), skiprows=[0], dtype=str, low_memory=False)  # row 0 = long names; row 1 = codes
sup = pd.read_csv(os.path.join(RAW, "chr_analytic_supplement_20260325.csv"), dtype=str, low_memory=False)
num = lambda s: pd.to_numeric(s, errors="coerce")
ann = ann[ann.countycode != "000"].copy(); sup = sup[sup.countycode != "000"].copy()
R["n_county_rows_annual"] = int(len(ann)); R["n_county_rows_supplement"] = int(len(sup))

a = pd.DataFrame({"fips": ann.fipscode, "state": ann.state, "county": ann.county,
                  "fei_ann": num(ann.v133_rawvalue), "diab_ann": num(ann.v060_rawvalue) * 100,
                  "inact_ann": num(ann.v070_rawvalue) * 100, "unins_ann": num(ann.v085_rawvalue) * 100,
                  "obes_ann": num(ann.v011_rawvalue) * 100,
                  "income": num(ann.v063_rawvalue), "rural": num(ann.v058_rawvalue)})
if a.rural.max() <= 1.0001: a["rural"] = a.rural * 100            # stored as proportion -> percent
s = pd.DataFrame({"fips": sup.fipscode, "fei": num(sup.v133_rawvalue), "diab": num(sup.v060_rawvalue) * 100,
                  "inact": num(sup.v070_rawvalue) * 100, "unins": num(sup.v085_rawvalue) * 100, "obes": num(sup.v011_rawvalue) * 100})
d = a.merge(s, on="fips", how="outer", indicator=True)
R["merge_counts"] = d["_merge"].value_counts().to_dict(); d = d.drop(columns="_merge")
d["income_k"] = d.income / 1000.0; d["log_income"] = np.log(d.income)
d.to_csv(os.path.join(OUT, "cleaned_county_dataset_all_variables.csv"), index=False)

MAIN = ["fei", "diab", "income_k", "unins", "rural", "inact"]
# PRIMARY analysis: 2025 Annual Data Release (complete and internally consistent data years; the March 2026 supplement lacks
# diabetes/inactivity for 120 Kentucky and 67 Pennsylvania counties and does not update income or rurality).
P = d[["fips", "state", "county", "fei_ann", "diab_ann", "inact_ann", "unins_ann", "obes_ann", "income_k", "log_income", "rural"]].rename(
    columns={"fei_ann": "fei", "diab_ann": "diab", "inact_ann": "inact", "unins_ann": "unins", "obes_ann": "obes"})
# SENSITIVITY dataset: March 2026 supplement values (2023 data) for FEI, diabetes, inactivity, uninsured, obesity; income/rurality from annual release
S = d[["fips", "state", "county", "fei", "diab", "inact", "unins", "obes", "income_k", "log_income", "rural"]].copy()
d_all = d; d = P
cc = d.dropna(subset=MAIN).copy()
R["n_counties_supplement_sensitivity"] = int(S.dropna(subset=MAIN).shape[0])
R["supplement_missing_states_for_diabetes"] = sorted(set(S.state) - set(S.dropna(subset=["diab"]).state))
R["n_counties_main_complete_cases"] = int(len(cc)); R["n_states_in_sample"] = int(cc.state.nunique())
R["n_missing_by_var"] = {k: int(d[k].isna().sum()) for k in MAIN + ["obes"]}
cc.to_csv(os.path.join(OUT, "cleaned_county_dataset.csv"), index=False)
R["fei_range_observed"] = [float(cc.fei.min()), float(cc.fei.max())]

# ------------------------------------------------------------------ descriptives
lab = {"fei": "Food Environment Index (0-10)", "diab": "Adult diabetes prevalence (%)", "income_k": "Median household income ($1,000s)",
       "unins": "Uninsured, under 65 (%)", "rural": "Rural population (%)", "inact": "Physical inactivity (%)", "obes": "Adult obesity (%)"}
desc = {}
for k in MAIN + ["obes"]:
    x = cc[k] if k != "obes" else d.obes.dropna()
    desc[k] = {"label": lab[k], "n": int(x.notna().sum()), "mean": float(x.mean()), "sd": float(x.std()), "median": float(x.median()),
               "q1": float(x.quantile(.25)), "q3": float(x.quantile(.75)), "min": float(x.min()), "max": float(x.max())}
R["descriptives"] = desc

# ------------------------------------------------------------------ Spearman
r, p = stats.spearmanr(cc.fei, cc.diab); R["spearman_fei_diab"] = {"rho": float(r), "p": float(p), "n": int(len(cc))}
for k in ["income_k", "unins", "rural", "inact"]:
    r2, p2 = stats.spearmanr(cc[k], cc.diab); R[f"spearman_{k}_diab"] = {"rho": float(r2), "p": float(p2)}
r3, p3 = stats.spearmanr(cc.fei, cc.income_k); R["spearman_fei_income"] = {"rho": float(r3), "p": float(p3)}

# ------------------------------------------------------------------ OLS machinery
def ols(y, X, names, cluster=None, hc="HC3"):
    n, k = X.shape; XtXi = np.linalg.inv(X.T @ X); b = XtXi @ X.T @ y; e = y - X @ b
    if cluster is None:
        h = np.einsum("ij,jk,ik->i", X, XtXi, X)
        w = e ** 2 / (1 - h) ** 2 if hc == "HC3" else e ** 2
        V = XtXi @ (X.T @ (X * w[:, None])) @ XtXi
        dfp = n - k
    else:
        g = pd.Series(cluster).astype("category").cat.codes.values; G = g.max() + 1
        meat = np.zeros((k, k))
        for gi in range(G):
            ug = X[g == gi].T @ e[g == gi]; meat += np.outer(ug, ug)
        V = XtXi @ meat @ XtXi * (G / (G - 1)) * ((n - 1) / (n - k)); dfp = G - 1
    se = np.sqrt(np.diag(V)); t = b / se; pv = 2 * stats.t.sf(np.abs(t), dfp); tc = stats.t.ppf(.975, dfp)
    ss_res = e @ e; ss_tot = ((y - y.mean()) ** 2).sum(); r2 = 1 - ss_res / ss_tot
    return {"names": names, "b": b, "se": se, "p": pv, "lo": b - tc * se, "hi": b + tc * se, "r2": r2,
            "adj_r2": 1 - (1 - r2) * (n - 1) / (n - k), "n": n, "resid": e, "fitted": X @ b, "XtXi": XtXi}

def fit(df, xs, y="diab", std=False, cluster=False, fe=False, hc="HC3"):
    dd = df.dropna(subset=[y] + xs).copy()
    Y = dd[y].values.astype(float); Xv = dd[xs].values.astype(float)
    if std: Y = (Y - Y.mean()) / Y.std(ddof=1); Xv = (Xv - Xv.mean(0)) / Xv.std(0, ddof=1)
    X = np.column_stack([np.ones(len(dd)), Xv]); names = ["intercept"] + xs
    if fe:
        D = pd.get_dummies(dd.state, drop_first=True).values.astype(float); X = np.column_stack([X, D]); names += [f"st_{i}" for i in range(D.shape[1])]
    m = ols(Y, X, names, cluster=dd.state.values if cluster else None, hc=hc)
    m["df"] = dd; m["X"] = X; return m

def pack(m, keep):
    out = {"n": int(m["n"]), "r2": float(m["r2"]), "adj_r2": float(m["adj_r2"])}
    for k in keep:
        i = m["names"].index(k); out[k] = {"b": float(m["b"][i]), "se": float(m["se"][i]), "lo": float(m["lo"][i]), "hi": float(m["hi"][i]), "p": float(m["p"][i])}
    return out

XS = ["fei", "income_k", "unins", "rural", "inact"]
# unadjusted and adjusted (primary): robust HC3 SEs
m0 = fit(cc, ["fei"]); R["model_unadjusted_hc3"] = pack(m0, ["fei"])
m1 = fit(cc, XS); R["model_adjusted_hc3"] = pack(m1, XS)
m1s = fit(cc, XS, std=True); R["model_adjusted_standardized_hc3"] = pack(m1s, XS)
m0s = fit(cc, ["fei"], std=True); R["model_unadjusted_standardized_hc3"] = pack(m0s, ["fei"])
m_nofei = fit(cc, [x for x in XS if x != "fei"]); R["r2_without_fei"] = float(m_nofei["r2"]); R["r2_increment_from_fei"] = float(m1["r2"] - m_nofei["r2"])
# sensitivity
R["sens_state_clustered_se"] = pack(fit(cc, XS, cluster=True), XS)
R["sens_state_clustered_se_standardized"] = pack(fit(cc, XS, std=True, cluster=True), XS)
R["sens_state_fixed_effects_clustered"] = pack(fit(cc, XS, cluster=True, fe=True), XS)
R["sens_state_fixed_effects_clustered_standardized"] = pack(fit(cc, XS, std=True, cluster=True, fe=True), XS)
R["sens_plus_obesity_hc3"] = pack(fit(cc.dropna(subset=["obes"]), XS + ["obes"]), XS + ["obes"])
R["sens_plus_obesity_standardized"] = pack(fit(cc.dropna(subset=["obes"]), XS + ["obes"], std=True), XS + ["obes"])
cc2 = cc.copy(); XS_log = ["fei", "log_income", "unins", "rural", "inact"]
R["sens_log_income_standardized"] = pack(fit(cc2, XS_log, std=True), XS_log)
m_sup = fit(S, XS, std=True); R["sens_supplement_2023_standardized"] = pack(m_sup, XS)
R["sens_supplement_2023_unstandardized"] = pack(fit(S, XS), XS)
R["sens_supplement_2023_spearman_fei_diab"] = dict(zip(["rho", "p"], [float(v) for v in stats.spearmanr(*S.dropna(subset=MAIN)[["fei", "diab"]].values.T)]))
R["sens_complete_case_states"] = int(S.dropna(subset=MAIN).state.nunique())

# ------------------------------------------------------------------ VIF and diagnostics (primary model)
Xp = cc[XS].values.astype(float); vif = {}
for j, nme in enumerate(XS):
    o = np.delete(Xp, j, 1); A = np.column_stack([np.ones(len(o)), o]); beta = np.linalg.lstsq(A, Xp[:, j], rcond=None)[0]
    r2j = 1 - ((Xp[:, j] - A @ beta) ** 2).sum() / ((Xp[:, j] - Xp[:, j].mean()) ** 2).sum(); vif[nme] = float(1 / (1 - r2j))
R["vif"] = vif; R["vif_max"] = max(vif.values())
res, fit_ = m1["resid"], m1["fitted"]
sdres = res / res.std(ddof=XS.__len__() + 1)
# Breusch-Pagan (studentized / Koenker): n*R2 of e^2 on X
e2 = res ** 2; Xb = m1["X"]; gb = np.linalg.lstsq(Xb, e2, rcond=None)[0]; r2b = 1 - ((e2 - Xb @ gb) ** 2).sum() / ((e2 - e2.mean()) ** 2).sum()
bp = len(e2) * r2b; R["breusch_pagan"] = {"lm": float(bp), "df": len(XS), "p": float(stats.chi2.sf(bp, len(XS)))}
h = np.einsum("ij,jk,ik->i", m1["X"], m1["XtXi"], m1["X"]); s2 = (res @ res) / (len(res) - m1["X"].shape[1]); cook = (res ** 2 / (m1["X"].shape[1] * s2)) * h / (1 - h) ** 2
R["residual_diagnostics"] = {"skew": float(stats.skew(res)), "excess_kurtosis": float(stats.kurtosis(res)), "pct_abs_std_resid_gt3": float((np.abs(sdres) > 3).mean() * 100),
                              "max_cooks_d": float(cook.max()), "n_cooks_d_gt_4_over_n": int((cook > 4 / len(res)).sum()),
                              "spearman_abs_resid_vs_fitted": float(stats.spearmanr(np.abs(res), fit_)[0])}
# does dropping high-influence counties change the FEI coefficient (standardized)?
keep = cook <= 4 / len(res); R["sens_drop_high_cooks_standardized"] = pack(fit(m1["df"][keep], XS, std=True), XS)

# ------------------------------------------------------------------ quintiles of FEI
cc["fei_q"] = pd.qcut(cc.fei, 5, labels=[1, 2, 3, 4, 5], duplicates="drop")
qs = []
for q, g in cc.groupby("fei_q", observed=True):
    n_ = len(g); m_ = g.diab.mean(); se_ = g.diab.std(ddof=1) / np.sqrt(n_); tc = stats.t.ppf(.975, n_ - 1)
    qs.append({"quintile": int(q), "n": int(n_), "fei_min": float(g.fei.min()), "fei_max": float(g.fei.max()), "diab_mean": float(m_), "lo": float(m_ - tc * se_), "hi": float(m_ + tc * se_)})
R["quintiles"] = qs
R["quintile_diff_q1_minus_q5"] = float(qs[0]["diab_mean"] - qs[-1]["diab_mean"])
# adjusted means by quintile (holding other covariates at sample means) via dummy model
dq = pd.get_dummies(cc.fei_q, prefix="q", drop_first=True).astype(float)
Xq = np.column_stack([np.ones(len(cc)), dq.values, cc[["income_k", "unins", "rural", "inact"]].values]); yq = cc.diab.values
mq = ols(yq, Xq, ["i"] + list(dq.columns) + ["income_k", "unins", "rural", "inact"])
R["adjusted_diff_q1_minus_q5_pp"] = {"b": float(-mq["b"][4]), "lo": float(-mq["hi"][4]), "hi": float(-mq["lo"][4]), "p": float(mq["p"][4])}

# ------------------------------------------------------------------ figure (two panels, Okabe-Ito)
BL, OR, VR, GR = "#0072B2", "#D55E00", "#009E73", "#555555"
plt.rcParams.update({"font.size": 11, "font.family": "DejaVu Sans"})
fig, ax = plt.subplots(1, 2, figsize=(13, 5.6), gridspec_kw={"width_ratios": [1.05, 1]})
x = np.arange(1, len(qs) + 1); mu = [q["diab_mean"] for q in qs]; err = [[q["diab_mean"] - q["lo"] for q in qs], [q["hi"] - q["diab_mean"] for q in qs]]
ax[0].bar(x, mu, color=BL, width=.65, yerr=err, capsize=4, ecolor="black", zorder=3)
for xi, q in zip(x, qs): ax[0].text(xi, 0.4, f"n={q['n']}", ha="center", color="white", fontsize=9, zorder=4)
ax[0].set_xticks(x); ax[0].set_xticklabels([f"Q{q['quintile']}\n{q['fei_min']:.1f} to\n{q['fei_max']:.1f}" for q in qs])
ax[0].set_xlabel("Food Environment Index quintile (index range, 0 = worst, 10 = best)")
ax[0].set_ylabel("Mean adult diabetes prevalence (%)"); ax[0].set_ylim(0, max(q["hi"] for q in qs) * 1.15)
ax[0].set_title("A. Unadjusted diabetes prevalence by quintile", loc="left", fontsize=12); ax[0].grid(axis="y", alpha=.25, zorder=0)
mstd = R["model_adjusted_standardized_hc3"]; order = ["fei", "income_k", "unins", "rural", "inact"]
names = {"fei": "Food Environment Index", "income_k": "Median household income", "unins": "Uninsured (%)", "rural": "Rural (%)", "inact": "Physical inactivity (%)"}
yy = np.arange(len(order))[::-1]
for yi, k in zip(yy, order):
    c = OR if k == "fei" else BL; ax[1].errorbar(mstd[k]["b"], yi, xerr=[[mstd[k]["b"] - mstd[k]["lo"]], [mstd[k]["hi"] - mstd[k]["b"]]], fmt="o", color=c, capsize=4, ms=7)
ax[1].axvline(0, color=GR, ls="--", lw=1); ax[1].set_yticks(yy); ax[1].set_yticklabels([names[k] for k in order])
ax[1].set_xlabel("Standardized coefficient\n(SD of diabetes prevalence per SD of predictor)")
ax[1].set_title(f"B. Adjusted associations (n = {mstd['n']:,} counties)", loc="left", fontsize=12); ax[1].grid(axis="x", alpha=.25)
for a_ in ax:
    for sp_ in ("top", "right"): a_.spines[sp_].set_visible(False)
fig.text(.01, .005, "Source: County Health Rankings & Roadmaps, 2025 Annual Data Release (data years 2019-2023). Error bars are 95% confidence intervals; panel B uses heteroskedasticity-robust (HC3) standard errors.",
         fontsize=7.5, color=GR)
fig.tight_layout(rect=(0, .03, 1, 1)); fig.savefig(os.path.join(OUT, "figure1_food_environment_diabetes.png"), dpi=300); plt.close(fig)

# diagnostics figure (supplementary, not in paper)
fg, axd = plt.subplots(1, 2, figsize=(10, 4))
axd[0].scatter(fit_, res, s=4, alpha=.3, color=BL); axd[0].axhline(0, color=OR); axd[0].set_xlabel("Fitted diabetes prevalence (%)"); axd[0].set_ylabel("Residual (percentage points)")
stats.probplot(res, plot=axd[1]); axd[1].get_lines()[0].set_markersize(2); axd[1].set_title("Normal Q-Q of residuals")
fg.tight_layout(); fg.savefig(os.path.join(OUT, "diagnostics_residuals.png"), dpi=150); plt.close(fg)

# ------------------------------------------------------------------ save
json.dump(R, open(os.path.join(OUT, "results.json"), "w"), indent=2)
flat = []
def walk(k, o):
    if isinstance(o, dict):
        for kk, vv in o.items(): walk(f"{k}.{kk}" if k else kk, vv)
    elif isinstance(o, list) and o and isinstance(o[0], dict):
        for i, vv in enumerate(o): walk(f"{k}[{i}]", vv)
    else: flat.append((k, o))
walk("", R); pd.DataFrame(flat, columns=["quantity", "value"]).to_csv(os.path.join(OUT, "results.csv"), index=False)
print(json.dumps({k: R[k] for k in ["n_counties_main_complete_cases", "n_states_in_sample", "spearman_fei_diab", "model_unadjusted_hc3", "model_adjusted_hc3", "model_adjusted_standardized_hc3", "vif", "breusch_pagan", "residual_diagnostics"]}, indent=1))
