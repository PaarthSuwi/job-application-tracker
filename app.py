# app.py - Streamlit web dashboard for Job Application Tracker

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from sheets_manager import (
    get_all_applications, add_application,
    update_application_status, mark_ghosted_applications
)
from config import STATUS

st.set_page_config(
    page_title="Job Application Tracker",
    page_icon="briefcase",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px; border-radius: 12px; color: white; text-align: center;
    }
    .insight-box {
        background: #f8f9fa; border-left: 4px solid #667eea;
        padding: 12px 16px; border-radius: 6px; margin: 8px 0;
    }
</style>
""", unsafe_allow_html=True)

# ---- Check for secrets / credentials ----
secrets_ok = "gcp_service_account" in st.secrets if hasattr(st, 'secrets') else False

# ---- Sidebar ----
with st.sidebar:
    st.title("Job Tracker")
    st.markdown("---")

    if not secrets_ok:
        st.warning("⚠️ Google credentials not configured yet. Add secrets in Streamlit Cloud settings to enable data sync.")
    else:
        if st.button("Scan Gmail Now", use_container_width=True, type="primary"):
            try:
                from gmail_scanner import scan_gmail
                from sheets_manager import mark_ghosted_applications
                with st.spinner("Scanning Gmail..."):
                    new, updated = scan_gmail(days_back=30)
                    mark_ghosted_applications()
                st.success(f"Done! {new} new, {updated} updated")
                st.rerun()
            except Exception as e:
                st.error(f"Gmail scan failed: {e}")

    st.markdown("### Add Application")
    with st.form("add_form", clear_on_submit=True):
        company = st.text_input("Company")
        role = st.text_input("Role")
        source = st.selectbox("Source", ["LinkedIn", "Naukri", "Indeed", "Referral", "Email/Auto", "Other"])
        link = st.text_input("Job Link (optional)")
        submitted = st.form_submit_button("Add", use_container_width=True)
        if submitted and company and role:
            if secrets_ok:
                try:
                    result = add_application(company=company, role=role, source=source, job_link=link)
                    if result:
                        st.success(f"Added: {company} - {role}")
                        st.rerun()
                    else:
                        st.warning("Already tracked!")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("Credentials not configured. Please add secrets first.")

    st.markdown("### Update Status")
    with st.form("update_form", clear_on_submit=True):
        upd_company = st.text_input("Company ", key="upd_co")
        upd_role = st.text_input("Role ", key="upd_role")
        upd_status = st.selectbox("New Status", list(STATUS.values()))
        upd_notes = st.text_input("Notes (optional)")
        upd_submitted = st.form_submit_button("Update", use_container_width=True)
        if upd_submitted and upd_company and upd_role:
            if secrets_ok:
                try:
                    result = update_application_status(upd_company, upd_role, upd_status, notes=upd_notes)
                    if result:
                        st.success("Updated!")
                        st.rerun()
                    else:
                        st.warning("Not found.")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.error("Credentials not configured. Please add secrets first.")

# ---- Load data ----
def load_data():
    if not secrets_ok:
        return pd.DataFrame(columns=[
            'Date Applied', 'Company', 'Role', 'Source', 'Job Link',
            'Status', 'Last Updated', 'Response Date', 'Notes', 'Email Subject'
        ])
    try:
        df = get_all_applications()
        if not df.empty and 'Date Applied' in df.columns:
            df['Date Applied'] = pd.to_datetime(df['Date Applied'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()

df = load_data()

# ---- Banner if not configured ----
if not secrets_ok:
    st.warning("""
    ### ⚙️ Setup Required
    This app needs Google credentials to connect to your data.
    
    **To finish setup:**
    1. Go to your app settings on Streamlit Cloud
    2. Click **Secrets** and paste in your `gcp_service_account` JSON
    3. Also add your `gmail_token` (optional, for Gmail scanning)
    
    See the README for the exact format needed.
    """)

# ---- Main title ----
st.title("📋 Job Application Tracker")
st.markdown("---")

if df.empty and secrets_ok:
    st.info("No applications yet. Add your first one in the sidebar, or click 'Scan Gmail Now'!")
    st.stop()

if df.empty:
    st.stop()

# ---- KPIs ----
total = len(df)
responded = len(df[df['Status'].isin([STATUS["SHORTLISTED"], STATUS["INTERVIEW"], STATUS["OFFER"], STATUS["REJECTED"]])])
active = len(df[df['Status'].isin([STATUS["APPLIED"], STATUS["SHORTLISTED"], STATUS["INTERVIEW"]])])
interviews = len(df[df['Status'] == STATUS["INTERVIEW"]])
offers = len(df[df['Status'] == STATUS["OFFER"]])
response_rate = round((responded / total) * 100, 1) if total > 0 else 0

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Applied", total)
with col2:
    st.metric("Response Rate", f"{response_rate}%")
with col3:
    st.metric("Active", active)
with col4:
    st.metric("Interviews", interviews)
with col5:
    st.metric("Offers", offers)

st.markdown("---")

# ---- Charts ----
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Status Breakdown")
    status_counts = df['Status'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Count']
    fig_pie = px.pie(status_counts, values='Count', names='Status',
                     color_discrete_sequence=px.colors.qualitative.Set3)
    st.plotly_chart(fig_pie, use_container_width=True)

with col_right:
    st.subheader("Applications Over Time")
    if 'Date Applied' in df.columns and not df['Date Applied'].isna().all():
        df_time = df.dropna(subset=['Date Applied'])
        df_time = df_time.groupby(df_time['Date Applied'].dt.to_period('W')).size().reset_index()
        df_time.columns = ['Week', 'Count']
        df_time['Week'] = df_time['Week'].astype(str)
        fig_line = px.line(df_time, x='Week', y='Count', markers=True)
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("No date data available yet.")

# ---- Source analysis ----
col_s1, col_s2 = st.columns(2)

with col_s1:
    st.subheader("Top Sources")
    if 'Source' in df.columns:
        src = df['Source'].value_counts().reset_index()
        src.columns = ['Source', 'Count']
        fig_bar = px.bar(src, x='Source', y='Count', color='Count',
                         color_continuous_scale='Blues')
        st.plotly_chart(fig_bar, use_container_width=True)

with col_s2:
    st.subheader("Source Response Rate")
    if 'Source' in df.columns and 'Status' in df.columns:
        df_resp = df.copy()
        df_resp['Got Response'] = df_resp['Status'].isin([
            STATUS["SHORTLISTED"], STATUS["INTERVIEW"], STATUS["OFFER"]
        ])
        src_resp = df_resp.groupby('Source')['Got Response'].agg(['sum', 'count']).reset_index()
        src_resp['Response Rate (%)'] = (src_resp['sum'] / src_resp['count'] * 100).round(1)
        src_resp.columns = ['Source', 'Responses', 'Total', 'Response Rate (%)']
        fig_resp = px.bar(src_resp, x='Source', y='Response Rate (%)',
                          color='Response Rate (%)', color_continuous_scale='RdYlGn',
                          range_color=[0, 100])
        st.plotly_chart(fig_resp, use_container_width=True)

# ---- Insights ----
st.subheader("Self-Analysis Insights")
insights = []

if response_rate < 10 and total > 5:
    insights.append("Your response rate is below 10%. Consider tailoring your resume more to each role.")
if response_rate >= 20:
    insights.append(f"Great job! Your {response_rate}% response rate is above average.")
if interviews > 0 and offers == 0 and interviews >= 3:
    insights.append("You're getting interviews but no offers yet. Focus on interview preparation.")
if offers > 0:
    insights.append(f"You have {offers} offer(s)! Negotiate well.")

ghosted = len(df[df['Status'] == STATUS.get("GHOSTED", "Ghosted")])
if ghosted > total * 0.4 and total > 5:
    insights.append(f"{ghosted} applications were ghosted. Quality over quantity may help.")

if 'Source' in df.columns:
    best_src = df_resp.sort_values('Response Rate (%)').iloc[-1] if 'df_resp' in dir() else None
    if best_src is not None and best_src['Total'] >= 3:
        insights.append(f"'{best_src['Source']}' is your best source with {best_src['Response Rate (%)']}% response rate. Focus there!")

if not insights:
    insights.append("Keep applying! Insights will appear as your data grows.")

for ins in insights:
    st.markdown(f"""<div class="insight-box">{ins}</div>""", unsafe_allow_html=True)

# ---- Filters and Table ----
st.markdown("---")
st.subheader("All Applications")

col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    status_filter = st.multiselect("Filter by Status", df['Status'].unique().tolist(), default=df['Status'].unique().tolist())
with col_f2:
    source_filter = st.multiselect("Filter by Source", df['Source'].unique().tolist() if 'Source' in df.columns else [], default=df['Source'].unique().tolist() if 'Source' in df.columns else [])
with col_f3:
    search = st.text_input("Search by Company/Role")

filtered = df.copy()
if status_filter:
    filtered = filtered[filtered['Status'].isin(status_filter)]
if source_filter and 'Source' in filtered.columns:
    filtered = filtered[filtered['Source'].isin(source_filter)]
if search:
    mask = (
        filtered['Company'].str.contains(search, case=False, na=False) |
        filtered['Role'].str.contains(search, case=False, na=False)
    )
    filtered = filtered[mask]

st.dataframe(filtered, use_container_width=True, hide_index=True)
st.caption(f"Showing {len(filtered)} of {total} applications")
