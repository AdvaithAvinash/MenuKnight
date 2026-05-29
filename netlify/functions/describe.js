// Phase 2 of 2: Text-only — batch description generation
// Groq is tried first (fast), Gemini is the fallback
const GROQ_API_KEY   = process.env.GROQ_API_KEY;
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;

const GEMINI_MODELS = [
  "gemini-2.5-flash",
  "gemini-2.0-flash",
  "gemini-2.0-flash-001",
  "gemini-flash-latest",
  "gemini-2.5-flash-lite",
];
const GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models";
const GROQ_BASE   = "https://api.groq.com/openai/v1";

const DESCRIBE_PROMPT =
  "For each dish below write a 1-2 sentence description for a first-time traveler. " +
  "Be friendly and specific.\n" +
  "Return ONLY a valid JSON array, no markdown fences:\n" +
  '[{"dish":"Name","description":"Description."}]\n\nDishes:\n';

// Warm-invocation cache — persists while Lambda container is alive
const _cache = new Map();

function parseDescriptionJSON(text, uncached, result) {
  const match = text.match(/\[[\s\S]*\]/);
  if (!match) return;
  JSON.parse(match[0]).forEach(({ dish, description }) => {
    if (dish) {
      result[dish] = description || "";
      _cache.set(dish.toLowerCase(), description || "");
    }
  });
}

async function fetchViaGroq(uncached) {
  const prompt = DESCRIBE_PROMPT + uncached.map((d) => `- ${d}`).join("\n");
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);
  let res;
  try {
    res = await fetch(`${GROQ_BASE}/chat/completions`, {
      method: "POST",
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${GROQ_API_KEY}`,
      },
      body: JSON.stringify({
        model: "llama-3.3-70b-versatile",
        messages: [{ role: "user", content: prompt }],
        max_tokens: 2048,
        temperature: 0.5,
      }),
    });
  } finally { clearTimeout(timer); }

  if (!res.ok) throw new Error(`Groq ${res.status}`);
  const data = await res.json();
  return data?.choices?.[0]?.message?.content ?? "";
}

async function fetchViaGemini(uncached) {
  const prompt = DESCRIBE_PROMPT + uncached.map((d) => `- ${d}`).join("\n");
  for (const model of GEMINI_MODELS) {
    const url = `${GEMINI_BASE}/${model}:generateContent?key=${GEMINI_API_KEY}`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 9000);
    let res;
    try {
      res = await fetch(url, {
        method: "POST",
        signal: controller.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }),
      });
    } catch { continue; }
    finally { clearTimeout(timer); }

    if (!res.ok) continue;
    const data = await res.json();
    return data?.candidates?.[0]?.content?.parts?.[0]?.text ?? "";
  }
  throw new Error("All Gemini models failed");
}

async function fetchDescriptions(dishes) {
  const result = {};
  const uncached = dishes.filter((d) => !_cache.has(d.toLowerCase()));
  dishes.forEach((d) => { if (_cache.has(d.toLowerCase())) result[d] = _cache.get(d.toLowerCase()); });
  if (!uncached.length) return result;

  let text = "";
  if (GROQ_API_KEY) {
    try { text = await fetchViaGroq(uncached); }
    catch { /* fall through to Gemini */ }
  }
  if (!text && GEMINI_API_KEY) {
    try { text = await fetchViaGemini(uncached); }
    catch { /* return what we have */ }
  }

  if (text) {
    try { parseDescriptionJSON(text, uncached, result); }
    catch { /* ignore parse errors */ }
  }

  return result;
}

function resp(statusCode, data) {
  return {
    statusCode,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "Content-Type",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    },
    body: JSON.stringify(data),
  };
}

exports.handler = async (event) => {
  const method = event.httpMethod;
  if (method === "OPTIONS") return resp(200, {});
  if (method !== "POST") return resp(405, { error: "Method not allowed" });
  if (!GROQ_API_KEY && !GEMINI_API_KEY) return resp(500, { error: "No AI API key configured." });

  let body;
  try { body = JSON.parse(event.body); }
  catch { return resp(400, { error: "Body must be JSON" }); }

  const { dishes } = body;
  if (!Array.isArray(dishes) || !dishes.length) return resp(400, { error: "dishes must be a non-empty array" });

  const descriptions = await fetchDescriptions(dishes);
  return resp(200, {
    descriptions: dishes.map((dish) => ({ dish, description: descriptions[dish] || "" })),
  });
};
