#!/usr/bin/env python3
"""
CFA Quantitative Suite - Institutional Equity Research & Wealth Management Dashboard
Interactive Web Interface powered by Streamlit, Plotly & Autonomous Agentic Copilot.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from cfa_quant import (
    UnifiedPortfolio, FixedCouponBond, InflationLinkedBond, MunicipalBond, MortgageBackedSecurity,
    PublicEquityStock, RealEstateAsset, PrivateEquityHolding,
    CfaValuationEngine, ForensicAccountingEngine, CapmSmlModel, IndustryBenchmarkEngine, ExcelModelExporter,
    BaseValuationModel, UnifiedValuationSuite, ThreeStageDcfValuation, ResidualIncomeValuation, DividendDiscountModelValuation, MarketMultiplesValuation,
    PortfolioRebalancingEngine, RebalancingBlotter, TradeOrder,
    FactorRiskModelEngine, ActiveRiskDecomposition, FactorExposure,
    CoveredCallStrategy, ProtectiveCollarStrategy, BullCallSpreadStrategy, IronCondorStrategy, LongStraddleStrategy, GreeksHedgingSolver,
    BlackLittermanEngine, GipsCompositeEngine, ScenarioLabEngine, MarginalAllocationEngine, PerformanceAttributionEngine, FixedIncomeLdiEngine, VolatilitySurfaceEngine,
    LifeCyclePortfolioEngine, LifeCycleClient, IpsGeneratorEngine, ClientProfile, TaxLegalOptimizationEngine, AccountBalances,
    SecurityMaster, TransactionLedger, CustodianIngestionGateway, NewsWireEngine, CentralDataHopper, MacroEngine, SecEdgarClient, MarketDataClient,
    CfaAgentHarness, HybridRagEngine, PortfolioVisualizer, FinancialChartEngine
)
from scripts.query_cfa_kb import search_kb

st.set_page_config(
    page_title="CFA Quant Suite | Institutional Equity & Wealth Management",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Copilot Session State
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {
            "role": "assistant",
            "content": "👋 **Hello! I am your CFA Agentic Copilot.** I have full read/write access to our 3,871-topic curriculum library, live SEC filings, DCF engines, Muni TEY solvers, DuckDB transaction ledgers, and CIPM attribution engines. Ask me a question or command tools!",
            "tool_invoked": None
        }
    ]

# ==================== SIDEBAR COPILOT & CONTROLS ====================
with st.sidebar:
    st.title("📈 CFA Quant Suite")
    ticker = st.text_input("Equity Ticker", value="MSFT").upper()
    growth_stage1 = st.slider("Stage 1 Growth Rate (%)", min_value=1.0, max_value=30.0, value=8.0, step=0.5) / 100.0
    
    st.markdown("---")
    with st.expander("🤖 **CFA Autonomous Copilot Pane**", expanded=True):
        st.caption("AI Agent with live tool-calling and sandbox workspace.")
        
        chat_container = st.container(height=320)
        for msg in st.session_state.chat_history:
            with chat_container.chat_message(msg["role"]):
                if msg.get("tool_invoked"):
                    st.caption(f"⚙️ **Tool Executed:** `{msg['tool_invoked']}`")
                st.markdown(msg["content"])
                
        copilot_prompt = st.chat_input("Ask Copilot or command tools...")
        if copilot_prompt:
            st.session_state.chat_history.append({"role": "user", "content": copilot_prompt, "tool_invoked": None})
            
            harness = CfaAgentHarness()
            with st.spinner("🤖 Copilot reasoning and executing tools..."):
                agent_res = harness.process_chat_message(copilot_prompt)
                
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": agent_res["response"],
                "tool_invoked": agent_res["tool_invoked"]
            })
            st.rerun()

        harness_temp = CfaAgentHarness()
        w_files = harness_temp.list_workspace_files()
        if w_files:
            st.markdown("📁 **Copilot Workspace Files:**")
            for wf in w_files:
                st.code(f"{wf['filename']} ({wf['size_bytes']} B)", language="text")

# ==================== MAIN DASHBOARD TABS ====================
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13, tab14, tab15 = st.tabs([
    "🏛️ Valuation & SML",
    "📈 Price Action & Zoom",
    "🌐 3D Vol Surface",
    "➕ Marginal Asset Addition",
    "🏛️ Muni Bonds & TEY",
    "📊 CIPM Attribution",
    "🧪 Scenario Lab & Compare",
    "🛡️ Fixed Income LDI",
    "🎯 Opportunity Cost & EVA",
    "👥 Peer Comps & DuPont 5-Way",
    "📝 IPS & Life-Cycle Glidepath",
    "⚖️ Tax & Legal Wealth Alpha",
    "🌐 Macro & Yield Curve",
    "📚 CFA Knowledge Base",
    "📰 Live News Wire & Media"
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
    
    bench_engine = IndustryBenchmarkEngine()
    ratios = bench_engine.compute_cfa_ratios(latest_stmt)
    
    # ------------------ TAB 1: VALUATION & SML ------------------
    with tab1:
        st.header(f"🏛️ Institutional Valuation Memo: {ticker} ({sec_data['entity_name']})")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Market Price", f"${mkt_data['current_price']:,.2f}")
        col2.metric("3-Stage DCF Value", f"${dcf_res['intrinsic_value_per_share']:,.2f}", delta=f"{((dcf_res['intrinsic_value_per_share'] - mkt_data['current_price'])/dcf_res['intrinsic_value_per_share'])*100:+.1f}% MoS")
        col3.metric("Residual Income Value", f"${ri_res['intrinsic_value_per_share']:,.2f}")
        col4.metric("Dynamic WACC", f"{wacc_res['wacc']*100:.2f}%")
        
        exporter = ExcelModelExporter()
        wb_bytes = exporter.generate_valuation_workbook(
            ticker=ticker,
            company_name=sec_data["entity_name"],
            current_price=mkt_data["current_price"],
            shares_outstanding=shares,
            beta=mkt_data["beta"],
            risk_free_rate=rf,
            wacc=wacc_res["wacc"],
            cost_of_equity=wacc_res["cost_of_equity"],
            growth_stage1=growth_stage1,
            latest_stmt=latest_stmt,
            historical_stmts=sec_data["statements"],
            ratios=ratios,
            forensic={"f_score": f_score["piotroski_f_score"], "m_score": m_score["beneish_m_score"], "sloan_accruals": sloan["sloan_accrual_ratio"]}
        )
        st.download_button(
            label=f"📥 Download Linked 3-Statement & DCF Model ({ticker}.xlsx)",
            data=wb_bytes,
            file_name=f"{ticker}_Valuation_Model.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # Polymorphic Valuation Ensemble
        val_suite = UnifiedValuationSuite([
            ThreeStageDcfValuation(stage1_growth=growth_stage1),
            ResidualIncomeValuation(roe_forecast=ratios.get("roe", 0.22)),
            DividendDiscountModelValuation(dividend_growth_stage1=growth_stage1 * 0.8),
            MarketMultiplesValuation(target_pe_multiple=26.5, target_ev_ebitda_multiple=17.5)
        ])
        poly_data = {
            "free_cash_flow": cfo - capex,
            "book_value_of_equity": book_val,
            "dividend_per_share": max(0.50, latest_stmt.get("dividends_paid", 0) / shares) if shares > 0 else 2.50,
            "eps_ttm": max(1.0, net_inc / shares) if shares > 0 else 10.0,
            "ebitda": latest_stmt.get("operating_income", 1000000000.0) * 1.15,
            "net_debt": total_debt - cash
        }
        poly_eval = val_suite.evaluate_all_models(ticker, poly_data, cost_of_capital=wacc_res["wacc"], shares_outstanding=shares)
        
        st.markdown("---")
        st.subheader("🎯 CFA Polymorphic Equity Valuation Consensus Bridge (Football Field)")
        st.caption("Cross-methodology intrinsic valuation triangulation comparing DCF, Residual Income, DDM, and Market Comps against spot price.")
        
        model_names = [m["model_name"] for m in poly_eval["model_outputs"]]
        model_prices = [m["intrinsic_value"] for m in poly_eval["model_outputs"]]
        
        fig_bridge = go.Figure()
        fig_bridge.add_trace(go.Bar(
            y=model_names,
            x=model_prices,
            orientation='h',
            marker=dict(color=['#00E676', '#2979FF', '#FFB300', '#AB47BC']),
            text=[f"${p:,.2f}" for p in model_prices],
            textposition='auto',
            name="Model Intrinsic Value"
        ))
        fig_bridge.add_vline(x=mkt_data["current_price"], line_width=3, line_dash="dash", line_color="#FF1744", annotation_text=f"Spot Price: ${mkt_data['current_price']:,.2f}", annotation_position="top right")
        fig_bridge.add_vline(x=poly_eval["consensus_mean_value_per_share"], line_width=3, line_dash="dot", line_color="#00E5FF", annotation_text=f"Consensus Mean: ${poly_eval['consensus_mean_value_per_share']:,.2f}", annotation_position="bottom right")
        fig_bridge.update_layout(title=f"Intrinsic Valuation Triangulation: {ticker}", xaxis_title="Implied Equity Value Per Share ($)", yaxis_title="Polymorphic Valuation Methodology", template="plotly_dark")
        st.plotly_chart(fig_bridge, use_container_width=True)
        
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

    # ------------------ TAB 3: 3D VOLATILITY SURFACE & SKEW ------------------
    with tab3:
        st.header(f"🌐 {ticker} 3D Implied Volatility Surface & Volatility Smile")
        st.caption("Continuous 3D volatility surface mesh mapped across Moneyness (K/S) and Expiration Tenor (DTE).")
        
        vol_eng = VolatilitySurfaceEngine(risk_free_rate=rf)
        df_contracts = vol_eng.fetch_live_options_surface_data(ticker)
        mesh = vol_eng.build_surface_mesh(df_contracts)
        v_metrics = vol_eng.extract_surface_metrics(ticker, df_contracts, mesh)
        
        vm1, vm2, vm3, vm4 = st.columns(4)
        vm1.metric("ATM IV (30-Day)", f"{v_metrics.atm_iv_30d:.1f}%")
        vm2.metric("ATM IV (180-Day)", f"{v_metrics.atm_iv_180d:.1f}%", v_metrics.term_structure_slope)
        vm3.metric("25-Delta Risk Reversal", f"{v_metrics.skew_25d_risk_reversal_30d:+.2f}%", "Put Skew (Crash Premium)" if v_metrics.skew_25d_risk_reversal_30d > 0 else "Call Skew")
        vm4.metric("25-Delta Butterfly", f"{v_metrics.butterfly_25d_kurtosis_30d:+.2f}%", "Fat Tails / Kurtosis")
        
        fig_3d = vol_eng.render_3d_surface_figure(mesh, ticker, v_metrics.spot_price)
        st.plotly_chart(fig_3d, use_container_width=True)
        
        fig_2d = vol_eng.render_2d_skew_and_term_structure(mesh, ticker)
        st.plotly_chart(fig_2d, use_container_width=True)

        st.markdown("---")
        st.subheader("🎯 Institutional Options Strategy & Payoff Architecture")
        st.caption("Constructs multi-leg derivatives strategies with dynamic Black-Scholes terminal P&L and Greeks.")
        
        opt_strat_choice = st.selectbox(
            "Select Derivatives Strategy Structure:",
            ["Covered Call (Yield Enhancement)", "Protective Collar (Downside Floor + Financed Cap)", "Bull Call Spread (Defined Risk Vertical)", "Iron Condor (Delta-Neutral Range-Bound)", "Long Straddle (Pure Volatility Breakout)"]
        )
        
        s0_spot = float(v_metrics.spot_price if v_metrics.spot_price > 0 else 500.0)
        spots_range = np.linspace(s0_spot * 0.70, s0_spot * 1.30, 100)
        
        if opt_strat_choice.startswith("Covered Call"):
            c_call_k = st.slider("Call Strike Price ($)", min_value=float(s0_spot * 0.90), max_value=float(s0_spot * 1.25), value=float(round(s0_spot * 1.05, 1)))
            strat_inst = CoveredCallStrategy(spot_price_entry=s0_spot, call_strike=c_call_k, time_to_expiry_years=0.25, implied_volatility=v_metrics.atm_iv_30d/100.0 or 0.22)
        elif opt_strat_choice.startswith("Protective Collar"):
            col_p_k = st.slider("Protective Put Floor Strike ($)", min_value=float(s0_spot * 0.75), max_value=float(s0_spot * 0.98), value=float(round(s0_spot * 0.90, 1)))
            col_c_k = st.slider("Financing Call Cap Strike ($)", min_value=float(s0_spot * 1.02), max_value=float(s0_spot * 1.30), value=float(round(s0_spot * 1.10, 1)))
            strat_inst = ProtectiveCollarStrategy(spot_price_entry=s0_spot, put_strike=col_p_k, call_strike=col_c_k, time_to_expiry_years=0.25, implied_volatility=v_metrics.atm_iv_30d/100.0 or 0.22)
        elif opt_strat_choice.startswith("Bull Call"):
            b_k1 = st.slider("Lower Call Strike K1 ($)", min_value=float(s0_spot * 0.85), max_value=float(s0_spot * 1.05), value=float(round(s0_spot * 0.98, 1)))
            b_k2 = st.slider("Upper Call Strike K2 ($)", min_value=float(b_k1 + 1.0), max_value=float(s0_spot * 1.25), value=float(round(s0_spot * 1.08, 1)))
            strat_inst = BullCallSpreadStrategy(spot_price_entry=s0_spot, lower_strike_k1=b_k1, upper_strike_k2=b_k2, time_to_expiry_years=0.25, implied_volatility=v_metrics.atm_iv_30d/100.0 or 0.22)
        elif opt_strat_choice.startswith("Iron Condor"):
            ic_k1 = s0_spot * 0.85
            ic_k2 = s0_spot * 0.92
            ic_k3 = s0_spot * 1.08
            ic_k4 = s0_spot * 1.15
            strat_inst = IronCondorStrategy(spot_price_entry=s0_spot, put_long_k1=ic_k1, put_short_k2=ic_k2, call_short_k3=ic_k3, call_long_k4=ic_k4, time_to_expiry_years=0.15, implied_volatility=v_metrics.atm_iv_30d/100.0 or 0.22)
        else:
            strat_inst = LongStraddleStrategy(spot_price_entry=s0_spot, strike_price=s0_spot, time_to_expiry_years=0.25, implied_volatility=v_metrics.atm_iv_30d/100.0 or 0.22)
            
        pnl_arr = strat_inst.compute_profit_loss(spots_range)
        max_p, max_l = strat_inst.get_max_profit_and_loss()
        bes = strat_inst.get_break_even_points()
        port_g = strat_inst.compute_portfolio_greeks(s0_spot)
        
        op1, op2, op3, op4 = st.columns(4)
        op1.metric("Max Profit", f"${max_p:,.2f}" if max_p is not None else "Unlimited")
        op2.metric("Max Loss", f"${max_l:,.2f}" if max_l is not None else "Unlimited")
        op3.metric("Breakeven Spot", ", ".join([f"${b:.2f}" for b in bes]))
        op4.metric("Strategy Net Delta", f"{port_g['total_delta']:+.2f}", f"Gamma: {port_g['total_gamma']:+.3f}")
        
        fig_pnl = go.Figure()
        fig_pnl.add_trace(go.Scatter(x=spots_range, y=pnl_arr, mode='lines', name='Expiration Net P&L ($)', line=dict(color='#00E676' if pnl_arr[-1]>=0 else '#FF5252', width=3)))
        fig_pnl.add_hline(y=0.0, line_dash="dash", line_color="#888888")
        fig_pnl.add_vline(x=s0_spot, line_dash="dot", line_color="#FFA726", annotation_text=f"Spot (${s0_spot:.2f})")
        fig_pnl.update_layout(title=f"{strat_inst.name} Terminal Profit & Loss Profile", xaxis_title="Underlying Stock Spot Price ($)", yaxis_title="Net Profit / Loss ($)", template="plotly_dark")
        st.plotly_chart(fig_pnl, use_container_width=True)

        st.markdown("---")
        st.subheader("🛡️ Multi-Greeks Hedging Optimization Solver")
        st.caption("Solves exact shares and option contracts to immunize against directional (Delta), curve (Gamma), and volatility (Vega) risk.")
        
        h_col1, h_col2 = st.columns(2)
        with h_col1:
            target_hedge = st.selectbox("Hedging Target Regime:", ["Delta-Neutral (Underlying Stock)", "Gamma-Delta Neutral (1 Option + Stock)", "Vega-Gamma-Delta Neutral (2 Options + Stock)"])
        with h_col2:
            st.info(f"Active Position Greeks: **Delta = {port_g['total_delta']:+.1f}** | **Gamma = {port_g['total_gamma']:+.2f}** | **Vega = {port_g['total_vega_per_1pct']:+.2f}**")
            
        if target_hedge.startswith("Delta-Neutral"):
            sol_h = GreeksHedgingSolver.solve_delta_neutral_hedging(port_g["total_delta"])
        elif target_hedge.startswith("Gamma-Delta"):
            sol_h = GreeksHedgingSolver.solve_gamma_delta_neutral_hedging(port_g["total_delta"], port_g["total_gamma"], h1_delta_per_contract=50.0, h1_gamma_per_contract=2.5)
        else:
            sol_h = GreeksHedgingSolver.solve_vega_gamma_delta_neutral_hedging(
                port_g["total_delta"], port_g["total_gamma"], port_g["total_vega_per_1pct"],
                h1_greeks_per_contract={"delta": 45.0, "gamma": 2.5, "vega": 12.0},
                h2_greeks_per_contract={"delta": -30.0, "gamma": 1.5, "vega": 18.0}
            )
        st.json(sol_h)

# ------------------ TAB 4: MARGINAL ASSET ADDITION & 3D LANDSCAPE ------------------
with tab4:
    st.header("➕ Marginal Asset Addition & 3D Risk-Return Landscape")
    st.caption("Simulates the before-and-after impact of adding an investment to a portfolio across return, volatility, Sharpe ratio, and MCTR risk contributions.")
    
    base_p = UnifiedPortfolio("Marcus Family Wealth (Base)")
    base_p.add_instrument(PublicEquityStock("US Large Cap Equities", beta=1.0, expected_earnings_growth=0.065, historical_volatility=0.18), 6000000.0)
    base_p.add_instrument(FixedCouponBond("Core US Aggregate Bonds", coupon_rate=0.035, maturity_years=7.0, yield_to_maturity=0.045), 4000000.0)
    
    col_add1, col_add2 = st.columns(2)
    with col_add1:
        st.subheader("📦 Select Investment Instrument to Add")
        add_type = st.selectbox("Asset Category", ["Direct Real Estate LP", "Individual Tech Growth Equity (e.g. MSFT)", "10-Year TIPS Inflation Hedge", "Private Equity / Venture LP", "Custom Asset"])
        add_amount = st.number_input("Dollar Allocation Amount ($)", min_value=50000.0, value=2000000.0, step=100000.0)
        
    with col_add2:
        st.subheader("🔬 Asset Characteristics")
        if add_type == "Direct Real Estate LP":
            cand_inst = RealEstateAsset("Institutional Direct Real Estate Fund", net_operating_income=110000.0, cap_rate=0.055, expected_appreciation_rate=0.035)
        elif add_type == "Individual Tech Growth Equity (e.g. MSFT)":
            cand_inst = PublicEquityStock("Microsoft Corporation (MSFT)", ticker="MSFT", beta=1.1, dividend_yield=0.008, expected_earnings_growth=0.12, historical_volatility=0.23)
        elif add_type == "10-Year TIPS Inflation Hedge":
            cand_inst = InflationLinkedBond("10Y US TIPS (Inflation Linked)", coupon_rate=0.020, maturity_years=10.0, yield_to_maturity=0.021)
        elif add_type == "Private Equity / Venture LP":
            cand_inst = PrivateEquityHolding("Global Growth Equity Fund LP", target_irr=0.15)
        else:
            c_ret = st.number_input("Expected Return (%)", value=8.5, step=0.5) / 100.0
            c_vol = st.number_input("Annual Volatility (%)", value=16.0, step=0.5) / 100.0
            cand_inst = PublicEquityStock("Custom Candidate Asset", expected_earnings_growth=c_ret, historical_volatility=c_vol)

        st.info(f"**Selected:** {cand_inst.name}\n- Expected Return: **{cand_inst.compute_expected_return()*100:.2f}%**\n- Volatility: **{cand_inst.compute_volatility()*100:.2f}%**\n- Duration: **{cand_inst.compute_duration():.1f} yrs**")

    if st.button("🚀 Simulate Incremental Asset Addition"):
        marg_eng = MarginalAllocationEngine()
        sim_res, f_3d, f_bar, f_donut = marg_eng.simulate_asset_addition(base_p, cand_inst, dollar_to_add=add_amount)
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Return Delta", f"{sim_res.delta_metrics['return_delta_bps']:+.1f} bps/yr", f"New Return: {sim_res.metrics_after['expected_annual_return_pct']:.2f}%")
        k2.metric("Volatility Delta", f"{sim_res.delta_metrics['volatility_delta_bps']:+.1f} bps", "Lower Risk" if sim_res.delta_metrics['volatility_delta_bps'] < 0 else "Higher Risk")
        k3.metric("Sharpe Delta", f"{sim_res.delta_metrics['sharpe_delta']:+.2f}", f"New Sharpe: {sim_res.metrics_after['sharpe_ratio']:.2f}")
        k4.metric("Diversification Benefit", f"{sim_res.diversification_benefit_pct:.1f}%")
        
        st.success(f"**Recommendation Verdict:** {sim_res.recommendation_verdict}")
        st.plotly_chart(f_3d, use_container_width=True)
        
        v_c1, v_c2 = st.columns(2)
        with v_c1:
            st.plotly_chart(f_bar, use_container_width=True)
        with v_c2:
            st.plotly_chart(f_donut, use_container_width=True)

# ------------------ TAB 5: MUNICIPAL BONDS & TAX-EQUIVALENT YIELD (TEY) ------------------
with tab5:
    st.header("🏛️ Institutional Municipal Bond & Tax-Equivalent Yield (TEY) Studio")
    st.caption("Evaluates municipal bond tax-alpha, Muni/Treasury yield ratios, and Key Rate Duration (KRD) curves.")
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.subheader("📋 Municipal Bond Parameters")
        muni_name = st.text_input("Muni Bond Name", value="State of California General Obligation Bond 2035")
        muni_type = st.selectbox("Bond Structure", ["GO (General Obligation - Tax Backed)", "Revenue (Enterprise / Revenue Backed)"])
        muni_state = st.selectbox("Issuing State", ["CA", "NY", "FL", "TX", "IL", "NJ", "MA"])
        muni_yield = st.number_input("Stated Muni Yield to Maturity (YTM %)", value=3.45, step=0.05) / 100.0
        muni_mat = st.number_input("Maturity (Years)", value=10.0, step=0.5)
        
    with col_m2:
        st.subheader("⚖️ Investor Tax Profile (2026 Brackets)")
        fed_tax = st.selectbox("Federal Marginal Tax Bracket", [0.37, 0.35, 0.32, 0.24], format_func=lambda x: f"{x*100:.0f}%")
        state_tax = st.number_input("State Marginal Tax Rate (%)", value=9.3 if muni_state=="CA" else (6.85 if muni_state=="NY" else 0.0), step=0.1) / 100.0
        t10y_yield = st.number_input("10Y US Treasury Benchmark Yield (%)", value=4.74, step=0.01) / 100.0
        
    muni_inst = MunicipalBond(
        name=muni_name,
        muni_type="GO" if "GO" in muni_type else "Revenue",
        issuing_state=muni_state,
        yield_to_maturity=muni_yield,
        maturity_years=muni_mat,
        treasury_benchmark_10y_yield=t10y_yield
    )
    
    tey_val = muni_inst.compute_tax_equivalent_yield(federal_tax_rate=fed_tax, state_tax_rate=state_tax)
    ratio_val = muni_inst.compute_muni_to_treasury_ratio()
    krd_dict = muni_inst.compute_key_rate_durations()
    
    mb1, mb2, mb3, mb4 = st.columns(4)
    mb1.metric("Stated Tax-Free Yield", f"{muni_yield*100:.2f}%")
    mb2.metric("Tax-Equivalent Yield (TEY)", f"{tey_val*100:.2f}%", f"+{(tey_val - muni_yield)*100:.2f}% Tax Alpha")
    mb3.metric("10Y Muni/Treasury Ratio", f"{ratio_val:.1f}%", muni_inst.get_valuation_signal())
    mb4.metric("Modified Duration", f"{muni_inst.compute_modified_duration():.2f} yrs")
    
    st.markdown("---")
    st.subheader("📊 Key Rate Duration (KRD) Curve Sensitivity")
    df_krd = pd.DataFrame([{"Tenor": k.replace("KRD_", ""), "Key Rate Duration (Years)": v} for k, v in krd_dict.items()])
    st.dataframe(df_krd, use_container_width=True)

# ------------------ TAB 6: CFA / CIPM PERFORMANCE ATTRIBUTION ------------------
with tab6:
    st.header("📊 CFA Level III & CIPM Institutional Performance Attribution")
    st.caption("Decomposes portfolio excess returns using Brinson-Fachler Equity Attribution and Campisi Fixed Income Attribution.")
    
    att_mode = st.radio("Attribution Methodology", ["Equity: Brinson-Fachler (Sector Allocation vs. Stock Selection)", "Fixed Income: Campisi (Income, Curve, Spread, Selection)"], horizontal=True)
    
    att_eng = PerformanceAttributionEngine()
    
    if "Equity" in att_mode:
        st.subheader("🔬 Equity Sector Allocation & Selection Decomposition")
        df_sample_sec = pd.DataFrame([
            {"sector": "Information Technology", "port_weight": 0.35, "bench_weight": 0.28, "port_return": 0.24, "bench_return": 0.20},
            {"sector": "Health Care", "port_weight": 0.15, "bench_weight": 0.12, "port_return": 0.08, "bench_return": 0.06},
            {"sector": "Financials", "port_weight": 0.20, "bench_weight": 0.22, "port_return": 0.12, "bench_return": 0.14},
            {"sector": "Consumer Discretionary", "port_weight": 0.12, "bench_weight": 0.18, "port_return": 0.15, "bench_return": 0.11},
            {"sector": "Utilities & Energy", "port_weight": 0.18, "bench_weight": 0.20, "port_return": 0.04, "bench_return": 0.02}
        ])
        
        bf_res = att_eng.compute_brinson_attribution(df_sample_sec, model="Brinson-Fachler")
        
        ab1, ab2, ab3, ab4 = st.columns(4)
        ab1.metric("Portfolio Return", f"{bf_res.portfolio_total_return_pct:.2f}%")
        ab2.metric("Benchmark Return", f"{bf_res.benchmark_total_return_pct:.2f}%")
        ab3.metric("Excess Return (Alpha)", f"{bf_res.excess_return_pct:+.2f}%")
        ab4.metric("Selection Value Added", f"{bf_res.total_selection_effect_bps:+.1f} bps")
        
        st.table(bf_res.sector_breakdown)
    else:
        st.subheader("🔬 Fixed Income Campisi Attribution Breakdown")
        camp_res = att_eng.compute_campisi_attribution(
            portfolio_coupon_income=0.0425,
            portfolio_duration=6.8,
            parallel_yield_shift_bps=35.0,
            curve_twist_slope_bps=-15.0,
            spread_duration=4.2,
            credit_spread_change_bps=-20.0,
            portfolio_total_return=0.0385,
            benchmark_total_return=0.0290
        )
        
        cb1, cb2, cb3 = st.columns(3)
        cb1.metric("1. Coupon Income Return", f"{camp_res.income_effect_pct:+.2f}%")
        cb2.metric("2. Treasury Shift (+35bps)", f"{camp_res.treasury_curve_shift_pct:+.2f}%")
        cb3.metric("3. Spread Tightening (-20bps)", f"{camp_res.credit_spread_effect_pct:+.2f}%")
        
        st.info(f"**Specific Bond Selection Alpha:** {camp_res.selection_alpha_pct:+.2f}% | Total Excess Return: {camp_res.excess_return_pct:+.2f}%")

        st.markdown("---")
        st.subheader("🏛️ GIPS Compliance & Composite Performance Disclosure")
        st.caption("Global Investment Performance Standards verification, Modified Dietz cash flow weighting, and internal dispersion.")
        
        gips_eng = GipsCompositeEngine("US_INSTITUTIONAL_CORE_DISCRETIONARY_COMPOSITE")
        sample_gips_ports = [
            ("P_ALPHA", 15000000.0, 16800000.0, 0.120),
            ("P_BETA", 25000000.0, 27750000.0, 0.110),
            ("P_GAMMA", 18000000.0, 20340000.0, 0.130),
            ("P_DELTA", 10000000.0, 11100000.0, 0.110),
            ("P_EPSILON", 32000000.0, 35360000.0, 0.105),
            ("P_ZETA", 14000000.0, 15610000.0, 0.115)
        ]
        for pid, bmv, emv, rg in sample_gips_ports:
            gips_eng.add_portfolio_period_data(pid, bmv, emv, gross_return=rg, annual_fee_bps=65.0)
            
        gips_res = gips_eng.compute_composite_annual_performance(benchmark_annual_return=0.095, total_firm_assets=500000000.0)
        p_row = gips_res["presentation"]
        
        gp1, gp2, gp3, gp4 = st.columns(4)
        gp1.metric("Composite Gross Return", f"{p_row['composite_gross_return_pct']:.2f}%")
        gp2.metric("Composite Net Return", f"{p_row['composite_net_return_pct']:.2f}%", f"{p_row['net_excess_return_pct']:+.2f}% vs Bmk")
        gp3.metric("Internal Dispersion", f"{p_row['internal_dispersion_std_pct']}%", "Asset-Weighted Std Dev")
        gp4.metric("Total Composite Assets", f"${p_row['composite_assets_usd']:,.0f}", f"{p_row['composite_pct_of_firm']:.1f}% of Firm")
        
        with st.expander("📄 View GIPS Annual Composite Schedule Table"):
            st.dataframe(pd.DataFrame([p_row]))

        st.markdown("---")
        st.subheader("🌐 Multi-Factor Active Risk Decomposition (Fama-French / Barra)")
        st.caption("Decomposes portfolio active risk (Tracking Error) into Systematic Factor Variances vs. Stock-Specific Idiosyncratic Risk.")
        
        frm_engine = FactorRiskModelEngine()
        demo_assets = ["MSFT", "AAPL", "NVDA", "JNJ", "XOM"]
        demo_dw = np.array([0.08, -0.05, 0.06, -0.04, -0.05])
        demo_B = np.array([
            [1.15, -0.20, -0.30,  0.40,  0.60, -0.10],
            [1.10, -0.15, -0.25,  0.30,  0.55, -0.15],
            [1.45,  0.30, -0.40,  0.85,  0.50,  0.20],
            [0.65, -0.40,  0.45, -0.20,  0.30, -0.30],
            [0.80, -0.10,  0.75, -0.15, -0.20,  0.40]
        ])
        demo_spec = np.array([0.0225, 0.0200, 0.0450, 0.0100, 0.0150])
        factor_decomp = frm_engine.decompose_active_risk("PORTFOLIO_ALPHA", "S&P500", demo_assets, demo_dw, demo_B, demo_spec, portfolio_active_return=0.028)
        
        fr1, fr2, fr3, fr4 = st.columns(4)
        fr1.metric("Total Tracking Error", f"{factor_decomp.total_tracking_error_bps:.1f} bps", f"{factor_decomp.total_tracking_error_bps/100:.2f}%/yr")
        fr2.metric("Factor Active Risk", f"{factor_decomp.factor_active_risk_bps:.1f} bps", f"{factor_decomp.factor_risk_pct_of_variance:.1f}% Active Var")
        fr3.metric("Specific Stock Risk", f"{factor_decomp.specific_active_risk_bps:.1f} bps", f"{factor_decomp.specific_risk_pct_of_variance:.1f}% Active Var")
        fr4.metric("Information Ratio (IR)", f"{factor_decomp.information_ratio:.2f}", "Alpha / Tracking Error")
        
        with st.expander("📊 View Factor Tilt Exposures (Betas) & FLAM Metrics"):
            st.json({
                "factor_exposures": factor_decomp.factor_exposures,
                "fundamental_law_metrics": factor_decomp.flam_metrics
            })

# ------------------ TAB 7: SCENARIO LAB & PORTFOLIO COMPARE ------------------
with tab7:
    st.header("🧪 CFA Multi-Portfolio Comparison & Macroeconomic Stress Lab")
    st.caption("Head-to-head comparison of Current vs. Proposed Portfolios and simulation of historical macro shocks.")
    
    port_curr = UnifiedPortfolio("Portfolio A (Current 60/40)")
    port_curr.add_instrument(PublicEquityStock("US Large Cap Equities", beta=1.0, expected_earnings_growth=0.065, historical_volatility=0.18), 6000000.0)
    port_curr.add_instrument(FixedCouponBond("Core Aggregate Bonds", coupon_rate=0.035, maturity_years=7.0, yield_to_maturity=0.045), 4000000.0)
    
    port_prop = UnifiedPortfolio("Portfolio B (CFA Institutional Endowment)")
    port_prop.add_instrument(PublicEquityStock("Global Compounders", beta=0.95, expected_earnings_growth=0.08, historical_volatility=0.16), 4000000.0)
    port_prop.add_instrument(FixedCouponBond("10Y Treasury LDI", coupon_rate=0.045, maturity_years=10.0, yield_to_maturity=0.0469), 2000000.0)
    port_prop.add_instrument(InflationLinkedBond("10Y TIPS Inflation Hedge", coupon_rate=0.020, maturity_years=10.0, yield_to_maturity=0.021), 1500000.0)
    port_prop.add_instrument(RealEstateAsset("Commercial Real Estate", net_operating_income=80000.0, cap_rate=0.055), 1500000.0)
    port_prop.add_instrument(PrivateEquityHolding("Growth Equity LP", target_irr=0.15), 1000000.0)
    
    lab_eng = ScenarioLabEngine()
    comp_report = lab_eng.compare_portfolios(port_curr, port_prop)
    
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("Return Delta", f"{comp_report.delta_metrics['expected_return_delta_bps']:+.1f} bps/yr", "Port B vs Port A")
    sc2.metric("Volatility Delta", f"{comp_report.delta_metrics['volatility_delta_bps']:+.1f} bps", "Lower Risk" if comp_report.delta_metrics['volatility_delta_bps'] < 0 else "Higher Risk")
    sc3.metric("Sharpe Delta", f"{comp_report.delta_metrics['sharpe_delta']:+.2f}", f"Port B Sharpe: {comp_report.metrics_b['sharpe_ratio']:.2f}")
    sc4.metric("95% VaR Protection Delta", f"${comp_report.delta_metrics['var_95_delta_usd']:+,.2f}")
    
    st.markdown("---")
    
    fig_bar_comp, fig_radar_comp = lab_eng.render_comparison_visuals(comp_report)
    vc1, vc2 = st.columns(2)
    with vc1:
        st.plotly_chart(fig_bar_comp, use_container_width=True)
    with vc2:
        st.plotly_chart(fig_radar_comp, use_container_width=True)
        
    st.subheader("⚡ Macroeconomic Stress Test & Crisis Simulation")
    st.table(comp_report.stress_test_comparison)

    st.markdown("---")
    st.subheader("⚖️ CFA Level III Black-Litterman Asset Allocation Optimizer")
    st.caption("Blends neutral market equilibrium returns (reverse optimization) with subjective tactical views and confidence matrices.")
    
    bl_assets = ["US Large Cap Equities", "Global Developed Equities", "US 10Y Treasuries", "Emerging Market Debt"]
    bl_cov = np.array([
        [0.038, 0.024, 0.002, 0.009],
        [0.024, 0.046, 0.001, 0.014],
        [0.002, 0.001, 0.008, 0.003],
        [0.009, 0.014, 0.003, 0.024]
    ])
    bl_mkt_w = np.array([0.45, 0.25, 0.20, 0.10])
    
    bl_eng = BlackLittermanEngine(bl_assets, bl_cov, bl_mkt_w, risk_aversion=2.5, tau=0.05)
    
    bc1, bc2 = st.columns(2)
    with bc1:
        st.markdown("**View 1: US Equities vs Global Developed Outperformance**")
        v1_outperf = st.slider("US Equities Outperformance Spread (%)", min_value=-5.0, max_value=8.0, value=2.5, step=0.5) / 100.0
        v1_conf = st.slider("View 1 Confidence Level", min_value=0.1, max_value=0.99, value=0.80, step=0.05)
    with bc2:
        st.markdown("**View 2: Absolute 10Y Treasury Return Expectation**")
        v2_ret = st.slider("US 10Y Treasury Expected Return (%)", min_value=2.0, max_value=8.0, value=5.25, step=0.25) / 100.0
        v2_conf = st.slider("View 2 Confidence Level", min_value=0.1, max_value=0.99, value=0.90, step=0.05)
        
    P_views = np.array([
        [1.0, -1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0]
    ])
    Q_views = np.array([v1_outperf, v2_ret])
    bl_results = bl_eng.blend_views(P_views, Q_views, confidences=[v1_conf, v2_conf])
    
    bl_df = pd.DataFrame({
        "Asset Class": bl_assets,
        "Benchmark Weight": [f"{w*100:.1f}%" for w in bl_results["market_benchmark_weights"]],
        "Implied Equilibrium (Pi)": [f"{r*100:.2f}%" for r in bl_results["implied_equilibrium_returns"]],
        "Posterior Return (mu_BL)": [f"{r*100:.2f}%" for r in bl_results["posterior_expected_returns"]],
        "Optimal BL Weight (w*)": [f"{w*100:.1f}%" for w in bl_results["optimal_constrained_weights"]],
        "Active Tilt": [f"{t*100:+.2f}%" for t in bl_results["active_tilts"]]
    })
    st.table(bl_df)

    st.markdown("---")
    st.subheader("📑 CFA Tax-Aware Rebalancing Blotter & FIX Order Routing")
    st.caption("Generates cost-optimized HIFO execution tickets to transition current holdings to target optimal allocations.")
    
    rebal_eng = PortfolioRebalancingEngine(capital_gains_tax_rate=0.238, default_corridor_band_pct=0.03)
    curr_holdings_sample = {
        "US Large Cap Equities": {"shares": 25000.0, "price": 240.0, "cost_basis": 180.0},
        "Global Developed Equities": {"shares": 8000.0, "price": 480.0, "cost_basis": 500.0},
        "US 10Y Treasuries": {"shares": 20000.0, "price": 100.0, "cost_basis": 100.0},
        "Emerging Market Debt": {"shares": 10000.0, "price": 85.0, "cost_basis": 90.0}
    }
    tgt_weights_dict = dict(zip(bl_assets, bl_results["optimal_constrained_weights"]))
    rebal_blotter = rebal_eng.construct_rebalancing_orders("ENDOWMENT_MANDATE", curr_holdings_sample, tgt_weights_dict, cash_balance=250000.0)
    
    rb1, rb2, rb3, rb4 = st.columns(4)
    rb1.metric("Portfolio Assets", f"${rebal_blotter.total_portfolio_value_usd:,.0f}")
    rb2.metric("Turnover Volume", f"${rebal_blotter.total_turnover_usd:,.0f}", f"{rebal_blotter.turnover_ratio_pct:.1f}% Turnover")
    rb3.metric("Net Realized Gain", f"${rebal_blotter.estimated_realized_gains_usd:+,.0f}", "HIFO Lot Matching")
    rb4.metric("Est Tax Drag", f"${rebal_blotter.estimated_tax_drag_usd:,.0f}", "23.8% Cap Gains")
    
    if rebal_blotter.orders:
        orders_df = pd.DataFrame([
            {
                "Order ID": o.order_id,
                "Action": o.action,
                "Symbol": o.symbol,
                "Shares": f"{o.shares:,.1f}",
                "Limit Price": f"${o.limit_price:,.2f}",
                "Notional USD": f"${o.notional_usd:,.2f}",
                "Realized Gain/(Loss)": f"${o.estimated_realized_gain_usd:+,.2f}",
                "FIX Tag 35": o.fix_tag_35,
                "Custodian": o.target_custodian
            }
            for o in rebal_blotter.orders
        ])
        st.dataframe(orders_df, use_container_width=True)
    else:
        st.info("✓ Portfolio is within acceptable rebalancing corridor bands. Zero turnover required.")

# ------------------ TAB 8: FIXED INCOME LDI & IMMUNIZATION ------------------
with tab8:
    st.header("🛡️ CFA Level III Fixed Income LDI & Immunization Studio")
    st.caption("Matches portfolio duration, satisfies convexity constraints, and minimizes M^2 structural dispersion.")
    
    ldi_engine = FixedIncomeLdiEngine()
    
    c_ldi1, c_ldi2 = st.columns(2)
    with c_ldi1:
        st.subheader("🎯 Liability Disbursement Obligation")
        liab_amount = st.number_input("Liability Cash Flow Amount ($)", min_value=100000.0, value=10000000.0, step=500000.0)
        liab_years = st.number_input("Liability Due In (Years)", min_value=1.0, value=7.0, step=0.5)
        discount_y = st.number_input("Discount Rate / YTM (%)", value=4.5, step=0.1) / 100.0
        
        target_liab = LiabilityObligation(
            name="Institutional Pension Liability",
            due_in_years=liab_years,
            cash_flow_amount=liab_amount,
            discount_yield=discount_y
        )
        
    with c_ldi2:
        st.subheader("📦 Candidate Bond Portfolio Construction (Barbell)")
        b1_mat = st.slider("Bond 1 Maturity (Short Leg)", 1, 5, 3)
        b1_coupon = st.number_input("Bond 1 Coupon Rate (%)", value=4.0, step=0.25) / 100.0
        b1_alloc = st.number_input("Bond 1 Dollar Allocation ($)", value=4200000.0, step=100000.0)
        
        b2_mat = st.slider("Bond 2 Maturity (Long Leg)", 8, 20, 12)
        b2_coupon = st.number_input("Bond 2 Coupon Rate (%)", value=4.8, step=0.25) / 100.0
        b2_alloc = st.number_input("Bond 2 Dollar Allocation ($)", value=3400000.0, step=100000.0)
        
        bond1 = ldi_engine.compute_bond_analytics(coupon_rate=b1_coupon, maturity_years=b1_mat, ytm=discount_y)
        bond2 = ldi_engine.compute_bond_analytics(coupon_rate=b2_coupon, maturity_years=b2_mat, ytm=discount_y)
        
    if st.button("🚀 Evaluate Immunization & Yield Curve Shocks"):
        port_assets = [(bond1, b1_alloc), (bond2, b2_alloc)]
        imm_res = ldi_engine.evaluate_liability_immunization(port_assets, target_liab)
        
        im1, im2, im3, im4 = st.columns(4)
        im1.metric("Portfolio PV", f"${imm_res.portfolio_present_value:,.2f}", "Solvent" if imm_res.is_solvency_satisfied else "Deficit")
        im2.metric("Macaulay Duration", f"{imm_res.portfolio_macaulay_duration:.2f} yrs", f"Liability: {imm_res.liability_macaulay_duration:.2f} yrs")
        im3.metric("Convexity", f"{imm_res.portfolio_convexity:.1f}", f"Liability: {imm_res.liability_convexity:.1f}")
        im4.metric("M^2 Dispersion", f"{imm_res.structural_dispersion_m2:.2f}")
        
        st.info(f"**Contingent Status:** {imm_res.contingent_immunization_status}")
        
        st.subheader("⚡ Non-Parallel Yield Curve Stress Test")
        shock_rows = []
        for s_type in ["Parallel +100bps", "Parallel -100bps", "Steepening", "Flattening", "Positive Butterfly"]:
            sh_out = ldi_engine.simulate_yield_curve_shifts(port_assets, target_liab, s_type)
            shock_rows.append({
                "Scenario": sh_out["scenario"],
                "Portfolio Value": f"${sh_out['portfolio_value_post_shock']:,.2f}",
                "Liability Value": f"${sh_out['liability_value_post_shock']:,.2f}",
                "Surplus / (Deficit)": f"${sh_out['post_shock_surplus']:,.2f}",
                "Protected": "✓ Protected" if sh_out["immunization_protected"] else "✗ Breach"
            })
        st.table(pd.DataFrame(shock_rows))

    # ------------------ TAB 9: OPPORTUNITY COST & EVA ------------------
    with tab9:
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

    # ------------------ TAB 10: PEER COMPS & DUPONT 5-WAY ------------------
    with tab10:
        st.header("👥 Competitor Benchmarking & DuPont 5-Way Analysis")
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

    # ------------------ TAB 11: IPS & LIFE-CYCLE GLIDEPATH (CFA LEVEL III) ------------------
    with tab11:
        st.header("📝 Institutional Investment Policy Statement (IPS) & Life-Cycle Glidepath")
        st.caption("Constructs an audit-ready, institutional IPS and dynamic age-based asset allocation glidepath.")
        
        with st.form("ips_form"):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                client_name = st.text_input("Client / Family Names", value="Dr. & Mrs. Alexander Wright")
                client_age = st.number_input("Primary Investor Age", min_value=18, max_value=95, value=48, step=1)
                spouse_age = st.number_input("Spouse Age (Optional)", min_value=18, max_value=95, value=46, step=1)
                jurisdiction = st.selectbox("Residency / Tax Jurisdiction", ["United States (Tax-Exempt State: FL/TX/NV/WY)", "United States (California / High-Tax)", "United States (New York / High-Tax)", "United Kingdom (Non-Dom / Remittance)", "Switzerland (Lump-Sum)", "Puerto Rico (Act 60)"])
                investable_assets = st.number_input("Total Investable Financial Assets ($)", min_value=100000.0, value=6500000.0, step=250000.0)
                annual_spending = st.number_input("Annual Living Expenses / Spending ($)", min_value=10000.0, value=250000.0, step=10000.0)
            with col_c2:
                employment_income = st.number_input("Annual Employment / Business Income ($)", min_value=0.0, value=450000.0, step=25000.0)
                human_cap_type = st.selectbox("Human Capital Character", ["bond_like (Low Career Volatility / Physician / Govt)", "equity_like (High Commission / Startup Founder)"])
                bequest_goal = st.number_input("Bequest / Legacy Target ($)", value=3000000.0, step=250000.0)
                risk_willing = st.selectbox("Subjective Risk Willingness", ["Aggressive", "Growth", "Moderate", "Conservative"])
                
            submit_ips = st.form_submit_button("🚀 Generate Institutional IPS & Age-Based Glidepath")
            
        if submit_ips:
            h_type = "bond_like" if "bond_like" in human_cap_type else "equity_like"
            lc_client = LifeCycleClient(
                client_name=client_name,
                current_age=client_age,
                annual_employment_income=employment_income,
                human_capital_type=h_type,
                annual_living_expenses=annual_spending,
                current_financial_assets=investable_assets,
                bequest_target_usd=bequest_goal,
                risk_willingness=risk_willing
            )
            
            lc_engine = LifeCyclePortfolioEngine()
            lc_profile = lc_engine.generate_lifecycle_profile(lc_client)
            df_glidepath = lc_engine.generate_glidepath_trajectory(lc_client)
            
            st.subheader("📊 Holistic Economic Net Worth & SAA Glidepath")
            w1, w2, w3, w4 = st.columns(4)
            w1.metric("Financial Assets", f"${lc_profile.financial_capital:,.2f}")
            w2.metric("Human Capital PV", f"${lc_profile.human_capital_pv:,.2f}", f"{lc_profile.human_capital_pct_of_wealth:.1f}% of Total")
            w3.metric("Total Economic Net Worth", f"${lc_profile.total_economic_net_worth:,.2f}")
            w4.metric("Recommended SAA", f"{lc_profile.recommended_equity_pct:.0f}% Equity / {lc_profile.recommended_fixed_income_pct:.0f}% FI")
            
            fig_glide = lc_engine.render_glidepath_figure(df_glidepath, client_name)
            st.plotly_chart(fig_glide, use_container_width=True)
            
            st.subheader("🎯 Goals-Based Wealth Management (GBWM) Decomposition")
            gb = lc_profile.goals_based_buckets
            gb1, gb2, gb3 = st.columns(3)
            gb1.metric("1. Lifestyle Protection Bucket", f"${gb.lifestyle_protection_usd:,.2f}", f"{gb.lifestyle_protection_pct:.1f}% of Portfolio")
            gb2.metric("2. Aspirational Growth Bucket", f"${gb.aspirational_growth_usd:,.2f}", f"{gb.aspirational_growth_pct:.1f}% of Portfolio")
            gb3.metric("3. Legacy & Bequest Bucket", f"${gb.legacy_bequest_usd:,.2f}", f"{gb.legacy_bequest_pct:.1f}% of Portfolio")
            
            st.markdown("---")
            
            profile = ClientProfile(
                client_names=client_name,
                ages=[client_age, spouse_age],
                residence_jurisdiction=jurisdiction,
                total_investable_assets=investable_assets,
                annual_spending_needs=annual_spending,
                human_capital_value=lc_profile.human_capital_pv,
                human_capital_type=h_type,
                bequest_legacy_goal=bequest_goal,
                risk_willingness=risk_willing
            )
            ips_eng = IpsGeneratorEngine()
            ips_doc = ips_eng.generate_full_ips_document(profile)
            st.success("✓ Investment Policy Statement successfully compiled!")
            st.markdown(ips_doc)
            st.download_button("📥 Download Full IPS Document (.md)", ips_doc, file_name=f"IPS_{client_name.replace(' ', '_')}.md", mime="text/markdown")

    # ------------------ TAB 12: TAX & LEGAL WEALTH ALPHA ------------------
    with tab12:
        st.header("⚖️ Tax-Alpha Asset Location & Cross-Border Optimization")
        
        tl_col1, tl_col2 = st.columns(2)
        with tl_col1:
            st.subheader("🏛️ Asset Location Optimizer")
            st.caption("Places assets into Taxable vs. Traditional 401k vs. Roth accounts to minimize tax drag.")
            taxable_bal = st.number_input("Taxable Brokerage Balance ($)", value=4500000.0, step=100000.0)
            trad_bal = st.number_input("Tax-Deferred (Traditional 401k/IRA) Balance ($)", value=2500000.0, step=100000.0)
            roth_bal = st.number_input("Tax-Exempt (Roth IRA/401k) Balance ($)", value=1500000.0, step=100000.0)
            
            if st.button("Compute Tax-Alpha Asset Placement"):
                tl_eng = TaxLegalOptimizationEngine()
                loc_res = tl_eng.optimize_asset_location(AccountBalances(taxable_bal, trad_bal, roth_bal))
                st.metric("Estimated Annual Tax Drag Savings", f"${loc_res['estimated_annual_tax_savings_usd']:,.2f}", f"+{loc_res['tax_alpha_basis_points']} bps/yr Tax Alpha")
                st.json(loc_res["asset_placement"])
                
        with tl_col2:
            st.subheader("🌐 State & Relocation Tax Arbitrage")
            curr_st = st.selectbox("Current Residency State", ["California", "New York", "New Jersey", "Massachusetts"])
            prop_st = st.selectbox("Proposed Relocation State", ["Florida", "Texas", "Nevada", "Wyoming", "Puerto Rico (Act 60)"])
            inc_val = st.number_input("Annual Ordinary Income ($)", value=750000.0, step=50000.0)
            cg_val = st.number_input("Annual Capital Gains Realized ($)", value=500000.0, step=50000.0)
            
            if st.button("Evaluate Jurisdiction Arbitrage"):
                tl_eng = TaxLegalOptimizationEngine()
                arb_res = tl_eng.evaluate_jurisdiction_tax_arbitrage(curr_st, prop_st, inc_val, cg_val)
                st.metric("Annual Tax Savings", f"${arb_res['annual_tax_arbitrage_savings']:,.2f}/yr")
                st.metric("10-Year Compounded Wealth Delta", f"${arb_res['10_year_compounded_savings']:,.2f}")

    # ------------------ TAB 13: MACRO & YIELD CURVE ------------------
    with tab13:
        st.header("🌐 Macroeconomic & Yield Curve Regime Studio")
        if has_data:
            m_summary = macro_snap["macro_risk_summary"]
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("10Y Treasury Yield", m_summary["risk_free_rate_10y"])
            mc2.metric("SOFR Benchmark Rate", m_summary["sofr_benchmark"])
            mc3.metric("10Y Breakeven Inflation", m_summary["inflation_expectation_10y"])
            mc4.metric("HY Credit Spread", m_summary["credit_spread_hy_bps"])
            
            yc = macro_snap["yield_curve"]["yields"]
            tenors = list(yc.keys())
            rates = [yc[k] * 100 for k in tenors]
            
            fig_yc = go.Figure()
            fig_yc.add_trace(go.Scatter(x=tenors, y=rates, mode='lines+markers', name='Yield Curve', line=dict(color='#00E676', width=3), marker=dict(size=10)))
            fig_yc.update_layout(title=f"Yield Curve Regime: {macro_snap['yield_curve']['regime']}", xaxis_title="Tenor", yaxis_title="Yield (%)", template="plotly_dark")
            st.plotly_chart(fig_yc, use_container_width=True)

    # ------------------ TAB 14: CFA KNOWLEDGE BASE ------------------
    with tab14:
        st.header("📚 CFA Curriculum & Quantitative Research Search")
        query = st.text_input("Query CFA Knowledge Base (Formulas, LOS, Mock Exams, Research):", value="Municipal Bond Tax Equivalent Yield")
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

    # ------------------ TAB 15: LIVE NEWS WIRE & MEDIA TERMINAL ------------------
    with tab15:
        st.header("📰 Institutional Real-Time News Wire & Media Terminal")
        st.caption("Live streaming SEC 8-K filings, Federal Reserve FOMC wires, MarketWatch, CNBC & financial press feeds with automated quality scoring and vector search.")
        
        nw_engine = NewsWireEngine()
        
        # Top control hopper
        c_top1, c_top2, c_top3, c_top4 = st.columns([3, 2, 2, 2])
        search_kw = c_top1.text_input("🔍 Search News & Filings:", value=ticker)
        min_q = c_top2.slider("Min Quality Score", min_value=0.0, max_value=1.0, value=0.4, step=0.1)
        wire_filter = c_top3.selectbox("Filter Wire Channel", ["ALL", "EQUITY_WIRE", "FINANCIAL_WIRE", "SEC_8K"])
        
        if c_top4.button("📡 Ingest Live Wires"):
            with st.spinner("Polling live SEC, Fed, and market wire feeds..."):
                n_t = nw_engine.ingest_ticker_news(ticker, max_articles=5)
                w_stats = nw_engine.ingest_all_wire_sources(max_articles_per_wire=3)
                st.success(f"✓ Ingested {n_t} {ticker} articles + {sum(w_stats.values())} macro/SEC wire disclosures!")
                
        # Perform query
        news_items = nw_engine.search_news_wire(search_kw or ticker, ticker=ticker if not search_kw else None, min_quality_score=min_q, top_k=15)
        
        if not news_items:
            st.info(f"No news articles found matching '{search_kw}'. Click '📡 Ingest Live Wires' above to poll breaking feeds.")
        else:
            col_list, col_reader = st.columns([4, 6])
            
            with col_list:
                st.subheader(f"⚡ Live Feed ({len(news_items)} items)")
                article_options = [f"[{i+1}] {item['headline'][:50]}... ({item['source_wire']})" for i, item in enumerate(news_items)]
                selected_idx = st.radio("Select Article to Read:", range(len(news_items)), format_func=lambda i: f"⭐ {news_items[i]['quality_score']:.1f} | {news_items[i]['headline'][:55]}... ({news_items[i]['published_at'][:10]})")
                
            with col_reader:
                selected_art = news_items[selected_idx]
                st.subheader(selected_art["headline"])
                
                # Metadata Bar
                mb1, mb2, mb3 = st.columns(3)
                mb1.metric("Quality Score", f"{selected_art['quality_score'] * 100:.0f}%")
                sent_val = selected_art['sentiment_score']
                mb2.metric("Sentiment", f"{sent_val:+.2f}", delta="Bullish" if sent_val > 0.05 else ("Bearish" if sent_val < -0.05 else "Neutral"))
                mb3.metric("Ticker / Domain", f"{selected_art['ticker']} | {selected_art['domain']}")
                
                st.markdown(f"**Byline:** `{selected_art['author']}` | **Published:** `{selected_art['published_at']}` | **Source:** `{selected_art['source_wire']}`")
                
                # Tags
                if selected_art.get("subjects"):
                    st.markdown("🏷️ **Topic Taxonomy:** " + " ".join([f"`{s}`" for s in selected_art["subjects"][:6]]))
                if selected_art.get("related_tickers"):
                    st.markdown("🏢 **Related Entities:** " + " ".join([f"`{t}`" for t in selected_art["related_tickers"][:8]]))
                
                st.markdown("---")
                
                # Hero Image or Chart if available
                if selected_art.get("lead_image_url"):
                    try:
                        st.image(selected_art["lead_image_url"], caption=f"Visual asset via {selected_art['domain']}", use_container_width=True)
                    except Exception:
                        pass
                
                st.markdown(f"### Article Summary\n{selected_art['summary']}")
                
                if selected_art.get("url"):
                    st.link_button("🌐 Open Full Source Document / SEC Filing", selected_art["url"])

