"""
AI Customer Churn & Support Assistant — Streamlit UI.

Features:
  1. Executive Churn Dashboard: Key metric KPIs + visual charts.
  2. Customer Directory & Risk Analysis: Search by ID/Name/Email, view profile and risk factors.
  3. AI Assistant & SQL Agent: Live interactive chat with LangChain and Gemini.
"""
import os
import requests
import streamlit as st
import pandas as pd

# ---------------------------------------------------------------------------
# App Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Customer Churn & Support Assistant",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

# ---------------------------------------------------------------------------
# Helper Functions for API Calls
# ---------------------------------------------------------------------------
@st.cache_data(ttl=15)
def fetch_analytics_summary():
    try:
        res = requests.get(f"{API_BASE_URL}/analytics/summary", timeout=10)
        return res.json() if res.status_code == 200 else None
    except Exception:
        return None

@st.cache_data(ttl=15)
def fetch_churn_by_plan():
    try:
        res = requests.get(f"{API_BASE_URL}/analytics/churn-by-plan", timeout=10)
        if res.status_code == 200:
            data = res.json()
            return data.get("results", []) if isinstance(data, dict) else data
        return []
    except Exception:
        return []

@st.cache_data(ttl=15)
def fetch_avg_spend_by_plan():
    try:
        res = requests.get(f"{API_BASE_URL}/analytics/avg-spend-by-plan", timeout=10)
        if res.status_code == 200:
            data = res.json()
            return data.get("results", []) if isinstance(data, dict) else data
        return []
    except Exception:
        return []

@st.cache_data(ttl=15)
def fetch_high_risk_customers():
    try:
        res = requests.get(f"{API_BASE_URL}/analytics/high-risk?limit=100", timeout=10)
        if res.status_code == 200:
            data = res.json()
            return data.get("results", []) if isinstance(data, dict) else data
        return []
    except Exception:
        return []

def search_customers(query: str = "", plan: str = "All", churn_status: str = "All"):
    params = {"page_size": 50, "page": 1}
    if query:
        params["search"] = query
    if plan != "All":
        params["plan"] = plan
    if churn_status == "Churned":
        params["churn"] = True
    elif churn_status == "Active":
        params["churn"] = False
    try:
        res = requests.get(f"{API_BASE_URL}/customers", params=params, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return data.get("results", []) if isinstance(data, dict) else data
        return []
    except Exception:
        return []

def query_ai_assistant(question: str):
    try:
        res = requests.post(f"{API_BASE_URL}/ask", json={"question": question}, timeout=60)
        return res.status_code, res.json()
    except Exception as e:
        return 500, {"detail": f"Failed to reach backend: {e}"}

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("🛡️ Churn Assistant")
st.sidebar.caption("FastAPI + SQLite + LangChain + Gemini")

nav = st.sidebar.radio(
    "Navigation",
    ["📊 Analytics Dashboard", "👥 Customer Directory & Risk", "💬 AI Support Assistant"],
)

st.sidebar.divider()
st.sidebar.markdown(f"**Backend URL**: `{API_BASE_URL}`")
try:
    health = requests.get(f"{API_BASE_URL}/health", timeout=3).json()
    st.sidebar.success(f"Backend Online (v{health.get('version', '0.0.0')})")
except Exception:
    st.sidebar.error("Backend Offline. Start FastAPI on port 8000.")


# ---------------------------------------------------------------------------
# Tab 1: Analytics Dashboard
# ---------------------------------------------------------------------------
if nav == "📊 Analytics Dashboard":
    st.title("📊 Executive Churn & Customer Analytics")
    st.markdown("Real-time behavioral insights and customer retention metrics.")

    summary = fetch_analytics_summary()
    if summary:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Customers", f"{summary['total_customers']:,}")
        col2.metric("Overall Churn Rate", f"{summary['churn_rate']:.1f}%")
        col3.metric("Avg Monthly Spend", f"${summary['avg_monthly_spend']:.2f}")
        col4.metric("High-Risk Customers", f"{summary.get('high_risk_count', summary.get('high_risk_customers', 0)):,}")

        st.divider()

        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Churn Rate by Plan")
            churn_data = fetch_churn_by_plan()
            if churn_data:
                df_churn = pd.DataFrame(churn_data)
                df_churn = df_churn.rename(columns={"plan": "Plan", "churn_rate": "Churn Rate (%)"})
                st.bar_chart(df_churn.set_index("Plan")["Churn Rate (%)"])
                st.dataframe(df_churn, use_container_width=True, hide_index=True)

        with col_right:
            st.subheader("Average Spend by Plan")
            spend_data = fetch_avg_spend_by_plan()
            if spend_data:
                df_spend = pd.DataFrame(spend_data)
                df_spend = df_spend.rename(columns={"plan": "Plan", "avg_spend": "Avg Monthly Spend ($)"})
                st.bar_chart(df_spend.set_index("Plan")["Avg Monthly Spend ($)"])
                st.dataframe(df_spend, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("⚠️ Top Active High-Risk Customers (Attention Needed)")
        high_risk = fetch_high_risk_customers()
        if high_risk:
            df_risk = pd.DataFrame(high_risk)[
                ["customer_id", "name", "plan", "monthly_spend", "support_tickets", "satisfaction_score", "last_login_days"]
            ]
            df_risk.columns = ["ID", "Name", "Plan", "Spend ($)", "Tickets", "Satisfaction (0-10)", "Days Since Login"]
            st.dataframe(df_risk.head(15), use_container_width=True, hide_index=True)
    else:
        st.warning("Unable to connect to FastAPI backend analytics. Please ensure the backend is running.")


# ---------------------------------------------------------------------------
# Tab 2: Customer Directory & Risk Profiler
# ---------------------------------------------------------------------------
elif nav == "👥 Customer Directory & Risk":
    st.title("👥 Customer Directory & Churn Risk Profiler")

    col_s1, col_s2, col_s3 = st.columns([3, 1, 1])
    with col_s1:
        search_query = st.text_input("Search by Name, Email, or Customer ID", placeholder="e.g. C0001, Liam, etc.")
    with col_s2:
        selected_plan = st.selectbox("Plan Filter", ["All", "Basic", "Standard", "Premium"])
    with col_s3:
        selected_churn = st.selectbox("Status Filter", ["All", "Active", "Churned"])

    customers = search_customers(search_query, selected_plan, selected_churn)

    if customers:
        st.write(f"Found **{len(customers)}** customers matching criteria:")
        df_cust = pd.DataFrame(customers)[
            ["customer_id", "name", "email", "age", "plan", "monthly_spend", "tenure_months", "support_tickets", "last_login_days", "satisfaction_score", "churn"]
        ]
        df_cust["churn"] = df_cust["churn"].apply(lambda x: "🚨 Churned" if x else "✅ Active")
        df_cust.columns = ["ID", "Name", "Email", "Age", "Plan", "Spend ($)", "Tenure (mo)", "Tickets", "Inactive Days", "Score", "Status"]
        st.dataframe(df_cust, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("🔍 Quick Customer Risk Drilldown")
        selected_id = st.selectbox("Select Customer to Inspect:", [c["customer_id"] for c in customers])
        cust_profile = next((c for c in customers if c["customer_id"] == selected_id), None)

        if cust_profile:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Support Tickets", cust_profile["support_tickets"], delta="High" if cust_profile["support_tickets"] > 5 else "Normal", delta_color="inverse")
            c2.metric("Satisfaction Score", f"{cust_profile['satisfaction_score']}/10", delta="Low" if cust_profile["satisfaction_score"] < 5.0 else "Healthy")
            c3.metric("Days Since Login", f"{cust_profile['last_login_days']}d", delta="Inactive" if cust_profile["last_login_days"] > 30 else "Recent", delta_color="inverse")
            c4.metric("Monthly Spend", f"${cust_profile['monthly_spend']:.2f}")

            # Quick AI prompt trigger
            if st.button(f"🤖 Ask AI Assistant why {cust_profile['name']} ({cust_profile['customer_id']}) is at risk"):
                st.session_state["preset_question"] = f"Why is customer {cust_profile['customer_id']} at risk of churn and what should we do?"
                st.info("Question loaded! Go to the '💬 AI Support Assistant' tab to view response.")
    else:
        st.info("No customers found matching the search criteria.")


# ---------------------------------------------------------------------------
# Tab 3: AI Support Assistant & SQL Agent
# ---------------------------------------------------------------------------
elif nav == "💬 AI Support Assistant":
    st.title("💬 AI Churn & Retention Assistant")
    st.markdown("Ask natural language questions about specific customer risks or ask dynamic analytics questions.")

    col_q1, col_q2 = st.columns([4, 1])
    with col_q1:
        default_q = st.session_state.get("preset_question", "Why is customer C0001 at risk of churn and what retention actions should we take?")
        user_question = st.text_input("Enter your question:", value=default_q)
    with col_q2:
        st.write("")
        st.write("")
        ask_btn = st.button("🚀 Ask Assistant", type="primary", use_container_width=True)

    st.markdown("**Suggested Quick Questions:**")
    q_col1, q_col2, q_col3 = st.columns(3)
    if q_col1.button("📌 'Which plan has the highest churn rate?'"):
        user_question = "Which plan has the highest churn rate?"
        ask_btn = True
    if q_col2.button("📌 'Show me the top 5 customers by spend'"):
        user_question = "Show me the top 5 customers by monthly spend."
        ask_btn = True
    if q_col3.button("📌 'Why is customer C0002 at risk of churn?'"):
        user_question = "Why is customer C0002 at risk of churn and what should we do?"
        ask_btn = True

    if ask_btn and user_question:
        with st.status("⚡ Querying AI Assistant...", expanded=True) as status:
            st.write("🔍 Inspecting customer database and generating insights...")
            status_code, response_data = query_ai_assistant(user_question)
            if status_code == 200:
                status.update(label="✅ Analysis Complete!", state="complete", expanded=False)
            else:
                status.update(label="❌ Analysis Failed", state="error", expanded=False)

        if status_code == 200:
            st.markdown("### 💡 AI Response")
            st.markdown(response_data.get("answer", "No answer provided."))

            # Display SQL if available
            sql = response_data.get("sql_used")
            if sql:
                with st.expander("🔍 Dynamic SQL Query Executed by Agent", expanded=True):
                    st.code(sql, language="sql")

            # Display Sources
            sources = response_data.get("sources", [])
            if sources:
                st.caption(f"**Data Sources Used**: {', '.join(sources)}")
        else:
            st.error(f"Error ({status_code}): {response_data.get('detail', 'Unknown error')}")
