import time
from langchain_ollama import ChatOllama

llm = ChatOllama(model="gemma4:31b-cloud", temperature=0, streaming=False)

start = time.perf_counter()

response = llm.invoke("Giải thích Business Analyst là làm gì.")

end = time.perf_counter()

print(response.content)
print(f"\nResponse Time: {end - start:.2f} seconds")
