#!/usr/bin/env python3
"""
CFA Quantitative Suite - Institutional Equity Research & Wealth Management Dashboard
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
from cfa_quant.volatility_surface import VolatilitySurfaceEngine
from cfa_quant.excel_exporter import ExcelModelExporter
from cfa_quant.ips_generator import IpsGeneratorEngine, ClientProfile
from cfa_quant.tax_legal_engine import TaxLegalOptimizationEngine, AccountBalances
from cfa_quant.fixed_income_ldi import FixedIncomeLdiEngine, BondAsset, LiabilityObligation
from pipeline.sec_edgar_client import SecEdgarClient
from pipeline.market_data import MarketDataClient
from pipeline.macro_engine import MacroEngine
from pipeline.industry_benchmarks import IndustryBenchmarkEngine
from pipeline.capm_sml_model import CapmSmlModel
from pipeline.cfa_valuation_engine import CfaValuationEngine
from forensic_accounting import ForensicAccountingEngine
from scripts.query_cfa_kb import search_kb

st.set_page_config(
    page_title="CFA Quant Suite | Institutional Equity & Wealth Management",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.sidebar.title("📈 CFA Quant Engine")
st.sidebar.markdown("Institutional Valuation, SAA & Wealth Management Suite")
ticker = st.sidebar.text_input("Equity Ticker", value="MSFT").upper()
growth_stage1 = st.sidebar.slider("Stage 1 Growth Rate (%)", min_value=1.0, max_value=30.0, value=8.0, step=0.5) / 100.0

st.sidebar.markdown("---")
st.sidebar.caption("Grounded in CFA Level I/II/III Curriculum Standards.")

# ==================== MAIN DASHBOARD TABS ====================
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "🏛️ Valuation & SML",
    "📈 Price Action & Zoom",
    "🌐 3D Vol Surface",
    "🛡️ Fixed Income LDI",
    "🎯 Opportunity Cost & EVA",
    "👥 Peer Comps & DuPont 5-Way",
    "📝 IPS Generator (L3)",
    "⚖️ Tax & Legal Wealth Alpha",
    "🌐 Macro & Yield Curve",
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
        
        # 1-Click Excel Exporter Download Button
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

# ------------------ TAB 4: FIXED INCOME LDI & IMMUNIZATION ------------------
with tab4:
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
        
        # Yield Curve Shocks Table
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

    # ------------------ TAB 5: OPPORTUNITY COST & EVA ------------------
    with tab5:
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

    # ------------------ TAB 6: PEER COMPS & DUPONT 5-WAY ------------------
    with tab6:
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

# ------------------ TAB 7: IPS GENERATOR (CFA LEVEL III) ------------------
with tab7:
    st.header("📝 Institutional Investment Policy Statement (IPS) Generator")
    st.caption("Constructs an audit-ready, institutional IPS following CFA Level III Private Wealth standards.")
    
    with st.form("ips_form"):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            client_name = st.text_input("Client / Family Names", value="Dr. & Mrs. Alexander Wright")
            client_ages = st.text_input("Client Ages (comma separated)", value="56, 54")
            jurisdiction = st.selectbox("Residency / Tax Jurisdiction", ["United States (Tax-Exempt State: FL/TX/NV/WY)", "United States (California / High-Tax)", "United States (New York / High-Tax)", "United Kingdom (Non-Dom / Remittance)", "Switzerland (Lump-Sum)", "Puerto Rico (Act 60)"])
            investable_assets = st.number_input("Total Investable Assets ($)", min_value=100000.0, value=8500000.0, step=250000.0)
            annual_spending = st.number_input("Annual Living Expenses / Spending ($)", min_value=10000.0, value=280000.0, step=10000.0)
        with col_c2:
            human_cap_val = st.number_input("Human Capital Present Value ($)", value=3500000.0, step=100000.0)
            human_cap_type = st.selectbox("Human Capital Character", ["bond_like (Low Career Volatility)", "equity_like (High Commission / Startup)"])
            bequest_goal = st.number_input("Bequest / Legacy Target ($)", value=4000000.0, step=250000.0)
            risk_willing = st.selectbox("Subjective Risk Willingness", ["Above Average", "Moderate", "High", "Below Average"])
            
        submit_ips = st.form_submit_button("🚀 Generate Audit-Ready IPS Document")
        
    if submit_ips:
        ages_list = [int(a.strip()) for a in client_ages.split(",") if a.strip().isdigit()]
        profile = ClientProfile(
            client_names=client_name,
            ages=ages_list or [55],
            residence_jurisdiction=jurisdiction,
            total_investable_assets=investable_assets,
            annual_spending_needs=annual_spending,
            human_capital_value=human_cap_val,
            human_capital_type="bond_like" if "bond_like" in human_cap_type else "equity_like",
            bequest_legacy_goal=bequest_goal,
            risk_willingness=risk_willing
        )
        ips_eng = IpsGeneratorEngine()
        ips_doc = ips_eng.generate_full_ips_document(profile)
        st.success("✓ Investment Policy Statement successfully compiled!")
        st.markdown(ips_doc)
        st.download_button("📥 Download IPS Document (.md)", ips_doc, file_name=f"IPS_{client_name.replace(' ', '_')}.md", mime="text/markdown")

# ------------------ TAB 8: TAX & LEGAL WEALTH ALPHA ------------------
with tab8:
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

# ------------------ TAB 9: MACRO & YIELD CURVE ------------------
with tab9:
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

# ------------------ TAB 10: CFA KNOWLEDGE BASE ------------------
with tab10:
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
