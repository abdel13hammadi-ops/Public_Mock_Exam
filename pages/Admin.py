import streamlit as st

st.set_page_config(page_title="Admin", layout="wide")
st.title("Admin")

if st.session_state.get("admin_unlocked"):
    st.success("Admin is already unlocked for this browser session.")
    if st.button("Lock Admin"):
        st.session_state["admin_unlocked"] = False
        st.rerun()
else:
    st.info("Enter the admin password to unlock admin pages for this browser session.")
    password = st.text_input("Admin password", type="password")
    if st.button("Unlock Admin", type="primary"):
        expected = str(st.secrets.get("ADMIN_PASSWORD", "")).strip()
        if expected and password == expected:
            st.session_state["admin_unlocked"] = True
            st.success("Admin unlocked. You can now open admin pages from the sidebar.")
            st.rerun()
        else:
            st.error("Incorrect admin password or ADMIN_PASSWORD is missing in Streamlit Secrets.")
