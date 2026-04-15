import os
import subprocess
import tempfile
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

load_dotenv()


class TextToSpeech:
    def __init__(self):
        api_key = os.getenv("ELEVENLABS_API_KEY")
        self.agent_voice_id = os.getenv("ELEVENLABS_VOICE_ID")
        self.prospect_voice_id = os.getenv("ELEVENLABS_PROSPECT_VOICE_ID")

        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY is not set in .env")
        if not self.agent_voice_id:
            raise ValueError("ELEVENLABS_VOICE_ID is not set in .env")

        self.client = ElevenLabs(api_key=api_key)
        has_prospect_voice = bool(self.prospect_voice_id)
        print(f"  TTS: ElevenLabs | Agent voice set | Prospect voice: {'set' if has_prospect_voice else 'not set (will use agent voice)'}")

    def speak_agent(self, text: str) -> None:
        self._speak(text, self.agent_voice_id)

    def speak_prospect(self, text: str) -> None:
        voice_id = self.prospect_voice_id or self.agent_voice_id
        self._speak(text, voice_id)

    def _speak(self, text: str, voice_id: str) -> None:
        audio_generator = self.client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_turbo_v2_5",
            output_format="mp3_44100_128",
        )
        audio_bytes = b"".join(audio_generator)

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            subprocess.run(["afplay", tmp_path], check=True)
        finally:
            os.unlink(tmp_path)
