from utils.supabase_client import supabase
import time


def ensure_profile_exists(user):
    """Make sure a profile exists for the user."""
    try:
        existing = supabase.table("profiles")\
            .select("id")\
            .eq("id", user.id)\
            .execute()

        if not existing.data:
            supabase.table("profiles").insert({
                "id": user.id,
                "email": user.email,
                "full_name": user.user_metadata.get(
                    "full_name", user.email
                )
            }).execute()
        return True
    except Exception as e:
        print(f"Profile ensure failed: {e}")
        return False


def sign_up(email, password, full_name):
    """Register a new user."""
    try:
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {"full_name": full_name}
            }
        })
        user = response.user
        if user:
            time.sleep(1)
            ensure_profile_exists(user)
        return user, None
    except Exception as e:
        error_msg = str(e)
        if "rate limit" in error_msg.lower() or "429" in error_msg:
            return None, "Too many signup attempts. Please wait a few minutes and try again."
        elif "already registered" in error_msg.lower():
            return None, "This email is already registered. Please login instead."
        return None, error_msg


def sign_in(email, password):
    """Sign in an existing user."""
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        user = response.user
        if user:
            ensure_profile_exists(user)
        return user, None
    except Exception as e:
        error_msg = str(e)
        if "invalid" in error_msg.lower():
            return None, "Invalid email or password. Please try again."
        return None, error_msg


def sign_out():
    """Sign out the current user."""
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
