import os
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


def get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key)


def get_supabase_client():
    """Create and return a Supabase client."""
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_ANON_KEY")
    if not url or not key:
        raise ValueError("Supabase credentials not found.")
    return create_client(url, key)


supabase: Client = get_supabase_client()
