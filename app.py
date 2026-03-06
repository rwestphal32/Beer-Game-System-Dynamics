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
    int_down = st.toggle("⬇️ Downstream M&A (Acquire R1 & R3)", value=False, help="Spends £2.5M. Eliminates Info Delay. You capture full retail markup.")
    int_up = st.toggle("⬆️ Upstream M&A (Acquire M2: Apex Craft)", value=False, help="Spends £1.5M. M2 COGS plummets to £80 brewing cost.")
    
    st.markdown("---")
    st.header("🎛️ Inventory Control Room")
    st.markdown("Manually tune your W1 ordering algorithm to survive the volatility.")
    ws_alpha = st.slider("Forecasting Reactivity (α)", 0.05, 1.0, 0.40, help="High = panic ordering. Low = smooth rolling average.")
    ss_weeks = st.slider("Target Safety Stock (Weeks)", 0.0, 8.0, 2.0, help="Hold extra inventory to prevent stockouts.")
    
    st.markdown("---")
    st.header("💸 Unit Pricing (Fixed)")
    st.markdown("**M1: MacroBrew (70% Vol)**\n- COGS: £130\n- Wholesale: £200\n- Retail: £280")
    st.markdown("**M2: Apex Craft (30% Vol)**\n- COGS: £160 (£80 if acquired)\n- Wholesale: £300\n- Retail: £450")
    
    run_sim = st.button("🚀 Run 52-Week Simulation", type="primary", use_container_width=True)

# --- SIMULATION ENGINE ---
def run_system_dynamics(int_down, int_up, alpha, ss_weeks):
    weeks = 52
    np.random.seed(42) 
    time_idx = np.arange(weeks)
    
    # 1. FIXED MARKET PRICING (SEPARATED SKUS)
    p_ret_m1 = 280.0
    p_ws_m1 = 200.0
    c_m1 = 130.0 
    
    p_ret_m2 = 450.0
    p_ws_m2 = 300.0
    c_m2 = 80.0 if int_up else 160.0 
    
    m1_ratio = 0.70
    m2_ratio = 0.30
    holding_cost = 0.50
    
    # 2. GENERATE POS DEMAND (Base Consumer Traffic)
    pos_r1 = np.random.normal(1000, 50, weeks) # R1: Grocery 
    pos_r2 = np.random.normal(200, 80, weeks)  # R2: Corner Store
    pos_r2 = np.where(pos_r2 < 0, 0, pos_r2)
    pos_r3 = 500 + 300 * np.sin(2 * np.pi * time_idx / 12) + np.random.normal(0, 50, weeks) # R3: Sports Bar
    pos_r4 = 100 + 5 * time_idx + np.random.normal(0, 20, weeks) # R4: Craft Lounge
    
    # 3. RETAILER ORDERING (Information Delay)
    def calc_orders(pos, smooth):
        ord_arr = np.zeros(weeks)
        forecast = pos[0]
        for t in range(weeks):
            forecast = smooth * pos[t] + (1 - smooth) * forecast
            ord_arr[t] = max(0, forecast + np.random.normal(0, forecast*0.1))
        return ord_arr

    ord_r1 = pos_r1 if int_down else calc_orders(pos_r1, 0.2)
    ord_r2 = calc_orders(pos_r2, 0.1) 
    ord_r3 = pos_r3 if int_down else calc_orders(pos_r3, 0.4)
    ord_r4 = calc_orders(pos_r4, 0.3)
    
    # Split Demand into SKUs
    dem_m1 = (ord_r1 + ord_r2 + ord_r3 + ord_r4) * m1_ratio
    dem_m2 = (ord_r1 + ord_r2 + ord_r3 + ord_r4) * m2_ratio
    
    # 4. WHOLESALER DYNAMICS (Dual Pipelines)
    lead_time = 3 
    active_alpha = 0.05 if int_down else alpha
    
    # FIX: Dynamically scale starting inventory to prevent early stockouts
    inv_m1 = np.zeros(weeks); ord_to_m1 = np.zeros(weeks); arr_m1 = np.zeros(weeks); fill_m1 = np.zeros(weeks)
    inv_m2 = np.zeros(weeks); ord_to_m2 = np.zeros(weeks); arr_m2 = np.zeros(weeks); fill_m2 = np.zeros(weeks)
    
    curr_inv_m1 = dem_m1[0] * (lead_time + ss_weeks)
    curr_inv_m2 = dem_m2[0] * (lead_time + ss_weeks)
    
    fcst_m1 = dem_m1[0]; fcst_m2 = dem_m2[0]
    
    for t in range(weeks):
        # M1 Pipeline
        if t >= lead_time:
            curr_inv_m1 += ord_to_m1[t - lead_time]
            arr_m1[t] = ord_to_m1[t - lead_time]
        fulfilled_m1 = min(curr_inv_m1, dem_m1[t])
        fill_m1[t] = fulfilled_m1
        curr_inv_m1 -= fulfilled_m1
        inv_m1[t] = curr_inv_m1
        fcst_m1 = active_alpha * dem_m1[t] + (1 - active_alpha) * fcst_m1
        ord_to_m1[t] = max(0, (fcst_m1 * (lead_time + ss_weeks)) - curr_inv_m1)
        
        # M2 Pipeline
        if t >= lead_time:
            curr_inv_m2 += ord_to_m2[t - lead_time]
            arr_m2[t] = ord_to_m2[t - lead_time]
        fulfilled_m2 = min(curr_inv_m2, dem_m2[t])
        fill_m2[t] = fulfilled_m2
        curr_inv_m2 -= fulfilled_m2
        inv_m2[t] = curr_inv_m2
        fcst_m2 = active_alpha * dem_m2[t] + (1 - active_alpha) * fcst_m2
        ord_to_m2[t] = max(0, (fcst_m2 * (lead_time + ss_weeks)) - curr_inv_m2)

    # 5. FINANCIALS & DUAL SEGMENT LEDGER
    fr_m1 = np.where(dem_m1 > 0, fill_m1 / dem_m1, 1)
    fr_m2 = np.where(dem_m2 > 0, fill_m2 / dem_m2, 1)
    
    # Calculate Volume Sold per SKU per Retailer
    v_r1_m1 = ord_r1 * m1_ratio * fr_m1; v_r1_m2 = ord_r1 * m2_ratio * fr_m2
    v_r2_m1 = ord_r2 * m1_ratio * fr_m1; v_r2_m2 = ord_r2 * m2_ratio * fr_m2
    v_r3_m1 = ord_r3 * m1_ratio * fr_m1; v_r3_m2 = ord_r3 * m2_ratio * fr_m2
    v_r4_m1 = ord_r4 * m1_ratio * fr_m1; v_r4_m2 = ord_r4 * m2_ratio * fr_m2
    
    # Segment Pricing Logic
    pr1_m1 = p_ret_m1 if int_down else p_ws_m1; pr1_m2 = p_ret_m2 if int_down else p_ws_m2
    pr2_m1 = p_ws_m1; pr2_m2 = p_ws_m2
    pr3_m1 = p_ret_m1 if int_down else p_ws_m1; pr3_m2 = p_ret_m2 if int_down else p_ws_m2
    pr4_m1 = p_ws_m1; pr4_m2 = p_ws_m2
    
    # Revenues
    rev_r1_m1 = np.sum(v_r1_m1) * pr1_m1; rev_r1_m2 = np.sum(v_r1_m2) * pr1_m2
    rev_r2_m1 = np.sum(v_r2_m1) * pr2_m1; rev_r2_m2 = np.sum(v_r2_m2) * pr2_m2
    rev_r3_m1 = np.sum(v_r3_m1) * pr3_m1; rev_r3_m2 = np.sum(v_r3_m2) * pr3_m2
    rev_r4_m1 = np.sum(v_r4_m1) * pr4_m1; rev_r4_m2 = np.sum(v_r4_m2) * pr4_m2
    
    total_rev = rev_r1_m1 + rev_r1_m2 + rev_r2_m1 + rev_r2_m2 + rev_r3_m1 + rev_r3_m2 + rev_r4_m1 + rev_r4_m2
    
    # COGS
    cogs_m1_tot = np.sum(arr_m1) * c_m1
    cogs_m2_tot = np.sum(arr_m2) * c_m2
    total_cogs = cogs_m1_tot + cogs_m2_tot
    
    gross_profit = total_rev - total_cogs
    total_hold_cost = (np.sum(inv_m1) + np.sum(inv_m2)) * holding_cost
    
    opex = 1000000 
    if int_down: opex += 500000 
    if int_up: opex += 200000 
    
    ebitda = gross_profit - total_hold_cost - opex
    capex = 5000000 + (2500000 if int_down else 0) + (1500000 if int_up else 0)
    depreciation = capex / 10.0 
    nopat = (ebitda - depreciation) * (1 - 0.25)
    
    avg_wc = (np.mean(inv_m1) * c_m1) + (np.mean(inv_m2) * c_m2)
    roic = (nopat / (capex + avg_wc)) * 100 if (capex + avg_wc) > 0 else 0

    # Build High-Granularity Segment DataFrame
    segment_data = [
        {"Segment": "R1 (Grocery)", "SKU": "M1 (Macro)", "Type": "Revenue", "Vol": np.sum(v_r1_m1), "Unit Price": pr1_m1, "Total Value (£)": rev_r1_m1},
        {"Segment": "R1 (Grocery)", "SKU": "M2 (Craft)", "Type": "Revenue", "Vol": np.sum(v_r1_m2), "Unit Price": pr1_m2, "Total Value (£)": rev_r1_m2},
        {"Segment": "R2 (Corner)", "SKU": "M1 (Macro)", "Type": "Revenue", "Vol": np.sum(v_r2_m1), "Unit Price": pr2_m1, "Total Value (£)": rev_r2_m1},
        {"Segment": "R2 (Corner)", "SKU": "M2 (Craft)", "Type": "Revenue", "Vol": np.sum(v_r2_m2), "Unit Price": pr2_m2, "Total Value (£)": rev_r2_m2},
        {"Segment": "R3 (Sports Bar)", "SKU": "M1 (Macro)", "Type": "Revenue", "Vol": np.sum(v_r3_m1), "Unit Price": pr3_m1, "Total Value (£)": rev_r3_m1},
        {"Segment": "R3 (Sports Bar)", "SKU": "M2 (Craft)", "Type": "Revenue", "Vol": np.sum(v_r3_m2), "Unit Price": pr3_m2, "Total Value (£)": rev_r3_m2},
        {"Segment": "R4 (Lounge)", "SKU": "M1 (Macro)", "Type": "Revenue", "Vol": np.sum(v_r4_m1), "Unit Price": pr4_m1, "Total Value (£)": rev_r4_m1},
        {"Segment": "R4 (Lounge)", "SKU": "M2 (Craft)", "Type": "Revenue", "Vol": np.sum(v_r4_m2), "Unit Price": pr4_m2, "Total Value (£)": rev_r4_m2},
        {"Segment": "Mfg Replenish", "SKU": "M1 (Macro)", "Type": "COGS", "Vol": np.sum(arr_m1), "Unit Price": c_m1, "Total Value (£)": -cogs_m1_tot},
        {"Segment": "Mfg Replenish", "SKU": "M2 (Craft)", "Type": "COGS", "Vol": np.sum(arr_m2), "Unit Price": c_m2, "Total Value (£)": -cogs_m2_tot},
    ]

    metrics = {
        "Revenue": total_rev, "COGS": total_cogs, "Gross Profit": gross_profit, 
        "Holding Cost": total_hold_cost, "OPEX": opex, "EBITDA": ebitda, 
        "Depreciation": depreciation, "NOPAT": nopat, "CAPEX": capex, "ROIC": roic,
        "Lost Rev": (np.sum(dem_m1 - fill_m1) * p_ws_m1) + (np.sum(dem_m2 - fill_m2) * p_ws_m2)
    }
    
    df_flow = pd.DataFrame({
        "Week": time_idx,
        "Total_Consumer_POS": (pos_r1 + pos_r2 + pos_r3 + pos_r4),
        "Retailer_Orders_to_Us": (dem_m1 + dem_m2),
        "Our_Orders_to_Mfg": (ord_to_m1 + ord_to_m2),
        "Our_Inventory": (inv_m1 + inv_m2),
        "Missed_Sales": (dem_m1 - fill_m1) + (dem_m2 - fill_m2)
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
            st.markdown("### 📊 Dual-SKU Segment Ledger")
            df_segment["Vol"] = df_segment["Vol"].map("{:,.0f}".format)
            df_segment["Unit Price"] = df_segment["Unit Price"].map("£{:,.2f}".format)
            df_segment["Total Value (£)"] = df_segment["Total Value (£)"].map("£{:,.0f}".format)
            st.dataframe(df_segment, hide_index=True, use_container_width=True)
            
        with c_right:
            st.markdown("### 🧾 Detailed P&L Statement")
            pnl_df = pd.DataFrame({
                "Line Item": ["1. Total Revenue", "2. Total COGS", "3. Gross Profit", "4. Operating Expenses", "5. Holding Costs", "6. EBITDA", "7. Depreciation", "8. NOPAT"],
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
            c.node('R1', 'R1: Grocery\n' + ('[INTEGRATED] (Sell @ £280/450)' if int_down else '[SILOED] (Sell @ £200/300)'), color=color_r1_r3)
            c.node('R2', 'R2: Corner Store\n[SILOED] (Sell @ £200/300)', color='#e2e3e5')
            c.node('R3', 'R3: Sports Bar\n' + ('[INTEGRATED] (Sell @ £280/450)' if int_down else '[SILOED] (Sell @ £200/300)'), color=color_r1_r3)
            c.node('R4', 'R4: Craft Lounge\n[SILOED] (Sell @ £200/300)', color='#e2e3e5')

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
        fig.update_layout(title="Demand Amplification Across Echelons (Combined SKUs)", xaxis_title="Week", yaxis_title="Pallets")
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Wholesale Inventory Depletion & Stockouts")
        st.markdown("If the orange Stockout spikes appear, you are losing permanent revenue. Increase safety stock or acquire Retailers for better data.")
        
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df_flow["Week"], y=df_flow["Our_Inventory"], name="Physical Inventory", fill='tozeroy', line=dict(color='#1f77b4')))
        fig2.add_trace(go.Scatter(x=df_flow["Week"], y=df_flow["Missed_Sales"], name="Stockouts (Lost Sales)", fill='tozeroy', line=dict(color='#d62728')))
        fig2.update_layout(title="Warehouse Stock Levels vs Lost Sales (Combined SKUs)", xaxis_title="Week", yaxis_title="Pallets")
        st.plotly_chart(fig2, use_container_width=True)
