#!/usr/bin/env python3
"""
CFA Quantitative Suite - Institutional Equity Research & Portfolio Dashboard
Interactive Web Interface powered by Streamlit & Plotly.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from cfa_quant.models import OpportunityCostAssessment, ValuationResult
from cfa_quant.opportunity_cost import OpportunityCostEngine
from cfa_quant.stochastic_sim import MertonJumpDiffusion, MJDParameters
from cfa_quant.options_engine import OptionsAnalyticsEngine
from cfa_quant.charting import FinancialChartEngine
from pipeline.sec_edgar_client import SecEdgarClient
from pipeline.market_data import MarketDataClient
from pipeline.macro_engine import MacroEngine
from pipeline.industry_benchmarks import IndustryBenchmarkEngine
from pipeline.capm_sml_model import CapmSmlModel
from pipeline.cfa_valuation_engine import CfaValuationEngine
from pipeline.forensic_accounting import ForensicAccountingEngine
from scripts.query_cfa_kb import search_kb

st.set_page_config(
    page_title="CFA Quant Suite | Institutional Equity Valuation",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("📈 CFA Quant Engine")
st.sidebar.markdown("Institutional Valuation & Capital Allocation Suite")
ticker = st.sidebar.text_input("Equity Ticker", value="MSFT").upper()
growth_stage1 = st.sidebar.slider("Stage 1 Growth Rate (%)", min_value=1.0, max_value=30.0, value=8.0, step=0.5) / 100.0

st.sidebar.markdown("---")
st.sidebar.caption("Grounded in CFA Level I/II/III Curriculum & Academic Quant Research.")

# ==================== MAIN DASHBOARD TABS ====================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🏛️ Valuation & SML",
    "📈 Price Action & Zoom",
    "🎯 Opportunity Cost & EVA",
    "👥 Peer Comps & DuPont 5-Way",
    "🌐 Macro & Yield Curve",
    "🎲 Markov Monte Carlo Sim",
    "📚 CFA Knowledge Base"
])

# Shared Data Fetching
@st.cache_data(ttl=3600)
def load_company_data(t: str):
    sec = SecEdgarClient()
    mkt = MarketDataClient()
    macro = MacroEngine()
    bench = IndustryBenchmarkEngine()
    
    sec_data = sec.get_financial_history(t)
    mkt_data = mkt.get_market_quote(t)
    macro_snap = macro.get_comprehensive_macro_snapshot()
    peer_comp = bench.run_competitor_comparison(t)
    return sec_data, mkt_data, macro_snap, peer_comp

try:
    sec_data, mkt_data, macro_snap, peer_comp = load_company_data(ticker)
    has_data = sec_data is not None and len(sec_data["statements"]) >= 2
except Exception as e:
    has_data = False
    st.error(f"Error fetching data for {ticker}: {e}")

if has_data:
    latest_stmt = sec_data["statements"][-1]
    prior_stmt = sec_data["statements"][-2]
    rf = macro_snap["yield_curve"]["yields"]["10Y"]
    
    val_engine = CfaValuationEngine()
    total_debt = latest_stmt.get("long_term_debt", 0) + latest_stmt.get("short_term_debt", 0)
    wacc_res = val_engine.compute_wacc(
        market_cap=mkt_data["market_cap"],
        total_debt=total_debt,
        beta=mkt_data["beta"],
        risk_free_rate=rf
    )
    
    cfo = latest_stmt.get("operating_cash_flow", 0)
    capex = latest_stmt.get("capex", 0)
    cash = latest_stmt.get("cash_and_equivalents", 0)
    shares = mkt_data["shares_outstanding"]
    
    dcf_res = val_engine.compute_3stage_dcf(cfo, capex, cash, total_debt, shares, wacc_res["wacc"], growth_stage1=growth_stage1)
    
    book_val = latest_stmt.get("stockholders_equity", 1)
    net_inc = latest_stmt.get("net_income", 0)
    ri_res = val_engine.compute_residual_income_model(book_val, net_inc, wacc_res["cost_of_equity"], shares)
    
    forensic = ForensicAccountingEngine()
    f_score = forensic.compute_piotroski_f_score(latest_stmt, prior_stmt)
    m_score = forensic.compute_beneish_m_score(latest_stmt, prior_stmt)
    sloan = forensic.compute_sloan_accruals(latest_stmt)
    
    # ------------------ TAB 1: VALUATION & SML ------------------
    with tab1:
        st.header(f"🏛️ Institutional Valuation Memo: {ticker} ({sec_data['entity_name']})")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Market Price", f"${mkt_data['current_price']:,.2f}")
        col2.metric("3-Stage DCF Value", f"${dcf_res['intrinsic_value_per_share']:,.2f}", delta=f"{((dcf_res['intrinsic_value_per_share'] - mkt_data['current_price'])/dcf_res['intrinsic_value_per_share'])*100:+.1f}% MoS")
        col3.metric("Residual Income Value", f"${ri_res['intrinsic_value_per_share']:,.2f}")
        col4.metric("Dynamic WACC", f"{wacc_res['wacc']*100:.2f}%")
        
        st.markdown("---")
        c1, c2 = st.columns([1, 1])
        
        with c1:
            st.subheader("📊 Security Market Line (SML) & CAPM")
            capm_model = CapmSmlModel(risk_free_rate=rf, equity_risk_premium=0.050)
            sml_eval = capm_model.evaluate_security(ticker, mkt_data["beta"])
            
            betas = np.linspace(0.0, 2.0, 50)
            sml_returns = (rf + betas * 0.050) * 100
            
            fig_sml = go.Figure()
            fig_sml.add_trace(go.Scatter(x=betas, y=sml_returns, mode='lines', name='Security Market Line (SML)', line=dict(color='#2196F3', width=3)))
            fig_sml.add_trace(go.Scatter(x=[1.0], y=[(rf + 0.050)*100], mode='markers', name='Market Portfolio', marker=dict(size=12, color='#FF9800')))
            fig_sml.add_trace(go.Scatter(x=[mkt_data["beta"]], y=[sml_eval["expected_return_pct"]], mode='markers+text', name=ticker, text=[ticker], textposition="top center", marker=dict(size=14, color='#4CAF50', symbol='star')))
            
            fig_sml.update_layout(title="Security Market Line Equilibrium", xaxis_title="Beta (β)", yaxis_title="Expected Return (%)", template="plotly_dark")
            st.plotly_chart(fig_sml, use_container_width=True)
            st.info(f"**SML Stance:** {sml_eval['sml_verdict']}")
            
        with c2:
            st.subheader("📈 DCF Valuation Sensitivity Matrix")
            sens = val_engine.generate_sensitivity_matrix(cfo, capex, cash, total_debt, shares, wacc_res["wacc"], growth_stage1)
            df_sens = pd.DataFrame(sens["matrix"], index=[f"WACC {w:.2f}%" for w in sens["wacc_axis"]], columns=[f"g = {g:.1f}%" for g in sens["growth_axis"]])
            st.dataframe(df_sens.style.format("${:,.2f}").background_gradient(cmap="Greens"), use_container_width=True)
            
            st.subheader("🔍 Forensic Accounting & Quality Audit")
            fc1, fc2, fc3 = st.columns(3)
            fc1.metric("Piotroski F-Score", f"{f_score['piotroski_f_score']}/9", f_score['rating'])
            fc2.metric("Beneish M-Score", f"{m_score['beneish_m_score']:.2f}", m_score['manipulation_risk'])
            fc3.metric("Sloan Accruals", f"{sloan['sloan_accrual_ratio']:+.2f}%", sloan['earnings_quality'])

    # ------------------ TAB 2: PRICE ACTION & RECURSIVE ZOOM ------------------
    with tab2:
        st.header(f"📈 {ticker} Interactive Candlestick & Volume Surface")
        st.caption("Click-and-drag across any sub-region on the chart to zoom into that custom timeframe, or use the range buttons / slider below.")
        
        chart_eng = FinancialChartEngine()
        fig_candle = chart_eng.build_candlestick_figure(ticker, period="2y")
        st.plotly_chart(fig_candle, use_container_width=True)

    # ------------------ TAB 3: OPPORTUNITY COST & EVA ------------------
    with tab3:
        st.header("🎯 Opportunity Cost & Capital Allocation Assessment")
        opp_eng = OpportunityCostEngine(risk_free_rate=rf, equity_risk_premium=0.050)
        opp_res = opp_eng.evaluate_opportunity_cost(
            ticker=ticker,
            current_price=mkt_data["current_price"],
            market_cap=mkt_data["market_cap"],
            latest_cfo=cfo,
            latest_capex=capex,
            ebit=latest_stmt.get("operating_income", 0),
            total_debt=total_debt,
            stockholders_equity=book_val,
            cash=cash,
            wacc=wacc_res["wacc"],
            peer_metrics=peer_comp.get("peer_data", [])
        )
        
        o1, o2, o3 = st.columns(3)
        o1.metric("FCF Yield", f"{opp_res.fcf_yield_pct:.2f}%", f"{opp_res.fcf_yield_spread_over_treasury_bps:+.0f} bps over 10Y Treas.")
        o2.metric("ROIC vs WACC (EVA Spread)", f"{opp_res.economic_value_added_spread_pct:+.2f}%", "Economic Profit" if opp_res.economic_value_added_spread_pct > 0 else "Value Destruction")
        o3.metric("Next-Best Competitor Option", opp_res.next_best_competitor_ticker, f"Peer EVA: {opp_res.next_best_competitor_eva_spread:+.1f}%")
        
        st.markdown(f"### 📋 Allocation Verdict\n> **{opp_res.opportunity_cost_verdict}**")

    # ------------------ TAB 4: PEER COMPS & DUPONT 5-WAY ------------------
    with tab4:
        st.header("👥 Competitor Benchmarking & DuPont 5-Way Analysis")
        
        bench_engine = IndustryBenchmarkEngine()
        ratios = bench_engine.compute_cfa_ratios(latest_stmt)
        
        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("🔬 DuPont 5-Way ROE Decomposition")
            dp = ratios["dupont_5way"]
            df_dp = pd.DataFrame([
                {"Component": "Tax Burden (NI / EBT)", "Value": f"{dp['tax_burden']:.3f}"},
                {"Component": "Interest Burden (EBT / EBIT)", "Value": f"{dp['interest_burden']:.3f}"},
                {"Component": "EBIT Operating Margin", "Value": f"{dp['ebit_margin']:.2f}%"},
                {"Component": "Asset Turnover (Rev / Assets)", "Value": f"{dp['asset_turnover']:.3f}x"},
                {"Component": "Financial Leverage (Assets / Equity)", "Value": f"{dp['financial_leverage']:.2f}x"},
                {"Component": "Calculated ROE", "Value": f"{dp['roe_pct']:.2f}%"}
            ])
            st.table(df_dp)
            
        with c2:
            st.subheader("🏢 Industry Peer Group Comparison")
            if peer_comp and "peer_data" in peer_comp:
                df_peers = pd.DataFrame(peer_comp["peer_data"])
                st.dataframe(df_peers, use_container_width=True)

    # ------------------ TAB 5: MACRO & YIELD CURVE ------------------
    with tab5:
        st.header("🌐 Macroeconomic & Yield Curve Regime Studio")
        m_summary = macro_snap["macro_risk_summary"]
        
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("10Y Treasury Yield", m_summary["risk_free_rate_10y"])
        mc2.metric("SOFR Benchmark Rate", m_summary["sofr_benchmark"])
        mc3.metric("10Y Breakeven Inflation", m_summary["inflation_expectation_10y"])
        mc4.metric("HY Credit Spread", m_summary["credit_spread_hy_bps"])
        
        st.subheader("📉 US Treasury Yield Curve Structure")
        yc = macro_snap["yield_curve"]["yields"]
        tenors = list(yc.keys())
        rates = [yc[k] * 100 for k in tenors]
        
        fig_yc = go.Figure()
        fig_yc.add_trace(go.Scatter(x=tenors, y=rates, mode='lines+markers', name='Yield Curve', line=dict(color='#00E676', width=3), marker=dict(size=10)))
        fig_yc.update_layout(title=f"Yield Curve Regime: {macro_snap['yield_curve']['regime']}", xaxis_title="Tenor", yaxis_title="Yield (%)", template="plotly_dark")
        st.plotly_chart(fig_yc, use_container_width=True)

    # ------------------ TAB 6: MARKOV MONTE CARLO SIMULATOR ------------------
    with tab6:
        st.header("🎲 Markov Regime-Switching Monte Carlo 10,000-Path Simulator")
        sim_years = st.slider("Simulation Horizon (Years)", 1, 5, 3)
        
        mjd_params = MJDParameters(drift=0.10, volatility=mkt_data["beta"]*0.18, jump_intensity=0.3, jump_mean=-0.05, jump_std=0.08)
        sim = MertonJumpDiffusion(mjd_params)
        sim_res = sim.simulate(s0=mkt_data["current_price"], t_years=sim_years, n_steps=sim_years*12, n_sims=1000, random_state=42)
        
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Expected Terminal Price", f"${sim_res.mean_path[-1]:,.2f}")
        sc2.metric("95% Value at Risk (VaR)", f"{sim_res.var(0.05)*100:.2f}%")
        sc3.metric("95% Conditional VaR (CVaR)", f"{sim_res.cvar(0.05)*100:.2f}%")
        
        fig_mc = go.Figure()
        for i in range(min(50, len(sim_res.paths))):
            fig_mc.add_trace(go.Scatter(x=sim_res.time_grid, y=sim_res.paths[i], mode='lines', line=dict(color='rgba(100, 180, 255, 0.1)'), showlegend=False))
            
        fig_mc.add_trace(go.Scatter(x=sim_res.time_grid, y=sim_res.mean_path, mode='lines', name='Expected Mean Path', line=dict(color='#FFD700', width=3)))
        fig_mc.add_trace(go.Scatter(x=sim_res.time_grid, y=sim_res.quantile(0.95), mode='lines', name='95th Percentile', line=dict(color='#00E676', width=2, dash='dash')))
        fig_mc.add_trace(go.Scatter(x=sim_res.time_grid, y=sim_res.quantile(0.05), mode='lines', name='5th Percentile', line=dict(color='#FF5252', width=2, dash='dash')))
        
        fig_mc.update_layout(title=f"Stochastic Price Projections ({ticker})", xaxis_title="Years", yaxis_title="Stock Price ($)", template="plotly_dark")
        st.plotly_chart(fig_mc, use_container_width=True)

# ------------------ TAB 7: CFA KNOWLEDGE BASE ------------------
with tab7:
    st.header("📚 CFA Curriculum & Quantitative Research Search")
    query = st.text_input("Query CFA Knowledge Base (Formulas, LOS, Mock Exams, Research):", value="Human Capital Asset Allocation")
    if query:
        results = search_kb(query, limit=5)
        if results:
            for r in results:
                with st.expander(f"📖 {r['level']} | {r['topic']} ➔ {r['subtopic']}"):
                    if r['formulas']:
                        st.markdown(f"**Key Focus/Formulas:**\n```\n{r['formulas']}\n```")
                    st.markdown(f"**Excerpt:**\n{r['content']}")
        else:
            st.info("No matching curriculum items found.")
