import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from exa_py import Exa
from supabase import create_client, Client
from dotenv import load_dotenv
import re
from fake_useragent import UserAgent
from email_validator import validate_email, EmailNotValidError
from sentiment_analyzer import get_sentiment_analyzer

load_dotenv()

EXA_API_KEY = os.getenv("EXA_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

exa = Exa(api_key=EXA_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
ua = UserAgent()

def classify_email(email: str) -> str:
    if not email: return "unknown"
    generic_prefixes = [
        'info', 'contact', 'contacto', 'hello', 'hola', 'admin', 'sales', 'support', 'office',
        'recepcion', 'citas', 'reservas', 'team', 'ventas', 'atencion', 'soporte', 'groupbookings',
        'gerencia', 'comercial', 'ayuda', 'marketing', 'press', 'hr', 'jobs', 'careers',
        'klantenservice', 'affiliate', 'customer', 'serviciocliente', 'atencionalcliente', 'servicedesk',
        'management', 'hq', 'feedback', 'donations', 'privacy', 'legal'
    ]
    prefix = email.split('@')[0].lower()
    prefix_clean = re.sub(r'\d+', '', prefix)
    if any(gp == prefix_clean for gp in generic_prefixes): return "generic"
    return "personal"

async def fetch_webpage(url: str) -> str:
    """Fetch webpage content asynchronously."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={'User-Agent': ua.random}, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                html = await response.text()
                return BeautifulSoup(html, 'html.parser').get_text()
    except Exception as e:
        print(f"   ⚠️ Could not fetch webpage {url}: {e}")
        return ""

async def fetch_review_context(business_name: str, city: str) -> str:
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

async def process_lead(lead: dict) -> None:
    """Process a single lead asynchronously."""
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
            page_text = await fetch_webpage(website)

        # Refined Email Regex
        emails = set(re.findall(r'[a-zA-Z0-9\._%+-]+@[a-zA-Z0-9\.-]+\.[a-zA-Z]{2,}', page_text))
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

    review_context = await fetch_review_context(name, city)

    # Analyze sentiment of review context
    sentiment_analyzer = get_sentiment_analyzer(use_bert=False)  # Use VADER for speed
    sentiment_result = sentiment_analyzer.analyze_sentiment(review_context)

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
        "review_context": review_context,
        "sentiment_score": sentiment_result['sentiment_score'],
        "sentiment_label": sentiment_result['sentiment_label'],
        "sentiment_confidence": sentiment_result['confidence'],
        "key_emotions": sentiment_result['key_emotions']
    }).eq("id", lead_id).execute()
    print(f"✅ Enriched {name}")

async def enrich_leads(limit: int = 50, max_concurrency: int = 5):
    print(f"🕵️‍♂️ Starting enrichment process - Limit: {limit}, Max concurrency: {max_concurrency}...")
    response = supabase.table("leads").select("*").eq("status", "scouted").limit(limit).execute()
    leads = response.data
    if not leads: return

    # Create semaphore for rate limiting
    semaphore = asyncio.Semaphore(max_concurrency)

    async def process_with_semaphore(lead):
        async with semaphore:
            await process_lead(lead)

    # Process leads concurrently
    await asyncio.gather(*[process_with_semaphore(lead) for lead in leads])

if __name__ == "__main__":
    asyncio.run(enrich_leads())
