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
    "send it over", "that sounds good"
]

REJECTED_SIGNALS = [
    "not interested, take care", "i have to go", "please don't call",
    "remove me from", "not a good time ever", "goodbye"
]


class ConversationEngine:
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.script = self._load_script()

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

        return (
            f"You are a professional sales representative for {script['product_name']}, "
            f"{script['product_description']}.\n\n"
            f"Your goal is to qualify the prospect and book a 30-minute discovery call.\n\n"
            f"OPENING LINE (use this verbatim to start the call):\n"
            f"{script['opening']}\n\n"
            f"KEY VALUE PROPOSITIONS (weave these naturally into the conversation):\n"
            f"{value_block}\n\n"
            f"HOW TO HANDLE OBJECTIONS:\n"
            f"{objection_block}\n\n"
            f"CLOSING (use when the moment is right):\n"
            f"{script['closing']}\n\n"
            f"RULES:\n"
            f"- Be conversational and human — do not read the script verbatim\n"
            f"- Keep each response to 2-4 sentences\n"
            f"- Listen to what the prospect says and adapt accordingly\n"
            f"- If the prospect clearly wants to end the call, close gracefully\n"
            f"- When the conversation is progressing well, move toward the closing line\n"
        )

    def _detect_outcome(self, prospect_reply: str) -> str | None:
        reply_lower = prospect_reply.lower()
        if any(signal in reply_lower for signal in CONVERTED_SIGNALS):
            return "converted"
        if any(signal in reply_lower for signal in REJECTED_SIGNALS):
            return "rejected"
        return None

    def run(self, prospect_name: str, persona: str = "skeptical") -> dict:
        prospect = ProspectSimulator(persona=persona)
        agent_messages = []
        conversation_log = []
        outcome = "incomplete"

        print(f"\n{'='*60}")
        print(f"  CALL SIMULATION")
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

        # --- Conversation loop (max 8 prospect turns) ---
        for _ in range(8):
            prospect_reply = prospect.respond(agent_reply)
            conversation_log.append({"role": "prospect", "content": prospect_reply})
            print(f"PROSPECT  : {prospect_reply}\n")

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
        }

    def _agent_turn(self, messages: list) -> str:
        response = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=self._build_agent_system_prompt(),
            messages=messages
        )
        return response.content[0].text.strip()
