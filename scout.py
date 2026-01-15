import os
import argparse
import re
import time
from exa_py import Exa
from supabase import create_client, Client
from dotenv import load_dotenv
from rapidfuzz import fuzz, process
from models import LeadModel
from pydantic import ValidationError

# Load environment variables
load_dotenv()

# Configuration
EXA_API_KEY = os.getenv("EXA_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Clients
exa = Exa(api_key=EXA_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def scout_leads(niche, city, limit=10):
    print(f"🚀 Scouting for {niche} in {city} (finding {limit} NEW leads)...")

    found_count = 0
    # We'll ask for some extra results from Exa to account for filters and duplicates
    search_limit = limit * 3

    try:
        # Fetch existing lead names and URLs for deduplication
        existing_leads_resp = supabase.table("leads").select("business_name", "website_url").execute()
        existing_names = [L["business_name"] for L in existing_leads_resp.data]
        existing_urls = [L["website_url"] for L in existing_leads_resp.data]

        results = exa.search_and_contents(
            f"best {niche} in {city} with reviews rating and contact details",
            num_results=search_limit,
            text=True,
            highlights=True
        )

        for result in results.results:
            if found_count >= limit: break

            business_name = result.title
            website_url = result.url

            # 1. URL Deduplication (exact)
            if website_url in existing_urls:
                print(f"⏭️ Skipping (URL exists): {business_name}")
                continue

            # 2. Fuzzy Name Deduplication
            if existing_names:
                # Use token_sort_ratio to be robust to word order (e.g. "Dentista Madrid" vs "Madrid Dentista")
                best_match = process.extractOne(business_name, existing_names, scorer=fuzz.token_sort_ratio)
                if best_match and best_match[1] > 85: # 85% similarity threshold
                    print(f"⏭️ Skipping (Fuzzy Match: '{best_match[0]}' - {best_match[1]:.1f}%): {business_name}")
                    continue

            # Rating extraction from text/highlights context
            rating = None
            text_context = f"{result.title} {getattr(result, 'text', '')} {' '.join(getattr(result, 'highlights', []))}"
            # Matches formats like "4.5 stars", "Rating: 4", "puntuación de 3.8"
            rating_match = re.search(r'(\d\.\d|\d)\s*(?:stars|estrellas|puntuación|rating)', text_context, re.IGNORECASE)
            if rating_match:
                try:
                    rating = float(rating_match.group(1))
                    if rating > 5.0: rating = 5.0 # Cap just in case
                except: pass

            # 3. Pydantic Validation & Insertion
            try:
                lead_data = {
                    "business_name": business_name,
                    "website_url": website_url,
                    "city": city,
                    "niche": niche,
                    "rating": rating,
                    "status": "scouted"
                }
                # Create and validate model
                validated_lead = LeadModel(**lead_data)

                # model_dump(mode='json') handles types like HttpUrl by converting them to strings
                supabase.table("leads").insert(validated_lead.model_dump(mode='json', exclude_none=True)).execute()
                print(f"✅ Added NEW: {business_name} (Rating: {rating if rating else 'N/A'})")

                found_count += 1

                # Update local cache to prevent duplicates in the SAME run
                existing_names.append(business_name)
                existing_urls.append(website_url)

            except ValidationError as ve:
                print(f"⚠️ Validation failed for {business_name}: {ve}")
                continue

        if found_count < limit:
            print(f"🏁 Finished. Found {found_count} new leads out of {limit} requested.")
        else:
            print(f"✅ Target reached: {found_count} new leads added.")

    except Exception as e:
        print(f"❌ Scouting failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--niche", type=str, default="dentists")
    parser.add_argument("--city", type=str, default="Madrid")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    scout_leads(args.niche, args.city, args.limit)
