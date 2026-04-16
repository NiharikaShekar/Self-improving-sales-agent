import json
import os
import shutil
from collections import Counter
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

from memory.database import fetch_calls_for_version, get_conversion_rate

load_dotenv()

SCRIPT_PATH = Path(__file__).parent / "script.json"
ARCHIVE_DIR = Path(__file__).parent.parent / "logs" / "script_history"


class ScriptImprover:
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.script = self._load_script()

    def _load_script(self) -> dict:
        with open(SCRIPT_PATH) as f:
            return json.load(f)

    def _archive_current_script(self) -> None:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        version = self.script["version"]
        archive_path = ARCHIVE_DIR / f"script_v{version}.json"
        shutil.copy(SCRIPT_PATH, archive_path)
        print(f"Archived script v{version} → {archive_path.relative_to(Path.cwd())}")

    def _build_summary(self, calls: list[dict]) -> str:
        total = len(calls)
        if total == 0:
            return "No calls recorded for this version."

        outcomes = [c["outcome"] for c in calls]
        converted = outcomes.count("converted")
        rejected = outcomes.count("rejected")
        incomplete = outcomes.count("incomplete")
        rate = round(converted / total * 100, 1)

        all_objections = []
        for c in calls:
            all_objections.extend(c.get("objections_raised", []))
        objection_counts = Counter(all_objections)

        quality_counts = Counter(c.get("call_quality", "unknown") for c in calls)

        improvement_notes = [
            c["improvement_note"]
            for c in calls
            if c.get("improvement_note") and c["improvement_note"] != "none"
        ]

        lines = [
            f"Total calls     : {total}",
            f"Converted       : {converted}  |  Rejected: {rejected}  |  Incomplete: {incomplete}",
            f"Conversion rate : {rate}%",
            f"Quality spread  : {dict(quality_counts)}",
            "",
            "Objections that appeared (by frequency):",
        ]

        if objection_counts:
            for obj, count in objection_counts.most_common():
                lines.append(f"  - {obj}: {count} time(s)")
        else:
            lines.append("  - None matched known objection types")

        lines.append("")
        lines.append("Analyst improvement notes from individual calls:")
        if improvement_notes:
            for note in improvement_notes:
                lines.append(f"  - {note}")
        else:
            lines.append("  - No specific notes recorded")

        return "\n".join(lines)

    def improve(self) -> dict:
        current_version = self.script["version"]
        calls = fetch_calls_for_version(current_version)

        if not calls:
            raise ValueError(
                f"No calls recorded for script v{current_version}. "
                "Run a batch first before triggering the improvement cycle."
            )

        summary = self._build_summary(calls)

        print(f"\n{'='*60}")
        print(f"  IMPROVEMENT CYCLE - Analyzing v{current_version} performance")
        print(f"{'='*60}")
        print(summary)
        print()

        prompt = f"""You are a sales training expert. Below is a sales script and the performance data from {len(calls)} calls that used it.

Your task is to produce an improved version of the script that addresses the observed weaknesses.

CURRENT SCRIPT (JSON):
{json.dumps(self.script, indent=2)}

PERFORMANCE SUMMARY:
{summary}

INSTRUCTIONS:
- Keep the same JSON structure exactly
- Increment the "version" field by 1
- Improve the opening, value propositions, objection handlers, and closing based on the data
- Add or refine objection handlers for any objection types that appeared but were not handled well
- If the conversion rate is high, make targeted improvements rather than wholesale rewrites
- Make the language more natural, specific, and responsive to real objections
- Do not invent statistics - only use the figures already in the script

Respond with valid JSON only. No explanation, no markdown, no code fences.
"""

        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = response.content[0].text.strip()
        except Exception as e:
            raise RuntimeError(f"LLM call failed during improvement: {e}") from e

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            new_script = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Improvement LLM returned invalid JSON — script not modified. Error: {e}\nRaw output: {raw[:200]}"
            ) from e

        required_keys = {"version", "product_name", "opening", "value_propositions", "objection_handlers", "closing"}
        missing = required_keys - set(new_script.keys())
        if missing:
            raise ValueError(
                f"Improved script is missing required fields: {missing} — script not modified."
            )

        if new_script["version"] != current_version + 1:
            new_script["version"] = current_version + 1

        self._archive_current_script()

        with open(SCRIPT_PATH, "w") as f:
            json.dump(new_script, f, indent=2)

        print(f"Script upgraded: v{current_version} -> v{new_script['version']}")
        print(f"Saved to {SCRIPT_PATH.relative_to(Path.cwd())}\n")

        return new_script
