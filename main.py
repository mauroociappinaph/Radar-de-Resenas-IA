import argparse
import asyncio
from scout import scout_leads
from enrich import enrich_leads
from audit_agent import analyze_leads
from dispatch import dispatch_emails

async def run_pipeline(niche, city, limit, max_concurrency=5):
    print(f"🤖 RADAR DE RESEÑAS IA - Orchestrator ({niche} in {city})")
    scout_leads(niche, city, limit)
    await enrich_leads(limit=limit, max_concurrency=max_concurrency)
    analyze_leads(limit=limit)
    dispatch_emails(limit=limit)
    print("\n✅ Pipeline Finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--niche", type=str, default="dentists")
    parser.add_argument("--city", type=str, default="Madrid")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--max-concurrency", type=int, default=5)
    args = parser.parse_args()
    asyncio.run(run_pipeline(args.niche, args.city, args.limit, args.max_concurrency))
