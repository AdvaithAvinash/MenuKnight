// Phase 1 of 2: Vision-only — extract dish names from image
// Kept lean so it comfortably fits inside Netlify's 10s free-tier timeout
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

async function callGeminiVision(image, mimeType) {
  let lastErr = "No models tried";
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
        body: JSON.stringify({
          contents: [{ parts: [
            { text: EXTRACT_PROMPT },
            { inlineData: { mimeType, data: image } },
          ]}],
        }),
      });
    } catch (e) {
      lastErr = e.name === "AbortError" ? `${model} timed out` : `Network error: ${e.message}`;
      continue;
    } finally { clearTimeout(timer); }

    const body = await res.text();
    if (res.status === 404) { lastErr = `${model} → 404`; continue; }
    if (!res.ok) { lastErr = `${model} → ${res.status}: ${body.slice(0, 150)}`; continue; }

    const data = JSON.parse(body);
    return { text: data?.candidates?.[0]?.content?.parts?.[0]?.text ?? "", model };
  }
  throw new Error(`Gemini Vision failed. Last: ${lastErr}`);
}

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
  if (method === "GET") return resp(200, { status: "ok", service: "IdliPeek/analyze" });
  if (method !== "POST") return resp(405, { error: "Method not allowed" });
  if (!GEMINI_API_KEY) return resp(500, { error: "GEMINI_API_KEY not set in Netlify environment variables." });

  let body;
  try { body = JSON.parse(event.body); }
  catch { return resp(400, { error: "Body must be JSON" }); }

  const { image, mimeType, filename = "upload" } = body;
  if (!image || !mimeType) return resp(400, { error: "Missing: image (base64) and mimeType" });
  if (!["image/jpeg", "image/png", "image/webp"].includes(mimeType)) return resp(400, { error: `Unsupported mimeType '${mimeType}'` });
  if (image.length > 5_600_000) return resp(400, { error: "Image too large. Max ~4 MB." });

  try {
    const { text: rawText, model } = await callGeminiVision(image, mimeType);
    const dishes = parseDishes(rawText);
    return resp(200, { filename, dishes, count: dishes.length, raw_gemini_output: rawText, model_used: model });
  } catch (e) {
    return resp(502, { error: e.message });
  }
};
