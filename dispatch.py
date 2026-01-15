import os
import smtplib
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", SMTP_USER)
LIVE_MODE = os.getenv("LIVE_MODE", "false").lower() == "true"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def is_html_content(content):
    """Detecta si el contenido es HTML."""
    return bool(re.search(r'<[^>]+>', content))

def send_email(to_email, subject, body):
    if not LIVE_MODE:
        content_type = "HTML" if is_html_content(body) else "TEXT"
        print(f"🏜️ [DRAFT MODE] To: {to_email} | Subject: {subject} | Type: {content_type}")
        return True

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject

        # Detectar si es HTML o texto plano
        if is_html_content(body):
            msg.attach(MIMEText(body, 'html'))
            print(f"📧 Sending HTML email to: {to_email}")
        else:
            msg.attach(MIMEText(body, 'plain'))
            print(f"📧 Sending TEXT email to: {to_email}")

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"✅ Email SENT to: {to_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
        return False

def dispatch_emails(limit: int = 50):
    print(f"🚀 Starting dispatch process ({'LIVE' if LIVE_MODE else 'DRAFT'} MODE) - Limit: {limit}...")
    response = supabase.table("leads").select("*").eq("status", "analyzed").limit(limit).execute()
    leads = response.data
    if not leads:
        print("📭 No leads ready to dispatch.")
        return

    for lead in leads:
        to_email = lead['contact_email']
        subject = lead.get('email_subject', f"Propuesta para {lead['business_name']}")
        body = lead['email_draft']

        if send_email(to_email, subject, body):
            supabase.table("leads").update({"status": "contacted"}).eq("id", lead["id"]).execute()
            print(f"✔️ {lead['business_name']} marked as contacted.")

if __name__ == "__main__":
    dispatch_emails()
