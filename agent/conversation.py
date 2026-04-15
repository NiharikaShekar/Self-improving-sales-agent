import json
import os
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv
from agent.prospect import ProspectSimulator

load_dotenv()

SCRIPT_PATH = Path(__file__).parent / "script.json"

CONVERTED_SIGNALS = [
    "sounds reasonable", "that works", "go ahead and send",
    "let's schedule", "book that", "i'm in", "yes, i'd be open",
    "send it over", "that sounds good", "talk tuesday", "talk wednesday",
    "send the invite", "send a calendar", "lock it in", "we're good",
    "sounds good", "that makes sense", "let's do it", "i'm open"
]

REJECTED_SIGNALS = [
    "not interested, take care", "i have to go", "please don't call",
    "remove me from", "not a good time ever", "goodbye"
]


class ConversationEngine:
    def __init__(self, voice_mode: bool = False):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.script = self._load_script()
        self.voice_mode = voice_mode
        self.tts = None

        if voice_mode:
            try:
                from voice.tts import TextToSpeech
                self.tts = TextToSpeech()
            except Exception as e:
                print(f"  Voice init failed: {e}. Falling back to text mode.")
                self.voice_mode = False

    def _load_script(self) -> dict:
        with open(SCRIPT_PATH) as f:
            return json.load(f)

    def _build_agent_system_prompt(self) -> str:
        script = self.script
        objection_block = "\n".join(
            f"- If they raise '{key}': {handler}"
            for key, handler in script["objection_handlers"].items()
        )
        value_block = "\n".join(f"- {vp}" for vp in script["value_propositions"])

        metadata = script.get("product_metadata", {})
        metadata_block = "\n".join(f"- {k}: {v}" for k, v in metadata.items())

        return (
            f"You are a sales representative for {script['product_name']}, "
            f"{script['product_description']}.\n\n"
            f"Your goal is to qualify the prospect and book a discovery call.\n\n"
            f"OPENING LINE - use this exactly, word for word:\n"
            f"{script['opening']}\n\n"
            f"VALUE PROPOSITIONS - you may only use these points. Do not invent new ones:\n"
            f"{value_block}\n\n"
            f"PRODUCT FACTS - you may reference these when the prospect asks for specifics:\n"
            f"{metadata_block}\n\n"
            f"OBJECTION RESPONSES - when an objection arises, use the matching response below "
            f"as closely as possible. You may supplement with product facts above if relevant:\n"
            f"{objection_block}\n\n"
            f"CLOSING - use this line to close:\n"
            f"{script['closing']}\n\n"
            f"STRICT RULES:\n"
            f"- You MUST stay within the script and product facts. Do not invent statistics or claims.\n"
            f"- If the prospect asks a question the script does not cover, use the product facts or acknowledge briefly and redirect.\n"
            f"- Keep each response to 2-3 sentences maximum.\n"
            f"- If the prospect is clearly ending the call, do not argue - close politely.\n"
        )

    def _detect_outcome(self, prospect_reply: str) -> str | None:
        reply_lower = prospect_reply.lower()
        if any(signal in reply_lower for signal in CONVERTED_SIGNALS):
            return "converted"
        if any(signal in reply_lower for signal in REJECTED_SIGNALS):
            return "rejected"
        return None

    def _speak_agent(self, text: str) -> None:
        if self.voice_mode and self.tts:
            print("  [Agent speaking...]\n")
            self.tts.speak_agent(text)

    def _speak_prospect(self, text: str) -> None:
        if self.voice_mode and self.tts:
            print("  [Prospect speaking...]\n")
            self.tts.speak_prospect(text)

    def run(self, prospect_name: str, persona: str = "skeptical") -> dict:
        prospect = ProspectSimulator(persona=persona)
        agent_messages = []
        conversation_log = []
        outcome = "incomplete"

        mode_label = "VOICE + TEXT" if self.voice_mode else "TEXT"
        print(f"\n{'='*60}")
        print(f"  CALL SIMULATION [{mode_label}]")
        print(f"  Prospect : {prospect_name}  |  Persona : {persona}")
        print(f"  Script   : v{self.script['version']}  |  Product : {self.script['product_name']}")
        print(f"{'='*60}\n")

        # --- Agent opens the call ---
        agent_messages.append({
            "role": "user",
            "content": (
                f"Start the sales call now. The prospect's name is {prospect_name}. "
                f"Begin with your opening line."
            )
        })

        agent_reply = self._agent_turn(agent_messages)
        conversation_log.append({"role": "agent", "content": agent_reply})
        print(f"AGENT     : {agent_reply}\n")
        self._speak_agent(agent_reply)

        # --- Conversation loop (max 8 prospect turns) ---
        for _ in range(8):
            prospect_reply = prospect.respond(agent_reply)
            conversation_log.append({"role": "prospect", "content": prospect_reply})
            print(f"PROSPECT  : {prospect_reply}\n")
            self._speak_prospect(prospect_reply)

            outcome = self._detect_outcome(prospect_reply)
            if outcome:
                break

            agent_messages.append({"role": "assistant", "content": agent_reply})
            agent_messages.append({
                "role": "user",
                "content": f'The prospect just said: "{prospect_reply}"\n\nRespond as the sales agent.'
            })

            agent_reply = self._agent_turn(agent_messages)
            conversation_log.append({"role": "agent", "content": agent_reply})
            print(f"AGENT     : {agent_reply}\n")
            self._speak_agent(agent_reply)

        print(f"\n{'='*60}")
        print(f"  OUTCOME : {(outcome or 'incomplete').upper()}")
        print(f"  TURNS   : {len(conversation_log)}")
        print(f"{'='*60}\n")

        return {
            "prospect_name": prospect_name,
            "persona": persona,
            "script_version": self.script["version"],
            "product": self.script["product_name"],
            "outcome": outcome or "incomplete",
            "turn_count": len(conversation_log),
            "conversation": conversation_log,
            "voice_enabled": self.voice_mode,
        }

    def _agent_turn(self, messages: list) -> str:
        response = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=self._build_agent_system_prompt(),
            messages=messages
        )
        return response.content[0].text.strip()
