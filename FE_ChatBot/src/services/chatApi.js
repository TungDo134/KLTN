const BASE_URL = import.meta.env.VITE_FASTAPI_URL;

if (!BASE_URL) {
  throw new Error("VITE_FASTAPI_URL not found");
}

const readStream = async (response, onProgress) => {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let fullText = "";
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (const event of events) {
      const dataLines = event
        .split("\n")
        .filter((line) => line.startsWith("data: "))
        .map((line) => line.slice(6));

      const data = dataLines.join("\n");
      if (!data) continue;
      if (data === "[DONE]") return fullText;

      const token = JSON.parse(data);
      fullText += token;
      onProgress(token, fullText);
    }
  }

  return fullText;
};

const chatApi = {
  sendMessageStream: async (prompt, conversationSessionId, onProgress) => {
    const token = localStorage.getItem("access_token");

    const response = await fetch(`${BASE_URL}/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token && { Authorization: `Bearer ${token}` }),
      },
      body: JSON.stringify({ prompt, conversationSessionId }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw { response: { data: error } };
    }

    const responseText = await readStream(response, onProgress);
    return { data: { response: responseText } };
  },
};

export default chatApi;
