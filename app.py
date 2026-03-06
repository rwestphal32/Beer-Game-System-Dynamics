import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import graphviz

st.set_page_config(page_title="Supply Chain M&A Simulator", layout="wide")

st.title("🌐 Networked Supply Chain: M&A System Dynamics")
st.markdown("Simulating the financial and physical impacts of vertical integration. Watch how eliminating Information Delay destroys the Bullwhip Effect and alters ROIC.")

# --- SIDEBAR & STRATEGY ---
with st.sidebar:
    st.header("🏢 Corporate Strategy")
    st.info("You are W1: Central Network Distributing.")
    integrate_r1_r3 = st.toggle("Execute Vertical Integration (Acquire R1 & R3)", value=False, help="Spends £2.5M CAPEX to acquire the Grocery and Sports Bar. Eliminates info delay and captures retail margin.")
    
    st.markdown("---")
    st.header("💸 Financial Baselines")
    wholesale_margin = st.slider("Wholesale Margin %", 10, 30, 15) / 100.0
    retail_margin = 0.35 # We capture this if we integrate
    holding_cost_per_unit = st.number_input("Holding Cost/Unit/Wk (£)", value=0.50)
    base_capex = 5000000 # £5M Base Wholesale Infrastructure
    acquisition_capex = 2500000 # Cost to buy R1 & R3
    
    run_sim = st.button("🚀 Run 52-Week Simulation", type="primary", use_container_width=True)

# --- SIMULATION ENGINE ---
def run_system_dynamics(is_integrated):
    weeks = 52
    
    # 1. Generate Raw POS Demand (Foot Traffic at Retailers)
    np.random.seed(42) # Fixed seed for direct comparison
    time_idx = np.arange(weeks)
    
    # R1: Grocery (Steady, High Vol)
    pos_r1 = np.random.normal(1000, 50, weeks)
    # R2: Corner Store (Erratic, Low Vol)
    pos_r2 = np.random.normal(200, 80, weeks)
    pos_r2 = np.where(pos_r2 < 0, 0, pos_r2)
    # R3: Sports Bar (Spikes/Seasonality)
    pos_r3 = 500 + 300 * np.sin(2 * np.pi * time_idx / 12) + np.random.normal(0, 50, weeks)
    # R4: Craft Lounge (Trend-driven, rising)
    pos_r4 = 100 + 5 * time_idx + np.random.normal(0, 20, weeks)
    
    # 2. Retailer Ordering Logic (Information Delay)
    def calculate_orders(pos_demand, smoothing_factor=0.3):
        orders = np.zeros(weeks)
        forecast = pos_demand[0]
        for t in range(weeks):
            # Update forecast based on exponential smoothing
            forecast = smoothing_factor * pos_demand[t] + (1 - smoothing_factor) * forecast
            # Order = Forecast + replacing any safety stock dipped into
            orders[t] = forecast + np.random.normal(0, forecast*0.1) 
        return orders

    # If integrated, R1 and R3 pass exact POS data instantly (no smoothing/panic)
    ord_r1 = pos_r1 if is_integrated else calculate_orders(pos_r1, 0.2)
    ord_r2 = calculate_orders(pos_r2, 0.1) # Highly erratic ordering
    ord_r3 = pos_r3 if is_integrated else calculate_orders(pos_r3, 0.4)
    ord_r4 = calculate_orders(pos_r4, 0.3)
    
    total_wholesale_demand = ord_r1 + ord_r2 + ord_r3 + ord_r4
    
    # 3. Wholesaler Dynamics (Us)
    ws_inventory = np.zeros(weeks)
    ws_orders_to_mfg = np.zeros(weeks)
    ws_arrivals = np.zeros(weeks)
    
    starting_inv = 3000
    current_inv = starting_inv
    lead_time = 3 # Average physical delay from Manufacturers
    
    ws_forecast = total_wholesale_demand[0]
    
    for t in range(weeks):
        # 1. Receive goods from past orders
        if t >= lead_time:
            current_inv += ws_orders_to_mfg[t - lead_time]
            ws_arrivals[t] = ws_orders_to_mfg[t - lead_time]
            
        # 2. Fulfill Retailer Orders
        demand_today = total_wholesale_demand[t]
        fulfilled = min(current_inv, demand_today)
        current_inv -= fulfilled
        ws_inventory[t] = current_inv
        
        # 3. Forecast and place orders to Manufacturers
        ws_forecast = 0.4 * demand_today + 0.6 * ws_forecast
        target_inv = ws_forecast * (lead_time + 1) # Safety stock formula
        order_qty = max(0, target_inv - current_inv)
        ws_orders_to_mfg[t] = order_qty

    # 4. Financial Calculations
    unit_cogs = 10.0 # Blended cost from Manufacturers
    unit_wholesale_price = unit_cogs * (1 + wholesale_margin)
    unit_retail_price = unit_wholesale_price * (1 + retail_margin)
    
    # Revenue (Base wholesale rev + retail rev if integrated)
    rev_r1 = pos_r1 * unit_retail_price if is_integrated else ord_r1 * unit_wholesale_price
    rev_r2 = ord_r2 * unit_wholesale_price
    rev_r3 = pos_r3 * unit_retail_price if is_integrated else ord_r3 * unit_wholesale_price
    rev_r4 = ord_r4 * unit_wholesale_price
    
    total_revenue = np.sum(rev_r1 + rev_r2 + rev_r3 + rev_r4)
    total_cogs = np.sum(ws_arrivals) * unit_cogs
    total_holding_cost = np.sum(ws_inventory) * holding_cost_per_unit
    
    opex = 1000000 # Base £1M OPEX
    if is_integrated: opex += 500000 # Extra OPEX for running the retail stores
    
    ebitda = total_revenue - total_cogs - total_holding_cost - opex
    
    capex = base_capex + acquisition_capex if is_integrated else base_capex
    depreciation = capex / 10.0 # 10 year schedule
    nopat = (ebitda - depreciation) * (1 - 0.25)
    
    avg_working_capital = np.mean(ws_inventory) * unit_cogs
    roic = (nopat / (capex + avg_working_capital)) * 100

    metrics = {
        "Revenue": total_revenue, "COGS": total_cogs, "Holding Cost": total_holding_cost,
        "EBITDA": ebitda, "CAPEX": capex, "ROIC": roic, "Avg Inv": np.mean(ws_inventory)
    }
    
    df_flow = pd.DataFrame({
        "Week": time_idx,
        "Consumer_POS_Demand": pos_r1 + pos_r2 + pos_r3 + pos_r4,
        "Retailer_Orders_to_Us": total_wholesale_demand,
        "Our_Orders_to_Mfg": ws_orders_to_mfg,
        "Our_Inventory": ws_inventory
    })
    
    return metrics, df_flow

# --- DASHBOARD UI ---
if run_sim:
    metrics, df_flow = run_system_dynamics(integrate_r1_r3)
    
    t1, t2, t3 = st.tabs(["💰 Financial Executive Summary", "📦 Flow of Goods (Bullwhip)", "🗺️ Network Map"])
    
    with t1:
        st.subheader("P&L and Returns Profile (52-Week)")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Revenue", f"£{metrics['Revenue']:,.0f}")
        c2.metric("EBITDA", f"£{metrics['EBITDA']:,.0f}")
        c3.metric("Capital Deployed (CAPEX)", f"£{metrics['CAPEX']:,.0f}")
        c4.metric("ROIC (Annualized)", f"{metrics['ROIC']:.1f}%")
        
        st.markdown("---")
        st.markdown("### Financial Mechanics")
        st.markdown(f"**Total COGS:** £{metrics['COGS']:,.0f} \n\n**Total Inventory Holding Costs:** £{metrics['Holding Cost']:,.0f} \n\n**Average Working Capital Units:** {metrics['Avg Inv']:,.0f} pallets")
        
    with t2:
        st.subheader("System Dynamics: The Bullwhip Effect")
        st.markdown("Notice the variance spread. Consumer demand is relatively smooth, but delayed information causes our orders to the manufacturers to swing violently.")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_flow["Week"], y=df_flow["Consumer_POS_Demand"], name="Consumer Foot Traffic (Actual Need)", line=dict(color='green', width=2)))
        fig.add_trace(go.Scatter(x=df_flow["Week"], y=df_flow["Retailer_Orders_to_Us"], name="Retailer Orders (Distorted)", line=dict(color='orange', width=2, dash='dash')))
        fig.add_trace(go.Scatter(x=df_flow["Week"], y=df_flow["Our_Orders_to_Mfg"], name="Our Orders to Mfg (Bullwhip)", line=dict(color='red', width=3)))
        
        fig.update_layout(title="Demand Amplification Across Echelons", xaxis_title="Week", yaxis_title="Pallets")
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Wholesale Inventory Depletion")
        fig2 = px.area(df_flow, x="Week", y="Our_Inventory", title="Wholesale Warehouse Stock Levels")
        st.plotly_chart(fig2, use_container_width=True)

    with t3:
        st.subheader("Supply Chain Network Topology")
        dot = graphviz.Digraph(node_attr={'shape': 'box', 'style': 'filled', 'fontname': 'Helvetica'})
        dot.attr(rankdir='LR')
        
        # Mfgs
        with dot.subgraph(name='cluster_mfg') as c:
            c.attr(label='Tier 1: Manufacturers', style='dashed', color='gray')
            c.node('M1', 'M1: MacroBrew Corp\n(High Vol, Low Var)', color='#cce5ff')
            c.node('M2', 'M2: Apex Craftworks\n(Med Vol, High Var)', color='#cce5ff')
            
        # Us
        with dot.subgraph(name='cluster_ws') as c:
            c.attr(label='Tier 2: Wholesale', style='dashed', color='gray')
            c.node('W1', 'W1: Central Network (US)\nMaster Inventory', color='#fff3cd', shape='cylinder')
            
        # Retailers
        with dot.subgraph(name='cluster_ret') as c:
            c.attr(label='Tier 3: Retailers', style='dashed', color='gray')
            color_r1_r3 = '#d4edda' if integrate_r1_r3 else '#e2e3e5'
            
            c.node('R1', 'R1: Grocery (Steady)\n' + ('[INTEGRATED]' if integrate_r1_r3 else '[SILOED]'), color=color_r1_r3)
            c.node('R2', 'R2: Corner Store (Erratic)\n[SILOED]', color='#e2e3e5')
            c.node('R3', 'R3: Sports Bar (Spikes)\n' + ('[INTEGRATED]' if integrate_r1_r3 else '[SILOED]'), color=color_r1_r3)
            c.node('R4', 'R4: Craft Lounge (Trend)\n[SILOED]', color='#e2e3e5')

        # Edges
        dot.edge('M1', 'W1', label=' 2 Wk Delay')
        dot.edge('M2', 'W1', label=' 4 Wk Delay')
        dot.edge('W1', 'R1', color='green' if integrate_r1_r3 else 'black')
        dot.edge('W1', 'R2')
        dot.edge('W1', 'R3', color='green' if integrate_r1_r3 else 'black')
        dot.edge('W1', 'R4')
        
        st.graphviz_chart(dot, use_container_width=True)
