"""
============ UNUSED ============
"""


"""from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import HumanMessage, SystemMessage
from .base import ModelLLMPlatform


class LlamaNvidia(ModelLLMPlatform):
    def __init__(self, api_key: str, system_prompt: str = None):
        self.system_prompt = system_prompt

        self.client = ChatNVIDIA(
            model="meta/llama-3.1-405b-instruct",
            api_key=api_key,
            temperature=0.5,  # Model creative
            max_tokens=1024)

    # Khai báo hàm là async và dùng await cho ainvoke
    async def achat(self, prompt: str) -> str:
        messages = []

        # Thêm system prompt
        if self.system_prompt:
            messages.append(SystemMessage(content=self.system_prompt))

        messages.append(HumanMessage(content=prompt))

        try:
            response = await self.client.ainvoke(messages)
            return response.content
        except Exception as e:
            raise RuntimeError(f"NVIDIA API error: {e}")"""
