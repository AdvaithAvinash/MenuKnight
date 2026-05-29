// Netlify Function — Node.js 18+ (built-in fetch, zero npm dependencies)
// v4: warm-invocation description cache (Phase 9) + mobile-ready response
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;

const EXTRACT_PROMPT =
  "You are a menu reader. Extract only the food dish names from this menu image. " +
  "Ignore prices, calorie counts, section headers, and descriptions. " +
  "Return one dish name per line, nothing else.";

const MODELS = [
  "gemini-2.5-flash",
  "gemini-2.0-flash",
  "gemini-2.0-flash-001",
  "gemini-flash-latest",
  "gemini-2.5-flash-lite",
];

const GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models";

// ── Warm-invocation cache (persists while Lambda container is alive) ───────────
const _descCache = new Map(); // normalised dish name → description string

function cacheKey(dish) {
  return dish.toLowerCase().trim();
}

// ── Gemini helpers ────────────────────────────────────────────────────────────
async function callGeminiText(prompt) {
  for (const model of MODELS) {
    const url = `${GEMINI_BASE}/${model}:generateContent?key=${GEMINI_API_KEY}`;
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }),
      });
      if (!res.ok) continue;
      const data = await res.json();
      return data?.candidates?.[0]?.content?.parts?.[0]?.text ?? "";
    } catch { continue; }
  }
  return "";
}

async function callGeminiVision(image, mimeType) {
  let lastErr = "No models tried";
  for (const model of MODELS) {
    const url = `${GEMINI_BASE}/${model}:generateContent?key=${GEMINI_API_KEY}`;
    let res;
    try {
      res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ parts: [
            { text: EXTRACT_PROMPT },
            { inlineData: { mimeType, data: image } },
          ]}],
        }),
      });
    } catch (e) { lastErr = `Network error on ${model}: ${e.message}`; continue; }

    const bodyText = await res.text();
    if (res.status === 404) { lastErr = `${model} → 404: ${bodyText.slice(0, 200)}`; continue; }
    if (!res.ok) { lastErr = `${model} → ${res.status}: ${bodyText.slice(0, 200)}`; continue; }

    const data = JSON.parse(bodyText);
    return { text: data?.candidates?.[0]?.content?.parts?.[0]?.text ?? "", model };
  }
  throw new Error(`All Gemini models failed. Last: ${lastErr}`);
}

// ── Batch descriptions with cache ─────────────────────────────────────────────
async function fetchDescriptions(dishes) {
  if (!dishes.length) return {};

  const result = {};
  const uncached = [];

  // Serve from warm cache first
  for (const dish of dishes) {
    const k = cacheKey(dish);
    if (_descCache.has(k)) {
      result[dish] = _descCache.get(k);
    } else {
      uncached.push(dish);
    }
  }

  if (!uncached.length) return result;

  const prompt =
    "For each dish below, write a 1-2 sentence description for a first-time traveler. " +
    "Be friendly and specific.\n" +
    "Return ONLY a valid JSON array, no markdown:\n" +
    '[{"dish": "Name", "description": "Description."}]\n\nDishes:\n' +
    uncached.map((d) => `- ${d}`).join("\n");

  const text = await callGeminiText(prompt);
  if (text) {
    try {
      const match = text.match(/\[[\s\S]*\]/);
      if (match) {
        JSON.parse(match[0]).forEach(({ dish, description }) => {
          if (dish) {
            result[dish] = description || "";
            _descCache.set(cacheKey(dish), description || ""); // store in warm cache
          }
        });
      }
    } catch { /* silently return empty descriptions */ }
  }

  return result;
}

// ── Dish parser ───────────────────────────────────────────────────────────────
function parseDishes(raw) {
  if (!raw || !raw.trim()) return [];
  const seen = new Set();
  const dishes = [];
  for (let line of raw.split(/[\n,]/)) {
    line = line.replace(/^[\s\d.)•\-*]+/, "").trim();
    line = line.replace(/[\$₹£€]\s*\d+(\.\d+)?|Rs\.?\s*\d+|\d+(\.\d+)?\s*(rs|₹|\$)?$/gi, "").trim();
    if (!line || line.length < 2) continue;
    if (/^[\$₹£€]?\s*\d+(\.\d+)?\s*$/.test(line)) continue;
    const key = line.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    dishes.push(line.replace(/\b\w/g, (c) => c.toUpperCase()));
  }
  return dishes;
}

// ── Response helper ───────────────────────────────────────────────────────────
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

// ── Handler ───────────────────────────────────────────────────────────────────
exports.handler = async (event) => {
  const method = event.httpMethod;

  if (method === "OPTIONS") return resp(200, {});
  if (method === "GET") return resp(200, { status: "ok", service: "IdliPeek", version: 4, cacheSize: _descCache.size });
  if (method !== "POST") return resp(405, { error: "Method not allowed" });

  if (!GEMINI_API_KEY) {
    return resp(500, { error: "GEMINI_API_KEY is not set — add it in Netlify → Environment variables." });
  }

  let body;
  try { body = JSON.parse(event.body); }
  catch { return resp(400, { error: "Request body must be JSON" }); }

  const { image, mimeType, filename = "upload" } = body;
  if (!image || !mimeType) return resp(400, { error: "Missing: image (base64) and mimeType" });
  if (!["image/jpeg", "image/png", "image/webp"].includes(mimeType)) return resp(400, { error: `Unsupported mimeType '${mimeType}'` });
  if (image.length > 5_600_000) return resp(400, { error: "Image too large. Max ~4 MB." });

  try {
    const { text: rawText, model } = await callGeminiVision(image, mimeType);
    const dishes = parseDishes(rawText);
    const descriptions = await fetchDescriptions(dishes);

    const results = dishes.map((dish) => ({
      dish,
      description: descriptions[dish] || "",
    }));

    return resp(200, { filename, results, dishes, count: dishes.length, raw_gemini_output: rawText, model_used: model });
  } catch (e) {
    return resp(502, { error: e.message });
  }
};
