import json

import pandas as pd
import streamlit as st
from supabase import create_client

APP_VERSION = "MY_PROGRESS_V6_ENROLLED_CERT_ACCESS"
PUBLIC_ACCESS_MODE = True
PUBLIC_GUEST_EMAIL = "public.guest@example.com"
PAID_STATUS_VALUES = {"active", "paid", "trialing", "premium", "subscribed"}

PAID_STATUS_VALUES = {"active", "paid", "premium", "subscribed", "trialing"}

st.set_page_config(page_title="My Progress", layout="wide", initial_sidebar_state="expanded")


def get_supabase_client():
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        st.error("Supabase secrets are missing. Add SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in Streamlit secrets.")
        st.stop()
    return create_client(url, key)


def get_current_user_email():
    email = str(st.session_state.get("user_email", "") or st.session_state.get("account_email", "")).strip().lower()
    if email and "@" in email and "." in email.split("@")[-1]:
        return email
    if PUBLIC_ACCESS_MODE:
        return PUBLIC_GUEST_EMAIL
    return None

@st.cache_data(ttl=60)
def fetch_user_profile(email):
    if not email:
        return {}
    supabase = get_supabase_client()
    result = (
        supabase.table("app_users")
        .select("email,full_name,subscription_status,preferred_language_code")
        .eq("email", email)
        .limit(1)
        .execute()
    )
    return (result.data or [{"email": email, "full_name": "Public Guest", "subscription_status": "active", "preferred_language_code": "en"}])[0]


@st.cache_data(ttl=60)
def fetch_languages():
    supabase = get_supabase_client()
    try:
        result = (
            supabase.table("languages")
            .select("language_code,language_name,native_name,is_active,display_order")
            .eq("is_active", True)
            .order("display_order")
            .execute()
        )
        return result.data or []
    except Exception:
        return [{"language_code": "en", "language_name": "English", "native_name": "English"}]


@st.cache_data(ttl=60)
@st.cache_data(ttl=60)
def fetch_user_certifications(user_email=None):
    # TEMPORARY PUBLIC ACCESS: show every active certification without requiring user_certification_access.
    try:
        result = (
            get_supabase_client().table("certifications")
            .select("exam_name,display_name,certification_code,passing_score,time_limit_minutes,question_count,is_active")
            .eq("is_active", True)
            .order("display_name")
            .execute()
        )
        return result.data or []
    except Exception:
        return []

def language_label(language_code):
    languages = fetch_languages()
    for lang in languages:
        if lang.get("language_code") == language_code:
            native = lang.get("native_name") or lang.get("language_name") or language_code
            return f"{native} ({language_code})"
    return language_code


def require_paid_access(profile):
    # TEMPORARY PUBLIC ACCESS: progress page is open.
    st.success("Public access mode ✅ My Progress unlocked")
    return "active"

@st.cache_data(ttl=60)
def load_attempts(user_email, exam_name, language_code):
    if not user_email or not exam_name or not language_code:
        return []
    supabase = get_supabase_client()
    result = (
        supabase.table("exam_attempts")
        .select("id,user_email,mode,category,score,correct_answers,total_questions,domain_breakdown,completed_at,exam_name,language_code")
        .eq("user_email", user_email)
        .eq("exam_name", exam_name)
        .eq("language_code", language_code)
        .order("id", desc=True)
        .execute()
    )
    return result.data or []


def normalize_breakdown(value):
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def make_domain_table(attempts):
    totals = {}
    for attempt in attempts:
        breakdown = normalize_breakdown(attempt.get("domain_breakdown"))
        for name, data in breakdown.items():
            if not isinstance(data, dict):
                continue
            correct = int(data.get("correct", 0) or 0)
            total = int(data.get("total", 0) or 0)
            if name not in totals:
                totals[name] = {"correct": 0, "total": 0}
            totals[name]["correct"] += correct
            totals[name]["total"] += total

    rows = []
    for name, data in totals.items():
        total = data["total"]
        correct = data["correct"]
        percent = round((correct / total) * 100, 2) if total else 0
        rows.append({"Domain": name, "Correct": correct, "Total": total, "Accuracy %": percent})
    return pd.DataFrame(rows).sort_values("Accuracy %") if rows else pd.DataFrame()


st.title("My Progress")
st.caption(f"App version: {APP_VERSION}")

user_email = get_current_user_email()

profile = fetch_user_profile(user_email)
require_paid_access(profile)

preferred_language = str(profile.get("preferred_language_code") or "en").strip().lower()
st.info(f"Account: {user_email} | Preferred language: {language_label(preferred_language)}")

certifications = fetch_user_certifications(user_email)
if not certifications:
    st.error("No certification enrollment found for this account.")
    st.info("Ask an admin to enroll this email in a certification, or purchase access when payments are enabled.")
    st.stop()

exam_names = [c["exam_name"] for c in certifications]
display_by_exam = {c["exam_name"]: c.get("display_name") or c["exam_name"] for c in certifications}
selected_exam = st.selectbox(
    "Choose certification for progress",
    exam_names,
    format_func=lambda x: display_by_exam.get(x, x),
    key="my_progress_exam_name",
)

attempts = load_attempts(user_email, selected_exam, preferred_language)

if not attempts:
    st.info("No attempts found for this certification and language yet. Complete a mock exam or practice set first.")
    st.stop()

scores = [float(a.get("score") or 0) for a in attempts]
latest_score = float(attempts[0].get("score") or 0)
average_score = round(sum(scores) / len(scores), 2) if scores else 0
best_score = round(max(scores), 2) if scores else 0
attempt_count = len(attempts)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Latest Score", f"{latest_score}%")
c2.metric("Average Score", f"{average_score}%")
c3.metric("Best Score", f"{best_score}%")
c4.metric("Attempts", attempt_count)

st.divider()
st.header("Weak Areas by Domain")
domain_df = make_domain_table(attempts)
if domain_df.empty:
    st.warning("No domain breakdown data saved yet.")
else:
    st.dataframe(domain_df, use_container_width=True, hide_index=True)
    weakest = domain_df.iloc[0]
    st.info(f"Weakest domain: {weakest['Domain']} ({weakest['Accuracy %']}%)")

st.divider()
st.header("Attempt History")
history_rows = []
for attempt in attempts:
    history_rows.append({
        "Attempt ID": attempt.get("id"),
        "Completed At": attempt.get("completed_at") or "Not recorded",
        "Mode": attempt.get("mode"),
        "Category": attempt.get("category"),
        "Score %": attempt.get("score"),
        "Correct": attempt.get("correct_answers"),
        "Total": attempt.get("total_questions"),
    })
st.dataframe(pd.DataFrame(history_rows), use_container_width=True, hide_index=True)

st.divider()
st.header("Recommendation")
if not domain_df.empty:
    weakest = domain_df.iloc[0]
    st.write(f"Focus next on **{weakest['Domain']}** for **{display_by_exam.get(selected_exam, selected_exam)}**.")
else:
    st.write("Complete more attempts to generate recommendations.")
