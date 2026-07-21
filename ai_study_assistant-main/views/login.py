import streamlit as st
from utils.auth import sign_in, sign_up


def show_login_page():
    st.title("🎓 AI Study Assistant")
    st.subheader("Your intelligent study companion")
    st.write("Sign in to save your sessions, track progress and access your study history.")

    tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])

    with tab1:
        st.subheader("Welcome back!")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Login", use_container_width=True):
                if email and password:
                    with st.spinner("Signing in..."):
                        user, error = sign_in(email, password)
                        if user:
                            st.session_state.user = user
                            st.session_state.session_id = None
                            st.success("Logged in successfully! ✅")
                            st.rerun()
                        else:
                            st.error(f"Login failed: {error}")
                else:
                    st.warning("Please fill in all fields.")

        with col2:
            if st.button("Continue as Guest", use_container_width=True):
                st.session_state.user = None
                st.session_state.guest_mode = True
                st.rerun()

    with tab2:
        st.subheader("Create an account")
        full_name = st.text_input("Full Name", key="signup_name")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        confirm = st.text_input("Confirm Password", type="password", key="signup_confirm")

        if st.button("Sign Up", use_container_width=True):
            if full_name and email and password and confirm:
                if password != confirm:
                    st.error("Passwords do not match!")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters!")
                else:
                    with st.spinner("Creating account..."):
                        user, error = sign_up(email, password, full_name)
                        if user:
                            st.success("Account created! Please check your email to verify. ✅")
                        else:
                            st.error(f"Sign up failed: {error}")
            else:
                st.warning("Please fill in all fields.")
