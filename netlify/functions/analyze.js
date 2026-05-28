// Netlify Function — Node.js 18+ (uses built-in fetch, zero npm dependencies)
// v2: model fallback loop — tries each free-tier vision model until one responds
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;

const EXTRACT_PROMPT =
  "You are a menu reader. Extract only the food dish names from this menu image. " +
  "Ignore prices, calorie counts, section headers, and descriptions. " +
  "Return one dish name per line, nothing else.";

// Free-tier Gemini models that support vision, tried in order
const MODELS = [
  "gemini-1.5-flash",
  "gemini-1.5-flash-latest",
  "gemini-1.5-flash-001",
  "gemini-2.0-flash",
  "gemini-2.0-flash-exp",
];

// ── Gemini call with model fallback ───────────────────────────────────────────
async function callGemini(image, mimeType) {
  let lastErr = "No models tried";

  for (const model of MODELS) {
    const url =
      `https://generativelanguage.googleapis.com/v1/models/${model}:generateContent` +
      `?key=${GEMINI_API_KEY}`;

    let res;
    try {
      res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{
            parts: [
              { text: EXTRACT_PROMPT },
              { inlineData: { mimeType, data: image } },
            ],
          }],
        }),
      });
    } catch (e) {
      lastErr = `Network error on ${model}: ${e.message}`;
      continue;
    }

    if (res.status === 404) {
      lastErr = `Model not available: ${model}`;
      continue; // try next model
    }

    if (!res.ok) {
      const body = await res.text();
      lastErr = `${model} returned ${res.status}: ${body}`;
      continue;
    }

    const data = await res.json();
    const text = data?.candidates?.[0]?.content?.parts?.[0]?.text ?? "";
    return { text, model };
  }

  throw new Error(`All Gemini models failed. Last error: ${lastErr}`);
}

// ── Dish parser ───────────────────────────────────────────────────────────────
function parseDishes(raw) {
  if (!raw || !raw.trim()) return [];
  const seen = new Set();
  const dishes = [];

  for (let line of raw.split(/[\n,]/)) {
    line = line.replace(/^[\s\d.)•\-*]+/, "").trim();
    line = line.replace(
      /[\$₹£€]\s*\d+(\.\d+)?|Rs\.?\s*\d+|\d+(\.\d+)?\s*(rs|₹|\$)?$/gi, ""
    ).trim();
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
  if (method === "GET") return resp(200, { status: "ok", service: "IdliPeek", version: 2 });
  if (method !== "POST") return resp(405, { error: "Method not allowed" });

  if (!GEMINI_API_KEY) {
    return resp(500, {
      error: "GEMINI_API_KEY is not set — add it in Netlify → Site configuration → Environment variables.",
    });
  }

  let body;
  try {
    body = JSON.parse(event.body);
  } catch {
    return resp(400, { error: "Request body must be JSON" });
  }

  const { image, mimeType, filename = "upload" } = body;
  if (!image || !mimeType) {
    return resp(400, { error: "Missing fields: image (base64) and mimeType are required" });
  }

  const ALLOWED = ["image/jpeg", "image/png", "image/webp"];
  if (!ALLOWED.includes(mimeType)) {
    return resp(400, { error: `Unsupported mimeType '${mimeType}'. Allowed: ${ALLOWED.join(", ")}` });
  }

  if (image.length > 5_600_000) {
    return resp(400, { error: "Image too large. Max ~4 MB." });
  }

  try {
    const { text: rawText, model } = await callGemini(image, mimeType);
    const dishes = parseDishes(rawText);

    return resp(200, {
      filename,
      dishes,
      count: dishes.length,
      raw_gemini_output: rawText,
      model_used: model,
    });
  } catch (e) {
    return resp(502, { error: e.message });
  }
};
