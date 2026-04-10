function extractJsonFromText(text) {
  if (!text || typeof text !== "string") return null;

  // 1) Prefer fenced json blocks: ```json ... ```
  const fenced = text.match(/```json\s*([\s\S]*?)\s*```/i);
  if (fenced?.[1]) return fenced[1].trim();

  // 2) Fallback: try to find the first top-level JSON object by braces
  const firstBrace = text.indexOf("{");
  if (firstBrace === -1) return null;

  let depth = 0;
  for (let i = firstBrace; i < text.length; i++) {
    const ch = text[i];
    if (ch === "{") depth++;
    if (ch === "}") depth--;
    if (depth === 0) {
      const candidate = text.slice(firstBrace, i + 1).trim();
      return candidate.startsWith("{") && candidate.endsWith("}") ? candidate : null;
    }
  }

  return null;
}

export default extractJsonFromText;

