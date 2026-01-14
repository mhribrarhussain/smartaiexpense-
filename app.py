import streamlit as st
import pandas as pd
import plotly.express as px
import database
import model
import analysis
import re
from datetime import datetime

# Page Configuration
st.set_page_config(page_title="Smart Expense Manager", page_icon="💰", layout="wide")

# Custom CSS for Glassmorphism
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
    }
    div.stButton > button:first-child {
        background-color: rgba(255, 255, 255, 0.1);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 10px;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }
    div.stButton > button:first-child:hover {
        background-color: rgba(255, 255, 255, 0.2);
        border-color: rgba(255, 255, 255, 0.5);
    }
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(5px);
        -webkit-backdrop-filter: blur(5px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        margin-bottom: 20px;
    }
    h1, h2, h3 {
        color: #f0f2f6;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize Components
@st.cache_resource
def get_classifier():
    clf = model.ExpenseClassifier()
    try:
        clf.load_model()
    except:
        clf.train()
    return clf

classifier = get_classifier()
database.init_db()

# Sidebar
st.sidebar.title("💰 Smart Expense")
page = st.sidebar.radio("Navigation", ["➕ Add Expense", "📊 Dashboard", "📜 History"])

# --- PAGE: ADD EXPENSE ---
if page == "➕ Add Expense":
    st.title("Add New Expense")
    
    with st.container():
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        col1, col2 = st.columns([2, 1])
        
        with col1:
            raw_input = st.text_input("Describe your expense (e.g., 'Pizza 1200')", key="expense_input")
        
        predicted_category = "Select..."
        amount = 0.0
        details = ""
        
        if raw_input:
            match = re.search(r'(\d+(\.\d+)?)', raw_input)
            if match:
                amount = float(match.group(1))
                details = raw_input.replace(match.group(1), "").strip()
                if details:
                    predicted_category = classifier.predict(details)
        
        with col2:
            st.metric("Detected Amount", f"${amount}")
            
        st.markdown('</div>', unsafe_allow_html=True)

        if raw_input and amount > 0:
            st.info(f"🤖 AI Categorized as: **{predicted_category}**")
            
            with st.form("expense_form"):
                final_text = st.text_input("Description", value=details)
                final_amount = st.number_input("Amount", value=amount)
                
                categories = ["Food", "Travel", "Bills", "Shopping", "Health", "Others"]
                try:
                    default_index = categories.index(predicted_category)
                except ValueError:
                    default_index = 0
                    
                final_category = st.selectbox("Category", categories, index=default_index)
                
                submitted = st.form_submit_button("✅ Save Expense")
                if submitted:
                    database.add_expense(final_text, final_amount, final_category)
                    st.success("Expense saved successfully!")
                    st.balloons()

# --- PAGE: DASHBOARD ---
elif page == "📊 Dashboard":
    st.title("Financial Dashboard")
    
    total_spending = analysis.get_monthly_total()
    suggestions = analysis.generate_suggestions()
    
    # Top Stats
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="glass-card" style="text-align: center;">
            <h3>Total Monthly Spending</h3>
            <h1 style="color: #4CAF50;">${total_spending:,.2f}</h1>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown('<div class="glass-card" style="min-height: 160px;"><h3>💡 AI Insights</h3>', unsafe_allow_html=True)
        for s in suggestions:
            if "Alert" in s:
                st.warning(s)
            else:
                st.success(s)
        st.markdown('</div>', unsafe_allow_html=True)

    # Charts
    breakdown = analysis.get_category_breakdown()
    daily = analysis.get_daily_spending()

    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        if breakdown:
            df_pie = pd.DataFrame(list(breakdown.items()), columns=['Category', 'Amount'])
            fig_pie = px.pie(df_pie, values='Amount', names='Category', title='Spending by Category', hole=0.4)
            fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No data for pie chart.")

    with col_chart2:
        if daily:
            df_bar = pd.DataFrame(list(daily.items()), columns=['Date', 'Amount'])
            fig_bar = px.bar(df_bar, x='Date', y='Amount', title='Daily Spending Trend')
            fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No data for trend chart.")

# --- PAGE: HISTORY ---
elif page == "📜 History":
    st.title("Transaction History")
    
    df = database.get_all_expenses_as_dataframe()
    if not df.empty:
        # Sort by latest
        df = df.sort_values(by="id", ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No expenses found.")
