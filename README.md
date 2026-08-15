# CFA Knowledge Base & Quantitative Skill Engine 📈

An institutional-grade **Financial Knowledge Base and Quantitative Skill Engine** grounded in the official **CFA (Chartered Financial Analyst) Level I, II, and III** curriculum standards, practitioner monographs, and peer-reviewed academic research from **arXiv Quantitative Finance (`q-fin`) & Economics (`econ`)**.

---

## 🌟 Key Highlights

- **3,840+ Deduplicated Knowledge Items**: Ingested and indexed across 45 full-length PDF textbooks, review guides, formula sheets, and 2024 Level III official mock exams with complete answer keys.
- **SQLite FTS5 + BM25 Analytical Search Engine**: Zero-latency local full-text search with automated formula detection and query snippet extraction.
- **Autonomous Agent Skills**: Built-in specialized execution skills for **Private Wealth Management (IPS & Human Capital)**, **Institutional Portfolio Planning (Black-Litterman & Corridors)**, and **Curriculum Retrieval**.
- **Self-Contained & Lightweight**: The entire compiled and vacuumed search database is stored in a clean, portable 11MB SQLite file (`data/cfa_knowledge_base.sqlite`).

---

## 🏗️ Repository Architecture

```
cfa_knowledge_base/
├── data/
│   └── cfa_knowledge_base.sqlite     # 11MB Indexed SQLite FTS5 database (3,842 items)
├── scripts/
│   ├── query_cfa_kb.py               # Fast CLI search utility with BM25 ranking
│   ├── ingest_all_cfa.py             # Markdown and textbook parsing engine
│   ├── ingest_all_pdfs.py            # Deep PyMuPDF parser for textbooks & exams
│   ├── ingest_arxiv_and_finance_kb.py# Automated arXiv academic paper feed
│   └── prune_and_deduplicate.py      # Database pruner, cleaner, and optimizer
├── skills/
│   ├── cfa-kb-search/                # Knowledge base retrieval skill
│   ├── cfa-wealth-advisor/           # Level III Private Wealth & IPS advisor
│   │   └── scripts/human_capital_calc.py
│   └── cfa-portfolio-engine/         # Level III Asset Allocation & Rebalancing
│       └── scripts/rebalance_corridor.py
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🚀 Quickstart

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/cfa_knowledge_base.git
cd cfa_knowledge_base

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Searching the Knowledge Base

Run the search CLI on any topic, formula, reading, or case study:

```bash
# Search for Level III IPS & Human Capital formulas:
python3 scripts/query_cfa_kb.py "human capital asset allocation IPS"

# Search for Black-Litterman and portfolio optimization models:
python3 scripts/query_cfa_kb.py "Black-Litterman portfolio optimization factor model"

# Search for Forensic Accounting & Earnings Quality:
python3 scripts/query_cfa_kb.py "Beneish M-Score Sloan Accruals earnings quality"
```

---

## 🛠️ Computational Tools & Skills

### 1. Human Capital & Economic Balance Sheet (`cfa-wealth-advisor`)
Calculates the present value of mortality-weighted future wages:
$$HC_0 = \sum_{t=1}^{N} \frac{p(s_t) \cdot w_{t-1} \cdot (1 + g_t)}{(1 + r_f + y)^t}$$
```bash
python3 skills/cfa-wealth-advisor/scripts/human_capital_calc.py
```

### 2. Dynamic Rebalancing Corridors (`cfa-portfolio-engine`)
Computes optimal corridor widths $[w_i - \Delta w, w_i + \Delta w]$ balancing asset volatility against transaction costs, taxes, and correlation:
```bash
python3 skills/cfa-portfolio-engine/scripts/rebalance_corridor.py
```

---

## 📄 License & Disclaimer

This project is intended for financial research, quantitative modeling, and educational purposes. All academic papers belong to their respective authors on arXiv.org. Official CFA Institute curriculum standards and trademarks belong to CFA Institute.
