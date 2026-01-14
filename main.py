import argparse
from scout import scout_leads
from enrich import enrich_leads
from audit_agent import analyze_leads
from dispatch import dispatch_emails

def run_pipeline(niche, city, limit):
    print(f"🤖 RADAR DE RESEÑAS IA - Orchestrator ({niche} in {city})")
    scout_leads(niche, city, limit)
    enrich_leads(limit=limit)
    analyze_leads(limit=limit)
    dispatch_emails(limit=limit)
    print("\n✅ Pipeline Finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--niche", type=str, default="dentists")
    parser.add_argument("--city", type=str, default="Madrid")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    run_pipeline(args.niche, args.city, args.limit)
