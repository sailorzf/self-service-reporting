from abc import ABC, abstractmethod
from openai import OpenAI
from app.config import settings

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, messages: list[dict], temperature: float = 0.3) -> str:
        pass

class DashScopeProvider(LLMProvider):
    """Qwen via DashScope (OpenAI compatible)."""
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.dashscope_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.model = settings.dashscope_model

    def generate(self, messages: list[dict], temperature: float = 0.3) -> str:
        response = self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=temperature,
        )
        return response.choices[0].message.content
