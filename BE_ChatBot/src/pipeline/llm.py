"""
UNUSED - CHANGE TO FILE "llm_container.py"
"""

# """
# Factory to create a object (LLM)
# """
#
# # --- LOAD .env ---
# from dotenv import load_dotenv
#
# from src.core.llm_container import get_llm_model, LLMProvider
#
# load_dotenv()
#
# # --- IMPORT ---
# import os
# from langchain_nvidia_ai_endpoints import ChatNVIDIA
#
#
# class LLM:
#     def __init__(self) -> None:
#         self.system_prompt_path = os.getenv('SYSTEM_PROMPT')
#         self.system_prompt = self._load_system_prompt()
#
#     # --- AI Configuration ---
#     def _load_system_prompt(self) -> str | None:
#         """Đọc system prompt từ file. Trả về None nếu không tìm thấy."""
#         if not self.system_prompt_path:
#             return None
#         try:
#             with open(self.system_prompt_path, "r", encoding="utf-8") as f:
#                 content = f.read()
#                 print(f"✅ System prompt loaded from: {self.system_prompt_path}")
#                 return content
#         except FileNotFoundError:
#             print(f"⚠️  System prompt file not found: {self.system_prompt_path}. Proceeding without it.")
#             return None
#
#     def get_llm(
#             self,
#             provider: LLMProvider | None = None,
#             model_name: str | None = None,
#             temperature: float = 0.5,
#             max_tokens: int = 1024,
#     ):
#         _provider = provider or LLMProvider(os.getenv("LLM_PROVIDER", "nvidia"))
#         _model = model_name or os.getenv("LLM_MODEL")
#
#         return get_llm_model(
#             provider=_provider,
#             model_name=_model,
#             temperature=temperature,
#             max_tokens=max_tokens,
#         )
