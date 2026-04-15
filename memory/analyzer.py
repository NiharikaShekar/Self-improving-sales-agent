import json
import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

KNOWN_OBJECTIONS = [
    "price",
    "not_interested",
    "already_have_solution",
    "no_time",
    "need_approval",
    "data_privacy",
]


class CallAnalyzer:
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def analyze(self, result: dict) -> dict:
        conversation_text = self._format_conversation(result["conversation"])
        outcome = result["outcome"]

        prompt = f"""You are analyzing a sales call transcript. Extract structured insights.

OUTCOME: {outcome}

TRANSCRIPT:
{conversation_text}

KNOWN OBJECTION TYPES: {", ".join(KNOWN_OBJECTIONS)}

Respond with valid JSON only — no explanation, no markdown. Use this exact structure:
{{
  "objections_raised": ["list only objection types from the known list that actually appeared"],
  "call_quality": "one of: excellent / good / average / poor",
  "improvement_note": "one specific, actionable sentence about what the agent could do differently to improve conversion — or 'none' if the call was excellent"
}}"""

        response = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.content[0].text.strip()

        
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            analysis = json.loads(raw)
        except json.JSONDecodeError:
            analysis = {
                "objections_raised": [],
                "call_quality": "unknown",
                "improvement_note": "Analysis parsing failed."
            }

        return analysis

    def _format_conversation(self, conversation: list[dict]) -> str:
        lines = []
        for turn in conversation:
            speaker = "AGENT" if turn["role"] == "agent" else "PROSPECT"
            lines.append(f"{speaker}: {turn['content']}")
        return "\n\n".join(lines)
