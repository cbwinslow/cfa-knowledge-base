# 🏛️ CFA Institute Quantitative Suite & Knowledge Base

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![CFA Level I, II, III](https://img.shields.io/badge/standards-CFA%20Institute-gold.svg)](https://www.cfainstitute.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An institutional-grade quantitative finance, equity valuation, macroeconomic regime modeling, and private wealth management suite grounded strictly in the official **CFA Institute Level I, II, and III Curriculum**.

---

## 🌟 Core System Architecture

```text
cfa_knowledge_base/
├── cfa_quant/                            # Core Quantitative Domain Package (cfa-quant-suite)
│   ├── models.py                         # Typed dataclass data contracts & schemas
│   ├── capital_market_expectations.py    # Grinold-Kroner & Singer-Terhaar CME models
│   ├── portfolio_execution_feedback.py   # Black-Litterman optimizer & Brinson-Fachler attribution
│   ├── ips_generator.py                  # CFA Level III Institutional IPS Generator
│   ├── tax_legal_engine.py               # Tax-Alpha Asset Placement & State Arbitrage
│   ├── opportunity_cost.py               # ROIC-WACC EVA Spread & Next-Best Alternative Screener
│   ├── stochastic_sim.py                 # Markov Regime-Switching & Merton Jump Diffusion 10k Monte Carlo
│   ├── options_engine.py                 # Vectorized Black-Scholes Greeks (Delta, Gamma, Vega, Vanna, Volga)
│   ├── charting.py                       # Interactive Candlestick & Volume surface with Box Zoom
│   ├── fred_inventory.py                 # Master catalog of 30+ core macroeconomic series
│   └── duckdb_macro_store.py             # Columnar time-series warehouse (FRED direct ingestion)
│
├── pipeline/                             # Fundamental Equity Research Pipeline
│   ├── sec_edgar_client.py               # Point-in-time SEC 10-K & 10-Q XBRL duration-validated parser
│   ├── cfa_valuation_engine.py           # 3-Stage DCF (FCFF), Dynamic WACC & Residual Income Model
│   ├── forensic_accounting.py            # Piotroski F-Score (0-9), Beneish M-Score & Sloan Accruals
│   ├── industry_benchmarks.py            # DuPont 5-Way decomposition & Competitor Peer Medians
│   ├── capm_sml_model.py                 # Security Market Line (SML) & Jensen's Alpha
│   ├── run_valuation.py                  # Single-stock valuation research memo CLI
│   └── screener.py                       # Multi-stock fundamental screener & Margin of Safety ranker
│
├── .agents/skills/                       # Autonomous CFA Agent Skills Suite
│   ├── cfa-wealth-advisor/               # CFA Level III Private Wealth & IPS compiler
│   ├── cfa-portfolio-engine/             # SAA/TAA, Black-Litterman & Rebalancing Corridors
│   ├── cfa-kb-search/                    # FTS5 full-text curriculum search tool
│   └── skill-creator/                    # Antigravity skill structure validator
│
├── data/
│   ├── cfa_knowledge_base.sqlite         # 3,871 indexed curriculum notes, mock exams & research papers
│   ├── financial_formulas.json           # 30+ fundamental CFA formulas with LaTeX definitions
│   ├── gaap_ifrs_standards.json          # US GAAP vs. IFRS analytical reconciliation dictionary
│   └── jurisdiction_tax_rules.json       # 50-State & Global Wealth Tax Policy dictionary
│
└── app.py                                # Multi-Tab Interactive Streamlit Dashboard
```

---

## 🚀 Quick Start

### 1. Installation & Environment Setup

```bash
# Clone the repository
git clone https://github.com/cbwinslow/cfa-knowledge-base.git
cd cfa-knowledge-base

# Create & activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install package in editable development mode
pip install -e .
pip install -r requirements.txt
```

---

### 2. Launch the Interactive Web Dashboard

```bash
streamlit run app.py
```

The interactive dashboard provides **8 comprehensive financial workspaces**:
1. **🏛️ Valuation & SML**: DCF intrinsic value, Dynamic WACC, Residual Income (EVA), and Security Market Line.
2. **📈 Price Action & Zoom**: High-definition candlestick chart with interactive range buttons, slider, and click-and-drag box zoom.
3. **🎯 Opportunity Cost & EVA**: Live FCF yield vs. 10-Yr Treasury spread, hurdle rate audit, and next-best competitor warning.
4. **👥 Peer Comps & DuPont 5-Way**: DuPont decomposition (Tax/Interest Burden, Margin, Asset Turnover, Leverage) vs. industry medians.
5. **📝 IPS Generator (L3)**: Client intake form compiling institutional Investment Policy Statements.
6. **⚖️ Tax & Legal Wealth Alpha**: Asset location optimizer (Taxable vs. Traditional 401k vs. Roth) & State Tax Relocation Arbitrage.
7. **🌐 Macro & Yield Curve**: Live US Treasury curve, SOFR benchmark, breakeven inflation, and recession spread signals.
8. **📚 CFA Knowledge Base**: Instant full-text search across 3,871 indexed curriculum pages and mock exams.

---

### 3. Command-Line Tools

#### Run Institutional Equity Valuation Memo
```bash
python3 pipeline/run_valuation.py MSFT
```

#### Run Batch Margin-of-Safety Screener
```bash
python3 pipeline/screener.py AAPL MSFT GOOGL NVDA AMZN
```

#### Search the CFA Curriculum Database
```bash
python3 scripts/query_cfa_kb.py "Black-Litterman asset allocation"
```

#### Compile an Investment Policy Statement from Client JSON
```bash
python3 .agents/skills/cfa-wealth-advisor/scripts/compile_ips.py .agents/skills/cfa-wealth-advisor/examples/client_case_entrepreneur.json
```

---

## 🔬 Mathematical & Theoretical Foundations

### 1. Grinold-Kroner Model (Capital Market Expectations)
$$E(R_e) = \frac{D}{P} - \Delta S + i + g + \Delta(P/E)$$

### 2. Singer-Terhaar Model (Global Asset Integration)
$$E(R_i) = R_f + \phi \left(\rho_{i,G} \sigma_i \text{Sharpe}_G\right) + (1 - \phi) \left(\sigma_i \text{Sharpe}_G\right) + \text{Illiquidity Premium}$$

### 3. Black-Litterman Reverse Optimization
$$\Pi = \lambda \Sigma w_{mkt}$$
$$E(R) = \left[ (\tau \Sigma)^{-1} + P^T \Omega^{-1} P \right]^{-1} \left[ (\tau \Sigma)^{-1} \Pi + P^T \Omega^{-1} Q \right]$$

### 4. Brinson-Fachler Active Performance Attribution
$$A_i = (w_i - W_i)(B_i - B), \quad S_i = W_i(R_i - B_i), \quad I_i = (w_i - W_i)(R_i - B_i)$$

---

## 📜 Fiduciary & Curriculum Compliance

All models and skills are grounded in:
* **CFA Institute Code of Ethics and Standards of Professional Conduct**
* **CFA Level I, II, and III Curriculum (2024–2026 Editions)**
* **GIPS (Global Investment Performance Standards)**

---

## 👤 Author
* **C.B. Winslow** (Passed all three CFA exams in 2014, Active CFA Institute Member)
