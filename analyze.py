"""
Analysis & charts for the Consumer/Company economic simulation (main.py).

Usage (same as before):
    consumer_df = model.datacollector.get_agenttype_vars_dataframe(Consumer)
    company_df  = model.datacollector.get_agenttype_vars_dataframe(Company)   # (Step, AgentID) or (Step, Name) index, both work
    companies   = model.agents.select(agent_type=Company)

    build_report(consumer_df, company_df, companies, out_html="report.html")

WHAT THE NOISE CHARTS NEED
    The datacollector has to record the shocked attributes, so the model needs
        Company:  "MarginalCost": "marginal_cost"
        Consumer: "Essentials":   "essentials"
    in its agenttype_reporters. Without them the report still builds, it just
    skips the noise charts.

HOW A SHOCK IS DETECTED
    Step 0 is collected when the model is created, before any noise, so a
    company's / consumer's value at step 0 is its "normal" value. Every stretch
    of ticks where the value differs from that is one shock. That means the
    detection reads the data only, the model doesn't have to log anything.
    (If you later add permanent changes to those attributes, e.g. R&D lowering
    marginal_cost, they would be read as a never-ending shock.)

    The datacollector runs before end_noise/deploy_noise inside step(), so a shock
    deployed at the end of tick t shows up in the data from tick t+1 to tick
    t+duration. Shaded bands in the charts cover exactly those ticks.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.colors import qualitative
from plotly.subplots import make_subplots

PALETTE = qualitative.Plotly
PHASE_COLORS = {"before": "#9aa0a6", "during": "#e4572e", "after": "#4c9f70"}


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _to_float(series: pd.Series) -> pd.Series:
    """values can come back as sympy Float objects (dtype=object): coerce to python floats."""
    return series.apply(lambda v: float(v) if v is not None else np.nan)


def _company_market_map(companies) -> dict:
    return {c.name: c.market for c in companies}


def _color_map(companies) -> dict:
    """one fixed color per company, so a company looks the same in every chart."""
    names = sorted(c.name for c in companies)
    return {name: PALETTE[i % len(PALETTE)] for i, name in enumerate(names)}


def _prep_company_df(company_df: pd.DataFrame, companies) -> pd.DataFrame:
    df = company_df.reset_index()  # works for a (Step, AgentID) and for a (Step, Name) index
    for col in ("Price", "Wealth", "MarginalCost"):
        if col in df.columns:
            df[col] = _to_float(df[col])
    df["Step"] = df["Step"].astype(int)
    df["Market"] = df["Name"].map(_company_market_map(companies))
    return df


def _prep_consumer_df(consumer_df: pd.DataFrame) -> pd.DataFrame:
    df = consumer_df.reset_index()
    for col in ("Wealth", "Savings", "Salary", "MPC", "LiveUtile", "Essentials"):
        if col in df.columns:
            df[col] = _to_float(df[col])
    df["Step"] = df["Step"].astype(int)
    return df


def combine_transactions(companies) -> pd.DataFrame:
    """stitches every company's `.transactions` into one dataframe, tagged with company and market."""
    frames = []
    for c in companies:
        if c.transactions.empty:
            continue
        t = c.transactions.copy()
        t["price"] = _to_float(t["price"])
        t["time"] = t["time"].astype(int)
        t["company"] = c.name
        t["market"] = c.market
        frames.append(t)
    if not frames:
        return pd.DataFrame(columns=["consumer_id", "price", "time", "company", "market"])
    return pd.concat(frames, ignore_index=True)


def _markets_in(df: pd.DataFrame, market_col: str = "Market") -> list:
    return sorted(df[market_col].dropna().unique())


# ----------------------------------------------------------------------
# Shock detection (reads the noise straight out of the data)
# ----------------------------------------------------------------------

def find_cost_shocks(company_df: pd.DataFrame, companies, tol: float = 1e-6) -> pd.DataFrame:
    """one row per cost shock: Name, Market, start, end (inclusive ticks), base, shocked, pct, ongoing."""
    cols = ["Name", "Market", "start", "end", "base", "shocked", "pct", "ongoing"]
    df = _prep_company_df(company_df, companies)
    if "MarginalCost" not in df.columns:
        return pd.DataFrame(columns=cols)

    rows = []
    for name, g in df.sort_values("Step").groupby("Name"):
        base = g["MarginalCost"].iloc[0]  # step 0 = before any noise
        market = g["Market"].iloc[0]
        last_step = int(g["Step"].iloc[-1])

        runs, run = [], None  # run = [start, end, shocked value]
        for step, value in zip(g["Step"], g["MarginalCost"]):
            under_shock = abs(value - base) > tol
            if under_shock and run is not None and abs(value - run[2]) <= tol:
                run[1] = int(step)  # the same shock goes on
                continue
            if run is not None:  # the previous shock is over (or another one starts right away)
                runs.append(run)
                run = None
            if under_shock:
                run = [int(step), int(step), value]
        if run is not None:
            runs.append(run)

        for start, end, value in runs:
            rows.append({"Name": name, "Market": market, "start": start, "end": end, "base": base,
                         "shocked": value, "pct": (value / base - 1) * 100, "ongoing": end == last_step})

    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols).sort_values(["start", "Name"]).reset_index(drop=True)


def shock_event_metrics(shocks: pd.DataFrame, company_df: pd.DataFrame, tx_df: pd.DataFrame, companies) -> pd.DataFrame:
    """for every shock: the shocked company's units sold / profit / price, and its rival's price,
    averaged per tick in three windows of the same length as the shock: before, during, after.
    (a window can overlap another shock of the same company; windows are clipped to the run.)

    profit per tick = change in the company's wealth, because the only thing that moves company
    wealth in the model is  +price -marginal_cost  on every sale."""
    df = _prep_company_df(company_df, companies).sort_values(["Name", "Step"])
    df["Profit"] = df.groupby("Name")["Wealth"].diff()
    last = int(df["Step"].max())
    ticks = pd.RangeIndex(1, last + 1)
    market_of = _company_market_map(companies)

    units = {n: g.groupby("time").size().reindex(ticks, fill_value=0) for n, g in tx_df.groupby("company")}
    series = {}
    for name, g in df.groupby("Name"):
        g = g.set_index("Step").reindex(ticks)
        series[name] = {"price": g["Price"], "profit": g["Profit"],
                        "units": units.get(name, pd.Series(0, index=ticks))}

    def window(a, b):
        return ticks[(ticks >= a) & (ticks <= b)]

    def avg(s, w):
        return float(s.loc[w].mean()) if len(w) else np.nan

    rows = []
    for ev in shocks.itertuples():
        length = ev.end - ev.start + 1
        wins = {"before": window(ev.start - length, ev.start - 1),
                "during": window(ev.start, ev.end),
                "after": window(ev.end + 1, ev.end + length)}
        rivals = [n for n, m in market_of.items() if m == ev.Market and n != ev.Name]
        row = {"Company": ev.Name, "Market": ev.Market, "label": f"{ev.Name} {ev.start}–{ev.end}",
               "start": ev.start, "end": ev.end, "ticks": length, "ongoing": ev.ongoing, "cost_pct": ev.pct}
        for phase, w in wins.items():
            row[f"price_{phase}"] = avg(series[ev.Name]["price"], w)
            row[f"units_{phase}"] = avg(series[ev.Name]["units"], w)
            row[f"profit_{phase}"] = avg(series[ev.Name]["profit"], w)
            rival_prices = [avg(series[r]["price"], w) for r in rivals]
            rival_prices = [p for p in rival_prices if not np.isnan(p)]
            row[f"rival_{phase}"] = float(np.mean(rival_prices)) if rival_prices else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def _shade(fig, shocks, market, colors, row=None, label=False):
    """paints a band over every cost shock of the companies of `market`."""
    if shocks is None or shocks.empty:
        return
    for ev in shocks[shocks["Market"] == market].itertuples():
        kwargs = {}
        if label:
            kwargs = dict(annotation_text=f"{ev.Name} {ev.pct:+.0f}%", annotation_position="top left",
                          annotation_font_size=9)
        fig.add_vrect(x0=ev.start - 0.5, x1=ev.end + 0.5, fillcolor=colors.get(ev.Name, "grey"),
                      opacity=0.15, line_width=0, layer="below",
                      **({"row": row, "col": 1} if row else {}), **kwargs)


# ----------------------------------------------------------------------
# Company charts (one subplot per market, shocks shaded)
# ----------------------------------------------------------------------

def fig_price_vs_cost(company_df, companies, shocks=None, colors=None) -> go.Figure:
    """price (solid) against marginal cost (dotted) for every company. both only change at certain
    ticks, so they are drawn as steps. the gap between the lines is the margin per sale: when a
    shock lifts the cost above the price the company sells at a loss until it reprices (every 7 ticks)."""
    colors = colors or _color_map(companies)
    df = _prep_company_df(company_df, companies)
    df = df[df["Step"] >= 1]  # step 0 is the starting state, prices aren't set yet
    markets = _markets_in(df)
    fig = make_subplots(rows=len(markets), cols=1, subplot_titles=[f"Market: {m}" for m in markets])
    for row, market in enumerate(markets, start=1):
        for name, g in df[df["Market"] == market].groupby("Name"):
            g = g.sort_values("Step")
            fig.add_trace(go.Scatter(x=g["Step"], y=g["Price"], mode="lines", name=f"{name} price",
                                     legendgroup=name, line=dict(color=colors[name], width=2.5, shape="hv")),
                          row=row, col=1)
            if "MarginalCost" in g.columns:
                fig.add_trace(go.Scatter(x=g["Step"], y=g["MarginalCost"], mode="lines", name=f"{name} marginal cost",
                                         legendgroup=name, line=dict(color=colors[name], width=1.5, dash="dot", shape="hv")),
                              row=row, col=1)
        _shade(fig, shocks, market, colors, row=row, label=True)
        fig.update_yaxes(title_text="$", row=row, col=1)
    fig.update_xaxes(title_text="Step (day)", row=len(markets), col=1)
    fig.update_layout(title="Price vs marginal cost (shaded = cost shock)", template="plotly_white",
                      height=340 * len(markets))
    return fig


def fig_profit_per_tick(company_df, companies, shocks=None, colors=None) -> go.Figure:
    """profit per tick = change of company wealth (the only thing that moves it is +price -marginal cost per sale).
    negative bars are ticks where the company lost money."""
    colors = colors or _color_map(companies)
    df = _prep_company_df(company_df, companies).sort_values(["Name", "Step"])
    df["Profit"] = df.groupby("Name")["Wealth"].diff()
    df = df[df["Step"] >= 1]
    markets = _markets_in(df)
    fig = make_subplots(rows=len(markets), cols=1, subplot_titles=[f"Market: {m}" for m in markets])
    for row, market in enumerate(markets, start=1):
        for name, g in df[df["Market"] == market].groupby("Name"):
            fig.add_trace(go.Bar(x=g["Step"], y=g["Profit"], name=name, legendgroup=name,
                                 marker_color=colors[name]), row=row, col=1)
        _shade(fig, shocks, market, colors, row=row)
        fig.update_yaxes(title_text="Profit ($)", row=row, col=1)
    fig.update_xaxes(title_text="Step (day)", row=len(markets), col=1)
    fig.update_layout(title="Profit per tick (shaded = cost shock)", barmode="group",
                      template="plotly_white", height=320 * len(markets))
    return fig


def fig_wealth_by_market(company_df, companies, shocks=None, colors=None) -> go.Figure:
    colors = colors or _color_map(companies)
    df = _prep_company_df(company_df, companies)
    markets = _markets_in(df)
    fig = make_subplots(rows=len(markets), cols=1, subplot_titles=[f"Market: {m}" for m in markets])
    for row, market in enumerate(markets, start=1):
        for name, g in df[df["Market"] == market].groupby("Name"):
            fig.add_trace(go.Scatter(x=g["Step"], y=g["Wealth"], mode="lines", name=name, legendgroup=name,
                                     line=dict(color=colors[name])), row=row, col=1)
        _shade(fig, shocks, market, colors, row=row)
        fig.update_yaxes(title_text="Wealth ($)", row=row, col=1)
    fig.update_xaxes(title_text="Step (day)", row=len(markets), col=1)
    fig.update_layout(title="Company wealth over time (shaded = cost shock)", template="plotly_white",
                      height=320 * len(markets))
    return fig


# ----------------------------------------------------------------------
# Shock impact: before / during / after
# ----------------------------------------------------------------------

def _fmt(x, nd=1):
    return "–" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:,.{nd}f}"


def fig_shock_table(metrics: pd.DataFrame) -> go.Figure:
    """one line per cost shock with the numbers behind the charts."""
    m = metrics
    cols = {
        "Company": list(m["Company"]),
        "Market": list(m["Market"]),
        "Ticks": [f"{r.start}–{r.end}" + ("*" if r.ongoing else "") for r in m.itertuples()],
        "Cost change": [f"{x:+.0f}%" for x in m["cost_pct"]],
        "Own price (before → during)": [f"{_fmt(r.price_before)} → {_fmt(r.price_during)}" for r in m.itertuples()],
        "Rival price (before → during)": [f"{_fmt(r.rival_before)} → {_fmt(r.rival_during)}" for r in m.itertuples()],
        "Units/tick (before → during → after)": [f"{_fmt(r.units_before)} → {_fmt(r.units_during)} → {_fmt(r.units_after)}" for r in m.itertuples()],
        "Profit/tick (before → during → after)": [f"{_fmt(r.profit_before)} → {_fmt(r.profit_during)} → {_fmt(r.profit_after)}" for r in m.itertuples()],
    }
    fig = go.Figure(go.Table(
        header=dict(values=list(cols), fill_color="#2b2d42", font=dict(color="white"), align="left"),
        cells=dict(values=list(cols.values()), align="left", fill_color="#f4f4f6", height=26),
    ))
    fig.update_layout(title="Cost shocks: what happened  (* = still running when the data ends)",
                      height=120 + 28 * len(m), margin=dict(t=60, b=10))
    return fig


def fig_shock_impact(metrics: pd.DataFrame) -> go.Figure:
    """for every cost shock: the same company in the equally long windows before, during and after it."""
    fig = make_subplots(rows=1, cols=3, subplot_titles=("Units sold per tick", "Profit per tick ($)", "Own price ($)"))
    for col, key in enumerate(("units", "profit", "price"), start=1):
        for phase in ("before", "during", "after"):
            fig.add_trace(go.Bar(x=metrics["label"], y=metrics[f"{key}_{phase}"], name=phase,
                                 marker_color=PHASE_COLORS[phase], legendgroup=phase, showlegend=(col == 1)),
                          row=1, col=col)
    fig.update_layout(title="Impact of each cost shock: before vs during vs after", barmode="group",
                      template="plotly_white", height=460)
    fig.update_xaxes(tickangle=-45)
    return fig


# ----------------------------------------------------------------------
# Transaction-level charts
# ----------------------------------------------------------------------

def fig_revenue_per_tick(tx_df, shocks=None, colors=None) -> go.Figure:
    markets = sorted(tx_df["market"].dropna().unique())
    fig = make_subplots(rows=len(markets), cols=1, subplot_titles=[f"Market: {m}" for m in markets])
    for row, market in enumerate(markets, start=1):
        rev = tx_df[tx_df["market"] == market].groupby(["time", "company"])["price"].sum().reset_index(name="revenue")
        for name, g in rev.groupby("company"):
            fig.add_trace(go.Bar(x=g["time"], y=g["revenue"], name=name, legendgroup=name,
                                 marker_color=(colors or {}).get(name)), row=row, col=1)
        _shade(fig, shocks, market, colors or {}, row=row)
        fig.update_yaxes(title_text="Revenue ($)", row=row, col=1)
    fig.update_xaxes(title_text="Step (day)", row=len(markets), col=1)
    fig.update_layout(title="Revenue per tick (price x units sold; costs not subtracted)", barmode="group",
                      template="plotly_white", height=320 * len(markets))
    return fig


def fig_cumulative_revenue_by_market(tx_df, shocks=None, colors=None) -> go.Figure:
    markets = sorted(tx_df["market"].dropna().unique())
    fig = make_subplots(rows=len(markets), cols=1, subplot_titles=[f"Market: {m}" for m in markets])
    for row, market in enumerate(markets, start=1):
        rev = tx_df[tx_df["market"] == market].groupby(["time", "company"])["price"].sum().reset_index(name="revenue")
        for name, g in rev.groupby("company"):
            g = g.sort_values("time")
            fig.add_trace(go.Scatter(x=g["time"], y=g["revenue"].cumsum(), mode="lines", name=name,
                                     legendgroup=name, line=dict(color=(colors or {}).get(name))), row=row, col=1)
        _shade(fig, shocks, market, colors or {}, row=row)
        fig.update_yaxes(title_text="Cumulative revenue ($)", row=row, col=1)
    fig.update_xaxes(title_text="Step (day)", row=len(markets), col=1)
    fig.update_layout(title="Cumulative revenue (shaded = cost shock)", template="plotly_white",
                      height=320 * len(markets))
    return fig


def fig_units_sold_over_time(tx_df, shocks=None, colors=None) -> go.Figure:
    markets = sorted(tx_df["market"].dropna().unique())
    fig = make_subplots(rows=len(markets), cols=1, subplot_titles=[f"Market: {m}" for m in markets])
    for row, market in enumerate(markets, start=1):
        counts = tx_df[tx_df["market"] == market].groupby(["time", "company"]).size().reset_index(name="units")
        for name, g in counts.groupby("company"):
            fig.add_trace(go.Scatter(x=g["time"], y=g["units"], mode="lines+markers", name=name,
                                     legendgroup=name, line=dict(color=(colors or {}).get(name))), row=row, col=1)
        _shade(fig, shocks, market, colors or {}, row=row)
        fig.update_yaxes(title_text="Units sold", row=row, col=1)
    fig.update_xaxes(title_text="Step (day)", row=len(markets), col=1)
    fig.update_layout(title="Units sold per tick (shaded = cost shock)", template="plotly_white",
                      height=320 * len(markets))
    return fig


def fig_market_share_over_time(tx_df, shocks=None, colors=None, window: int = 4) -> go.Figure:
    """rolling share of the units sold, one line per company (lines instead of stacked areas so the
    shock bands stay visible)."""
    markets = sorted(tx_df["market"].dropna().unique())
    fig = make_subplots(rows=len(markets), cols=1, subplot_titles=[f"Market: {m}" for m in markets])
    for row, market in enumerate(markets, start=1):
        counts = tx_df[tx_df["market"] == market].groupby(["time", "company"]).size().unstack(fill_value=0)
        share = (counts.div(counts.sum(axis=1), axis=0) * 100).rolling(window, min_periods=1).mean()
        for company in share.columns:
            fig.add_trace(go.Scatter(x=share.index, y=share[company], mode="lines", name=company,
                                     legendgroup=company, line=dict(color=(colors or {}).get(company))), row=row, col=1)
        _shade(fig, shocks, market, colors or {}, row=row)
        fig.update_yaxes(title_text="Share (%)", range=[0, 100], row=row, col=1)
    fig.update_xaxes(title_text="Step (day)", row=len(markets), col=1)
    fig.update_layout(title=f"Market share ({window}-tick rolling average, shaded = cost shock)",
                      template="plotly_white", height=320 * len(markets))
    return fig


def fig_consumer_loyalty(tx_df) -> go.Figure:
    """per market: % of consumers that never switched company."""
    rows = []
    for market in sorted(tx_df["market"].dropna().unique()):
        sub = tx_df[tx_df["market"] == market]
        for consumer_id, g in sub.groupby("consumer_id"):
            rows.append({"market": market, "loyal": g["company"].nunique() == 1})
    summary = pd.DataFrame(rows).groupby("market")["loyal"].mean().reset_index()
    fig = go.Figure(go.Bar(x=summary["market"], y=summary["loyal"] * 100))
    fig.update_layout(title="Consumers that never switched company", xaxis_title="Market",
                      yaxis_title="% of consumers", template="plotly_white", yaxis_range=[0, 100])
    return fig


# ----------------------------------------------------------------------
# Consumer charts
# ----------------------------------------------------------------------

def fig_avg_wealth_and_utile(consumer_df) -> go.Figure:
    df = _prep_consumer_df(consumer_df)
    agg = df.groupby("Step").agg(AvgWealth=("Wealth", "mean"), AvgUtile=("LiveUtile", "mean")).reset_index()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=agg["Step"], y=agg["AvgWealth"], name="Avg wealth", line=dict(color="seagreen")),
                  secondary_y=False)
    fig.add_trace(go.Scatter(x=agg["Step"], y=agg["AvgUtile"], name="Avg live utility", line=dict(color="darkorange")),
                  secondary_y=True)
    fig.update_layout(title="Average consumer wealth vs average utility", xaxis_title="Step (day)",
                      template="plotly_white")
    fig.update_yaxes(title_text="Avg wealth ($)", secondary_y=False)
    fig.update_yaxes(title_text="Avg live utility", secondary_y=True)
    return fig


def fig_essentials_noise_map(consumer_df, payday_every: int = 30):
    """heatmap of the essentials shocks: one row per consumer that was ever hit, one column per tick,
    colored by how far essentials are from the normal value. the dashed lines are paydays: essentials
    only matter on a payday (take-home = salary - essentials), so a shock that doesn't cross one
    changes nothing. returns None when there were no shocks / no Essentials column."""
    df = _prep_consumer_df(consumer_df)
    if "Essentials" not in df.columns:
        return None
    df = df.sort_values(["AgentID", "Step"])
    base = df.groupby("AgentID")["Essentials"].transform("first")
    df["pct"] = (df["Essentials"] / base - 1) * 100
    df.loc[df["pct"].abs() < 1e-4, "pct"] = 0.0
    grid = df.pivot(index="AgentID", columns="Step", values="pct")
    grid = grid[(grid.abs() > 0).any(axis=1)]
    if grid.empty:
        return None
    zmax = max(float(grid.abs().max().max()), 1.0)
    fig = go.Figure(go.Heatmap(
        z=grid.values, x=list(grid.columns), y=[f"Consumer {int(i)}" for i in grid.index],
        colorscale="RdBu_r", zmid=0, zmin=-zmax, zmax=zmax,
        colorbar=dict(title="Essentials vs normal (%)"),
        hovertemplate="%{y}<br>tick %{x}<br>%{z:+.1f}%<extra></extra>",
    ))
    for tick in [s for s in grid.columns if s > 0 and s % payday_every == 0]:
        fig.add_vline(x=tick, line_dash="dash", line_color="black", opacity=0.6,
                      annotation_text="payday", annotation_position="top", annotation_font_size=9)
    fig.update_layout(title="Essentials shocks per consumer (red = more expensive than normal, dashed = payday)",
                      xaxis_title="Step (day)", template="plotly_white",
                      height=140 + 40 * len(grid))
    return fig


# ----------------------------------------------------------------------
# Full report
# ----------------------------------------------------------------------

def build_figures(consumer_df, company_df, companies) -> list:
    """all the report charts as a list of plotly figures (use this one in streamlit: st.plotly_chart(fig)).
    `companies` = model.agents.select(agent_type=Company)  (market mapping + transactions)."""
    companies = list(companies)
    colors = _color_map(companies)
    tx_df = combine_transactions(companies)
    shocks = find_cost_shocks(company_df, companies)
    metrics = shock_event_metrics(shocks, company_df, tx_df, companies) if (not shocks.empty and not tx_df.empty) else None

    figs = []
    if metrics is not None:
        figs.append(fig_shock_table(metrics))
    figs.append(fig_price_vs_cost(company_df, companies, shocks, colors))
    figs.append(fig_profit_per_tick(company_df, companies, shocks, colors))
    if metrics is not None:
        figs.append(fig_shock_impact(metrics))
    figs.append(fig_wealth_by_market(company_df, companies, shocks, colors))
    if not tx_df.empty:
        figs += [
            fig_revenue_per_tick(tx_df, shocks, colors),
            fig_cumulative_revenue_by_market(tx_df, shocks, colors),
            fig_units_sold_over_time(tx_df, shocks, colors),
            fig_market_share_over_time(tx_df, shocks, colors),
            fig_consumer_loyalty(tx_df),
        ]
    figs.append(fig_avg_wealth_and_utile(consumer_df))
    noise_map = fig_essentials_noise_map(consumer_df)
    if noise_map is not None:
        figs.append(noise_map)
    return figs


def build_report(consumer_df, company_df, companies, out_html: str = "report.html") -> str:
    """same charts written into one html file. returns the file name."""
    figs = build_figures(consumer_df, company_df, companies)

    with open(out_html, "w", encoding="utf-8") as f:
        f.write("<html><head><title>Simulation Report</title></head><body style='font-family:sans-serif'>\n")
        f.write("<h1>Economic Simulation Report</h1>\n")
        f.write("<p>Shaded bands = a company's marginal cost was shocked (noise). "
                "Every company keeps its color in every chart.</p>\n")
        for i, fig in enumerate(figs):
            f.write(fig.to_html(full_html=False, include_plotlyjs="cdn" if i == 0 else False))
            f.write("<hr>\n")
        f.write("</body></html>")
    return out_html