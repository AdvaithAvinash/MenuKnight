# 🍛 IdliPeek — TODO Checklist
> Peek before you pick

## 📌 Project Goal
Upload a menu image → extract dish names → fetch real images → generate descriptions → return a scrollable visual menu preview.

---

# 🧱 PHASE 0 — PROJECT SETUP

## 🏗️ Repository & Structure
- [ ] Create Git repository `idlipeek`
- [ ] Initialize Python project (3.10+)
- [ ] Create folder structure:
  - [ ] `main.py` — CLI entry point
  - [ ] `config.py` — API keys and constants
  - [ ] `gemini_client.py` — Gemini API wrapper
  - [ ] `image_loader.py` — image loading and base64 encoding
  - [ ] `parser.py` — dish name extraction and cleaning
  - [ ] `image_search/` — per-source image search modules
    - [ ] `__init__.py`
    - [ ] `unsplash.py`
    - [ ] `pexels.py`
    - [ ] `spoonacular.py`
    - [ ] `serpapi.py`
    - [ ] `resolver.py` — fallback chain logic
  - [ ] `cache.py` — in-memory caching layer
  - [ ] `assembler.py` — response builder
  - [ ] `utils.py` — shared helpers (logging, validators)
  - [ ] `tests/` — all test files
    - [ ] `test_image_loader.py`
    - [ ] `test_parser.py`
    - [ ] `test_gemini_client.py`
    - [ ] `test_image_search.py`
    - [ ] `test_assembler.py`
    - [ ] `test_cache.py`
    - [ ] `test_pipeline.py`

## ⚙️ Environment Setup
- [ ] Create and activate virtual environment (`python -m venv .venv`)
- [ ] Create `requirements.txt` and install:
  - [ ] `requests`
  - [ ] `python-dotenv`
  - [ ] `Pillow`
  - [ ] `flask` or `fastapi` + `uvicorn` (for Phase 10)
- [ ] Create `.env` file with placeholder keys:
  - [ ] `GEMINI_API_KEY`
  - [ ] `UNSPLASH_ACCESS_KEY`
  - [ ] `PEXELS_API_KEY`
  - [ ] `SPOONACULAR_API_KEY`
  - [ ] `SERPAPI_KEY`
- [ ] Add `.env` to `.gitignore`
- [ ] Add `.gitignore` (also ignore `__pycache__`, `.venv`, `*.pyc`)

## 🧪 Smoke Test
- [ ] Run `python main.py --help` — confirm CLI starts without errors
- [ ] Confirm all imports resolve cleanly

---

# 🖼️ PHASE 1 — IMAGE INPUT PIPELINE

## 📥 Image Loader (`image_loader.py`)
- [ ] Implement `load_image(path: str) -> dict`
  - [ ] Validate file exists (raise clear error if not)
  - [ ] Validate file extension is one of: `.jpg`, `.jpeg`, `.png`, `.webp`
  - [ ] Open and read file bytes
  - [ ] Convert to base64 string
  - [ ] Detect MIME type from extension
  - [ ] Return structured object:
    ```python
    {
      "filename": "menu.jpg",
      "base64": "<base64_string>",
      "mime_type": "image/jpeg"
    }
    ```

## 🧪 Tests (`tests/test_image_loader.py`)
- [ ] Test valid `.jpg` input returns correct structure
- [ ] Test valid `.png` input returns correct structure
- [ ] Test non-existent file raises `FileNotFoundError`
- [ ] Test unsupported extension (`.gif`, `.pdf`) raises `ValueError`
- [ ] Test base64 output is a non-empty string

---

# 🤖 PHASE 2 — GEMINI MENU EXTRACTION

## 🔌 Gemini Client Setup (`gemini_client.py`)
- [ ] Load `GEMINI_API_KEY` from environment
- [ ] Implement `extract_dishes_from_image(base64_image: str, mime_type: str) -> str`
  - [ ] Build multipart request with image and prompt
  - [ ] Use Gemini Flash 2.5 Vision API endpoint
  - [ ] Set timeout (e.g., 30s)
  - [ ] Return raw text response (no parsing yet)
  - [ ] Raise descriptive error on API failure (4xx, 5xx, timeout)

## 🧾 Prompt Engineering
- [ ] Use prompt:
  > "You are a menu reader. Extract only the food dish names from this menu image. Ignore prices, calorie counts, section headers, and descriptions. Return one dish name per line, nothing else."
- [ ] Test prompt against at least 3 varied menu styles (printed, handwritten photo, fancy restaurant)
- [ ] Tune prompt if output contains noise

## 🧪 Tests (`tests/test_gemini_client.py`)
- [ ] Test with a clear sample menu image — verify response is non-empty string
- [ ] Test API key missing raises clear `EnvironmentError`
- [ ] Test simulated API 500 response is handled gracefully
- [ ] Test simulated timeout is handled gracefully

---

# 🧹 PHASE 3 — DISH CLEANING & PARSING

## 🧼 Parser Module (`parser.py`)
- [ ] Implement `parse_dish_list(raw_text: str) -> list[str]`
  - [ ] Split on newlines and commas
  - [ ] Strip leading/trailing whitespace from each item
  - [ ] Remove lines that are:
    - [ ] Empty or whitespace-only
    - [ ] Purely numeric (prices like `120`, `$5.00`)
    - [ ] Short noise tokens (fewer than 2 characters)
    - [ ] Known non-dish patterns (e.g., lines starting with `*`, `-` alone)
  - [ ] Remove inline prices (`₹120`, `$5`, `Rs.80`)
  - [ ] Normalize to Title Case
  - [ ] Deduplicate (case-insensitive)
  - [ ] Return clean list: `["Masala Dosa", "Idli Sambar", ...]`

## 🧪 Tests (`tests/test_parser.py`)
- [ ] Test clean Gemini output parses correctly
- [ ] Test output with prices mixed in — prices removed
- [ ] Test output with bullet points and numbering — stripped
- [ ] Test duplicate dish names are collapsed to one
- [ ] Test empty string input returns empty list
- [ ] Test input with only noise returns empty list

---

# 🌐 PHASE 4 — IMAGE SEARCH (SINGLE SOURCE FIRST)

## 🖼️ Unsplash Integration (`image_search/unsplash.py`)
- [ ] Load `UNSPLASH_ACCESS_KEY` from environment
- [ ] Implement `search_unsplash(dish_name: str) -> str | None`
  - [ ] Call Unsplash Search Photos API
  - [ ] Use `dish_name` as query term
  - [ ] Return URL of first result's `regular` size image
  - [ ] Return `None` if no results found
  - [ ] Handle API errors gracefully (log + return `None`)

## 🧪 Tests (`tests/test_image_search.py`)
- [ ] Test `"Pizza"` returns a valid HTTPS URL
- [ ] Test `"Biryani"` returns a valid HTTPS URL
- [ ] Test nonsense query (e.g., `"xyzabc123"`) returns `None`
- [ ] Test missing API key raises `EnvironmentError`

---

# 🔁 PHASE 5 — MULTI-SOURCE FALLBACK CHAIN

## 🍽️ Spoonacular Integration (`image_search/spoonacular.py`)
- [ ] Load `SPOONACULAR_API_KEY` from environment
- [ ] Implement `search_spoonacular(dish_name: str) -> str | None`
  - [ ] Call Spoonacular Recipe/Food Search API
  - [ ] Return first result image URL or `None`

## 📸 Pexels Integration (`image_search/pexels.py`)
- [ ] Load `PEXELS_API_KEY` from environment
- [ ] Implement `search_pexels(dish_name: str) -> str | None`
  - [ ] Call Pexels Search API
  - [ ] Return first result's `medium` photo URL or `None`

## 🔍 SerpAPI Integration (`image_search/serpapi.py`)
- [ ] Load `SERPAPI_KEY` from environment
- [ ] Implement `search_serpapi(dish_name: str) -> str | None`
  - [ ] Call SerpAPI Google Images endpoint
  - [ ] Return first result's image URL or `None`

## 🧠 Resolver / Fallback Chain (`image_search/resolver.py`)
- [ ] Implement `get_best_dish_image(dish_name: str) -> dict`
  - [ ] Try sources in order: Spoonacular → Unsplash → Pexels → SerpAPI
  - [ ] Return on first non-`None` result
  - [ ] Return structure:
    ```python
    {
      "image_url": "https://...",
      "source": "unsplash",
      "found": True
    }
    ```
  - [ ] Return `{"image_url": None, "source": None, "found": False}` if all fail

## 🧪 Tests
- [ ] Simulate Spoonacular returning `None` → verify Unsplash is tried
- [ ] Simulate all sources returning `None` → verify graceful empty result
- [ ] Test resolver returns correct `source` field
- [ ] Verify no exception propagates from resolver under any failure

---

# 📝 PHASE 6 — DISH DESCRIPTION GENERATION

## 🤖 Gemini Text Mode (`gemini_client.py`)
- [ ] Implement `describe_dish(dish_name: str) -> str`
  - [ ] Use Gemini Flash 2.5 text-only mode
  - [ ] Prompt:
    > "Describe the dish '{dish_name}' in 1–2 simple, friendly sentences for a traveler who has never heard of it before."
  - [ ] Return description string
  - [ ] Return empty string on failure (do not crash pipeline)

## 🧪 Tests
- [ ] Test `"Masala Dosa"` returns non-empty readable text
- [ ] Test `"Pizza"` returns non-empty readable text
- [ ] Test API failure returns empty string without raising

---

# 📦 PHASE 7 — RESPONSE ASSEMBLY

## 🧩 Assembler Module (`assembler.py`)
- [ ] Define output schema per dish:
  ```python
  {
    "dish": "Masala Dosa",
    "image_url": "https://...",
    "image_source": "unsplash",
    "description": "A crispy crepe made from fermented rice batter...",
    "image_found": True
  }
  ```
- [ ] Implement `assemble_results(dish_names: list[str]) -> list[dict]`
  - [ ] For each dish: fetch image + description (can be sequential for now)
  - [ ] Build and return list of result objects
  - [ ] Log progress per dish

## 🧪 Tests (`tests/test_assembler.py`)
- [ ] Test output list length matches input dish count
- [ ] Test each result object has all required fields
- [ ] Test no field is `None` for a known dish
- [ ] Test empty input list returns empty output list

---

# ⚡ PHASE 8 — END-TO-END PIPELINE

## 🔗 Full Integration (`main.py`)
- [ ] Wire full flow:
  1. Accept image path from CLI (`sys.argv` or `argparse`)
  2. Load image → base64
  3. Call Gemini Vision → raw text
  4. Parse raw text → dish list
  5. Assemble results (image + description per dish)
  6. Print final JSON to stdout
- [ ] Add step-by-step logging (each stage prints status)
- [ ] Add total elapsed time logging
- [ ] Handle and display user-friendly error messages

## 🧪 Tests (`tests/test_pipeline.py`)
- [ ] Run full pipeline with a real menu image
- [ ] Verify output is valid JSON
- [ ] Verify each dish entry has image + description
- [ ] Verify pipeline completes under 30 seconds for a 5-dish menu
- [ ] Test with a noisy/low-quality menu image

---

# 🧠 PHASE 9 — CACHING LAYER

## 💾 Cache Module (`cache.py`)
- [ ] Implement in-memory dict-based cache
- [ ] Implement `cache_get(key: str) -> dict | None`
- [ ] Implement `cache_set(key: str, value: dict)`
- [ ] Use `dish_name` (lowercased, stripped) as cache key
- [ ] Optional: add TTL (time-to-live) per entry
- [ ] Wire cache into `assembler.py`:
  - [ ] Check cache before API calls
  - [ ] Store result in cache after successful fetch

## 🧪 Tests (`tests/test_cache.py`)
- [ ] Test cache miss → returns `None`
- [ ] Test cache set + get → returns stored value
- [ ] Test case-insensitive key lookup
- [ ] Test repeated dish in pipeline triggers only one API call (assert call count)

---

# 🌐 PHASE 10 — API / FRONTEND INTEGRATION

## 📡 REST API Layer (optional upgrade)
- [ ] Add Flask or FastAPI app (`api.py`)
- [ ] Implement endpoint: `POST /analyze`
  - [ ] Accept: multipart image upload
  - [ ] Return: JSON list of dish results
- [ ] Add basic request validation (file size, type)
- [ ] Add CORS headers for web frontend

## 📱 Frontend / Glide Integration
- [ ] Connect Glide upload action → `/analyze` endpoint
- [ ] Map JSON response fields to Glide components:
  - [ ] Dish name → title
  - [ ] `image_url` → photo
  - [ ] `description` → detail text
- [ ] Test full flow: upload from mobile → gallery renders

## 🧪 Tests
- [ ] POST request with valid image returns 200 + JSON
- [ ] POST request with invalid file type returns 400
- [ ] POST request with no file returns 422
- [ ] Manual test: upload real restaurant menu from phone → verify gallery

---

# 🚀 PHASE 11 — OPTIMIZATION

## 💰 Cost Reduction
- [ ] Batch multiple dish descriptions into a single Gemini call
- [ ] Prioritize cache hits before any API call
- [ ] Log API call counts per pipeline run
- [ ] Estimate cost per menu scan (Gemini tokens + image API calls)

## ⚡ Performance
- [ ] Parallelize image search calls across dishes (`concurrent.futures.ThreadPoolExecutor`)
- [ ] Parallelize description generation across dishes
- [ ] Benchmark before and after parallelization

## 🧪 Tests
- [ ] Compare API call count: pre-cache vs post-cache for repeated dishes
- [ ] Measure pipeline time: sequential vs parallel image fetching
- [ ] Target: ≤ 10s for a 10-dish menu with cache warm

---

# ✅ FINAL VALIDATION CHECKLIST

- [ ] Works correctly with 5+ different real restaurant menus
- [ ] Handles low-quality / noisy / skewed menu images
- [ ] No broken image URLs in output
- [ ] All descriptions are readable and accurate
- [ ] No unhandled exceptions during normal operation
- [ ] API keys are never logged or exposed
- [ ] `.env` is excluded from version control
- [ ] All tests pass (`python -m pytest tests/`)
- [ ] README documents setup and usage steps
- [ ] System is stable under 10 repeated pipeline runs

---

> **Build order:** Always complete and test one phase fully before starting the next.
> **Rule:** If a phase's tests don't pass, do not advance.
