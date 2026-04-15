from agent.conversation import ConversationEngine
from agent.improver import ScriptImprover
from memory.analyzer import CallAnalyzer
from memory.database import initialize_db, save_call, get_conversion_rate


DEMO_CALLS = [
    ("Marcus", "skeptical"),
    ("Priya",  "price_sensitive"),
    ("Tom",    "hostile"),
    ("Lisa",   "friendly"),
]


def run_single_call(prospect_name: str, persona: str) -> None:
    engine = ConversationEngine()
    analyzer = CallAnalyzer()

    result = engine.run(prospect_name=prospect_name, persona=persona)

    analysis = analyzer.analyze(result)
    call_id = save_call(result, analysis)

    print(f"--- Analysis (call #{call_id}) ---")
    print(f"Objections  : {', '.join(analysis['objections_raised']) or 'none detected'}")
    print(f"Quality     : {analysis['call_quality']}")
    print(f"Note        : {analysis['improvement_note']}\n")


def print_stats(label: str, script_version: int) -> None:
    stats = get_conversion_rate(script_version)
    print(f"\n{'='*60}")
    print(f"  {label} — Script v{script_version}")
    print(f"{'='*60}")
    print(f"  Calls      : {stats['total']}")
    print(f"  Converted  : {stats['converted']}")
    print(f"  Rejected   : {stats['rejected']}")
    print(f"  Incomplete : {stats['incomplete']}")
    print(f"  Rate       : {stats['rate']}%")
    print(f"{'='*60}\n")


def demo() -> None:
    initialize_db()

    # ── Iteration 1: run calls with v1 script ──────────────────────
    print("\n" + "█"*60)
    print("  ITERATION 1 — Running calls with v1 script")
    print("█"*60 + "\n")

    for name, persona in DEMO_CALLS:
        run_single_call(name, persona)

    print_stats("RESULTS AFTER ITERATION 1", script_version=1)

    # ── Improvement cycle: v1 → v2 ─────────────────────────────────
    improver = ScriptImprover()
    improver.improve()

    # ── Iteration 2: run calls with v2 script ──────────────────────
    print("\n" + "█"*60)
    print("  ITERATION 2 — Running calls with v2 script")
    print("█"*60 + "\n")

    for name, persona in DEMO_CALLS:
        run_single_call(name, persona)

    print_stats("RESULTS AFTER ITERATION 2", script_version=2)

    # ── Side-by-side comparison ─────────────────────────────────────
    v1 = get_conversion_rate(script_version=1)
    v2 = get_conversion_rate(script_version=2)

    print(f"\n{'='*60}")
    print("  IMPROVEMENT SUMMARY")
    print(f"{'='*60}")
    print(f"  v1 conversion rate : {v1['rate']}%  ({v1['converted']}/{v1['total']} calls)")
    print(f"  v2 conversion rate : {v2['rate']}%  ({v2['converted']}/{v2['total']} calls)")
    delta = round(v2['rate'] - v1['rate'], 1)
    direction = "+" if delta >= 0 else ""
    print(f"  Change             : {direction}{delta}%")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    demo()
