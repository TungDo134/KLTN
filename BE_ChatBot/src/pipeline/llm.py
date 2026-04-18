"""
Factory to create a object (LLM)
"""

# --- LOAD .env ---
from dotenv import load_dotenv

load_dotenv()

# --- IMPORT ---
import os
from langchain_nvidia_ai_endpoints import ChatNVIDIA

model_name = 'meta/llama-3.3-70b-instruct'


class LLM:
    def __init__(self) -> None:
        self.system_prompt_path = os.getenv('SYSTEM_PROMPT')
        self.system_prompt = self._load_system_prompt()

    # --- AI Configuration ---
    def _load_system_prompt(self) -> str | None:
        """Đọc system prompt từ file. Trả về None nếu không tìm thấy."""
        if not self.system_prompt_path:
            return None
        try:
            with open(self.system_prompt_path, "r", encoding="utf-8") as f:
                content = f.read()
                print(f"✅ System prompt loaded from: {self.system_prompt_path}")
                return content
        except FileNotFoundError:
            print(f"⚠️  System prompt file not found: {self.system_prompt_path}. Proceeding without it.")
            return None

    @staticmethod
    def get_llm() -> ChatNVIDIA:
        nvidia_api_key = os.getenv("NVIDIA_API_KEY")
        if not nvidia_api_key:
            raise ValueError("NVIDIA_API_KEY environment variable not set.")

        llm = ChatNVIDIA(
            # model="meta/llama-3.1-405b-instruct",
            model=model_name,
            api_key=nvidia_api_key,
            temperature=0.5,
            max_tokens=1024,
        )
        return llm
