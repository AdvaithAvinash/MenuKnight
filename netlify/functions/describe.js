// Phase 2 of 2: Text-only — batch description generation for a list of dishes
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;

const MODELS = [
  "gemini-2.5-flash",
  "gemini-2.0-flash",
  "gemini-2.0-flash-001",
  "gemini-flash-latest",
  "gemini-2.5-flash-lite",
];

const GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models";

// Warm-invocation cache — persists while Lambda container is alive
const _cache = new Map();

async function fetchDescriptions(dishes) {
  const result = {};
  const uncached = dishes.filter((d) => !_cache.has(d.toLowerCase()));

  // Serve cached first
  dishes.forEach((d) => { if (_cache.has(d.toLowerCase())) result[d] = _cache.get(d.toLowerCase()); });

  if (!uncached.length) return result;

  const prompt =
    "For each dish below write a 1-2 sentence description for a first-time traveler. " +
    "Be friendly and specific.\n" +
    "Return ONLY a valid JSON array, no markdown fences:\n" +
    '[{"dish":"Name","description":"Description."}]\n\nDishes:\n' +
    uncached.map((d) => `- ${d}`).join("\n");

  for (const model of MODELS) {
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
    const text = data?.candidates?.[0]?.content?.parts?.[0]?.text ?? "";

    try {
      const match = text.match(/\[[\s\S]*\]/);
      if (match) {
        JSON.parse(match[0]).forEach(({ dish, description }) => {
          if (dish) {
            result[dish] = description || "";
            _cache.set(dish.toLowerCase(), description || "");
          }
        });
      }
    } catch { /* return empty descriptions */ }
    break;
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
  if (!GEMINI_API_KEY) return resp(500, { error: "GEMINI_API_KEY not set." });

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
