import os
import time
import re
from openai import OpenAI
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if OPENROUTER_API_KEY:
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
    MODEL_NAME = "xiaomi/mimo-v2-flash:free"
else:
    client = None

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_rating_status(stars):
    try:
        if stars is None or str(stars).lower() == 'none': return "Visibility (Unknown digital presence)"
        s = float(stars)
        if s == 0: return "Visibility (No reviews yet)"
        if s < 4.0: return "Crisis Management (Low rating)"
        return "Optimization (High rating)"
    except: return "Visibility"

def analyze_leads(limit: int = 50):
    print(f"🧠 Starting analysis process - Limit: {limit}...")
    response = supabase.table("leads").select("*").eq("status", "enriched").eq("email_valid", True).eq("email_type", "personal").limit(limit).execute()
    leads = response.data
    if not leads: return

    for lead in leads:
        lead_id, name, niche, city, rating = lead.get("id"), lead.get("business_name"), lead.get("niche", "Business"), lead.get("city", "the city"), lead.get("rating")
        review_context = lead.get("review_context", "No direct reviews found.")
        if not client: break

        key_issue = get_rating_status(rating)
        print(f"🤖 Auditing: {name}...")

        prompt = f"""
        Act as a world-class Copywriter. Sender: Mauro Ciappina. Target: {name}. Context: {key_issue}.
        Feedback: {review_context}
        TASK:
        1. THOUGHT PROCESS: Why is this critical?
        2. SUBJECT LINE: Short, mentions feedback detail.
        3. EMAIL DRAFT: Personalized, cites details from feedback.
        Language: Spanish. Tone: Consultative. Length: <150 words.
        FORMAT: <thinking>...</thinking><subject>...</subject><email>...</email>
        """

        try:
            completion = client.chat.completions.create(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}])
            raw_response = completion.choices[0].message.content

            # Robust extraction
            thinking_match = re.search(r'<thinking>(.*?)</thinking>', raw_response, re.DOTALL)
            thinking = thinking_match.group(1).strip() if thinking_match else ""

            subject_match = re.search(r'<subject>(.*?)</subject>', raw_response, re.DOTALL)
            if subject_match:
                subject = subject_match.group(1).strip()
            else:
                subject_fallback = re.search(r'(?:Asunto|Subject|Subject\sLine):\s*(.*)', raw_response, re.IGNORECASE)
                subject = subject_fallback.group(1).strip() if subject_fallback else "Consulta Estratégica"

            subject = re.sub(r'^(Asunto|Subject|Subject\sLine):\s*', '', subject, flags=re.IGNORECASE).strip()

            email_match = re.search(r'<email>(.*?)</email>', raw_response, re.DOTALL)
            if email_match:
                email_draft = email_match.group(1).strip()
            else:
                # Fallback: remove thinking and subject tags/content to get the likely email body
                clean_body = raw_response
                if thinking_match: clean_body = clean_body.replace(thinking_match.group(0), "") # Use group(0) to replace the full matched tag
                if subject_match: clean_body = clean_body.replace(subject_match.group(0), "") # Use group(0) to replace the full matched tag

                # Also try to remove the fallback subject line if it was found and not part of a tag
                if not subject_match:
                    subject_fallback_match = re.search(r'(?:Asunto|Subject|Subject\sLine):\s*(.*)', clean_body, re.IGNORECASE)
                    if subject_fallback_match:
                        clean_body = clean_body.replace(subject_fallback_match.group(0), "")

                email_draft = clean_body.strip()

            supabase.table("leads").update({"status": "analyzed", "email_subject": subject, "email_draft": email_draft, "analysis_thinking": thinking}).eq("id", lead_id).execute()
            print(f"✅ Draft created for {name}")
            time.sleep(1)
        except Exception as e: print(f"❌ Error analyzing {name}: {e}")

if __name__ == "__main__":
    analyze_leads()
