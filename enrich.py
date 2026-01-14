import os
import requests
from bs4 import BeautifulSoup
from exa_py import Exa
from supabase import create_client, Client
from dotenv import load_dotenv
import re
from fake_useragent import UserAgent
from email_validator import validate_email, EmailNotValidError

load_dotenv()

EXA_API_KEY = os.getenv("EXA_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

exa = Exa(api_key=EXA_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
ua = UserAgent()

def classify_email(email: str) -> str:
    if not email: return "unknown"
    generic_prefixes = ['info', 'contact', 'contacto', 'hello', 'hola', 'admin', 'sales', 'support', 'office', 'recepcion', 'citas', 'reservas', 'team']
    prefix = email.split('@')[0].lower()
    prefix_clean = re.sub(r'\d+', '', prefix)
    if prefix_clean in generic_prefixes: return "generic"
    return "personal"

def fetch_review_context(business_name: str, city: str) -> str:
    print(f"   🔍 Fetching Contextual Insights for {business_name}...")
    try:
        query = f"customer reviews complaints and praises for '{business_name}' in {city}"
        search_response = exa.search_and_contents(query, num_results=3, text=True, highlights=True)
        context_parts = []
        for result in search_response.results:
            if result.highlights: context_parts.append("\n".join(result.highlights))
            elif result.text: context_parts.append(result.text[:500] + "...")
        return "\n---\n".join(context_parts) if context_parts else "No specific recent reviews found."
    except Exception as e:
        print(f"   ⚠️ Could not fetch review context: {e}")
        return "Context fetch failed."

def enrich_leads(limit: int = 50):
    print(f"🕵️‍♂️ Starting enrichment process - Limit: {limit}...")
    response = supabase.table("leads").select("*").eq("status", "scouted").limit(limit).execute()
    leads = response.data
    if not leads: return

    for lead in leads:
        lead_id, name, website, city = lead.get("id"), lead.get("business_name"), lead.get("website_url"), lead.get("city")
        print(f"🔥 Analyzing: {website}...")
        email = None
        source_url = website
        try:
            search_response = exa.search_and_contents(f"site:{website.split('//')[-1].split('/')[0]} contact page 'email'", num_results=1, text=True)
            if search_response.results:
                result = search_response.results[0]
                source_url, page_text = result.url, result.text
            else:
                page = requests.get(website, headers={'User-Agent': ua.random}, timeout=10)
                page_text = BeautifulSoup(page.content, 'html.parser').get_text()

            emails = set(re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', page_text))
            filtered_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.js', '.css'))]
            for e in filtered_emails:
                if classify_email(e) == "personal":
                    email = e
                    break
            if not email and filtered_emails: email = filtered_emails[0]

            if not email:
                domain = website.split('//')[-1].split('/')[0].replace("www.", "")
                for alias in ["info", "contact", "admin"]:
                    guessed = f"{alias}@{domain}"
                    try:
                        validate_email(guessed, check_deliverability=True)
                        email = guessed
                        break
                    except: continue
        except Exception as e: print(f"   ❌ Enrichment failed: {e}")

        review_context = fetch_review_context(name, city)
        email_valid = False
        if email:
            try:
                v = validate_email(email, check_deliverability=True)
                email, email_valid = v["email"], True
            except: email_valid = False

        supabase.table("leads").update({
            "status": "enriched",
            "contact_email": email,
            "email_type": classify_email(email),
            "email_valid": email_valid,
            "review_context": review_context
        }).eq("id", lead_id).execute()
        print(f"✅ Enriched {name}")

if __name__ == "__main__":
    enrich_leads()
