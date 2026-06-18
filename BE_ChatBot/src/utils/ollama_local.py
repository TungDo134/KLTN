import time
from langchain_ollama import ChatOllama

llm = ChatOllama(model="qwen3.5:4b", temperature=0)

start = time.perf_counter()

response = llm.invoke("Giải thích Business Analyst là làm gì.")

end = time.perf_counter()

print(response.content)
print(f"\nResponse Time: {end - start:.2f} seconds")
