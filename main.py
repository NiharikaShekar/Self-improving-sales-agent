from agent.conversation import ConversationEngine
from memory.analyzer import CallAnalyzer
from memory.database import initialize_db, save_call, get_conversion_rate


def run_call(prospect_name: str, persona: str = "skeptical") -> None:
    engine = ConversationEngine()
    analyzer = CallAnalyzer()

    result = engine.run(prospect_name=prospect_name, persona=persona)

    print("Analyzing call...")
    analysis = analyzer.analyze(result)

    call_id = save_call(result, analysis)

    print(f"\n--- CALL ANALYSIS (id: {call_id}) ---")
    print(f"Objections raised : {', '.join(analysis['objections_raised']) or 'none'}")
    print(f"Call quality      : {analysis['call_quality']}")
    print(f"Improvement note  : {analysis['improvement_note']}")

    stats = get_conversion_rate()
    print(f"\n--- OVERALL STATS ---")
    print(f"Total calls  : {stats['total']}")
    print(f"Converted    : {stats['converted']}")
    print(f"Rejected     : {stats['rejected']}")
    print(f"Conversion % : {stats['rate']}%")


if __name__ == "__main__":
    initialize_db()
    run_call(prospect_name="Sarah", persona="skeptical")
