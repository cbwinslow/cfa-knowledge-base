#!/usr/bin/env python3
"""
SEC EDGAR Financial Statement Ingestion Client
Fetches point-in-time XBRL 10-K and 10-Q financial statement facts directly from the official SEC EDGAR API.
"""

import json
import urllib.request
import time
from datetime import datetime
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
            time.sleep(0.15)
            return data
        except Exception as e:
            print(f"Error fetching facts for CIK {cik} ({ticker}): {e}")
            return None

    def extract_annual_series(self, facts: Dict[str, Any], tag: str, taxonomy: str = "us-gaap") -> Dict[int, Dict[str, Any]]:
        try:
            items = facts["facts"][taxonomy][tag]["units"]["USD"]
        except KeyError:
            return {}

        annual = {}
        for item in items:
            form = item.get("form")
            if form == "10-K":
                fy = item.get("fy")
                val = item.get("val")
                filed = item.get("filed")
                start = item.get("start")
                end = item.get("end")
                
                # Check for full 12-month annual duration (>= 300 days) or instantaneous balance sheet items
                duration_days = 365
                if start and end:
                    try:
                        d_start = datetime.strptime(start, "%Y-%m-%d")
                        d_end = datetime.strptime(end, "%Y-%m-%d")
                        duration_days = (d_end - d_start).days
                    except Exception:
                        pass
                
                if fy and val is not None and (duration_days >= 300 or start is None):
                    # Keep latest filed record or largest valid 12M value for that fiscal year
                    if fy not in annual or filed > annual[fy]["filed_date"] or val > annual[fy]["value"]:
                        annual[fy] = {
                            "value": float(val),
                            "filed_date": filed,
                            "period_end": end,
                            "tag": tag
                        }
        return annual

    def get_financial_history(self, ticker: str) -> Optional[Dict[str, Any]]:
        facts = self.get_company_facts(ticker)
        if not facts:
            return None

        tags = {
            "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet", "SalesRevenueGoodsNet"],
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
                        if metric not in history[fy] or history[fy][metric] == 0:
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
    data = client.get_financial_history("MSFT")
    if data:
        latest = data["statements"][-1]
        print(f"MSFT FY{latest['fiscal_year']} Revenue: ${latest.get('revenue', 0):,.0f}")
        print(f"MSFT FY{latest['fiscal_year']} Operating Income: ${latest.get('operating_income', 0):,.0f}")
