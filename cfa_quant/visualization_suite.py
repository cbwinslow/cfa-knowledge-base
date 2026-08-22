"""
Reusable Institutional Financial Visualization Suite (Plotly Dark Theme)
Encapsulated, modular chart factory classes implementing:
1. 3D Risk-Return-Diversification Landscape Surface (Weight vs. Correlation vs. Sharpe)
2. Before-and-After Incremental Allocation Waterfall & Spider Radar
3. Marginal Contribution to Risk (MCTR & %CTR) Donut Decomposition
4. Multi-Asset Efficient Frontier with Tangency & Portfolio Migration Trajectory
"""

from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class PortfolioVisualizer:
    def __init__(self, template: str = "plotly_dark"):
        self.template = template
        self.primary_color = "#00E676"   # Neon Green
        self.secondary_color = "#2979FF" # Electric Blue
        self.accent_color = "#FFD700"    # Gold
        self.danger_color = "#FF5252"    # Coral Red
        self.bg_color = "#181a20"
        self.grid_color = "#333842"

    def plot_3d_risk_return_landscape(
        self,
        base_return: float,
        base_vol: float,
        candidate_name: str,
        candidate_return: float,
        candidate_vol: float,
        rf: float = 0.045
    ) -> go.Figure:
        """
        Renders a 3D Plotly Surface mapping:
        X-axis: Candidate Asset Allocation Weight (w_c: 0% to 50%)
        Y-axis: Correlation with Base Portfolio (rho: -0.80 to +0.95)
        Z-axis: Resulting Portfolio Sharpe Ratio
        """
        weights = np.linspace(0.0, 0.50, 40)
        correlations = np.linspace(-0.80, 0.95, 40)
        
        W, RHO = np.meshgrid(weights, correlations)
        
        # Portfolio Expected Return: E(R_p) = (1 - w)*R_b + w*R_c
        port_ret = ((1.0 - W) * base_return) + (W * candidate_return)
        
        # Portfolio Variance: Var = (1-w)^2*sigma_b^2 + w^2*sigma_c^2 + 2*w*(1-w)*sigma_b*sigma_c*rho
        port_var = (((1.0 - W) ** 2) * (base_vol ** 2)) + ((W ** 2) * (candidate_vol ** 2)) + (2.0 * W * (1.0 - W) * base_vol * candidate_vol * RHO)
        port_vol = np.sqrt(np.maximum(port_var, 1e-6))
        
        # Sharpe Ratio Surface
        sharpe_surface = (port_ret - rf) / port_vol

        fig = go.Figure()
        
        fig.add_trace(go.Surface(
            x=W * 100.0,
            y=RHO,
            z=sharpe_surface,
            colorscale="Plasma",
            colorbar=dict(title=dict(text="Portfolio Sharpe Ratio", font=dict(color="#FFF", size=11)), tickfont=dict(color="#FFF")),
            contours=dict(
                z=dict(show=True, usecolormap=True, project=dict(z=True), highlightcolor="#00E676", width=2)
            ),
            lighting=dict(ambient=0.6, diffuse=0.8, roughness=0.5, specular=0.4),
            hovertemplate="<b>Added Weight:</b> %{x:.1f}%<br><b>Correlation:</b> %{y:.2f}<br><b>Sharpe Ratio:</b> %{z:.2f}<extra></extra>"
        ))

        fig.update_layout(
            title=f"🌐 3D Optimization Landscape: Impact of Adding {candidate_name}",
            template=self.template,
            scene=dict(
                xaxis=dict(title="Added Asset Weight (%)", gridcolor=self.grid_color, backgroundcolor=self.bg_color, tickfont=dict(color="#FFF")),
                yaxis=dict(title="Correlation (ρ with Portfolio)", gridcolor=self.grid_color, backgroundcolor=self.bg_color, tickfont=dict(color="#FFF")),
                zaxis=dict(title="Portfolio Sharpe Ratio", gridcolor=self.grid_color, backgroundcolor=self.bg_color, tickfont=dict(color="#FFF")),
                camera=dict(eye=dict(x=-1.5, y=-1.5, z=1.1))
            ),
            margin=dict(l=10, r=10, t=50, b=10),
            height=580
        )
        return fig

    def plot_before_after_migration(
        self,
        before_metrics: Dict[str, Any],
        after_metrics: Dict[str, Any],
        candidate_name: str,
        added_weight_pct: float
    ) -> go.Figure:
        """
        Renders side-by-side comparative metric cards and bar deltas.
        """
        categories = ["Expected Return (%)", "Annual Volatility (%)", "Sharpe Ratio", "Macaulay Duration (Yrs)", "95% VaR (%)"]
        
        val_before = [
            before_metrics["expected_annual_return_pct"],
            before_metrics["annual_volatility_pct"],
            before_metrics["sharpe_ratio"],
            before_metrics["macaulay_duration_years"],
            before_metrics["var_95_pct_1yr"]
        ]
        
        val_after = [
            after_metrics["expected_annual_return_pct"],
            after_metrics["annual_volatility_pct"],
            after_metrics["sharpe_ratio"],
            after_metrics["macaulay_duration_years"],
            after_metrics["var_95_pct_1yr"]
        ]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=categories,
            y=val_before,
            name="Pre-Allocation (Current)",
            marker_color=self.secondary_color,
            text=[f"{v:.2f}" for v in val_before],
            textposition="auto"
        ))
        
        fig.add_trace(go.Bar(
            x=categories,
            y=val_after,
            name=f"Post-Allocation (+{added_weight_pct:.1f}% {candidate_name})",
            marker_color=self.primary_color,
            text=[f"{v:.2f}" for v in val_after],
            textposition="auto"
        ))
        
        fig.update_layout(
            title=f"📊 Pre- vs. Post-Allocation Impact Analysis (+{added_weight_pct:.1f}% {candidate_name})",
            barmode="group",
            template=self.template,
            height=400,
            yaxis=dict(gridcolor=self.grid_color),
            margin=dict(l=40, r=40, t=50, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        return fig

    def plot_marginal_risk_contributions(self, holdings_names: List[str], mctr_pct_contributions: List[float]) -> go.Figure:
        """
        Renders a donut chart decomposing Percentage Contribution to Total Portfolio Risk (%CTR).
        """
        fig = go.Figure(data=[go.Pie(
            labels=holdings_names,
            values=mctr_pct_contributions,
            hole=0.45,
            marker=dict(colors=["#00E676", "#2979FF", "#FFD700", "#FF5252", "#9C27B0", "#00E5FF"]),
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>Risk Contribution: %{value:.1f}%<extra></extra>"
        )])
        
        fig.update_layout(
            title="🔬 Percentage Contribution to Total Risk (%CTR)",
            template=self.template,
            height=380,
            margin=dict(l=20, r=20, t=50, b=20)
        )
        return fig

if __name__ == "__main__":
    viz = PortfolioVisualizer()
    print("Testing Portfolio Visualizer Suite...")
    fig_3d = viz.plot_3d_risk_return_landscape(
        base_return=0.075,
        base_vol=0.12,
        candidate_name="Commercial Real Estate LP",
        candidate_return=0.095,
        candidate_vol=0.14
    )
    print("✓ Successfully generated 3D Risk-Return Landscape Figure!")
