import os
import json
import subprocess
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# Set page config
st.set_page_config(
    page_title="Ownly Review Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
    <style>
    .main {
        background-color: #f7f9fc;
    }
    .stAlert {
        border-radius: 10px;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 5px solid #319795;
        margin-bottom: 20px;
    }
    .metric-header {
        font-size: 14px;
        color: #718096;
        text-transform: uppercase;
        font-weight: bold;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 800;
        color: #1a202c;
    }
    </style>
""", unsafe_allow_html=True)

# Helper to check if analysis files exist
def check_files_exist():
    return (
        os.path.exists("weekly_note.md") and
        os.path.exists("themes_roadmap.csv") and
        os.path.exists("strategy_qa.json") and
        os.path.exists("consolidated_reviews.json")
    )

# Sidebar
st.sidebar.image("https://raw.githubusercontent.com/rapido-labs/rapido-brand-assets/main/logo.png", width=120)
st.sidebar.title("Ownly Analytics")
st.sidebar.markdown("---")

# Pipeline runner trigger
st.sidebar.subheader("Pipeline Actions")
if st.sidebar.button("🚀 Run Analysis Pipeline"):
    with st.spinner("Running review aggregation and analysis..."):
        try:
            # Run run_analyzer.py in a subprocess
            result = subprocess.run(["python3", "run_analyzer.py"], capture_output=True, text=True, check=True)
            st.sidebar.success("Analysis executed successfully! ✅")
            st.rerun()
        except subprocess.CalledProcessError as e:
            st.sidebar.error("Pipeline run failed! ❌")
            st.sidebar.code(e.stderr)

# Check data availability
if not check_files_exist():
    st.title("📊 Ownly Review Intelligence Dashboard")
    st.warning("⚠️ No compiled review analysis data found. Please trigger the pipeline to generate reports.")
    st.info("💡 You can run the pipeline by clicking the **🚀 Run Analysis Pipeline** button in the sidebar.")
    st.stop()

# Load Data
@st.cache_data
def load_reviews():
    with open("consolidated_reviews.json", "r") as f:
        return json.load(f)

@st.cache_data
def load_themes():
    return pd.read_csv("themes_roadmap.csv")

@st.cache_data
def load_qa():
    with open("strategy_qa.json", "r") as f:
        return json.load(f)

@st.cache_data
def load_weekly_note():
    with open("weekly_note.md", "r") as f:
        return f.read()

reviews_raw = load_reviews()
themes_df = load_themes()
qa_data = load_qa()
weekly_note_md = load_weekly_note()

# Sidebar downloads
st.sidebar.subheader("Export Reports")
if os.path.exists("email_draft.html"):
    with open("email_draft.html", "r") as f:
        html_content = f.read()
    st.sidebar.download_button(
        "📥 Download HTML Newsletter",
        data=html_content,
        file_name="ownly_weekly_newsletter.html",
        mime="text/html"
    )

if os.path.exists("weekly_note.md"):
    st.sidebar.download_button(
        "📝 Download Executive Note (MD)",
        data=weekly_note_md,
        file_name="ownly_weekly_pulse_note.md",
        mime="text/plain"
    )

st.sidebar.markdown("---")
st.sidebar.subheader("📧 Send Report via Email")
recipient_input = st.sidebar.text_input("Recipient Email:", placeholder="manager@ownly.com")

if st.sidebar.button("📨 Send Report"):
    if not recipient_input:
        st.sidebar.warning("Please enter a valid email address.")
    else:
        if os.path.exists("email_draft.html"):
            with open("email_draft.html", "r") as f:
                html_content = f.read()
            
            from phase4_delivery.delivery import EmailDeliverer
            deliverer = EmailDeliverer()
            
            if not deliverer.is_configured():
                st.sidebar.error("SMTP credentials (SMTP_USER/SMTP_PASS) are not configured in `.env`.")
            else:
                with st.spinner("Sending report..."):
                    from datetime import datetime
                    date_str = datetime.now().strftime("%B %d, %Y")
                    subject = f"Ownly App Review Weekly Pulse Note - {date_str}"
                    success = deliverer.send_email(subject, html_content, recipient=recipient_input)
                    if success:
                        st.sidebar.success(f"Report sent to {recipient_input}! ✅")
                    else:
                        st.sidebar.error("Failed to send email. Check console logs.")
        else:
            st.sidebar.error("No email report compiled yet. Please run the analysis first.")

# Convert reviews to DataFrame for charting
df = pd.DataFrame(reviews_raw)
if "rating" in df.columns:
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
if "theme" not in df.columns:
    df["theme"] = "General / Uncategorized"

# Title Banner
st.markdown("""
<div style="background: linear-gradient(135deg, #1A365D 0%, #2A4365 100%); padding: 30px; border-radius: 12px; margin-bottom: 25px; color: white;">
    <h1 style="margin: 0; font-size: 32px; font-weight: 800;">Ownly Review Intelligence</h1>
    <p style="margin: 5px 0 0 0; color: #cbd5e0; font-size: 16px;">Zero-Commission Food Delivery - Strategic Customer & Partner Feedback Insights (Last 7 Weeks)</p>
</div>
""", unsafe_allow_html=True)

# Metrics Row
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-header">Total Feedback Reviews</div>
        <div class="metric-value">{len(df)}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    avg_rating = df["rating"].mean()
    rating_display = f"{avg_rating:.2f} / 5.0" if not pd.isna(avg_rating) else "N/A"
    st.markdown(f"""
    <div class="metric-card" style="border-left-color: #3182ce;">
        <div class="metric-header">Average Store Rating</div>
        <div class="metric-value">{rating_display}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    scrubbed_count = df["text"].str.contains(r"\[EMAIL\]|\[PHONE\]").sum()
    st.markdown(f"""
    <div class="metric-card" style="border-left-color: #805ad5;">
        <div class="metric-header">PII Masked Incidents</div>
        <div class="metric-value">{scrubbed_count}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    unique_sources = df["source"].nunique()
    st.markdown(f"""
    <div class="metric-card" style="border-left-color: #dd6b20;">
        <div class="metric-header">Active Channels</div>
        <div class="metric-value">{unique_sources}</div>
    </div>
    """, unsafe_allow_html=True)

# Main layout split
left_col, right_col = st.columns([1, 1])

with left_col:
    st.subheader("📋 Core Strategic Insights")
    
    # Show themes
    st.markdown("#### Discovered Feedback Themes")
    for _, row in themes_df.iterrows():
        st.info(f"**{row['Theme Name']}**\n\n{row['Description']}")

    st.markdown("---")
    
    # Q&As in Expanders
    st.markdown("#### Deep-Dive Product Strategy Answers")
    
    with st.expander("🔍 Users' struggle points on the app"):
        st.write(qa_data.get("struggle_points", "N/A"))
        
    with st.expander("🛒 Most common frustrations while ordering"):
        st.write(qa_data.get("ordering_frustrations", "N/A"))
        
    with st.expander("🛵 Delivery partner and user operational issues"):
        st.write(qa_data.get("delivery_partner_and_user_issues", "N/A"))
        
    with st.expander("🔄 Causes for switching back to Zomato/Swiggy"):
        st.write(qa_data.get("switch_causes_and_loyalty_barriers", "N/A"))
        
    with st.expander("💡 Customer discovery challenges"):
        st.write(qa_data.get("discovery_challenges", "N/A"))
        
    with st.expander("🎁 Unmet feature requests & customer needs"):
        st.write(qa_data.get("unmet_needs", "N/A"))

with right_col:
    st.subheader("📊 Data Visualizations & Feed")
    
    # Chart tabs
    tab1, tab2 = st.tabs(["Channel Share", "Ratings Distribution"])
    
    with tab1:
        # Pie chart for channel source distributions
        source_counts = df["source"].value_counts().reset_index()
        source_counts.columns = ["source", "count"]
        fig1 = px.pie(
            source_counts,
            names="source",
            values="count",
            color_discrete_sequence=px.colors.qualitative.Pastel,
            title="Review Share by Channels"
        )
        st.plotly_chart(fig1, use_container_width=True)
        
    with tab2:
        # Bar chart for ratings
        ratings_df = df[df["rating"].notna()]
        if not ratings_df.empty:
            ratings_count = ratings_df["rating"].value_counts().reset_index()
            ratings_count.columns = ["rating", "count"]
            ratings_count = ratings_count.sort_values("rating")
            fig2 = px.bar(
                ratings_count,
                x="rating",
                y="count",
                labels={"rating": "Rating (Stars)", "count": "Reviews Count"},
                color="rating",
                color_continuous_scale=px.colors.sequential.Teal,
                title="Customer Ratings Count"
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No rating data available (all channels are social mocks/text only).")

    st.markdown("---")

    # Action Items checklist using Streamlit session state
    st.markdown("#### Strategic Action Item Tracker")
    
    # Initialize checklist in session state
    if "todo_items" not in st.session_state:
        # Parse action items from weekly note
        parsed_actions = []
        lines = weekly_note_md.split("\n")
        action_section = False
        for line in lines:
            if "Strategic Action Ideas" in line or "Action Ideas" in line:
                action_section = True
                continue
            if action_section and line.strip().startswith("-"):
                parsed_actions.append(line.replace("-", "").strip())
            elif action_section and line.strip() and line.strip()[0].isdigit() and "." in line:
                parts = line.split(".", 1)
                if len(parts) > 1:
                    parsed_actions.append(parts[1].strip())
            elif action_section and line.startswith("#"):
                action_section = False
                
        if not parsed_actions:
            parsed_actions = [
                "Optimize Cart Performance & UPI Fallbacks",
                "Launch Live In-App Chat Support Channel",
                "Enhance Delivery Partner Dispatch Operations"
            ]
        st.session_state.todo_items = {item: False for item in parsed_actions}

    # Render checklist
    for item in list(st.session_state.todo_items.keys()):
        status = st.checkbox(item, value=st.session_state.todo_items[item], key=f"todo_{item}")
        st.session_state.todo_items[item] = status

    # Allow custom items
    new_todo = st.text_input("➕ Add custom growth initiative:")
    if st.button("Add Initiative"):
        if new_todo and new_todo.strip() not in st.session_state.todo_items:
            st.session_state.todo_items[new_todo.strip()] = False
            st.rerun()

st.markdown("---")

# Interactive Reviews Feed
st.subheader("🔍 Interactive Review Search Feed")

col_f1, col_f2, col_f3, col_f4 = st.columns([1, 1, 1, 2])
with col_f1:
    source_filter = st.selectbox("Filter by Source", ["All"] + list(df["source"].unique()))
with col_f2:
    if "rating" in df.columns and df["rating"].notna().sum() > 0:
        ratings_available = ["All"] + [str(int(r)) for r in sorted(df["rating"].dropna().unique())]
        rating_filter = st.selectbox("Filter by Rating", ratings_available)
    else:
        rating_filter = st.selectbox("Filter by Rating", ["All"])
with col_f3:
    theme_filter = st.selectbox("Filter by Theme", ["All"] + list(df["theme"].unique()))
with col_f4:
    search_query = st.text_input("Search Review Comments", "")

# Apply filters
filtered_df = df.copy()
if source_filter != "All":
    filtered_df = filtered_df[filtered_df["source"] == source_filter]
if rating_filter != "All":
    filtered_df = filtered_df[filtered_df["rating"] == int(rating_filter)]
if theme_filter != "All":
    filtered_df = filtered_df[filtered_df["theme"] == theme_filter]
if search_query:
    filtered_df = filtered_df[
        filtered_df["text"].str.contains(search_query, case=False, na=False) |
        filtered_df["title"].str.contains(search_query, case=False, na=False)
    ]

st.write(f"Showing **{len(filtered_df)}** filtered reviews:")

# Prevent Pyarrow mixed-type serialization errors by casting rating to string
display_df = filtered_df[["source", "rating", "theme", "title", "text", "date"]].copy()
if "rating" in display_df.columns:
    display_df["rating"] = display_df["rating"].fillna("N/A").astype(str)

st.dataframe(
    display_df,
    use_container_width=True
)

# Export Data Button
csv_data = filtered_df.to_csv(index=False).encode('utf-8')
st.download_button(
    "📥 Download Filtered Dataset (CSV)",
    data=csv_data,
    file_name="ownly_filtered_reviews.csv",
    mime="text/csv"
)
