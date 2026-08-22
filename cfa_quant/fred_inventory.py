"""
Institutional FRED & Macroeconomic Data Catalog
Comprehensive inventory of the 30+ primary macroeconomic, monetary, yield curve,
inflation, labor, and credit risk series utilized in institutional finance.
"""

from typing import Dict, List, Any

FRED_MACRO_INVENTORY: Dict[str, Dict[str, Any]] = {
    # ==================== 1. US TREASURY TERM STRUCTURE & SPREADS ====================
    "DGS1MO": {
        "title": "1-Month Treasury Constant Maturity Rate",
        "category": "Yield Curve",
        "frequency": "Daily",
        "units": "Percent",
        "usage": "Ultra-short cash equivalent benchmark."
    },
    "DGS3MO": {
        "title": "3-Month Treasury Constant Maturity Rate",
        "category": "Yield Curve",
        "frequency": "Daily",
        "units": "Percent",
        "usage": "Primary risk-free rate proxy for derivatives and money market pricing."
    },
    "DGS2": {
        "title": "2-Year Treasury Constant Maturity Rate",
        "category": "Yield Curve",
        "frequency": "Daily",
        "units": "Percent",
        "usage": "Key policy-sensitive tenor reflecting near-term Fed rate expectations."
    },
    "DGS5": {
        "title": "5-Year Treasury Constant Maturity Rate",
        "category": "Yield Curve",
        "frequency": "Daily",
        "units": "Percent",
        "usage": "Medium-term corporate bond benchmark."
    },
    "DGS10": {
        "title": "10-Year Treasury Constant Maturity Rate",
        "category": "Yield Curve",
        "frequency": "Daily",
        "units": "Percent",
        "usage": "Standard institutional Risk-Free Rate (Rf) for DCF, CAPM, and WACC calculations."
    },
    "DGS30": {
        "title": "30-Year Treasury Constant Maturity Rate",
        "category": "Yield Curve",
        "frequency": "Daily",
        "units": "Percent",
        "usage": "Long-term liability matching for pension funds and life insurers."
    },
    "T10Y2Y": {
        "title": "10-Year Minus 2-Year Treasury Yield Spread",
        "category": "Yield Curve Inversion",
        "frequency": "Daily",
        "units": "Percent / bps",
        "usage": "Primary leading recession indicator. Inversion (< 0 bps) historically precedes US recessions by 6-18 months."
    },
    "T10Y3M": {
        "title": "10-Year Minus 3-Month Treasury Yield Spread",
        "category": "Yield Curve Inversion",
        "frequency": "Daily",
        "units": "Percent / bps",
        "usage": "New York Fed's preferred yield curve recession probability model."
    },

    # ==================== 2. MONETARY POLICY & BENCHMARK REFERENCE RATES ====================
    "SOFR": {
        "title": "Secured Overnight Financing Rate (SOFR)",
        "category": "Monetary Policy",
        "frequency": "Daily",
        "units": "Percent",
        "usage": "Official global post-LIBOR reference rate for variable debt, interest rate swaps, and institutional loans."
    },
    "EFFR": {
        "title": "Effective Federal Funds Rate",
        "category": "Monetary Policy",
        "frequency": "Daily",
        "units": "Percent",
        "usage": "Volume-weighted median rate of overnight federal funds transactions."
    },
    "DFEDTARU": {
        "title": "Federal Funds Target Range - Upper Limit",
        "category": "Monetary Policy",
        "frequency": "Daily",
        "units": "Percent",
        "usage": "Federal Open Market Committee (FOMC) target ceiling."
    },
    "DFEDTARL": {
        "title": "Federal Funds Target Range - Lower Limit",
        "category": "Monetary Policy",
        "frequency": "Daily",
        "units": "Percent",
        "usage": "Federal Open Market Committee (FOMC) target floor."
    },
    "WALCL": {
        "title": "Federal Reserve Total Assets (Balance Sheet)",
        "category": "Monetary Policy / Liquidity",
        "frequency": "Weekly",
        "units": "Millions of Dollars",
        "usage": "Tracks Quantitative Easing (QE) expansion vs. Quantitative Tightening (QT) contraction."
    },

    # ==================== 3. INFLATION & MARKET EXPECTATIONS ====================
    "CPIAUCSL": {
        "title": "Consumer Price Index for All Urban Consumers: All Items (Headline CPI)",
        "category": "Inflation",
        "frequency": "Monthly",
        "units": "Index",
        "usage": "Standard headline inflation metric for real return deflators."
    },
    "CPILFESL": {
        "title": "Core CPI (Excluding Food & Energy)",
        "category": "Inflation",
        "frequency": "Monthly",
        "units": "Index",
        "usage": "Core underlying structural inflation trend."
    },
    "PCEPI": {
        "title": "Personal Consumption Expenditures Price Index (PCE)",
        "category": "Inflation",
        "frequency": "Monthly",
        "units": "Index",
        "usage": "The Federal Reserve's primary statutory inflation target (2.0% annual goal)."
    },
    "PCEPILFE": {
        "title": "Core PCE Price Index",
        "category": "Inflation",
        "frequency": "Monthly",
        "units": "Index",
        "usage": "Key metric guiding FOMC interest rate adjustments."
    },
    "T5YIE": {
        "title": "5-Year Breakeven Inflation Rate",
        "category": "Inflation Expectations",
        "frequency": "Daily",
        "units": "Percent",
        "usage": "TIPS implied 5-year forward inflation expectation."
    },
    "T10YIE": {
        "title": "10-Year Breakeven Inflation Rate",
        "category": "Inflation Expectations",
        "frequency": "Daily",
        "units": "Percent",
        "usage": "TIPS implied 10-year forward inflation expectation used in long-term IPS models."
    },

    # ==================== 4. CREDIT RISK & SPREADS ====================
    "BAMLC0A0CM": {
        "title": "ICE BofA US Corporate Index Option-Adjusted Spread (OAS)",
        "category": "Credit Spreads",
        "frequency": "Daily",
        "units": "Percent / bps",
        "usage": "Investment-grade corporate credit risk premium over Treasuries."
    },
    "BAMLH0A0HYM2": {
        "title": "ICE BofA US High Yield Index Option-Adjusted Spread (OAS)",
        "category": "Credit Spreads",
        "frequency": "Daily",
        "units": "Percent / bps",
        "usage": "Junk bond credit default risk barometer; spikes during financial stress."
    },
    "NFCI": {
        "title": "Chicago Fed National Financial Conditions Index",
        "category": "Financial Conditions",
        "frequency": "Weekly",
        "units": "Index",
        "usage": "Comprehensive 105-indicator gauge of US money, debt, and equity market liquidity (Negative = Loose; Positive = Tight)."
    },

    # ==================== 5. REAL ECONOMIC ACTIVITY & LABOR ====================
    "GDPC1": {
        "title": "Real Gross Domestic Product",
        "category": "Economic Output",
        "frequency": "Quarterly",
        "units": "Billions of Chained 2017 Dollars",
        "usage": "US economic growth benchmark."
    },
    "UNRATE": {
        "title": "Civilian Unemployment Rate",
        "category": "Labor Market",
        "frequency": "Monthly",
        "units": "Percent",
        "usage": "Sahm Rule recession trigger (0.50% rise from 12-month low)."
    },
    "PAYEMS": {
        "title": "Total Nonfarm Payroll Employment",
        "category": "Labor Market",
        "frequency": "Monthly",
        "units": "Thousands of Persons",
        "usage": "Primary monthly US job creation indicator."
    },
    "UMCSENT": {
        "title": "University of Michigan Consumer Sentiment",
        "category": "Consumer Sentiment",
        "frequency": "Monthly",
        "units": "Index",
        "usage": "Leading indicator of personal consumption expenditures."
    },

    # ==================== 6. VOLATILITY & RISK BAROMETERS ====================
    "VIXCLS": {
        "title": "CBOE Volatility Index (VIX)",
        "category": "Market Volatility",
        "frequency": "Daily",
        "units": "Index",
        "usage": "S&P 500 30-day implied volatility / market fear gauge."
    }
}

def get_fred_inventory_summary() -> List[Dict[str, str]]:
    return [
        {"series_id": sid, "title": meta["title"], "category": meta["category"], "frequency": meta["frequency"]}
        for sid, meta in FRED_MACRO_INVENTORY.items()
    ]

if __name__ == "__main__":
    print(f"🏛️ CFA Institutional FRED Macro Inventory: {len(FRED_MACRO_INVENTORY)} Verified Core Series")
    for sid, meta in list(FRED_MACRO_INVENTORY.items())[:8]:
        print(f"  • {sid:12} | {meta['category']:22} | {meta['title']}")
