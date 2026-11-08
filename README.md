# Food environment and adult diabetes prevalence across U.S. counties

Ecological, cross-sectional analysis of whether a poorer county Food Environment Index is associated with higher adult diabetes prevalence after accounting for income, insurance, rurality and physical inactivity. Manuscript prepared for the Emory University Journal of Public Health (Original Research).

## Data (data_raw/)
- `chr_analytic_data2025_v3.csv`: County Health Rankings & Roadmaps 2025 Annual Data Release, analytic file (main analysis).
- `chr_analytic_supplement_20260325.csv`: March 25, 2026 supplemental release (sensitivity analysis).
Source: https://www.countyhealthrankings.org/health-data/methodology-and-sources/data-documentation

## Reproduce
```
python3 analysis.py          # cleaning, models, figure, results.json / results.csv
python3 build_paper.py       # latex/manuscript.tex + manuscript.pdf (needs pdflatex)
python3 build_verification.py
```
Needs Python 3 with pandas, numpy, scipy, matplotlib. Regression, robust standard errors, VIF and Breusch-Pagan are implemented in NumPy (no statsmodels needed).

## Outputs
- `outputs/cleaned_county_dataset.csv`: 3,100 counties used in the main model
- `outputs/results.json`, `results.csv`: every number reported in the paper
- `outputs/figure1_food_environment_diabetes.png` (300 dpi), `diagnostics_residuals.png`
- `latex/manuscript.tex`, `latex/manuscript.pdf`
- `verification.md`: claim-by-claim check, citation verification, word counts

Findings describe associations between county averages; they do not show cause and effect.
