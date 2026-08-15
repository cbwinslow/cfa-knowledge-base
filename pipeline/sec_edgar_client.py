#!/usr/bin/env python3
"""
SEC EDGAR Financial Statement Ingestion Client
Fetches point-in-time XBRL 10-K and 10-Q financial statement facts directly from the official SEC EDGAR API.
"""

import json
import urllib.request
import time
from pathlib import Path
from typing import Dict, Any, Optional

USER_AGENT = "CFA-Quant-Research admin@quantcfa.org"

class SecEdgarClient:
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path(__file__).resolve().parent.parent / "data" / "sec_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._ticker_to_cik: Dict[str, str] = {}
        self._load_ticker_map()

    def _load_ticker_map(self):
        cache_file = self.cache_dir / "company_tickers.json"
        if cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < 86400 * 7:
            with open(cache_file, "r") as f:
                data = json.load(f)
        else:
            url = "https://www.sec.gov/files/company_tickers.json"
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                with open(cache_file, "w") as f:
                    json.dump(data, f)
            except Exception as e:
                print(f"Warning: Could not fetch SEC ticker map: {e}")
                return

        for item in data.values():
            ticker = item["ticker"].upper()
            cik = str(item["cik_str"]).zfill(10)
            self._ticker_to_cik[ticker] = cik

    def get_cik(self, ticker: str) -> Optional[str]:
        return self._ticker_to_cik.get(ticker.upper())

    def get_company_facts(self, ticker: str) -> Optional[Dict[str, Any]]:
        cik = self.get_cik(ticker)
        if not cik:
            print(f"CIK not found for ticker {ticker}")
            return None

        cache_file = self.cache_dir / f"CIK{cik}.json"
        if cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < 86400 * 3:
            with open(cache_file, "r") as f:
                return json.load(f)

        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            with open(cache_file, "w") as f:
                json.dump(data, f)
            time.sleep(0.15)  # Respect SEC rate limit (max 10 req/sec)
            return data
        except Exception as e:
            print(f"Error fetching facts for CIK {cik} ({ticker}): {e}")
            return None

    def extract_annual_series(self, facts: Dict[str, Any], tag: str, taxonomy: str = "us-gaap") -> Dict[int, Dict[str, Any]]:
        """
        Extracts annual (10-K) series for a given XBRL tag, recording both period year and filing date (point-in-time).
        """
        try:
            items = facts["facts"][taxonomy][tag]["units"]["USD"]
        except KeyError:
            return {}

        annual = {}
        for item in items:
            form = item.get("form")
            # Filter for 10-K annual filings with full year duration (or frame CY)
            if form == "10-K":
                fy = item.get("fy")
                fp = item.get("fp")
                val = item.get("val")
                filed = item.get("filed")
                end = item.get("end")
                
                if fy and val is not None and (fp in ["FY", "Y"] or "CY" in str(item.get("frame", ""))):
                    annual[fy] = {
                        "value": float(val),
                        "filed_date": filed,
                        "period_end": end,
                        "tag": tag
                    }
        return annual

    def get_financial_history(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Parses full 3-statement financial items across recent fiscal years.
        """
        facts = self.get_company_facts(ticker)
        if not facts:
            return None

        # Standard US-GAAP Tag Mappings
        tags = {
            "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"],
            "cost_of_revenue": ["CostOfGoodsAndServicesSold", "CostOfRevenue"],
            "gross_profit": ["GrossProfit"],
            "operating_income": ["OperatingIncomeLoss"],
            "net_income": ["NetIncomeLoss"],
            "depreciation_amortization": ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization"],
            "operating_cash_flow": ["NetCashProvidedByUsedInOperatingActivities"],
            "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
            "cash_and_equivalents": ["CashAndCashEquivalentsAtCarryingValue"],
            "accounts_receivable": ["AccountsReceivableNetCurrent"],
            "inventory": ["InventoryNet"],
            "total_current_assets": ["AssetsCurrent"],
            "total_assets": ["Assets"],
            "total_current_liabilities": ["LiabilitiesCurrent"],
            "long_term_debt": ["LongTermDebtNoncurrent", "LongTermDebt"],
            "short_term_debt": ["DebtCurrent", "ShortTermBorrowings"],
            "total_liabilities": ["Liabilities"],
            "stockholders_equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]
        }

        history = {}
        for metric, tag_list in tags.items():
            for tag in tag_list:
                series = self.extract_annual_series(facts, tag)
                if series:
                    for fy, data in series.items():
                        if fy not in history:
                            history[fy] = {"fiscal_year": fy, "filing_date": data["filed_date"]}
                        if metric not in history[fy]:
                            history[fy][metric] = data["value"]
                    break

        sorted_years = sorted(history.keys())
        return {
            "entity_name": facts.get("entityName", ticker),
            "ticker": ticker.upper(),
            "cik": self.get_cik(ticker),
            "years": sorted_years,
            "statements": [history[y] for y in sorted_years]
        }

if __name__ == "__main__":
    client = SecEdgarClient()
    print("Testing SEC EDGAR Client with AAPL...")
    data = client.get_financial_history("AAPL")
    if data:
        print(f"Company: {data['entity_name']} | Years available: {data['years']}")
        latest = data["statements"][-1]
        print(f"Latest Fiscal Year ({latest['fiscal_year']}):")
        print(f"  Revenue: ${latest.get('revenue', 0):,.0f}")
        print(f"  Operating Income (EBIT): ${latest.get('operating_income', 0):,.0f}")
        print(f"  Net Income: ${latest.get('net_income', 0):,.0f}")
        print(f"  Operating Cash Flow: ${latest.get('operating_cash_flow', 0):,.0f}")
        print(f"  CapEx: ${latest.get('capex', 0):,.0f}")
