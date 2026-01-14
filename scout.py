import os
import argparse
from exa_py import Exa
from supabase import create_client, Client
from dotenv import load_dotenv

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
    print(f"🚀 Scouting for {niche} in {city} (Limit: {limit})...")

    query = f"best {niche} in {city} with reviews and contact details"

    try:
        results = exa.search(
            query,
            num_results=limit,
            use_autoprompt=True
        )

        for result in results.results:
            business_name = result.title
            website_url = result.url

            # Basic Deduplication
            existing = supabase.table("leads").select("id").eq("website_url", website_url).execute()

            if not existing.data:
                supabase.table("leads").insert({
                    "business_name": business_name,
                    "website_url": website_url,
                    "city": city,
                    "niche": niche,
                    "status": "scouted"
                }).execute()
                print(f"✅ Added: {business_name}")
            else:
                print(f"⏭️ Skipping (already exists): {business_name}")

    except Exception as e:
        print(f"❌ Scouting failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--niche", type=str, default="dentists")
    parser.add_argument("--city", type=str, default="Madrid")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    scout_leads(args.niche, args.city, args.limit)
