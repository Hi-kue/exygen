import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class MeterlessClient:
    """
    Client for interacting with the Meterless Runtime via OpenAI-compatible API.
    Handles routing to different model tiers (auto, deep, etc.) provided by Nightshift.
    """
    def __init__(self):
        self.api_base = os.getenv("NIGHTSHIFT_API_BASE", "http://127.0.0.1:8088/v1")
        self.api_key = os.getenv("NIGHTSHIFT_API_KEY", "local-dev-key")
        self.model_default = os.getenv("NIGHTSHIFT_MODEL_DEFAULT", "meterless/auto")
        self.model_deep = os.getenv("NIGHTSHIFT_MODEL_DEEP", "meterless/deep")
        
        self.client = OpenAI(
            base_url=self.api_base,
            api_key=self.api_key
        )

    def chat(self, system_prompt: str, user_prompt: str, model: str | None = None, temperature: float = 0.7):
        """Standard chat completion call to the Meterless runtime."""
        selected_model = model or self.model_default
        
        response = self.client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature
        )
        return response.choices[0].message.content

    def deep_chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.3):
        """Call using the 'deep' model tier for high-accuracy validation."""
        return self.chat(system_prompt, user_prompt, model=self.model_deep, temperature=temperature)
