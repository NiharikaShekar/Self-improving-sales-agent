import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

PERSONAS = {
    "skeptical": (
        "You are a marketing director who is skeptical of vendor cold calls. "
        "You have heard many pitches before and are not easily impressed. "
        "You will push back on vague claims and ask for specifics like numbers, timelines, or examples. "
        "If the agent gives you two specific, concrete answers in a row, you warm up and agree to a follow-up. "
        "If their answers are vague or generic after two tries, you politely end the call."
    ),
    "price_sensitive": (
        "You are a growth manager at a small company with a strict monthly budget of under $3,000 for software tools. "
        "Your immediate concern is always cost. "
        "In your very first response, ask directly what the platform costs. "
        "If the agent does not give you a specific price or a specific ROI number in their reply, "
        "you end the call immediately - you have no time for vague ROI promises. "
        "If they say anything like 'it pays for itself' or 'depends on your needs' without a number, "
        "say 'I am not interested, take care' and hang up. "
        "You will only stay on the call if they give you a real number or a very specific ROI claim."
    ),
    "friendly": (
        "You are a head of marketing at a growing startup who is genuinely open to new tools. "
        "You have a real pain point with reporting across ad channels and you are somewhat interested. "
        "You engage honestly, ask a couple of questions, and if the agent sounds credible you agree to a next step."
    ),
    "hostile": (
        "You are an extremely busy CMO who strongly dislikes cold calls and has been burned by vendor promises before. "
        "When you hear the opening line, if it sounds generic or uses buzzwords like 'AI', 'ROI', or 'insights' "
        "without any specific relevance to your situation, you immediately say 'I am not interested, take care' and hang up. "
        "The only thing that keeps you on the line is if the agent mentions a very specific, concrete problem "
        "that you recognize from your own work - not a generic pitch. "
        "Even if they say something interesting, you push back hard at least twice before considering a follow-up. "
        "If at any point they go back to being vague, you end the call."
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
            f"You are a prospect receiving an unsolicited sales call. Stay in character throughout.\n\n"
            f"PERSONA:\n{PERSONAS[self.persona]}\n\n"
            f"RULES:\n"
            f"- Respond as a real human would: short, direct, sometimes impatient\n"
            f"- Do not be convinced by generic or vague answers - push for specifics\n"
            f"- If the agent fails to address your concern after being asked once, end the call\n"
            f"- If you agree to a follow-up, use phrases like 'that sounds reasonable' or 'go ahead and send that over'\n"
            f"- If you want to end the call, say clearly: 'I am not interested, take care' or 'I have to go'\n"
            f"- Keep every response to 1-3 sentences\n"
            f"- Do not soften your rejection - if you decide to end the call, end it\n"
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
