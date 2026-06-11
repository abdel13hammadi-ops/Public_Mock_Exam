import streamlit as st
from supabase import create_client

# TEMPORARY: public access is enabled so users can use the site without an account.
PUBLIC_ACCESS_MODE = True
PUBLIC_GUEST_EMAIL = "public.guest@example.com"

PAID_STATUS = "active"
FREE_STATUS = "free"
PAID_STATUS_VALUES = {"active", "paid", "trialing", "premium", "subscribed"}


def get_supabase_client():
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        st.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in Streamlit secrets.")
        st.stop()
    return create_client(url, key)


def get_current_user_email():
    email = st.session_state.get("user_email", "") or st.session_state.get("account_email", "")
    email = str(email).strip().lower()
    if email and "@" in email:
        return email
    if PUBLIC_ACCESS_MODE:
        return PUBLIC_GUEST_EMAIL
    return None


def get_current_user():
    email = get_current_user_email()
    if not email:
        return None
    return {
        "email": email,
        "auth_user_id": st.session_state.get("auth_user_id"),
        "full_name": st.session_state.get("full_name", "Public Guest" if email == PUBLIC_GUEST_EMAIL else ""),
        "preferred_language_code": st.session_state.get("preferred_language_code", "en"),
    }


def get_user_profile(email=None):
    email = (email or get_current_user_email() or "").strip().lower()
    if not email:
        return None
    if PUBLIC_ACCESS_MODE and email == PUBLIC_GUEST_EMAIL:
        return {"email": PUBLIC_GUEST_EMAIL, "subscription_status": "active", "preferred_language_code": "en", "full_name": "Public Guest"}
    try:
        result = (
            get_supabase_client().table("app_users")
            .select("*")
            .eq("email", email)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
    except Exception:
        pass
    if PUBLIC_ACCESS_MODE:
        return {"email": email, "subscription_status": "active", "preferred_language_code": "en", "full_name": "Public Guest"}
    return None


def get_subscription_status(email=None):
    if PUBLIC_ACCESS_MODE:
        return "active"
    profile = get_user_profile(email=email)
    if not profile:
        return FREE_STATUS
    return str(profile.get("subscription_status") or FREE_STATUS).strip().lower()


def get_user_subscription_status(email=None):
    return get_subscription_status(email=email)


def is_paid_user(email=None):
    return get_subscription_status(email=email) in PAID_STATUS_VALUES


def get_preferred_language_code(email=None):
    profile = get_user_profile(email=email)
    if profile:
        return str(profile.get("preferred_language_code") or "en").strip().lower()
    return str(st.session_state.get("preferred_language_code", "en") or "en").strip().lower()


def require_login():
    email = get_current_user_email()
    if not email:
        st.warning("Please go to the Account page and log in first.")
        st.stop()
    return email


def require_paid_access(feature_name="This feature"):
    if PUBLIC_ACCESS_MODE:
        return True
    email = require_login()
    status = get_subscription_status(email=email)
    if status not in PAID_STATUS_VALUES:
        st.error(f"{feature_name} is available for paid users only.")
        st.info("Please upgrade your account to unlock this feature.")
        st.stop()
    return True


def admin_unlocked():
    return bool(st.session_state.get("admin_unlocked", False))


def check_admin_password(password: str) -> bool:
    expected = str(st.secrets.get("ADMIN_PASSWORD", "")).strip()
    return bool(expected) and str(password or "") == expected


def require_admin_access():
    if admin_unlocked():
        return True
    st.error("Admin access required.")
    st.info("Open the Admin page and enter the admin password first.")
    st.stop()


def render_sidebar_navigation():
    # Safe no-op/custom nav placeholder. Keeping this function prevents ImportError in pages.
    try:
        st.sidebar.caption("Salesforce Cert Prep")
        if PUBLIC_ACCESS_MODE:
            st.sidebar.success("Public access mode")
    except Exception:
        pass
