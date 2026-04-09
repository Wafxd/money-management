import os
from supabase import create_client, Client
import google.generativeai as genai

# --- CONFIG HARDCODE AMAN UNTUK VERCEL ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# --- CONFIG EMAIL PENGIRIM OTP ---
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")

# Inisialisasi Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print("GAGAL KONEK SUPABASE:", e)
    supabase = None

# Inisialisasi Gemini AI
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)