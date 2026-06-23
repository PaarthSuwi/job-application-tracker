# app.py - Streamlit web dashboard for Job Application Tracker

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from sheets_manager import (
    get_all_applications, add_application,
    update_application_status, mark_ghosted_applications
)
from gmail_scanner import scan_gmail
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

# ---- Sidebar ----
with st.sidebar:
    st.title("Job Tracker")
    st.markdown("---")

    if st.button("Scan Gmail Now", use_container_width=True, type="primary"):
        with st.spinner("Scanning Gmail..."):
            new, updated = scan_gmail(days_back=30)
            mark_ghosted_applications()
        st.success(f"Done! {new} new, {updated} updated")
        st.rerun()

    st.markdown("### Add Application")
    with st.form("add_form", clear_on_submit=True):
        company = st.text_input("Company*")
        role = st.text_input("Role*")
        source = st.selectbox("Source", [
            "LinkedIn", "Naukri", "Indeed", "Company Website",
            "Referral", "Internshala", "Unstop", "Other"
        ])
        link = st.text_input("Job Link")
        notes = st.text_area("Notes", height=60)
        if st.form_submit_button("Add", use_container_width=True) and company and role:
            add_application(company, role, source, link, notes=notes)
            st.success("Added!")
            st.rerun()

    st.markdown("### Update Status")
    with st.form("update_form", clear_on_submit=True):
        u_company = st.text_input("Company*", key="uc")
        u_role = st.text_input("Role*", key="ur")
        u_status = st.selectbox("New Status", list(STATUS.values()))
        u_notes = st.text_input("Notes", key="un")
        if st.form_submit_button("Update", use_container_width=True) and u_company and u_role:
            update_application_status(u_company, u_role, u_status, notes=u_notes)
            st.success("Updated!")
            st.rerun()

    st.markdown("---")
    if st.button("Mark Ghosted (21+ days)", use_container_width=True):
        mark_ghosted_applications()
        st.rerun()

# ---- Load Data ----
@st.cache_data(ttl=120)
def load_data():
    return get_all_applications()

df = load_data()

if df.empty:
    st.info("No applications yet. Add one from the sidebar or scan Gmail.")
    st.stop()

for col in ['Date Applied', 'Last Updated', 'Response Date']:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')

# ---- KPIs ----
st.markdown("## Job Application Dashboard")
st.markdown(f"*Refreshed: {datetime.now().strftime('%d %b %Y, %I:%M %p')}*")
st.markdown("---")

total = len(df)
responded = df[df['Status'].isin([
    STATUS['SHORTLISTED'], STATUS['INTERVIEW'],
    STATUS['OFFER'], STATUS['REJECTED']
])].shape[0]
active = df[df['Status'].isin([
    STATUS['APPLIED'], STATUS['SHORTLISTED'], STATUS['INTERVIEW']
])].shape[0]
offers = df[df['Status'] == STATUS['OFFER']].shape[0]
interviews = df[df['Status'] == STATUS['INTERVIEW']].shape[0]
response_rate = (responded / total * 100) if total > 0 else 0

col1, col2, col3, col4, col5 = st.columns(5)
for col, label, value, color in [
    (col1, "Total Applied", total, "#667eea"),
    (col2, "Response Rate", f"{response_rate:.1f}%", "#f39c12"),
    (col3, "Active", active, "#27ae60"),
    (col4, "Interviews", interviews, "#9b59b6"),
    (col5, "Offers", offers, "#e74c3c"),
]:
    with col:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,{color}99,{color}55);
             padding:20px;border-radius:12px;text-align:center;
             border:1px solid {color}44;margin-bottom:8px;">
          <div style="font-size:2rem;font-weight:700;">{value}</div>
          <div style="font-size:0.85rem;opacity:0.9;">{label}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("---")

# ---- Charts ----
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Applications by Status")
    status_counts = df['Status'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Count']
    color_map = {
        STATUS['APPLIED']: '#3498db', STATUS['SHORTLISTED']: '#f39c12',
        STATUS['INTERVIEW']: '#9b59b6', STATUS['OFFER']: '#27ae60',
        STATUS['REJECTED']: '#e74c3c', STATUS['GHOSTED']: '#95a5a6',
        STATUS['WITHDRAWN']: '#bdc3c7',
    }
    fig = px.pie(status_counts, names='Status', values='Count',
                 color='Status', color_discrete_map=color_map, hole=0.45)
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320)
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Applications Over Time")
    df_time = df.dropna(subset=['Date Applied'])
    if not df_time.empty:
        df_time = df_time.copy()
        df_time['Week'] = df_time['Date Applied'].dt.to_period('W').dt.start_time
        weekly = df_time.groupby('Week').size().reset_index(name='Applications')
        fig2 = px.line(weekly, x='Week', y='Applications', markers=True, line_shape='spline')
        fig2.update_traces(line_color='#667eea', marker_color='#764ba2', marker_size=7)
        fig2.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320)
        st.plotly_chart(fig2, use_container_width=True)

col_left2, col_right2 = st.columns(2)
with col_left2:
    st.subheader("Top Sources")
    if 'Source' in df.columns and df['Source'].notna().any():
        src_df = df['Source'].value_counts().reset_index()
        src_df.columns = ['Source', 'Count']
        fig3 = px.bar(src_df, x='Count', y='Source', orientation='h',
                      color='Count', color_continuous_scale='Purples')
        fig3.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300, showlegend=False,
                           yaxis=dict(autorange='reversed'))
        st.plotly_chart(fig3, use_container_width=True)

with col_right2:
    st.subheader("Source Response Rate")
    if 'Source' in df.columns:
        src_resp = df.groupby('Source').apply(
            lambda x: (x['Status'].isin([
                STATUS['SHORTLISTED'], STATUS['INTERVIEW'], STATUS['OFFER']
            ])).sum() / len(x) * 100
        ).reset_index()
        src_resp.columns = ['Source', 'Response Rate (%)']
        src_resp = src_resp.sort_values('Response Rate (%)', ascending=True)
        fig4 = px.bar(src_resp, x='Response Rate (%)', y='Source', orientation='h',
                      color='Response Rate (%)', color_continuous_scale='RdYlGn',
                      range_color=[0, 100])
        fig4.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300, showlegend=False)
        st.plotly_chart(fig4, use_container_width=True)

# ---- Self-Analysis ----
st.markdown("---")
st.subheader("Self-Analysis & Recommendations")
insights = []

if response_rate < 10:
    insights.append("Response rate below 10%. Tailor your resume more to each job description.")
elif response_rate < 25:
    insights.append("Moderate response rate. Add a personalised cover letter to boost callbacks.")
else:
    insights.append("Great response rate! Keep applying with the same approach.")

if 'Source' in df.columns:
    best_src = df[df['Status'].isin([STATUS['SHORTLISTED'], STATUS['INTERVIEW'], STATUS['OFFER']])]
    if not best_src.empty:
        top_source = best_src['Source'].value_counts().idxmax()
        insights.append(f"**{top_source}** is your most effective source - focus more applications there.")

df_resp = df[df['Response Date'].notna() & df['Date Applied'].notna()].copy()
if not df_resp.empty:
    df_resp['days_to_resp'] = (df_resp['Response Date'] - df_resp['Date Applied']).dt.days
    avg_days = df_resp['days_to_resp'].mean()
    insights.append(f"Average time to response: **{avg_days:.0f} days**.")

if interviews > 0:
    conversion = offers / interviews * 100
    insights.append(f"Interview to Offer rate: **{conversion:.0f}%** ({offers}/{interviews}).")
    if conversion < 30:
        insights.append("Low offer conversion - focus on interview prep (mock interviews, STAR method).")

ghosted = df[df['Status'] == STATUS['GHOSTED']].shape[0]
if ghosted > 5:
    insights.append(f"{ghosted} applications ghosted. Set follow-up reminders 2 weeks after applying.")

for insight in insights:
    st.markdown(f'<div class="insight-box">{insight}</div>', unsafe_allow_html=True)

# ---- Table ----
st.markdown("---")
st.subheader("All Applications")
f1, f2, f3 = st.columns(3)
with f1:
    status_filter = st.multiselect("Filter by Status", list(STATUS.values()), default=list(STATUS.values()))
with f2:
    sources = df['Source'].dropna().unique().tolist()
    source_filter = st.multiselect("Filter by Source", sources, default=sources)
with f3:
    days_filter = st.slider("Last N days", 7, 365, 90)

cutoff = datetime.today() - timedelta(days=days_filter)
filtered = df[
    (df['Status'].isin(status_filter)) &
    (df['Source'].isin(source_filter) if source_filter else True) &
    (df['Date Applied'] >= cutoff)
].copy()

filtered['Date Applied'] = filtered['Date Applied'].dt.strftime('%d %b %Y')
filtered['Last Updated'] = filtered['Last Updated'].dt.strftime('%d %b %Y')

st.dataframe(
    filtered[['Date Applied', 'Company', 'Role', 'Source', 'Status', 'Last Updated', 'Notes']],
    use_container_width=True, height=400
)
st.caption(f"Showing {len(filtered)} of {total} applications")
