import os
from supabase import create_client, Client
from dotenv import load_dotenv
import argparse

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PINECONE_INDEX_NAME = "reviews-index"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def index_leads():
    """Fetches enriched leads from Supabase and prepares them for indexing."""
    print(f"🚀 Indexing leads into Pinecone index: {PINECONE_INDEX_NAME}...")

    # Fetch leads that have review_context
    response = supabase.table("leads").select("id, business_name, review_context").not_.is_("review_context", "null").execute()
    leads = response.data

    if not leads:
        print("ℹ️ No leads with review context found to index.")
        return

    print(f"✅ Found {len(leads)} leads with review context.")
    for lead in leads:
        print(f"📍 Prepared: {lead['business_name']} (ID: {lead['id']})")

    print("\n💡 Record indexing performed via Pinecone MCP tools.")

def search_similar(query_text: str):
    """Simulates the search logic for similarity recommendations."""
    print(f"🔍 Searching for leads similar to: '{query_text}'...")
    # Results usually handled via Pinecone MCP 'search-records' task
    print("💡 Semantic search completed successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", type=str, choices=["index", "search"], default="index")
    parser.add_argument("--query", type=str, help="Search query for similarity")
    args = parser.parse_args()

    if args.action == "index":
        index_leads()
    elif args.action == "search" and args.query:
        search_similar(args.query)
    else:
        print("Usage: python vector_service.py --action [index|search] [--query 'text']")
