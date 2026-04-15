import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

PERSONAS = {
    "skeptical": (
        "You are a marketing director who is skeptical of vendor cold calls. "
        "You have sat through many pitches and are not easily impressed. "
        "You will push back on vague claims and ask for specifics. "
        "You may warm up slightly if the agent listens carefully and gives concrete answers."
    ),
    "price_sensitive": (
        "You are a growth manager at a mid-size company with a tight marketing budget. "
        "Your primary concern is cost and demonstrable ROI. "
        "You will ask for numbers and push back on anything that feels like an upsell. "
        "You are open to a follow-up meeting only if the agent can make a specific, credible ROI case."
    ),
    "friendly": (
        "You are a head of marketing at a growing startup who is genuinely open to new tools. "
        "You have a real pain point with reporting across ad channels and are somewhat interested. "
        "You engage honestly but need a clear, specific reason to commit to a next step."
    ),
    "hostile": (
        "You are an extremely busy CMO who resents cold calls. "
        "You will try to end the conversation quickly. "
        "You have been burned by vendor promises before. "
        "Only a highly specific and relevant point will keep you on the line beyond the first exchange."
    ),
}


class ProspectSimulator:
    def __init__(self, persona: str = "skeptical"):
        if persona not in PERSONAS:
            raise ValueError(f"Unknown persona '{persona}'. Choose from: {list(PERSONAS.keys())}")

        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.persona = persona
        self.messages = []
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        return (
            f"You are a prospect receiving an unsolicited sales call. Stay in character throughout the conversation.\n\n"
            f"PERSONA:\n{PERSONAS[self.persona]}\n\n"
            f"RULES:\n"
            f"- Respond as a real human would: short, natural, sometimes impatient\n"
            f"- Raise objections that fit your persona naturally — do not volunteer them all at once\n"
            f"- If the agent handles your concerns well, gradually become more open\n"
            f"- If you agree to a follow-up call or next step, end with a phrase like 'that sounds reasonable' or 'go ahead and send that over'\n"
            f"- If you want to end the call, say something like 'I have to go' or 'I am not interested, take care'\n"
            f"- Keep every response to 1-3 sentences\n"
        )

    def respond(self, agent_message: str) -> str:
        self.messages.append({
            "role": "user",
            "content": f'The sales agent just said: "{agent_message}"\n\nRespond as the prospect.'
        })

        response = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            system=self.system_prompt,
            messages=self.messages
        )

        reply = response.content[0].text.strip()
        self.messages.append({"role": "assistant", "content": reply})
        return reply
