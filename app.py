import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import graphviz

st.set_page_config(page_title="Supply Chain M&A Simulator", layout="wide")

st.title("🌐 Networked Supply Chain: M&A System Dynamics")
st.markdown("Simulating the financial and physical impacts of vertical integration across the US Three-Tier System.")

# --- SIDEBAR & STRATEGY ---
with st.sidebar:
    st.header("🏢 Corporate Strategy (M&A)")
    st.info("You are W1: Central Network Distributing.")
    integrate_r1_r3 = st.toggle("⬇️ Downstream M&A (Acquire R1 & R3)", value=False, help="Spends £2.5M to acquire Retailers. Captures 35% retail margin and eliminates Info Delay.")
    integrate_m2 = st.toggle("⬆️ Upstream M&A (Acquire M2: Apex Craft)", value=False, help="Spends £1.5M to acquire Craft Brewer. Drops COGS to raw brewing cost for M2 volume.")
    
    st.markdown("---")
    st.header("💸 Unit Economics & Logistics")
    wholesale_margin = st.slider("Wholesale Margin %", 10, 30, 15) / 100.0
    retail_margin = 0.35 
    mfg_cogs = 150.0 # Base cost to buy from Mfg
    raw_brewing_cost = 80.0 # Cost if we own the brewery (M2)
    logistics_cost = st.number_input("Logistics Cost/Pallet (£)", value=15.0)
    holding_cost_per_unit = st.number_input("Holding Cost/Pallet/Wk (£)", value=0.50)
    
    base_capex = 5000000 
    
    run_sim = st.button("🚀 Run 52-Week Simulation", type="primary", use_container_width=True)

# --- SIMULATION ENGINE ---
def run_system_dynamics(int_down, int_up):
    weeks = 52
    np.random.seed(42) 
    time_idx = np.arange(weeks)
    
    # 1. Generate Raw POS Demand (Foot Traffic at Retailers)
    pos_r1 = np.random.normal(1000, 50, weeks) # R1: Grocery 
    pos_r2 = np.random.normal(200, 80, weeks)  # R2: Corner Store
    pos_r2 = np.where(pos_r2 < 0, 0, pos_r2)
    pos_r3 = 500 + 300 * np.sin(2 * np.pi * time_idx / 12) + np.random.normal(0, 50, weeks) # R3: Sports Bar
    pos_r4 = 100 + 5 * time_idx + np.random.normal(0, 20, weeks) # R4: Craft Lounge
    
    # 2. Retailer Ordering Logic
    def calculate_orders(pos_demand, smoothing_factor=0.3):
        orders = np.zeros(weeks)
        forecast = pos_demand[0]
        for t in range(weeks):
            forecast = smoothing_factor * pos_demand[t] + (1 - smoothing_factor) * forecast
            orders[t] = forecast + np.random.normal(0, forecast*0.1) 
        return orders

    ord_r1 = pos_r1 if int_down else calculate_orders(pos_r1, 0.2)
    ord_r2 = calculate_orders(pos_r2, 0.1) 
    ord_r3 = pos_r3 if int_down else calculate_orders(pos_r3, 0.4)
    ord_r4 = calculate_orders(pos_r4, 0.3)
    
    total_wholesale_demand = ord_r1 + ord_r2 + ord_r3 + ord_r4
    
    # 3. Wholesaler Dynamics (Us)
    ws_inventory = np.zeros(weeks)
    ws_orders_to_mfg = np.zeros(weeks)
    ws_arrivals = np.zeros(weeks)
    
    current_inv = 3000
    lead_time = 3 
    ws_forecast = total_wholesale_demand[0]
    
    for t in range(weeks):
        if t >= lead_time:
            current_inv += ws_orders_to_mfg[t - lead_time]
            ws_arrivals[t] = ws_orders_to_mfg[t - lead_time]
            
        demand_today = total_wholesale_demand[t]
        fulfilled = min(current_inv, demand_today)
        current_inv -= fulfilled
        ws_inventory[t] = current_inv
        
        # Bullwhip Fix: If integrated, we trust the data and use a much smoother rolling average (0.1) instead of chasing noise (0.4)
        alpha = 0.1 if int_down else 0.4
        ws_forecast = alpha * demand_today + (1 - alpha) * ws_forecast
        
        target_inv = ws_forecast * (lead_time + 1) 
        ws_orders_to_mfg[t] = max(0, target_inv - current_inv)

    # 4. Unit Economics & Financial Calculations
    # Assuming M2 (Apex) makes up roughly 30% of total volume
    m1_ratio = 0.70
    m2_ratio = 0.30
    
    # Calculate Landed Cost based on Upstream Integration
    blended_cogs = (m1_ratio * mfg_cogs) + (m2_ratio * (raw_brewing_cost if int_up else mfg_cogs))
    landed_cost = blended_cogs + logistics_cost
    
    unit_wholesale_price = landed_cost * (1 + wholesale_margin)
    unit_retail_price = unit_wholesale_price * (1 + retail_margin)
    
    # Revenue Generation
    rev_r1 = pos_r1 * unit_retail_price if int_down else ord_r1 * unit_wholesale_price
    rev_r2 = ord_r2 * unit_wholesale_price
    rev_r3 = pos_r3 * unit_retail_price if int_down else ord_r3 * unit_wholesale_price
    rev_r4 = ord_r4 * unit_wholesale_price
    
    total_revenue = np.sum(rev_r1 + rev_r2 + rev_r3 + rev_r4)
    total_cogs = np.sum(ws_arrivals) * landed_cost
    gross_profit = total_revenue - total_cogs
    total_holding_cost = np.sum(ws_inventory) * holding_cost_per_unit
    
    opex = 1000000 
    if int_down: opex += 500000 
    if int_up: opex += 200000 
    
    ebitda = gross_profit - total_holding_cost - opex
    
    capex = base_capex
    if int_down: capex += 2500000
    if int_up: capex += 1500000
    
    depreciation = capex / 10.0 
    nopat = (ebitda - depreciation) * (1 - 0.25)
    
    avg_working_capital = np.mean(ws_inventory) * landed_cost
    roic = (nopat / (capex + avg_working_capital)) * 100

    unit_econ = {
        "Blended Purchase COGS": blended_cogs,
        "Logistics Cost": logistics_cost,
        "Total Landed Cost": landed_cost,
        "Wholesale Price to Retail": unit_wholesale_price,
        "Retail Price to Consumer": unit_retail_price
    }

    metrics = {
        "Revenue": total_revenue, "COGS": total_cogs, "Gross Profit": gross_profit, 
        "Holding Cost": total_holding_cost, "OPEX": opex, "EBITDA": ebitda, 
        "Depreciation": depreciation, "NOPAT": nopat,
        "CAPEX": capex, "ROIC": roic, "Avg Inv": np.mean(ws_inventory)
    }
    
    df_flow = pd.DataFrame({
        "Week": time_idx,
        "R1_Grocery_Demand": pos_r1,
        "R2_CornerStore_Demand": pos_r2,
        "R3_SportsBar_Demand": pos_r3,
        "R4_CraftLounge_Demand": pos_r4,
        "Total_Consumer_POS": pos_r1 + pos_r2 + pos_r3 + pos_r4,
        "Retailer_Orders_to_Us": total_wholesale_demand,
        "Our_Orders_to_Mfg": ws_orders_to_mfg,
        "Our_Inventory": ws_inventory
    })
    
    return metrics, df_flow, unit_econ

# --- DASHBOARD UI ---
if run_sim:
    metrics, df_flow, unit_econ = run_system_dynamics(integrate_r1_r3, integrate_m2)
    
    t1, t2, t3, t4 = st.tabs(["💰 Financials & Unit Economics", "🗺️ Network Map", "📦 Flow of Goods", "📊 Ordering Drivers"])
    
    with t1:
        st.subheader("P&L and Returns Profile (52-Week)")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Revenue", f"£{metrics['Revenue']:,.0f}")
        c2.metric("EBITDA", f"£{metrics['EBITDA']:,.0f}")
        c3.metric("Capital Deployed", f"£{metrics['CAPEX']:,.0f}")
        c4.metric("ROIC (Annualized)", f"{metrics['ROIC']:.1f}%")
        
        c_left, c_right = st.columns(2)
        with c_left:
            st.markdown("### 🔍 Unit Economics (Per Pallet)")
            unit_df = pd.DataFrame(list(unit_econ.items()), columns=["Metric", "Value (£)"])
            unit_df["Value (£)"] = unit_df["Value (£)"].map("£{:,.2f}".format)
            st.dataframe(unit_df, hide_index=True, use_container_width=True)
            
        with c_right:
            st.markdown("### 🧾 Detailed P&L Statement")
            pnl_df = pd.DataFrame({
                "Line Item": ["1. Total Revenue", "2. Total Landed COGS", "3. Gross Profit", "4. Operating Expenses (OPEX)", "5. Holding Costs", "6. EBITDA", "7. Depreciation", "8. NOPAT"],
                "Amount": [
                    f"£{metrics['Revenue']:,.0f}", f"(£{metrics['COGS']:,.0f})", f"£{metrics['Gross Profit']:,.0f}", 
                    f"(£{metrics['OPEX']:,.0f})", f"(£{metrics['Holding Cost']:,.0f})", f"£{metrics['EBITDA']:,.0f}", 
                    f"(£{metrics['Depreciation']:,.0f})", f"£{metrics['NOPAT']:,.0f}"
                ]
            })
            st.dataframe(pnl_df, hide_index=True, use_container_width=True)
        
    with t2:
        st.subheader("Supply Chain Network Topology")
        dot = graphviz.Digraph(node_attr={'shape': 'box', 'style': 'filled', 'fontname': 'Helvetica'})
        dot.attr(rankdir='LR')
        
        with dot.subgraph(name='cluster_mfg') as c:
            c.attr(label='Tier 1: Manufacturers', style='dashed', color='gray')
            color_m2 = '#d4edda' if integrate_m2 else '#e2e3e5'
            c.node('M1', 'M1: MacroBrew Corp\n[SILOED]', color='#e2e3e5')
            c.node('M2', 'M2: Apex Craftworks\n' + ('[INTEGRATED]' if integrate_m2 else '[SILOED]'), color=color_m2)
            
        with dot.subgraph(name='cluster_ws') as c:
            c.attr(label='Tier 2: Wholesale', style='dashed', color='gray')
            c.node('W1', 'W1: Central Network (US)\nMaster Inventory', color='#fff3cd', shape='cylinder')
            
        with dot.subgraph(name='cluster_ret') as c:
            c.attr(label='Tier 3: Retailers', style='dashed', color='gray')
            color_r1_r3 = '#d4edda' if integrate_r1_r3 else '#e2e3e5'
            c.node('R1', 'R1: Grocery (Steady)\n' + ('[INTEGRATED]' if integrate_r1_r3 else '[SILOED]'), color=color_r1_r3)
            c.node('R2', 'R2: Corner Store (Erratic)\n[SILOED]', color='#e2e3e5')
            c.node('R3', 'R3: Sports Bar (Spikes)\n' + ('[INTEGRATED]' if integrate_r1_r3 else '[SILOED]'), color=color_r1_r3)
            c.node('R4', 'R4: Craft Lounge (Trend)\n[SILOED]', color='#e2e3e5')

        dot.edge('M1', 'W1', color='black', label=' 2 Wk Delay')
        dot.edge('M2', 'W1', color='green' if integrate_m2 else 'black', label=' 4 Wk Delay')
        dot.edge('W1', 'R1', color='green' if integrate_r1_r3 else 'black')
        dot.edge('W1', 'R2')
        dot.edge('W1', 'R3', color='green' if integrate_r1_r3 else 'black')
        dot.edge('W1', 'R4')
        st.graphviz_chart(dot, use_container_width=True)

    with t3:
        st.subheader("Retailer Demand Profile (Point-of-Sale)")
        demand_cols = ["R1_Grocery_Demand", "R2_CornerStore_Demand", "R3_SportsBar_Demand", "R4_CraftLounge_Demand"]
        fig_stacked = px.area(df_flow, x="Week", y=demand_cols, title="Consumer Demand Breakdown by Retailer")
        st.plotly_chart(fig_stacked, use_container_width=True)

        st.markdown("---")
        st.subheader("System Dynamics: The Bullwhip Effect")
        st.markdown("Compare the Red Line (Our Orders to Mfg) against the Green Line (Actual Need).")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_flow["Week"], y=df_flow["Total_Consumer_POS"], name="Total POS Demand", line=dict(color='green', width=2)))
        fig.add_trace(go.Scatter(x=df_flow["Week"], y=df_flow["Retailer_Orders_to_Us"], name="Retailer Orders (Distorted)", line=dict(color='orange', width=2, dash='dash')))
        fig.add_trace(go.Scatter(x=df_flow["Week"], y=df_flow["Our_Orders_to_Mfg"], name="Our Orders to Mfg (Bullwhip)", line=dict(color='red', width=3)))
        
        fig.update_layout(title="Demand Amplification Across Echelons", xaxis_title="Week", yaxis_title="Pallets")
        st.plotly_chart(fig, use_container_width=True)

    with t4:
        st.subheader("Node Ordering Logic & Information Delays")
        st.markdown("This table exposes the underlying math driving the Bullwhip effect. Lower smoothing factors mean the node is highly reactive to daily noise.")
        
        logic_data = [
            {"Entity": "M1 (MacroBrew)", "Tier": "Mfg", "Order Logic": "Build-to-Order", "Physical Delay": "2 Weeks", "Info Smoothing (Alpha)": "N/A"},
            {"Entity": "M2 (Apex Craft)", "Tier": "Mfg", "Order Logic": "Build-to-Order", "Physical Delay": "4 Weeks", "Info Smoothing (Alpha)": "N/A"},
            {"Entity": "W1 (Us - Siloed)", "Tier": "Wholesale", "Order Logic": "Moving Avg + Safety Stock", "Physical Delay": "3 Weeks (Blended)", "Info Smoothing (Alpha)": "0.40 (Reactive)"},
            {"Entity": "W1 (Us - Integrated)", "Tier": "Wholesale", "Order Logic": "Data Analytics / Data Pooling", "Physical Delay": "3 Weeks (Blended)", "Info Smoothing (Alpha)": "0.10 (Smooth)"},
            {"Entity": "R1 (Grocery)", "Tier": "Retail", "Order Logic": "Corporate Algorithm", "Physical Delay": "Immediate", "Info Smoothing (Alpha)": "0.20 (Moderate)"},
            {"Entity": "R2 (Corner Store)", "Tier": "Retail", "Order Logic": "Visual Empty-Shelf Guessing", "Physical Delay": "Immediate", "Info Smoothing (Alpha)": "0.10 (Highly Reactive)"},
            {"Entity": "R3 (Sports Bar)", "Tier": "Retail", "Order Logic": "Weekend Preparation", "Physical Delay": "Immediate", "Info Smoothing (Alpha)": "0.40 (Reactive)"},
            {"Entity": "R4 (Craft Lounge)", "Tier": "Retail", "Order Logic": "Trend Following", "Physical Delay": "Immediate", "Info Smoothing (Alpha)": "0.30 (Moderate)"}
        ]
        st.dataframe(pd.DataFrame(logic_data), hide_index=True, use_container_width=True)
