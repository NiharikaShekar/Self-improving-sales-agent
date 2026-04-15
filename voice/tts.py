import os
import subprocess
import tempfile
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

load_dotenv()


class TextToSpeech:
    def __init__(self):
        api_key = os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID")

        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY is not set in .env")
        if not self.voice_id:
            raise ValueError("ELEVENLABS_VOICE_ID is not set in .env")

        self.client = ElevenLabs(api_key=api_key)

    def speak(self, text: str) -> None:
        audio_generator = self.client.text_to_speech.convert(
            voice_id=self.voice_id,
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
