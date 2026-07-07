import os
import time
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

load_dotenv()

llm = ChatOllama(
    model="gemma4:cloud",  # bỏ hậu tố :cloud khi gọi API trực tiếp
    base_url="https://ollama.com",
    client_kwargs={
        "headers": {"Authorization": f"Bearer {os.environ['OLLAMA_API_KEY']}"}
    },
)

start_time = time.perf_counter()
first_token_time = None
full_response = ""

for chunk in llm.stream([HumanMessage(content="Xin chào, giới thiệu bản thân")]):
    if first_token_time is None:
        first_token_time = time.perf_counter()
    full_response += chunk.content
    print(chunk.content, end="", flush=True)

end_time = time.perf_counter()

print(f"\n\n--- Time to first token: {first_token_time - start_time:.2f}s ---")
print(f"--- Tổng thời gian phản hồi: {end_time - start_time:.2f}s ---")
