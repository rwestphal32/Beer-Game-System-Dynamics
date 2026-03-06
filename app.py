import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import graphviz

st.set_page_config(page_title="Supply Chain M&A Simulator", layout="wide")

st.title("🌐 Networked Supply Chain: M&A System Dynamics")
st.markdown("Take manual control of the Wholesaler's inventory algorithm. Try to balance the Bullwhip against lost sales, then use M&A to fundamentally rewire the physics of the supply chain.")

# --- SIDEBAR: STRATEGY & CONTROL ROOM ---
with st.sidebar:
    st.header("🏢 M&A Strategy Toggles")
    st.info("You are W1: Central Network Distributing.")
    int_down = st.toggle("⬇️ Downstream M&A (Acquire R1 & R3)", value=False, help="Spends £2.5M. Eliminates Info Delay. Retail price locked at £280; you capture the delta.")
    int_up = st.toggle("⬆️ Upstream M&A (Acquire M2: Apex Craft)", value=False, help="Spends £1.5M. M2 COGS plummets to £80 brewing cost.")
    
    st.markdown("---")
    st.header("🎛️ Inventory Control Room")
    st.markdown("Manually tune your W1 ordering algorithm to survive the volatility.")
    ws_alpha = st.slider("Forecasting Reactivity (α)", 0.05, 1.0, 0.40, help="High = panic ordering based on yesterday. Low = smooth, slow rolling average.")
    ss_weeks = st.slider("Target Safety Stock (Weeks)", 0.0, 8.0, 2.0, help="Hold extra inventory to prevent stockouts, but traps Working Capital.")
    
    st.markdown("---")
    st.header("💸 Market Prices (Fixed)")
    st.markdown("- **Consumer Price:** £280 / pallet\n- **Wholesale Price:** £200 / pallet\n- **Holding Cost:** £0.50 / pallet / wk")
    holding_cost_per_unit = 0.50
    base_capex = 5000000 
    
    run_sim = st.button("🚀 Run 52-Week Simulation", type="primary", use_container_width=True)

# --- SIMULATION ENGINE ---
def run_system_dynamics(int_down, int_up, alpha, ss_weeks):
    weeks = 52
    np.random.seed(42) 
    time_idx = np.arange(weeks)
    
    # 1. FIXED MARKET PRICING
    p_retail = 280.0
    p_wholesale = 200.0
    c_m1 = 130.0 # Standard AB InBev cost
    c_m2 = 80.0 if int_up else 160.0 # Apex Craft cost drops if integrated
    
    m1_ratio = 0.70
    m2_ratio = 0.30
    blended_cogs = (m1_ratio * c_m1) + (m2_ratio * c_m2)
    
    # 2. GENERATE POS DEMAND
    pos_r1 = np.random.normal(1000, 50, weeks) # R1: Grocery 
    pos_r2 = np.random.normal(200, 80, weeks)  # R2: Corner Store
    pos_r2 = np.where(pos_r2 < 0, 0, pos_r2)
    pos_r3 = 500 + 300 * np.sin(2 * np.pi * time_idx / 12) + np.random.normal(0, 50, weeks) # R3: Sports Bar
    pos_r4 = 100 + 5 * time_idx + np.random.normal(0, 20, weeks) # R4: Craft Lounge
    
    # 3. RETAILER ORDERING (Information Delay)
    def calculate_orders(pos_demand, smoothing_factor):
        orders = np.zeros(weeks)
        forecast = pos_demand[0]
        for t in range(weeks):
            forecast = smoothing_factor * pos_demand[t] + (1 - smoothing_factor) * forecast
            orders[t] = max(0, forecast + np.random.normal(0, forecast*0.1))
        return orders

    ord_r1 = pos_r1 if int_down else calculate_orders(pos_r1, 0.2)
    ord_r2 = calculate_orders(pos_r2, 0.1) 
    ord_r3 = pos_r3 if int_down else calculate_orders(pos_r3, 0.4)
    ord_r4 = calculate_orders(pos_r4, 0.3)
    
    total_wholesale_demand = ord_r1 + ord_r2 + ord_r3 + ord_r4
    
    # 4. WHOLESALER DYNAMICS (Physical Delay & Fulfillment)
    ws_inventory = np.zeros(weeks)
    ws_orders_to_mfg = np.zeros(weeks)
    ws_arrivals = np.zeros(weeks)
    fulfilled_total = np.zeros(weeks)
    
    current_inv = 4000
    lead_time = 3 
    
    # If downstream integrated, the raw POS data allows us to safely use a perfectly smooth Alpha (0.05), overriding the manual panic slider
    active_alpha = 0.05 if int_down else alpha
    ws_forecast = total_wholesale_demand[0]
    
    for t in range(weeks):
        if t >= lead_time:
            current_inv += ws_orders_to_mfg[t - lead_time]
            ws_arrivals[t] = ws_orders_to_mfg[t - lead_time]
            
        demand_today = total_wholesale_demand[t]
        fulfilled = min(current_inv, demand_today)
        fulfilled_total[t] = fulfilled
        current_inv -= fulfilled
        ws_inventory[t] = current_inv
        
        ws_forecast = active_alpha * demand_today + (1 - active_alpha) * ws_forecast
        
        # Target Inventory = Pipeline Lead Time Demand + Manual Safety Stock
        target_inv = ws_forecast * (lead_time + ss_weeks) 
        ws_orders_to_mfg[t] = max(0, target_inv - current_inv)

    # 5. FINANCIALS & SEGMENT LEDGER
    # Calculate fill rate to apportion fulfilled volume back to specific retailers
    fill_rates = np.where(total_wholesale_demand > 0, fulfilled_total / total_wholesale_demand, 1)
    
    vol_r1 = ord_r1 * fill_rates
    vol_r2 = ord_r2 * fill_rates
    vol_r3 = ord_r3 * fill_rates
    vol_r4 = ord_r4 * fill_rates
    
    rev_r1 = np.sum(vol_r1) * (p_retail if int_down else p_wholesale)
    rev_r2 = np.sum(vol_r2) * p_wholesale
    rev_r3 = np.sum(vol_r3) * (p_retail if int_down else p_wholesale)
    rev_r4 = np.sum(vol_r4) * p_wholesale
    
    total_revenue = rev_r1 + rev_r2 + rev_r3 + rev_r4
    total_lost_sales = np.sum(total_wholesale_demand - fulfilled_total)
    lost_revenue = total_lost_sales * p_wholesale
    
    total_arrivals = np.sum(ws_arrivals)
    vol_m1 = total_arrivals * m1_ratio
    vol_m2 = total_arrivals * m2_ratio
    
    cogs_m1 = vol_m1 * c_m1
    cogs_m2 = vol_m2 * c_m2
    total_cogs = cogs_m1 + cogs_m2
    
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
    
    avg_working_capital = np.mean(ws_inventory) * blended_cogs
    roic = (nopat / (capex + avg_working_capital)) * 100 if (capex + avg_working_capital) > 0 else 0

    # Build Segment DataFrame
    segment_data = [
        {"Segment": "R1 (Grocery)", "Type": "Revenue", "Volume (Pallets)": np.sum(vol_r1), "Unit Price/Cost": p_retail if int_down else p_wholesale, "Total Value (£)": rev_r1},
        {"Segment": "R2 (Corner Store)", "Type": "Revenue", "Volume (Pallets)": np.sum(vol_r2), "Unit Price/Cost": p_wholesale, "Total Value (£)": rev_r2},
        {"Segment": "R3 (Sports Bar)", "Type": "Revenue", "Volume (Pallets)": np.sum(vol_r3), "Unit Price/Cost": p_retail if int_down else p_wholesale, "Total Value (£)": rev_r3},
        {"Segment": "R4 (Craft Lounge)", "Type": "Revenue", "Volume (Pallets)": np.sum(vol_r4), "Unit Price/Cost": p_wholesale, "Total Value (£)": rev_r4},
        {"Segment": "M1 (MacroBrew)", "Type": "COGS", "Volume (Pallets)": vol_m1, "Unit Price/Cost": c_m1, "Total Value (£)": -cogs_m1},
        {"Segment": "M2 (Apex Craft)", "Type": "COGS", "Volume (Pallets)": vol_m2, "Unit Price/Cost": c_m2, "Total Value (£)": -cogs_m2},
    ]

    metrics = {
        "Revenue": total_revenue, "COGS": total_cogs, "Gross Profit": gross_profit, 
        "Holding Cost": total_holding_cost, "OPEX": opex, "EBITDA": ebitda, 
        "Depreciation": depreciation, "NOPAT": nopat,
        "CAPEX": capex, "ROIC": roic, "Avg Inv": np.mean(ws_inventory),
        "Lost Sales": total_lost_sales, "Lost Rev": lost_revenue
    }
    
    df_flow = pd.DataFrame({
        "Week": time_idx,
        "R1_Demand": pos_r1, "R2_Demand": pos_r2, "R3_Demand": pos_r3, "R4_Demand": pos_r4,
        "Total_Consumer_POS": pos_r1 + pos_r2 + pos_r3 + pos_r4,
        "Retailer_Orders_to_Us": total_wholesale_demand,
        "Our_Orders_to_Mfg": ws_orders_to_mfg,
        "Our_Inventory": ws_inventory,
        "Missed_Sales": total_wholesale_demand - fulfilled_total
    })
    
    return metrics, df_flow, pd.DataFrame(segment_data)

# --- DASHBOARD UI ---
if run_sim:
    metrics, df_flow, df_segment = run_system_dynamics(int_down, int_up, ws_alpha, ss_weeks)
    
    t1, t2, t3 = st.tabs(["💰 Financials & Segment Profitability", "🗺️ Network Map", "📦 Flow of Goods & Bullwhip"])
    
    with t1:
        st.subheader("Executive Scorecard (52-Week)")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Revenue", f"£{metrics['Revenue']:,.0f}")
        c2.metric("EBITDA", f"£{metrics['EBITDA']:,.0f}")
        c3.metric("Stockout Penalty (Lost Rev)", f"£{metrics['Lost Rev']:,.0f}", delta="Critical Miss", delta_color="inverse")
        c4.metric("ROIC (Annualized)", f"{metrics['ROIC']:.1f}%")
        
        c_left, c_right = st.columns([1.5, 1])
        with c_left:
            st.markdown("### 📊 Segment Ledger (Flow of Dollars)")
            st.markdown("See exactly where margin is captured and COGS are drained based on your M&A state.")
            df_segment["Volume (Pallets)"] = df_segment["Volume (Pallets)"].map("{:,.0f}".format)
            df_segment["Unit Price/Cost"] = df_segment["Unit Price/Cost"].map("£{:,.2f}".format)
            df_segment["Total Value (£)"] = df_segment["Total Value (£)"].map("£{:,.0f}".format)
            st.dataframe(df_segment, hide_index=True, use_container_width=True)
            
        with c_right:
            st.markdown("### 🧾 Detailed P&L Statement")
            pnl_df = pd.DataFrame({
                "Line Item": ["1. Total Revenue", "2. Total COGS", "3. Gross Profit", "4. Operating Expenses (OPEX)", "5. Holding Costs", "6. EBITDA", "7. Depreciation", "8. NOPAT"],
                "Amount": [f"£{metrics['Revenue']:,.0f}", f"(£{metrics['COGS']:,.0f})", f"£{metrics['Gross Profit']:,.0f}", f"(£{metrics['OPEX']:,.0f})", f"(£{metrics['Holding Cost']:,.0f})", f"£{metrics['EBITDA']:,.0f}", f"(£{metrics['Depreciation']:,.0f})", f"£{metrics['NOPAT']:,.0f}"]
            })
            st.dataframe(pnl_df, hide_index=True, use_container_width=True)
        
    with t2:
        st.subheader("Supply Chain Network Topology")
        dot = graphviz.Digraph(node_attr={'shape': 'box', 'style': 'filled', 'fontname': 'Helvetica'})
        dot.attr(rankdir='LR')
        
        with dot.subgraph(name='cluster_mfg') as c:
            c.attr(label='Tier 1: Manufacturers', style='dashed', color='gray')
            color_m2 = '#d4edda' if int_up else '#e2e3e5'
            c.node('M1', 'M1: MacroBrew Corp\n[SILOED] (£130 COGS)', color='#e2e3e5')
            c.node('M2', 'M2: Apex Craftworks\n' + ('[INTEGRATED] (£80 COGS)' if int_up else '[SILOED] (£160 COGS)'), color=color_m2)
            
        with dot.subgraph(name='cluster_ws') as c:
            c.attr(label='Tier 2: Wholesale', style='dashed', color='gray')
            c.node('W1', 'W1: Central Network (US)\nMaster Inventory', color='#fff3cd', shape='cylinder')
            
        with dot.subgraph(name='cluster_ret') as c:
            c.attr(label='Tier 3: Retailers', style='dashed', color='gray')
            color_r1_r3 = '#d4edda' if int_down else '#e2e3e5'
            c.node('R1', 'R1: Grocery (Steady)\n' + ('[INTEGRATED] (Sell @ £280)' if int_down else '[SILOED] (Sell @ £200)'), color=color_r1_r3)
            c.node('R2', 'R2: Corner Store (Erratic)\n[SILOED] (Sell @ £200)', color='#e2e3e5')
            c.node('R3', 'R3: Sports Bar (Spikes)\n' + ('[INTEGRATED] (Sell @ £280)' if int_down else '[SILOED] (Sell @ £200)'), color=color_r1_r3)
            c.node('R4', 'R4: Craft Lounge (Trend)\n[SILOED] (Sell @ £200)', color='#e2e3e5')

        dot.edge('M1', 'W1', color='black', label=' 2 Wk Delay')
        dot.edge('M2', 'W1', color='green' if int_up else 'black', label=' 4 Wk Delay')
        dot.edge('W1', 'R1', color='green' if int_down else 'black')
        dot.edge('W1', 'R2')
        dot.edge('W1', 'R3', color='green' if int_down else 'black')
        dot.edge('W1', 'R4')
        st.graphviz_chart(dot, use_container_width=True)

    with t3:
        st.subheader("System Dynamics: The Bullwhip Effect")
        st.markdown("Watch the Red Line. If you are reactive (high $\\alpha$), the bullwhip explodes. If you smooth it too much without M&A data, you stock out.")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_flow["Week"], y=df_flow["Total_Consumer_POS"], name="Total POS Demand (Truth)", line=dict(color='green', width=2)))
        fig.add_trace(go.Scatter(x=df_flow["Week"], y=df_flow["Retailer_Orders_to_Us"], name="Retailer Orders (Distorted)", line=dict(color='orange', width=2, dash='dash')))
        fig.add_trace(go.Scatter(x=df_flow["Week"], y=df_flow["Our_Orders_to_Mfg"], name="Our Orders to Mfg (Bullwhip)", line=dict(color='red', width=3)))
        fig.update_layout(title="Demand Amplification Across Echelons", xaxis_title="Week", yaxis_title="Pallets")
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Wholesale Inventory Depletion & Stockouts")
        st.markdown("If the orange Stockout spikes appear, you are losing permanent revenue. Increase safety stock or acquire Retailers for better data.")
        
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df_flow["Week"], y=df_flow["Our_Inventory"], name="Physical Inventory", fill='tozeroy', line=dict(color='#1f77b4')))
        fig2.add_trace(go.Scatter(x=df_flow["Week"], y=df_flow["Missed_Sales"], name="Stockouts (Lost Sales)", fill='tozeroy', line=dict(color='#d62728')))
        fig2.update_layout(title="Warehouse Stock Levels vs Lost Sales", xaxis_title="Week", yaxis_title="Pallets")
        st.plotly_chart(fig2, use_container_width=True)
