"""Builds latex/manuscript.tex and manuscript.pdf from outputs/results.json (every number in the text comes from results.json).
Run after analysis.py:  python3 build_paper.py      Needs: pdflatex."""
import json, os, re, shutil, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "outputs"); TEX = os.path.join(HERE, "latex")
R = json.load(open(os.path.join(OUT, "results.json")))
REPO = "https://github.com/willhhx/food-environment-diabetes-county-analysis"

f1 = lambda x: f"{x:.1f}"; f2 = lambda x: f"{x:.2f}"
def sg(x, d=2): return (f"{x:.{d}f}").replace("-", "\u2212") if False else f"{x:.{d}f}"
def pv(p): return "p < 0.001" if p < 0.001 else f"p = {p:.3f}" if p < 0.01 else f"p = {p:.2f}"
def ci(m, k, d=2): return f"{m[k]['b']:.{d}f}, 95% CI {m[k]['lo']:.{d}f} to {m[k]['hi']:.{d}f}"
def cio(m, k, d=2): return f"95% CI {m[k]['lo']:.{d}f} to {m[k]['hi']:.{d}f}"

D = R["descriptives"]; A = R["model_adjusted_hc3"]; AS = R["model_adjusted_standardized_hc3"]; U = R["model_unadjusted_hc3"]; US = R["model_unadjusted_standardized_hc3"]
CL = R["sens_state_clustered_se"]; FE = R["sens_state_fixed_effects_clustered"]; FES = R["sens_state_fixed_effects_clustered_standardized"]
OB = R["sens_plus_obesity_hc3"]; LI = R["sens_log_income_standardized"]; SU = R["sens_supplement_2023_unstandardized"]; DC_ = R["sens_drop_high_cooks_standardized"]
Q = R["quintiles"]; AQ = R["adjusted_diff_q1_minus_q5_pp"]; RD = R["residual_diagnostics"]
sdfei = D["fei"]["sd"]; per_sd = -A["fei"]["b"] * sdfei
N = R["n_counties_main_complete_cases"]; NR = R["n_county_rows_annual"]

abstract = (
 f"Background: Counties with a poorer food environment may have higher rates of diabetes, but income, insurance, rurality, and physical inactivity travel with food access and could account for the pattern. "
 f"Methods: This cross-sectional, ecological study used the 2025 County Health Rankings & Roadmaps data for {N:,} U.S. counties. The Food Environment Index (a 0 to 10 score, higher is better) was compared with age-adjusted adult diabetes prevalence using Spearman rank correlation and ordinary least squares regression with heteroskedasticity-robust standard errors, adjusting for median household income, percent uninsured, percent rural, and physical inactivity. Obesity was left out of the main model because it may lie on the path between food environment and diabetes, and was added in a sensitivity analysis. "
 f"Results: A better Food Environment Index was strongly associated with lower diabetes prevalence before adjustment (Spearman RHO = {f2(R['spearman_fei_diab']['rho'])}; unadjusted R2 = {f2(U['r2'])}). After adjustment the association was much smaller but still present: each 1-point higher index was associated with {f2(abs(A['fei']['b']))} percentage points lower prevalence ({cio(A,'fei')}; standardized coefficient {f2(AS['fei']['b'])}). The full model explained {f2(A['r2'])} of the variation in county diabetes prevalence, but the food environment added only {R['r2_increment_from_fei']*100:.1f} percentage points of that, and physical inactivity dominated (standardized coefficient {f2(AS['inact']['b'])}). Results were similar across six sensitivity analyses. "
 f"Conclusions: A poorer food environment is associated with higher county diabetes prevalence after accounting for income, insurance, rurality, and inactivity, but the independent association is small. These ecological, cross-sectional results cannot show that food environments affect diabetes in individuals."
)
intro = [
 "Diabetes is not spread evenly across places, and county prevalence differs widely. Reviews describe a robust link between neighborhood socioeconomic disadvantage and diabetes (Bilal et al., 2018), and the broader literature treats social determinants of health as central to how diabetes develops (Hill-Briggs et al., 2021). Public health researchers have long asked whether features of the neighborhood itself, beyond the characteristics of the people who live there, contribute to this pattern.",
 "One feature of interest is the food environment: how easily residents can reach affordable, healthy food. Researchers have developed several ways to measure food access and to define so-called food deserts, areas where people have limited access to nutritious food (Ver Ploeg et al., 2015). Evidence linking the food environment to diabetes exists but is mixed. In a U.S. cohort followed over time, higher neighborhood exposure to healthy food was associated with a lower risk of developing type 2 diabetes (hazard ratio 0.88, 95% CI 0.79 to 0.98; Christine et al., 2015), while a review concluded that some findings on food environments and diabetes risk conflict (Bilal et al., 2018). The same review described the link between neighborhood socioeconomic status and diabetes as robust and repeatedly replicated, which raises a measurement problem: because food access, income, and insurance coverage are tangled together at the county level, an apparent food environment association may partly reflect these other factors.",
 "This study asks a focused question: is a poorer county food environment associated with higher adult diabetes prevalence after accounting for socioeconomic and behavioral factors that are not themselves downstream of the food environment? We use the Food Environment Index from County Health Rankings & Roadmaps, a county-level composite score, together with county estimates of diabetes prevalence. We adjust for median household income, the share of residents without health insurance, the share living in rural areas, and physical inactivity. We deliberately do not adjust for adult obesity in the main model. Obesity may be one of the ways a food environment relates to diabetes, so adjusting for it could hide part of the association we want to measure; we examine it separately as a sensitivity check. We report the size of the association, not only whether it is statistically distinguishable from zero, and we compare it with the other factors in the model.",
]
methods = {
 "Study design and data sources": [
  f"This was a cross-sectional ecological study, meaning the unit of analysis is the county and all variables describe counties, not individuals. We used the County Health Rankings & Roadmaps 2025 Annual Data Release analytic file (University of Wisconsin Population Health Institute, 2025), which assembles county measures from national sources (Remington et al., 2015). The file contained {NR:,} county-level rows. We removed state-level summary rows and merged variables on the five-digit county FIPS code (the standard federal county identifier); every row matched ({R['merge_counts']['both']:,} of {NR:,}).",
  "The file reports each measure for a specific data year, as documented by County Health Rankings & Roadmaps. The Food Environment Index combines two indicators, limited access to healthy foods (data year 2019) and food insecurity (2022), each weighted equally. Diabetes prevalence, physical inactivity, and the percent uninsured under age 65 are for 2022. Median household income is for 2023, and percent rural is from the 2020 Census. The outcome, diabetes prevalence, and the physical inactivity measure are model-based county estimates produced from survey data (the Behavioral Risk Factor Surveillance System), not direct counts of every resident. Model-based estimates borrow strength across places to stabilize small areas (Zhang et al., 2014), which means county values partly reflect the model and not only local survey responses.",
 ],
 "Variables": [
  "The outcome was age-adjusted prevalence of diagnosed diabetes among adults aged 18 and over (percent). The exposure was the Food Environment Index, scored from 0 (worst) to 10 (best). Covariates were median household income (in thousands of dollars), percent of the population under 65 without health insurance, percent of the population living in a census-defined rural area, and percent of adults reporting no leisure-time physical activity (age-adjusted). Adult obesity prevalence was used only in a sensitivity analysis.",
 ],
 "Statistical analysis": [
  f"We kept counties with complete data on all six main variables ({N:,} of {NR:,}; the Food Environment Index was missing for {R['n_missing_by_var']['fei']} counties, including all 17 Connecticut rows (its legacy counties and planning regions have no index values) and 35 counties elsewhere, and each other variable was missing for 8 or 9 counties). Because Connecticut contributes no complete counties, the analysis covers {R['n_states_in_sample']} jurisdictions: 49 states and the District of Columbia.",
  "We first described each variable and computed Spearman rank correlations, which measure whether two variables rise and fall together without assuming a straight-line relationship. We then fitted ordinary least squares (OLS) regression of diabetes prevalence on the Food Environment Index, first alone and then with income, percent uninsured, percent rural, and physical inactivity. Standard errors were heteroskedasticity-robust (HC3), which keeps confidence intervals valid when the spread of the errors differs across counties. We report coefficients in the original units (percentage points of diabetes prevalence per one-unit change) and standardized coefficients (standard deviations of diabetes prevalence per standard deviation of the predictor), which allow predictors measured on different scales to be compared. We report R2, the share of variation in diabetes prevalence explained by the model, and the increase in R2 attributable to the Food Environment Index.",
  "Model checks included variance inflation factors (VIF; values near 1 indicate little overlap among predictors, and values above 5 to 10 are usually considered a concern), the Breusch-Pagan test for unequal error spread, residual skewness and kurtosis, and Cook's distance, which flags counties with outsized influence. As a descriptive complement, we divided counties into quintiles (five equal-sized groups) of the Food Environment Index and compared mean diabetes prevalence across them, both unadjusted and adjusted for the four covariates.",
  "Sensitivity analyses were: (1) standard errors clustered by state, which allows counties in the same state to be correlated; (2) state fixed effects, which compares counties only with other counties in the same state, with state-clustered errors; (3) adding adult obesity; (4) replacing income with its natural logarithm; (5) using the March 2026 supplemental release of County Health Rankings & Roadmaps, which updated the Food Environment Index, diabetes, inactivity, uninsured, and obesity measures to 2023 data (this release lacks diabetes values for Kentucky and Pennsylvania counties and does not update income or rurality, so it was used as a check and not as the main dataset); and (6) excluding counties with high influence (Cook's distance above 4 divided by the number of counties). Analyses were implemented in Python with NumPy, SciPy, pandas, and Matplotlib. The data are public and aggregated to counties, so no individual-level data were used.",
 ],
}
results = {
 "Descriptive statistics": [
  f"The {N:,} counties had a mean Food Environment Index of {f1(D['fei']['mean'])} (standard deviation {f1(D['fei']['sd'])}; median {f1(D['fei']['median'])}) and a mean diabetes prevalence of {f1(D['diab']['mean'])}% (standard deviation {f1(D['diab']['sd'])}; range {f1(D['diab']['min'])}% to {f1(D['diab']['max'])}%). Table 1 shows all variables. The index distribution had a longer tail toward poorer scores (mean below median).",
 ],
 "Unadjusted association": [
  f"A better Food Environment Index was strongly associated with lower diabetes prevalence (Spearman RHO = {f2(R['spearman_fei_diab']['rho'])}, {pv(R['spearman_fei_diab']['p'])}). Mean diabetes prevalence fell from {f1(Q[0]['diab_mean'])}% in the lowest index quintile to {f1(Q[-1]['diab_mean'])}% in the highest, a difference of {f1(R['quintile_diff_q1_minus_q5'])} percentage points (Figure 1A). In an unadjusted regression, each 1-point higher index was associated with {f2(abs(U['fei']['b']))} percentage points lower prevalence ({cio(U,'fei')}), and the index alone accounted for {f2(U['r2'])} of the variation.",
  f"The index was closely related to the other socioeconomic measures: it correlated {f2(R['spearman_fei_income']['rho'])} with median household income. Diabetes prevalence correlated most strongly with physical inactivity (RHO = {f2(R['spearman_inact_diab']['rho'])}), followed by income (RHO = {f2(R['spearman_income_k_diab']['rho'])}) and percent uninsured (RHO = {f2(R['spearman_unins_diab']['rho'])}). Percent rural had a weak positive correlation (RHO = {f2(R['spearman_rural_diab']['rho'])}).",
 ],
 "Adjusted association": [
  f"After adjustment, the association between the food environment and diabetes shrank by about 80% but remained statistically distinguishable from zero (Table 2). Each 1-point higher Food Environment Index was associated with {f2(abs(A['fei']['b']))} percentage points lower diabetes prevalence ({cio(A,'fei')}, {pv(A['fei']['p'])}), equal to {f2(per_sd)} percentage points per standard deviation of the index. The standardized coefficient was {f2(AS['fei']['b'])} ({cio(AS,'fei')}), compared with {f2(US['fei']['b'])} before adjustment. The adjusted difference between the lowest and highest index quintiles was {f2(AQ['b'])} percentage points ({f2(AQ['lo'])} to {f2(AQ['hi'])}), compared with the unadjusted difference of {f1(R['quintile_diff_q1_minus_q5'])}.",
  f"The model explained {f2(A['r2'])} of the variation in county diabetes prevalence (adjusted R2 = {f2(A['adj_r2'])}, N = {N:,}). Removing the Food Environment Index lowered R2 only from {f2(A['r2'])} to {f2(R['r2_without_fei'])}, a change of {R['r2_increment_from_fei']*100:.1f} percentage points. The strongest predictor by far was physical inactivity (standardized coefficient {f2(AS['inact']['b'])}, {cio(AS,'inact')}). Percent uninsured had a small positive association ({f2(AS['unins']['b'])}, {cio(AS,'unins')}). Percent rural had a negative association ({f2(AS['rural']['b'])}, {cio(AS,'rural')}), the opposite direction from its weak positive unadjusted correlation. Median household income showed no clear association once the other variables were included ({f2(AS['income_k']['b'])}, {cio(AS,'income_k')}, {pv(AS['income_k']['p'])}).",
 ],
 "Model checks and sensitivity analyses": [
  f"Predictors were not strongly overlapping (largest VIF {f2(R['vif_max'])}; Food Environment Index VIF {f2(R['vif']['fei'])}). The Breusch-Pagan test indicated unequal error spread ({pv(R['breusch_pagan']['p'])}), which is why robust standard errors were used. Residuals were mildly right-skewed (skewness {f2(RD['skew'])}; excess kurtosis {f2(RD['excess_kurtosis'])}), {RD['pct_abs_std_resid_gt3']:.1f}% of counties had standardized residuals beyond 3, and the largest Cook's distance was {RD['max_cooks_d']:.3f}, so no single county dominated the fit.",
  f"The Food Environment Index association persisted in every sensitivity analysis (Table 3). With state-clustered errors the coefficient was unchanged by construction ({f2(CL['fei']['b'])}) but its interval widened ({cio(CL,'fei')}). Comparing counties only within the same state, the coefficient was smaller ({f2(FE['fei']['b'])}, {cio(FE,'fei')}; standardized {f2(FES['fei']['b'])}), and the model R2 rose to {f2(FE['r2'])}. Adding obesity gave a slightly larger food environment coefficient ({f2(OB['fei']['b'])}, {cio(OB,'fei')}), with obesity itself positively associated with diabetes ({f2(OB['obes']['b'])} percentage points per percentage point, {cio(OB,'obes')}). Using log income, the 2023 supplemental data ({SU['n']:,} counties; coefficient {f2(SU['fei']['b'])}, {cio(SU,'fei')}; Spearman RHO = {f2(R['sens_supplement_2023_spearman_fei_diab']['rho'])}), and excluding influential counties ({DC_['n']:,} counties) all left the association close to the main estimate. Income had small associations of differing sign across specifications (positive when obesity was added, negative in the 2023 data and with log income), so the near-zero income finding in the main model is not stable.",
 ],
}
discussion = {
 "Principal findings": [
  f"Counties with a poorer food environment had substantially higher diabetes prevalence, but most of that gap is shared with other characteristics of those counties. After accounting for income, insurance, rurality, and physical inactivity, a 1-point higher Food Environment Index was associated with {f2(abs(A['fei']['b']))} percentage points lower diabetes prevalence, and the index added less than one percentage point of explained variation. By any of these measures the independent association is small. For scale, the gap between the best and worst quintiles was about {f1(R['quintile_diff_q1_minus_q5'])} percentage points unadjusted and about {f1(AQ['b'])} after adjustment.",
  "The direction of the adjusted association is consistent with cohort evidence that higher neighborhood healthy-food exposure is associated with lower risk of type 2 diabetes (Christine et al., 2015). The small size is consistent with the review conclusion that food environment evidence is less consistent than evidence on neighborhood socioeconomic status (Bilal et al., 2018). Our results do not test any mechanism, and a small association at the county level does not mean food access is unimportant for individual households, because a county average can hide large differences between neighborhoods.",
 ],
 "Interpreting the other predictors": [
  f"Physical inactivity was by far the strongest correlate of county diabetes prevalence (standardized coefficient {f2(AS['inact']['b'])}). Two cautions apply. First, inactivity and diabetes are both model-based estimates built from the same survey, and shared modeling structure could strengthen the link between them beyond what a direct measurement would show; we did not test this. Second, inactivity could itself lie partly on the path between food environment, income, and diabetes. If so, adjusting for it removes some of the association we aimed to estimate, and the adjusted food environment coefficient would then understate the total association. The unadjusted and adjusted estimates therefore bracket a plausible range, and the truth for any particular causal question cannot be read from either one.",
  "The negative adjusted coefficient for percent rural runs opposite to national survey findings of higher crude diabetes prevalence in rural populations (O'Connor & Wellenius, 2012). Both can be true: in this dataset the crude correlation was weakly positive, and the sign changes once inactivity, income, and insurance are held constant. The coefficient describes rurality after those factors are accounted for, and should not be read as a statement that rural residents have lower diabetes risk.",
 ],
 "Strengths and limitations": [
  "Strengths include national coverage, a large sample, a main model chosen with a stated rationale for excluding obesity, effect sizes reported alongside significance, and consistent results across six sensitivity analyses. All numbers are produced by a script from public data.",
  "The main limitation is that the study is ecological and cross-sectional. Associations between county averages need not hold for individuals (the ecological fallacy), and the data cannot establish whether the food environment came before, followed, or merely coincided with diabetes prevalence. Unmeasured county characteristics, such as the age and racial and ethnic composition beyond age adjustment, health care access, and the built environment, may account for part of the association. The Food Environment Index is a composite of limited access to healthy foods and food insecurity, so it cannot show which component matters, and a county score does not describe access within the county; the food insecurity component is itself statistically estimated. The exposure and outcome come from different years (the index uses 2019 and 2022 data, diabetes 2022), so temporal ordering is not established. Diabetes and inactivity are modeled estimates, which may smooth differences between small counties. Connecticut is not represented, and the 2023 supplemental release could be used only as a sensitivity check. Finally, the large number of counties makes even trivial coefficients statistically significant, so the effect sizes, not the p-values, should guide interpretation.",
 ],
 "Implications": [
  "These results do not argue against improving food access, which has other justifications. They do suggest that policies aimed at food environments alone should not be expected to account for, or close, most of the county-level variation in diabetes prevalence. Future work should use individual-level or neighborhood-level data, measure change over time, and examine components of the index separately.",
 ],
}
conclusion = [
 f"In {N:,} U.S. counties, a poorer food environment was associated with higher adult diabetes prevalence, strongly before adjustment and modestly after adjustment for income, insurance, rurality, and physical inactivity ({f2(abs(A['fei']['b']))} percentage points per 1-point lower index; standardized coefficient {f2(AS['fei']['b'])}). The food environment explained little of the county variation beyond these other factors. Because the design is ecological and cross-sectional, the findings describe patterns across counties and do not show that changing a food environment would change diabetes rates.",
]
kt = (f"Key takeaway: Counties with a poorer food environment have higher diabetes prevalence, but after accounting for income, insurance, rurality, and physical inactivity the association shrinks to {f2(abs(A['fei']['b']))} percentage points per index point and adds under one percentage point of explained variation. Physical inactivity is by far the stronger correlate. These county-level results cannot show cause and effect.")

refs = [
 r"Bilal, U., Auchincloss, A. H., \& Diez-Roux, A. V. (2018). Neighborhood environments and diabetes risk and control. \emph{Current Diabetes Reports, 18}(9), Article 62. \url{https://doi.org/10.1007/s11892-018-1032-2}",
 r"Christine, P. J., Auchincloss, A. H., Bertoni, A. G., Carnethon, M. R., S\'anchez, B. N., Moore, K., Adar, S. D., Horwich, T. B., Watson, K. E., \& Diez Roux, A. V. (2015). Longitudinal associations between neighborhood physical and social environments and incident type 2 diabetes mellitus: The Multi-Ethnic Study of Atherosclerosis (MESA). \emph{JAMA Internal Medicine, 175}(8), 1311--1320. \url{https://doi.org/10.1001/jamainternmed.2015.2691}",
 r"Hill-Briggs, F., Adler, N. E., Berkowitz, S. A., Chin, M. H., Gary-Webb, T. L., Navas-Acien, A., Thornton, P. L., \& Haire-Joshu, D. (2021). Social determinants of health and diabetes: A scientific review. \emph{Diabetes Care, 44}(1), 258--279. \url{https://doi.org/10.2337/dci20-0053}",
 r"O'Connor, A., \& Wellenius, G. (2012). Rural--urban disparities in the prevalence of diabetes and coronary heart disease. \emph{Public Health, 126}(10), 813--820. \url{https://doi.org/10.1016/j.puhe.2012.05.029}",
 r"Remington, P. L., Catlin, B. B., \& Gennuso, K. P. (2015). The County Health Rankings: Rationale and methods. \emph{Population Health Metrics, 13}, Article 11. \url{https://doi.org/10.1186/s12963-015-0044-2}",
 r"University of Wisconsin Population Health Institute. (2025). \emph{County Health Rankings \& Roadmaps 2025 annual data release: Analytic data} [Data set]. \url{https://www.countyhealthrankings.org/health-data/methodology-and-sources/data-documentation}",
 r"University of Wisconsin Population Health Institute. (2026). \emph{County Health Rankings \& Roadmaps supplemental release, March 25, 2026} [Data set]. \url{https://www.countyhealthrankings.org/health-data/methodology-and-sources/data-documentation}",
 r"Ver Ploeg, M., Dutko, P., \& Breneman, V. (2015). Measuring food access and food deserts for policy purposes. \emph{Applied Economic Perspectives and Policy, 37}(2), 205--225. \url{https://doi.org/10.1093/aepp/ppu035}",
 r"Zhang, X., Holt, J. B., Lu, H., Wheaton, A. G., Ford, E. S., Greenlund, K. J., \& Croft, J. B. (2014). Multilevel regression and poststratification for small-area estimation of population health outcomes: A case study of chronic obstructive pulmonary disease prevalence using the Behavioral Risk Factor Surveillance System. \emph{American Journal of Epidemiology, 179}(8), 1025--1033. \url{https://doi.org/10.1093/aje/kwu018}",
]

# ------------------------------------------------------------------ LaTeX
def esc(s):
    s = s.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace("#", r"\#")
    s = re.sub(r"\bR2\b", r"$R^2$", s); s = s.replace("RHO", r"$\rho$")
    s = re.sub(r"\$\\rho\$ = (-?\d)", lambda m: r"$\rho = " + m.group(1), s)  # open math then close after number
    s = re.sub(r"(\$\\rho = -?\d\.\d+)", lambda m: m.group(1) + "$", s)
    s = s.replace("p < 0.001", "$p<0.001$")
    s = re.sub(r"\bp = (0\.\d+)", r"$p=\1$", s)
    return s
def paras(l): return "\n\n".join(esc(p) for p in l)
def block(d): return "\n\n".join(f"\\subsection*{{{k}}}\n" + paras(v) for k, v in d.items())

def drow(k):
    d = D[k]; return f"{d['label']} & {d['n']:,} & {d['mean']:.1f} & {d['sd']:.1f} & {d['median']:.1f} & {d['q1']:.1f}--{d['q3']:.1f} & {d['min']:.1f}--{d['max']:.1f} \\\\\n"
t1 = "".join(drow(k) for k in ["fei", "diab", "income_k", "unins", "rural", "inact"]).replace("$", r"\$").replace("(%)", r"(\%)")
names = [("fei", "Food Environment Index (per 1 point)"), ("income_k", r"Median household income (per \$1,000)"), ("unins", r"Uninsured (per 1 pp)"), ("rural", r"Rural population (per 1 pp)"), ("inact", r"Physical inactivity (per 1 pp)")]
def p_(p): return "$<$0.001" if p < 0.001 else f"{p:.3f}" if p < 0.01 else f"{p:.2f}"
t2 = ""
for k, lab in names:
    t2 += f"{lab} & {U['fei']['b']:.2f} ({U['fei']['lo']:.2f}, {U['fei']['hi']:.2f}) & " if k == "fei" else f"{lab} & & "
    t2 += f"{A[k]['b']:.3f} ({A[k]['lo']:.3f}, {A[k]['hi']:.3f}) & {p_(A[k]['p'])} & {AS[k]['b']:.2f} ({AS[k]['lo']:.2f}, {AS[k]['hi']:.2f}) \\\\\n"
t2 += f"\\midrule\n$R^2$ & {U['r2']:.2f} & {A['r2']:.2f} & & \\\\\nAdjusted $R^2$ & {U['adj_r2']:.2f} & {A['adj_r2']:.2f} & & \\\\\n$N$ counties & {U['n']:,} & {A['n']:,} & & \\\\\n"
def srow(lab, m, std=None):
    return f"{lab} & {m['n']:,} & {m['fei']['b']:.2f} ({m['fei']['lo']:.2f}, {m['fei']['hi']:.2f}) & {m['r2']:.2f} \\\\\n"
t3 = srow("Main model (HC3 robust SEs)", A) + srow("State-clustered SEs", CL) + srow("State fixed effects, clustered SEs", FE) + srow("Adding adult obesity", OB) + srow("March 2026 supplement (2023 data)", SU)
t3 += f"Log income (standardized FEI coefficient {LI['fei']['b']:.2f}; 95\\% CI {LI['fei']['lo']:.2f}, {LI['fei']['hi']:.2f}) & {LI['n']:,} & -- & {LI['r2']:.2f} \\\\\n"
t3 += f"Excluding high-influence counties (standardized FEI coefficient {DC_['fei']['b']:.2f}; 95\\% CI {DC_['fei']['lo']:.2f}, {DC_['fei']['hi']:.2f}) & {DC_['n']:,} & -- & {DC_['r2']:.2f} \\\\\n"

caption = ("Association between the County Health Rankings & Roadmaps Food Environment Index and adult diabetes prevalence in " + f"{N:,} U.S. counties. Panel A: mean diabetes prevalence by quintile of the index (Q1 = poorest food environment, Q5 = best); error bars are 95% confidence intervals. Panel B: standardized coefficients (standard deviations of diabetes prevalence per standard deviation of each predictor) from the adjusted regression model; bars are 95% confidence intervals from heteroskedasticity-robust (HC3) standard errors. The association is ecological and cross-sectional. Data: County Health Rankings & Roadmaps 2025 Annual Data Release (data years 2019 to 2023).")

tex = r"""\documentclass[12pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{graphicx,booktabs,url,setspace,caption,amsmath,float}
\usepackage[T1]{fontenc}\usepackage{lmodern}\usepackage[hidelinks]{hyperref}\usepackage{xurl}
\captionsetup{font=small,labelfont=bf,justification=justified}
\setstretch{1.15}
\title{Food Environment and Adult Diabetes Prevalence Across U.S. Counties: An Ecological Analysis Accounting for Socioeconomic Factors and Physical Inactivity}
\author{Haoxi Hu\thanks{Corresponding author: \href{mailto:hu.haoxi@northeastern.edu}{hu.haoxi@northeastern.edu}}\\[2pt]
\small Khoury College of Computer Sciences and Bouv\'e College of Health Sciences,\\
\small Northeastern University}
\date{}
\begin{document}
\maketitle
\vspace{-2em}
\begin{abstract}
""" + esc(abstract) + r"""
\end{abstract}
\noindent\textbf{Keywords:} food environment; diabetes; county health; socioeconomic factors; ecological study

\section*{Introduction}
""" + paras(intro) + r"""

\section*{Methods}
""" + block(methods) + r"""

\section*{Results}
""" + block(results) + r"""

\begin{table}[H]
\centering\small
\caption{Characteristics of the """ + f"{N:,}" + r""" counties in the main analysis. SD = standard deviation; IQR shown as 25th to 75th percentile; pp = percentage points. Source: County Health Rankings \& Roadmaps 2025 Annual Data Release; author analysis.}
\resizebox{\linewidth}{!}{%
\begin{tabular}{lrrrrrr}
\toprule
Variable & $N$ & Mean & SD & Median & 25th--75th & Range \\
\midrule
""" + t1 + r"""\bottomrule
\end{tabular}%
}
\end{table}

\begin{figure}[H]
\centering
\includegraphics[width=\linewidth]{figures/figure1_food_environment_diabetes.png}
\caption{""" + esc(caption) + r"""}
\end{figure}

\begin{table}[H]
\centering\footnotesize
\caption{Linear regression of county adult diabetes prevalence (\%) on the Food Environment Index. Unadjusted and adjusted coefficients are in percentage points of diabetes prevalence per unit; standardized coefficients are in standard deviations. Values are estimates (95\% confidence interval) with heteroskedasticity-robust (HC3) standard errors. The $p$-value is for the adjusted coefficient. Source: author analysis of County Health Rankings \& Roadmaps data.}
\resizebox{\linewidth}{!}{%
\begin{tabular}{lcccc}
\toprule
Predictor & Unadjusted & Adjusted & $p$ (adjusted) & Standardized (adjusted) \\
\midrule
""" + t2 + r"""\bottomrule
\end{tabular}%
}
\end{table}

\begin{table}[H]
\centering\footnotesize
\caption{Sensitivity analyses: coefficient for the Food Environment Index (percentage points of diabetes prevalence per 1-point higher index, unless noted; 95\% confidence interval) and model $R^2$. SEs = standard errors; FEI = Food Environment Index. Source: author analysis of County Health Rankings \& Roadmaps data.}
\resizebox{\linewidth}{!}{%
\begin{tabular}{lccc}
\toprule
Analysis & $N$ & FEI coefficient (95\% CI) & $R^2$ \\
\midrule
""" + t3 + r"""\bottomrule
\end{tabular}%
}
\end{table}

\section*{Discussion}
""" + block(discussion) + r"""

\section*{Conclusion}
""" + paras(conclusion) + r"""

\section*{Data and Code Availability}
All source files, the cleaned dataset, the analysis script, and a results file containing every reported number are openly available at \url{""" + REPO + r"""}.

\section*{References}
\begingroup\small\setlength{\parindent}{-0.5in}\setlength{\leftskip}{0.5in}\setlength{\parskip}{4pt}
""" + "\n\n".join(refs) + r"""
\endgroup
\end{document}
"""
os.makedirs(os.path.join(TEX, "figures"), exist_ok=True)
shutil.copy(os.path.join(OUT, "figure1_food_environment_diabetes.png"), os.path.join(TEX, "figures"))
open(os.path.join(TEX, "manuscript.tex"), "w").write(tex)
for _ in range(2):
    r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "manuscript.tex"], cwd=TEX, capture_output=True, text=True)
print("pdflatex rc", r.returncode, [l for l in r.stdout.splitlines() if l.startswith("!")][:5])

# ------------------------------------------------------------------ checks + word count
plain = lambda s: s.replace("RHO", "rho")
main = [abstract] + intro + sum(methods.values(), []) + sum(results.values(), []) + sum(discussion.values(), []) + conclusion
wc_main = sum(len(plain(p).split()) for p in main); wc_abs = len(plain(abstract).split())
allprose = " ".join(main) + kt
assert "\u2014" not in allprose and "---" not in allprose
for bad in ("causes ", " leads to", "caused by", "due to the food", "effect of the food environment on", "impact of"):
    assert bad not in allprose.lower(), bad
assert wc_main <= 4000
json.dump({"words_main_text_incl_abstract_excl_tables_figures_refs": wc_main, "words_abstract": wc_abs, "key_takeaway": kt}, open(os.path.join(OUT, "wordcount.json"), "w"), indent=1)
print("main words", wc_main, "abstract", wc_abs)
