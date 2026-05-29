// Phase 1 of 2: Vision-only — extract dish names from image
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const NVIDIA_API_KEY = process.env.NVIDIA_API_KEY;
const GROQ_API_KEY   = process.env.GROQ_API_KEY;

const EXTRACT_PROMPT =
  "You are a menu reader. Extract only the food dish names from this menu image. " +
  "Ignore prices, calorie counts, section headers, and descriptions. " +
  "Return one dish name per line, nothing else.";

// Only keep the 2 fastest Gemini models — no point queuing 5 when budget is tight
const GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash"];
const GEMINI_BASE   = "https://generativelanguage.googleapis.com/v1beta/models";

const NVIDIA_MODELS = [
  "nvidia/neva-22b",
  "meta/llama-3.2-11b-vision-instruct",
];
const NVIDIA_BASE = "https://integrate.api.nvidia.com/v1";
const GROQ_BASE   = "https://api.groq.com/openai/v1";

// deadline = absolute ms timestamp; each attempt gets whatever time is left
// (minus a 400ms buffer so we can still return a response before Netlify kills us)
async function callGeminiVision(image, mimeType, deadline) {
  let lastErr = "No models tried";
  for (const model of GEMINI_MODELS) {
    const remaining = deadline - Date.now();
    if (remaining < 1200) { lastErr = "Time budget reached"; break; }
    const timeout = Math.min(remaining - 400, 4500);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    let res;
    try {
      res = await fetch(`${GEMINI_BASE}/${model}:generateContent?key=${GEMINI_API_KEY}`, {
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
      lastErr = e.name === "AbortError" ? `${model} timed out` : `Network: ${e.message}`;
      continue;
    } finally { clearTimeout(timer); }

    const body = await res.text();
    if (res.status === 404) { lastErr = `${model} → 404`; continue; }
    if (!res.ok) { lastErr = `${model} → ${res.status}: ${body.slice(0, 120)}`; continue; }

    const data = JSON.parse(body);
    return { text: data?.candidates?.[0]?.content?.parts?.[0]?.text ?? "", model };
  }
  throw new Error(`Gemini failed: ${lastErr}`);
}

async function callNvidiaVision(image, mimeType, deadline) {
  let lastErr = "No NVIDIA models tried";
  for (const model of NVIDIA_MODELS) {
    const remaining = deadline - Date.now();
    if (remaining < 1200) { lastErr = "Time budget reached"; break; }
    const timeout = Math.min(remaining - 400, 4500);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    let res;
    try {
      res = await fetch(`${NVIDIA_BASE}/chat/completions`, {
        method: "POST",
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${NVIDIA_API_KEY}`,
        },
        body: JSON.stringify({
          model,
          messages: [{
            role: "user",
            content: [
              { type: "text", text: EXTRACT_PROMPT },
              { type: "image_url", image_url: { url: `data:${mimeType};base64,${image}` } },
            ],
          }],
          max_tokens: 1024,
        }),
      });
    } catch (e) {
      lastErr = e.name === "AbortError" ? `${model} timed out` : `Network: ${e.message}`;
      continue;
    } finally { clearTimeout(timer); }

    const body = await res.text();
    if (res.status === 404) { lastErr = `${model} → 404`; continue; }
    if (!res.ok) { lastErr = `${model} → ${res.status}: ${body.slice(0, 120)}`; continue; }

    const data = JSON.parse(body);
    return { text: data?.choices?.[0]?.message?.content ?? "", model };
  }
  throw new Error(`NVIDIA failed: ${lastErr}`);
}

async function callGroqVision(image, mimeType) {
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
        model: "meta-llama/llama-4-scout-17b-16e-instruct",
        messages: [{
          role: "user",
          content: [
            { type: "text", text: EXTRACT_PROMPT },
            { type: "image_url", image_url: { url: `data:${mimeType};base64,${image}` } },
          ],
        }],
        max_tokens: 1024,
      }),
    });
  } catch (e) {
    throw new Error(e.name === "AbortError" ? "WizardKnight timed out" : `Network: ${e.message}`);
  } finally { clearTimeout(timer); }

  const body = await res.text();
  if (!res.ok) throw new Error(`WizardKnight → ${res.status}: ${body.slice(0, 120)}`);
  const data = JSON.parse(body);
  return { text: data?.choices?.[0]?.message?.content ?? "", model: "meta-llama/llama-4-scout-17b-16e-instruct" };
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
  // Netlify free tier kills functions at 10s wall-clock from invocation.
  // We budget 8.5s from handler entry (cold-start is already "spent" before we get here).
  const DEADLINE = Date.now() + 8500;

  const method = event.httpMethod;
  if (method === "OPTIONS") return resp(200, {});
  if (method === "GET") return resp(200, { status: "ok", service: "MenuKnight/analyze" });
  if (method !== "POST") return resp(405, { error: "Method not allowed" });

  let body;
  try { body = JSON.parse(event.body); }
  catch { return resp(400, { error: "Body must be JSON" }); }

  const { image, mimeType, filename = "upload", provider = "gemini" } = body;
  if (!image || !mimeType) return resp(400, { error: "Missing: image (base64) and mimeType" });
  if (!["image/jpeg", "image/png", "image/webp"].includes(mimeType))
    return resp(400, { error: `Unsupported mimeType '${mimeType}'` });
  if (image.length > 5_600_000) return resp(400, { error: "Image too large. Max ~4 MB." });

  if (provider === "nvidia" && !NVIDIA_API_KEY) return resp(500, { error: "NVIDIA_API_KEY not set." });
  if (provider === "groq"   && !GROQ_API_KEY)   return resp(500, { error: "GROQ_API_KEY not set." });
  if (provider === "gemini" && !GEMINI_API_KEY)  return resp(500, { error: "GEMINI_API_KEY not set." });

  try {
    let result;

    if (provider === "groq") {
      result = await callGroqVision(image, mimeType);
    } else if (provider === "nvidia") {
      result = await callNvidiaVision(image, mimeType, DEADLINE);
    } else {
      result = await callGeminiVision(image, mimeType, DEADLINE);
    }

    const dishes = parseDishes(result.text);
    return resp(200, {
      filename, dishes, count: dishes.length,
      raw_gemini_output: result.text, model_used: result.model,
    });

  } catch (primaryErr) {
    // If primary model failed and Groq is available and we still have time,
    // fall back to Groq automatically so mobile users always get a result
    const remaining = DEADLINE - Date.now();
    if (provider !== "groq" && GROQ_API_KEY && remaining > 2000) {
      try {
        const result = await callGroqVision(image, mimeType);
        const dishes = parseDishes(result.text);
        return resp(200, {
          filename, dishes, count: dishes.length,
          raw_gemini_output: result.text,
          model_used: result.model,
          fallback_note: `Primary (${provider}) failed: ${primaryErr.message}`,
        });
      } catch (groqErr) {
        return resp(502, { error: `Both primary and fallback failed. Primary: ${primaryErr.message}` });
      }
    }
    return resp(502, { error: primaryErr.message });
  }
};
