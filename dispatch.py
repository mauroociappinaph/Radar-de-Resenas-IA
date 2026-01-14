from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def dispatch_emails(limit: int = 50):
    print(f"🚀 Starting dispatch process (DRAFT MODE) - Limit: {limit}...")
    response = supabase.table("leads").select("*").eq("status", "analyzed").limit(limit).execute()
    leads = response.data
    if not leads: return

    for lead in leads:
        print(f"--- [DRAFT FOR: {lead['business_name']} ({lead['contact_email']})] ---")
        print(f"Subject: {lead.get('email_subject', 'No Subject')}")
        print(lead['email_draft'])
        print("-" * 40)
        supabase.table("leads").update({"status": "contacted"}).eq("id", lead["id"]).execute()

if __name__ == "__main__":
    dispatch_emails()
