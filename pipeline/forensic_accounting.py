#!/usr/bin/env python3
"""
CFA Forensic Accounting & Quality of Earnings Engine
Calculates:
1. Piotroski F-Score (9-point fundamental financial health rating)
2. Beneish M-Score (Probabilistic earnings manipulation detection)
3. Sloan Accrual Ratio (Cash conversion vs accounting accruals)
"""

from typing import Dict, Any

class ForensicAccountingEngine:
    def compute_piotroski_f_score(self, current_stmt: Dict[str, Any], prior_stmt: Dict[str, Any]) -> Dict[str, Any]:
        scores = {}
        
        # 1. Profitability Signals
        net_inc = current_stmt.get("net_income", 0)
        tot_assets = max(current_stmt.get("total_assets", 1), 1)
        cfo = current_stmt.get("operating_cash_flow", 0)
        
        roa_curr = net_inc / tot_assets
        prior_assets = max(prior_stmt.get("total_assets", 1), 1)
        roa_prior = prior_stmt.get("net_income", 0) / prior_assets
        
        scores["F_ROA"] = 1 if roa_curr > 0 else 0
        scores["F_CFO"] = 1 if cfo > 0 else 0
        scores["F_DELTA_ROA"] = 1 if roa_curr > roa_prior else 0
        scores["F_ACCRUAL"] = 1 if cfo > net_inc else 0
        
        # 2. Leverage, Liquidity and Source of Funds
        curr_debt = current_stmt.get("long_term_debt", 0) + current_stmt.get("short_term_debt", 0)
        prior_debt = prior_stmt.get("long_term_debt", 0) + prior_stmt.get("short_term_debt", 0)
        lev_curr = curr_debt / tot_assets
        lev_prior = prior_debt / prior_assets
        scores["F_DELTA_LEVER"] = 1 if lev_curr <= lev_prior else 0
        
        cr_curr = current_stmt.get("total_current_assets", 1) / max(current_stmt.get("total_current_liabilities", 1), 1)
        cr_prior = prior_stmt.get("total_current_assets", 1) / max(prior_stmt.get("total_current_liabilities", 1), 1)
        scores["F_DELTA_LIQUID"] = 1 if cr_curr >= cr_prior else 0
        scores["F_EQUITY_OFFER"] = 1
        
        # 3. Operating Efficiency
        rev_curr = max(current_stmt.get("revenue", 1), 1)
        rev_prior = max(prior_stmt.get("revenue", 1), 1)
        gp_curr = current_stmt.get("gross_profit") or (rev_curr - current_stmt.get("cost_of_revenue", 0))
        gp_prior = prior_stmt.get("gross_profit") or (rev_prior - prior_stmt.get("cost_of_revenue", 0))
        
        gm_curr = gp_curr / rev_curr
        gm_prior = gp_prior / rev_prior
        scores["F_DELTA_MARGIN"] = 1 if gm_curr >= gm_prior else 0
        
        turn_curr = rev_curr / tot_assets
        turn_prior = rev_prior / prior_assets
        scores["F_DELTA_TURNOVER"] = 1 if turn_curr >= turn_prior else 0
        
        total_f_score = sum(scores.values())
        rating = "Strong / Value Buy" if total_f_score >= 7 else ("Neutral" if total_f_score >= 5 else "Weak / Distressed")
        
        return {
            "piotroski_f_score": total_f_score,
            "max_score": 9,
            "rating": rating,
            "details": scores
        }

    def compute_beneish_m_score(self, current_stmt: Dict[str, Any], prior_stmt: Dict[str, Any]) -> Dict[str, Any]:
        rev_t = max(current_stmt.get("revenue", 1), 1)
        rev_t_1 = max(prior_stmt.get("revenue", 1), 1)
        
        ar_t = current_stmt.get("accounts_receivable", 0)
        ar_t_1 = prior_stmt.get("accounts_receivable", 0)
        
        # Safe ratios with bounds to handle missing or zero line items
        if ar_t_1 > 0 and rev_t_1 > 0:
            dsri = (ar_t / rev_t) / (ar_t_1 / rev_t_1)
        else:
            dsri = 1.0
        dsri = max(0.2, min(5.0, dsri))
        
        gp_t = current_stmt.get("gross_profit") or (rev_t - current_stmt.get("cost_of_revenue", 0))
        gp_t_1 = prior_stmt.get("gross_profit") or (rev_t_1 - prior_stmt.get("cost_of_revenue", 0))
        gm_t = gp_t / rev_t
        gm_t_1 = gp_t_1 / rev_t_1
        gmi = (gm_t_1 / gm_t) if gm_t > 0 else 1.0
        gmi = max(0.2, min(5.0, gmi))
        
        sgi = max(0.5, min(3.0, rev_t / rev_t_1))
        
        tot_assets = max(current_stmt.get("total_assets", 1), 1)
        net_inc = current_stmt.get("net_income", 0)
        cfo = current_stmt.get("operating_cash_flow", 0)
        tata = max(-0.5, min(0.5, (net_inc - cfo) / tot_assets))
        
        curr_debt = current_stmt.get("long_term_debt", 0) + current_stmt.get("short_term_debt", 0)
        prior_debt = prior_stmt.get("long_term_debt", 0) + prior_stmt.get("short_term_debt", 0)
        prior_assets = max(prior_stmt.get("total_assets", 1), 1)
        
        lev_curr = curr_debt / tot_assets
        lev_prior = prior_debt / prior_assets
        lvgi = (lev_curr / lev_prior) if lev_prior > 0 else 1.0
        lvgi = max(0.2, min(5.0, lvgi))
        
        # Beneish M-Score Formula
        m_score = -4.84 + (0.920 * dsri) + (0.528 * gmi) + (0.892 * sgi) + (4.037 * tata) + (0.0327 * lvgi)
        manipulator_flag = m_score > -1.78
        
        return {
            "beneish_m_score": round(m_score, 3),
            "manipulation_risk": "High / Probable Red Flag" if manipulator_flag else "Low / Clean Accounting",
            "indices": {
                "DSRI": round(dsri, 3),
                "GMI": round(gmi, 3),
                "SGI": round(sgi, 3),
                "TATA": round(tata, 3),
                "LVGI": round(lvgi, 3)
            }
        }

    def compute_sloan_accruals(self, current_stmt: Dict[str, Any]) -> Dict[str, Any]:
        net_inc = current_stmt.get("net_income", 0)
        cfo = current_stmt.get("operating_cash_flow", 0)
        tot_assets = max(current_stmt.get("total_assets", 1), 1)
        
        accrual_ratio = (net_inc - cfo) / tot_assets
        quality = "High Quality (Cash Backed)" if accrual_ratio < 0 else ("Moderate" if accrual_ratio < 0.08 else "Low Quality (Accrual Driven)")
        
        return {
            "sloan_accrual_ratio": round(accrual_ratio * 100, 2),
            "earnings_quality": quality
        }
