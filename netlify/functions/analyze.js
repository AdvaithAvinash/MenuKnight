// Netlify Function — Node.js 18+ (uses built-in fetch, zero npm dependencies)
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const GEMINI_URL =
  "https://generativelanguage.googleapis.com/v1beta/models/" +
  "gemini-1.5-flash:generateContent";

const EXTRACT_PROMPT =
  "You are a menu reader. Extract only the food dish names from this menu image. " +
  "Ignore prices, calorie counts, section headers, and descriptions. " +
  "Return one dish name per line, nothing else.";

// ── Dish parser ───────────────────────────────────────────────────────────────
function parseDishes(raw) {
  if (!raw || !raw.trim()) return [];

  const seen = new Set();
  const dishes = [];

  for (let line of raw.split(/[\n,]/)) {
    line = line.replace(/^[\s\d.)•\-*]+/, "").trim(); // strip leading bullets/numbers
    line = line.replace(
      /[\$₹£€]\s*\d+(\.\d+)?|Rs\.?\s*\d+|\d+(\.\d+)?\s*(rs|₹|\$)?$/gi,
      ""
    ).trim(); // strip trailing prices

    if (!line || line.length < 2) continue;
    if (/^[\$₹£€]?\s*\d+(\.\d+)?\s*$/.test(line)) continue; // pure price line

    const key = line.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    dishes.push(line.replace(/\b\w/g, (c) => c.toUpperCase())); // Title Case
  }

  return dishes;
}

// ── CORS response helper ──────────────────────────────────────────────────────
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
  if (method === "GET") return resp(200, { status: "ok", service: "IdliPeek" });
  if (method !== "POST") return resp(405, { error: "Method not allowed" });

  if (!GEMINI_API_KEY) {
    return resp(500, {
      error: "GEMINI_API_KEY is not set. Add it in Netlify → Site configuration → Environment variables.",
    });
  }

  // Expect JSON body: { image: "<base64>", mimeType: "image/jpeg", filename: "..." }
  let body;
  try {
    body = JSON.parse(event.body);
  } catch {
    return resp(400, { error: "Request body must be JSON" });
  }

  const { image, mimeType, filename = "upload" } = body;

  if (!image || !mimeType) {
    return resp(400, { error: "Missing fields: image (base64 string) and mimeType are required" });
  }

  const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];
  if (!ALLOWED_TYPES.includes(mimeType)) {
    return resp(400, { error: `Unsupported mimeType '${mimeType}'. Allowed: ${ALLOWED_TYPES.join(", ")}` });
  }

  // ~4 MB limit (base64 of 4 MB is ~5.5 MB as a string)
  if (image.length > 5_600_000) {
    return resp(400, { error: "Image too large. Max ~4 MB." });
  }

  let geminiRes;
  try {
    geminiRes = await fetch(`${GEMINI_URL}?key=${GEMINI_API_KEY}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [
          {
            parts: [
              { text: EXTRACT_PROMPT },
              { inlineData: { mimeType, data: image } },
            ],
          },
        ],
      }),
    });
  } catch (e) {
    return resp(502, { error: `Failed to reach Gemini API: ${e.message}` });
  }

  if (!geminiRes.ok) {
    const errText = await geminiRes.text();
    return resp(502, { error: `Gemini API returned ${geminiRes.status}: ${errText}` });
  }

  let geminiData;
  try {
    geminiData = await geminiRes.json();
  } catch {
    return resp(502, { error: "Gemini API returned non-JSON response" });
  }

  const rawText = geminiData?.candidates?.[0]?.content?.parts?.[0]?.text ?? "";
  const dishes = parseDishes(rawText);

  return resp(200, {
    filename,
    dishes,
    count: dishes.length,
    raw_gemini_output: rawText,
  });
};
