import json
import os
import asyncio
from fastapi import FastAPI, Depends, HTTPException, Response, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from itsdangerous import URLSafeSerializer
import httpx
from typing import Optional
from dotenv import load_dotenv
from uuid import uuid4
import time
from pydantic import BaseModel
from starlette import status
from celery import Celery


# Load environment variables first
load_dotenv()

# ---- Environment variables ----
APP_ENV = os.getenv("APP_ENV", "development").lower()
# Ensure GITHUB_TOKEN is set in your .env file
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# ---- Ollama API URL ----
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3:mini")
OLLAMA_FALLBACK_MODELS = [
    m.strip() for m in os.getenv("OLLAMA_FALLBACK_MODELS", "").split(",") if m.strip()
]

app = FastAPI()

# ---- Session persistence ----
SESSIONS_FILE = "sessions.json"

# ---- GitHub API URL ----
GITHUB_API_URL = "https://api.github.com/users"

class ChatRequest(BaseModel):
    message: str
    repo: str
    github_user: str
    file: Optional[str] = None
    file_content: Optional[str] = None
    model: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    sources: list[str] = []
    meta: dict = {}


def load_sessions():
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_sessions():
    with open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f)

sessions = load_sessions()

# ---- Cookie signing ----
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if APP_ENV == "development":
        SECRET_KEY = "dev-only-secret-change-me"
        print("WARNING: SECRET_KEY is not set. Using an insecure development fallback.")
    else:
        raise RuntimeError("SECRET_KEY must be set when APP_ENV is not 'development'.")
serializer = URLSafeSerializer(SECRET_KEY)

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# ---- Env vars ----
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")


def ensure_github_oauth_config():
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="GitHub OAuth is not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET."
        )


# ---------- NEW: tiny in-memory TTL cache for GitHub responses ----------
from functools import lru_cache
from collections import defaultdict
import re
import math
from datetime import datetime, timedelta

_CACHE: dict[str, tuple[float, dict | list | str | int]] = {}
CACHE_TTL_SECONDS = 45  # short TTL to stay fresh
_REPO_CONTEXT_CACHE: dict[str, tuple[float, dict]] = {}
REPO_CONTEXT_TTL_SECONDS = 90
_OLLAMA_MODELS_CACHE: tuple[float, list[str]] | None = None
OLLAMA_MODELS_TTL_SECONDS = 30

def cache_get(key: str):
    hit = _CACHE.get(key)
    if not hit:
        return None
    exp, val = hit
    if time.time() > exp:
        _CACHE.pop(key, None)
        return None
    return val

def cache_set(key: str, val):
    _CACHE[key] = (time.time() + CACHE_TTL_SECONDS, val)

# ---------- REPLACE: gh_get to use cache (drop-in safe) ----------
async def gh_get(url: str):
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    ck = f"gh:{url}"
    cached = cache_get(ck)
    if cached is not None:
        class _Resp:
            status_code = 200
            headers = {}
            def json(self_nonlocal=cached):
                return cached
        return _Resp()

    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as c:
        r = await c.get(url, headers=headers)
        # If token is invalid/revoked, retry once without auth for public repos.
        if r.status_code == 401 and GITHUB_TOKEN:
            r = await c.get(url, headers={"Accept": "application/vnd.github.v3+json"})

    if r.status_code == 403 and r.headers.get("X-RateLimit-Remaining") == "0":
        return JSONResponse(
            {"reply": "GitHub rate limit reached. Try again in a few minutes."},
            status_code=429
        )
    r.raise_for_status()
    try:
        cache_set(ck, r.json())
    except Exception:
        pass
    return r

# ---- Helper: Fetch GitHub user ----
async def get_github_user(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        response.raise_for_status()
        return response.json()

# ---- Auth middleware (cookie reader) ----
def get_current_user(request: Request):
    cookie = request.cookies.get("session_id")
    if not cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        session_id = serializer.loads(cookie)["session_id"]
        session = sessions.get(session_id)
        if not session or session["expires"] < time.time():
            raise HTTPException(status_code=401, detail="Session expired")
        return session
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session")

# ---- Routes ----
@app.get("/")
async def root():
    return {"message": "Welcome to CodeScribeAI API"}

@app.get("/test")
async def test_endpoint():
    return {"message": "API is working"}

@app.get("/test-auth")
async def test_auth(user=Depends(get_current_user)):
    return {"message": f"Hello {user['user']}!"}

@app.get("/login/github")
async def github_login():
    ensure_github_oauth_config()
    state = os.urandom(16).hex()
    return RedirectResponse(
        f"https://github.com/login/oauth/authorize?"
        f"client_id={GITHUB_CLIENT_ID}&state={state}&scope=repo,user"
    )

@app.get("/auth/github/callback")
async def github_callback(code: str, state: Optional[str] = None):
    ensure_github_oauth_config()
    if not state:
        raise HTTPException(status_code=400, detail="Missing state parameter")

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            params={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "state": state,
            },
            headers={"Accept": "application/json"}
        )
        token_response.raise_for_status()
        token_data = token_response.json()

        user_data = await get_github_user(token_data["access_token"])

        session_id = str(uuid4())
        sessions[session_id] = {
            "access_token": token_data["access_token"],
            "user": user_data["login"],
            "user_id": user_data["id"],
            "expires": time.time() + 3600
        }
        save_sessions()

        signed_cookie = serializer.dumps({"session_id": session_id})
        response = RedirectResponse(url="http://localhost:5173")
        response.set_cookie(
            key="session_id",
            value=signed_cookie,
            httponly=True,
            samesite="Lax",
            secure=False,
        )
        return response

async def get_repo_default_branch(owner: str, repo: str) -> str:
    r = await gh_get(f"https://api.github.com/repos/{owner}/{repo}")
    if isinstance(r, JSONResponse):  # rate limited
        raise HTTPException(status_code=429, detail="Rate limited")
    return r.json()["default_branch"]

async def count_all_files(owner: str, repo: str) -> int:
    # Use Git Trees API to count all blobs (files) recursively
    default_branch = await get_repo_default_branch(owner, repo)
    r = await gh_get(f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1")
    if isinstance(r, JSONResponse):
        raise HTTPException(status_code=429, detail="Rate limited")
    data = r.json()
    tree = data.get("tree", [])
    return sum(1 for t in tree if t.get("type") == "blob")

async def fetch_root_contents(owner: str, repo: str):
    r = await gh_get(f"https://api.github.com/repos/{owner}/{repo}/contents")
    if isinstance(r, JSONResponse):
        raise HTTPException(status_code=429, detail="Rate limited")
    return r.json()

async def get_readme_text(owner: str, repo: str) -> str | None:
    # Try common README names in the root
    items = await fetch_root_contents(owner, repo)
    readme = next((f for f in items if f.get("type")=="file" and f["name"].lower().startswith("readme")), None)
    if not readme:
        return None
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as c:
        fr = await c.get(readme["download_url"])
        fr.raise_for_status()
        return fr.text[:4000]  # keep prompt small


# # Chat endpoint
# @app.post("/api/chat", response_model=ChatResponse)
# async def chat(req: ChatRequest):
#     msg = req.message.strip().lower()
#     if not msg:
#         return ChatResponse(reply="")

#     # 1) Local skills (no LLM)
#     if "name of" in msg or ("name" in msg and "repo" in msg):
#         return ChatResponse(reply=req.repo)

#     if "number of files" in msg or "count files" in msg or "how many files" in msg:
#         try:
#             total = await count_all_files(req.github_user, req.repo)
#             return ChatResponse(reply=f"{total} files in {req.github_user}/{req.repo}.", meta={"owner": req.github_user, "repo": req.repo})
#         except HTTPException as e:
#             if e.status_code == 429:
#                 return ChatResponse(reply="âš ï¸ GitHub rate limit reached. Please try again later.")
#             raise
#         except Exception as e:
#             return ChatResponse(reply=f"âš ï¸ Failed to count files: {e}")

#     # 2) â€œWhat is this repo about?â€ â†’ try README first, else LLM
#     if "what is this repo about" in msg or "explain this repo" in msg or "summary" in msg:
#         try:
#             readme = await get_readme_text(req.github_user, req.repo)
#         except HTTPException as e:
#             if e.status_code == 429:
#                 return ChatResponse(reply="âš ï¸ GitHub rate limit reached. Please try again later.")
#             return ChatResponse(reply=f"âš ï¸ GitHub error: {e.detail}")
#         except Exception as e:
#             readme = None

#         if readme:
#             # Ask LLM to summarize the README
#             prompt = f"Summarize this repository for a beginner in 5-7 lines:\n\n{readme}\n\nSummary:"
#         else:
#             # fallback: list root files and ask LLM to infer (less accurate)
#             try:
#                 items = await fetch_root_contents(req.github_user, req.repo)
#                 filelist = "\n".join(f"- {it['path']}" for it in items if it.get("type") == "file")[:3000]
#             except Exception:
#                 filelist = ""
#             prompt = f"Given these visible files, infer what the repository is about in 4-6 lines. If unsure, say so.\n\n{filelist}\n\nAnswer:"

#         try:
#             async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as c:
#                 ai_res = await c.post(f"{OLLAMA_URL}/api/generate",
#                                       json={"model": "phi3:mini", "prompt": prompt, "stream": False})
#                 ai_res.raise_for_status()
#                 ai = ai_res.json()
#                 return ChatResponse(reply=ai.get("response", "").strip() or "âš ï¸ AI returned empty response.")
#         except Exception as e:
#             return ChatResponse(reply=f"âš ï¸ Could not reach AI backend: {e}")
        
#     # 2b) â€œWhat is this repo about?â€ â†’ try README first, else LLM
#     if "what is this repo" in msg or "explain this repo" in msg or "summary" in msg:
#         try:
#             readme = await get_readme_text(req.github_user, req.repo)
#         except HTTPException as e:
#             if e.status_code == 429:
#                 return ChatResponse(reply="âš ï¸ GitHub rate limit reached. Please try again later.")
#             return ChatResponse(reply=f"âš ï¸ GitHub error: {e.detail}")
#         except Exception as e:
#             readme = None

#         if readme:
#             return ChatResponse(reply=readme)
        
#         # Detect programming languages used in repo
#     if "what programming languages" in msg or "languages used" in msg or "language breakdown" in msg:
#         try:
#             url = f"https://api.github.com/repos/{req.github_user}/{req.repo}/languages"
#             r = await gh_get(url)
#             if isinstance(r, JSONResponse):  # rate limited
#                 return ChatResponse(reply="âš ï¸ GitHub rate limit reached. Please try again later.")
            
#             data = r.json()
#             if not data:
#                 return ChatResponse(reply="No language data found for this repo.")
            
#             total = sum(data.values())
#             percentages = {lang: round((size / total) * 100, 2) for lang, size in data.items()}
#             breakdown = ", ".join([f"{lang} ({pct}%)" for lang, pct in percentages.items()])
            
#             return ChatResponse(
#                 reply=f"Programming languages used in {req.repo}: {breakdown}",
#                 meta={"languages": percentages}
#             )
#         except Exception as e:
#             return ChatResponse(reply=f"âš ï¸ Failed to fetch languages: {e}")


#     # 3) Generic fallback â†’ LLM with minimal context
#     prompt = f"Answer concisely:\n\nQ: {req.message}\nA:"
#     try:
#         async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as c:
#             ai_res = await c.post(f"{OLLAMA_URL}/api/generate",
#                                   json={"model": "phi3:mini", "prompt": prompt, "stream": False})
#             ai_res.raise_for_status()
#             ai = ai_res.json()
#             return ChatResponse(reply=ai.get("response", "").strip() or "âš ï¸ AI returned empty response.")
#     except Exception as e:
#         return ChatResponse(reply=f"âš ï¸ Could not reach AI backend: {e}")

# ---------- NEW: extra GitHub helpers ----------
async def get_repo_meta(owner: str, repo: str) -> dict:
    r = await gh_get(f"https://api.github.com/repos/{owner}/{repo}")
    if isinstance(r, JSONResponse):
        raise HTTPException(status_code=429, detail="Rate limited")
    return r.json()

async def get_contributors(owner: str, repo: str) -> list[dict]:
    r = await gh_get(f"https://api.github.com/repos/{owner}/{repo}/contributors")
    if isinstance(r, JSONResponse):
        raise HTTPException(status_code=429, detail="Rate limited")
    data = r.json()
    return data if isinstance(data, list) else []

async def get_languages(owner: str, repo: str) -> dict[str, int]:
    r = await gh_get(f"https://api.github.com/repos/{owner}/{repo}/languages")
    if isinstance(r, JSONResponse):
        raise HTTPException(status_code=429, detail="Rate limited")
    data = r.json()
    return data if isinstance(data, dict) else {}

# ---------- NEW: build context to ground the LLM ----------
async def build_repo_context(owner: str, repo: str, max_files: int = 12, include_readme: bool = False) -> dict:
    ck = f"{owner}/{repo}:readme={int(include_readme)}:files={max_files}"
    cached = _REPO_CONTEXT_CACHE.get(ck)
    if cached and time.time() < cached[0]:
        return cached[1]

    context: dict = {"owner": owner, "repo": repo, "files": [], "dirs": [], "languages": {}, "readme": ""}

    tasks = [
        fetch_root_contents(owner, repo),
        get_languages(owner, repo),
        get_repo_meta(owner, repo),
        get_contributors(owner, repo),
    ]
    if include_readme:
        tasks.append(get_readme_text(owner, repo))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    items, langs, meta, contr = results[0], results[1], results[2], results[3]
    readme = results[4] if include_readme and len(results) > 4 else None

    if not isinstance(items, Exception):
        files = [it["path"] for it in items if it.get("type") == "file"]
        dirs = [it["path"] for it in items if it.get("type") == "dir"]
        context["files"] = files[:max_files]
        context["dirs"] = dirs[:max_files]

    if not isinstance(langs, Exception):
        total = sum(langs.values()) or 1
        context["languages"] = {k: round(v * 100 / total, 2) for k, v in langs.items()}

    if not isinstance(meta, Exception):
        context["stars"] = meta.get("stargazers_count", 0)
        lic = meta.get("license") or {}
        context["license"] = lic.get("spdx_id") or lic.get("key") or ""
        context["description"] = meta.get("description") or ""
    else:
        context["stars"] = 0
        context["license"] = ""
        context["description"] = ""

    context["contributors_count"] = 0 if isinstance(contr, Exception) else len(contr)
    context["readme"] = "" if isinstance(readme, Exception) or not readme else str(readme)[:1000]

    _REPO_CONTEXT_CACHE[ck] = (time.time() + REPO_CONTEXT_TTL_SECONDS, context)
    return context

# ---------- NEW: smarter intent detection ----------
INTENT_PATTERNS = [
    ("summarize_file", r"\b(explain|summarize|describe|what does)\b.*\b(file|code)\b"),
    ("repo_structure", r"\b(file structure|folder structure|project structure|repo structure|directory structure|tree)\b"),
    ("list_files", r"\b(list|show|display|what are)\b.*\b(files|file list)\b|\bfiles in (this|the) repo\b"),
    ("get_languages", r"\b(language|languages|language breakdown)\b"),
    ("count_files", r"\b(how many|number of)\s+files\b|\bcount files\b"),
    ("get_stars", r"\b(stars?|stargazers?)\b"),
    ("get_repo_name", r"\b(name of\b|\bwhat.*name\b).*repo"),
    ("get_contributors", r"\b(contributor|contributors)\b"),
    ("summarize_repo", r"\b(summary|summarize|explain|describe|about)\b"),
]

def detect_intent(msg: str) -> str:
    text = msg.lower().strip()
    for intent, pat in INTENT_PATTERNS:
        if re.search(pat, text):
            return intent
    return "freeform"  # <â€” anything else goes to LLM (ChatGPT-like)

async def get_ollama_models() -> list[str]:
    global _OLLAMA_MODELS_CACHE
    if _OLLAMA_MODELS_CACHE and time.time() < _OLLAMA_MODELS_CACHE[0]:
        return _OLLAMA_MODELS_CACHE[1]

    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            res = await c.get(f"{OLLAMA_URL}/api/tags")
            res.raise_for_status()
            payload = res.json()
            models = [m.get("name", "") for m in payload.get("models", []) if m.get("name")]
            _OLLAMA_MODELS_CACHE = (time.time() + OLLAMA_MODELS_TTL_SECONDS, models)
            return models
    except Exception:
        return []

# ---------- NEW: robust LLM call with system-style instruction ----------
async def call_llm(prompt: str, requested_model: Optional[str] = None) -> str:
    installed = await get_ollama_models()

    # Priority: request model -> configured default -> configured fallbacks -> installed models
    candidates: list[str] = []
    for m in [requested_model, OLLAMA_MODEL, *OLLAMA_FALLBACK_MODELS, *installed]:
        if m and m not in candidates:
            candidates.append(m)
    if not candidates:
        candidates = [OLLAMA_MODEL]

    errors: list[str] = []
    for model_name in candidates:
        try:
            async with httpx.AsyncClient(timeout=90.0) as c:
                res = await c.post(
                    f"{OLLAMA_URL}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"num_predict": 220, "temperature": 0.2},
                    },
                )
            if res.status_code == 404:
                errors.append(f"{model_name}: not found")
                continue
            res.raise_for_status()
            answer = (res.json().get("response") or "").strip()
            if answer:
                return answer
            errors.append(f"{model_name}: empty response")
        except httpx.ReadTimeout:
            errors.append(f"{model_name}: timeout")
        except httpx.ConnectError:
            return f"Could not reach AI backend at {OLLAMA_URL}. Ensure Ollama is running."
        except Exception as e:
            errors.append(f"{model_name}: {repr(e)}")

    return "AI generation failed after model fallbacks: " + " | ".join(errors[:3])

def format_context_block(ctx: dict) -> str:
    lines = []
    if ctx.get("description"):
        lines.append(f"Repo description: {ctx['description']}")
    if ctx.get("license"):
        lines.append(f"License: {ctx['license']}")
    if "stars" in ctx:
        lines.append(f"Stars: {ctx['stars']}")
    if ctx.get("languages"):
        langs = ", ".join([f"{k} {v}%" for k, v in ctx["languages"].items()])
        lines.append(f"Languages: {langs}")
    if ctx.get("files"):
        lines.append("Top-level files:\n" + "\n".join(f"- {f}" for f in ctx["files"][:10]))
    if ctx.get("dirs"):
        lines.append("Top-level directories:\n" + "\n".join(f"- {d}" for d in ctx["dirs"][:10]))
    if ctx.get("readme"):
        lines.append("README excerpt:\n" + ctx["readme"][:600])
    return "\n\n".join(lines)


# ---------- REPLACE: the /api/chat endpoint with hybrid routing ----------
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    msg = (req.message or "").strip()
    if not msg:
        return ChatResponse(reply="")

    intent = detect_intent(msg)

    # 1) Structured intents â†’ GitHub API (deterministic answers)
    try:
        if intent == "summarize_file":
            if not req.file_content:
                return ChatResponse(reply="âš ï¸ To explain a file, please select one first.", meta={"grounded": False})

            # Large files (especially notebooks) can time out local models.
            max_chars = 12000
            file_body = req.file_content[:max_chars]
            truncated = len(req.file_content) > max_chars
            prompt = (
                "You are a helpful software assistant. "
                "Explain the code below clearly and concisely. "
                "Highlight its purpose, key functions, and overall structure.\n\n"
                f"File: `{req.file}`\n\n"
                f"Code:\n```\n{file_body}\n```\n\n"
                + ("Note: The file content was truncated for speed.\n\n" if truncated else "")
                + "Explanation:"
            )
            ans = await call_llm(prompt, req.model)
            return ChatResponse(reply=ans, sources=[req.file], meta={"grounded": True})

        if intent == "get_languages":
            langs = await get_languages(req.github_user, req.repo)
            if not langs:
                return ChatResponse(reply="No language data found.")
            total = sum(langs.values()) or 1
            pct = {k: round(v * 100 / total, 2) for k, v in langs.items()}
            breakdown = ", ".join(f"{k} ({v}%)" for k, v in pct.items())
            return ChatResponse(reply=f"Languages in {req.repo}: {breakdown}", meta={"languages": pct})

        if intent == "repo_structure":
            items = await fetch_root_contents(req.github_user, req.repo)
            files = [x["path"] for x in items if x.get("type") == "file"]
            dirs = [x["path"] for x in items if x.get("type") == "dir"]
            sample = (dirs[:12] + files[:12])[:20]
            if not sample:
                return ChatResponse(reply=f"I could not find visible root items for {req.github_user}/{req.repo}.")
            listing = "\n".join(f"- {p}" for p in sample)
            return ChatResponse(
                reply=(
                    f"Root structure for {req.github_user}/{req.repo}:\n"
                    f"- Directories: {len(dirs)}\n"
                    f"- Files: {len(files)}\n"
                    f"{listing}"
                ),
                meta={"dirs": len(dirs), "files": len(files), "grounded": True},
            )

        if intent == "list_files":
            items = await fetch_root_contents(req.github_user, req.repo)
            files = [x["path"] for x in items if x.get("type") == "file"]
            if not files:
                return ChatResponse(reply=f"No root-level files found in {req.github_user}/{req.repo}.", meta={"grounded": True})
            listing = "\n".join(f"- {p}" for p in files[:40])
            return ChatResponse(
                reply=f"Root files in {req.github_user}/{req.repo}:\n{listing}",
                meta={"files_returned": min(len(files), 40), "total_root_files": len(files), "grounded": True},
            )

        if intent == "count_files":
            # count **all** files via git trees API (more impressive than root only)
            try:
                total = await count_all_files(req.github_user, req.repo)
                return ChatResponse(reply=f"{req.repo} contains {total} files (all paths).")
            except Exception:
                # graceful fallback to root only
                files = await fetch_root_contents(req.github_user, req.repo)
                n = len([x for x in files if x.get('type') == 'file'])
                return ChatResponse(reply=f"{req.repo} has {n} files in the root directory (full count unavailable).")

        if intent == "get_stars":
            meta = await get_repo_meta(req.github_user, req.repo)
            stars = meta.get("stargazers_count", 0)
            return ChatResponse(reply=f"{req.repo} has â­ {stars} stars.", meta={"stars": stars})

        if intent == "get_repo_name":
            return ChatResponse(reply=f"The name of this repository is **{req.repo}**.")

        if intent == "get_contributors":
            contr = await get_contributors(req.github_user, req.repo)
            return ChatResponse(reply=f"{req.repo} has {len(contr)} contributors.", meta={"contributors": len(contr)})

    except HTTPException as e:
        if e.status_code == 429:
            return ChatResponse(reply="âš ï¸ GitHub rate limit reached. Please try again later.")
        return ChatResponse(reply=f"âš ï¸ GitHub error: {e.detail}")
    except Exception as e:
        # Donâ€™t block â€” weâ€™ll still try LLM with context
        pass

    # 2) Repo-related open questions â†’ LLM grounded with context
    if intent == "summarize_repo":
        ctx = await build_repo_context(req.github_user, req.repo, include_readme=True)
        ctx_block = format_context_block(ctx)
        prompt = (
            "You are a helpful software assistant. Use the provided repository context when relevant. "
            "If the context is weak or missing details, say what youâ€™re unsure about.\n\n"
            f"User question:\n{msg}\n\n"
            f"Repository context:\n{ctx_block}\n\n"
            "Answer clearly and concisely."
        )
        ans = await call_llm(prompt, req.model)
        return ChatResponse(reply=ans, sources=[], meta={"grounded": True})

    # 3) Anything else (general world questions, arbitrary chat) â†’ ChatGPT-like
    #    Still include repo context in case it helps, but donâ€™t force it.
    ctx = await build_repo_context(req.github_user, req.repo, include_readme=False)
    repo_signal = re.search(r"\b(repo|repository|project|file|folder|directory|codebase|this repo)\b", msg.lower())
    if repo_signal and not (ctx.get("files") or ctx.get("dirs") or ctx.get("readme")):
        return ChatResponse(
            reply=f"I couldn't fetch repository context for {req.github_user}/{req.repo} right now, so I can't give a grounded answer yet.",
            meta={"grounded": False},
        )
    ctx_block = format_context_block(ctx)
    prompt = (
        "You are a helpful assistant. If the question is about the repository, you MUST use the repository context below. "
        "Do not give generic textbook answers when repository context exists. Mention concrete files/directories from context. "
        "If the context is insufficient, say exactly what is missing.\n\n"
        f"User question:\n{msg}\n\n"
        f"Repository context (optional):\n{ctx_block}\n\n"
        "Answer:"
    )
    ans = await call_llm(prompt, req.model)
    return ChatResponse(reply=ans, sources=[], meta={"grounded": False})

@app.get("/health")
async def health():
    probs = []
    # Check GitHub
    try:
        r = await gh_get("https://api.github.com/rate_limit")
        if isinstance(r, JSONResponse):
            probs.append("github: rate limited")
    except Exception as e:
        probs.append(f"github: {e}")
    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as c:
            r = await c.get(f"{OLLAMA_URL}/api/tags")
            r.raise_for_status()
    except Exception as e:
        probs.append(f"ollama: {e}")
    return {"ok": len(probs)==0, "problems": probs}

@app.get("/api/ai-status")
async def ai_status():
    models = await get_ollama_models()
    return {
        "ollama_url": OLLAMA_URL,
        "default_model": OLLAMA_MODEL,
        "fallback_models": OLLAMA_FALLBACK_MODELS,
        "available_models": models,
        "ok": len(models) > 0,
    }

    
@app.get("/me")
async def get_me(user=Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {user['access_token']}"}
        )
        r.raise_for_status()
        return r.json()

@app.get("/repos/{username}")
async def get_github_repos(username: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{GITHUB_API_URL}/{username}/repos")
        
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="User not found")
        elif response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Error fetching repositories")
        
        return response.json()  # âœ… send everything back

    
@app.get("/repos/{owner}/{repo}/languages")
async def get_repo_languages(owner: str, repo: str):
    url = f"https://api.github.com/repos/{owner}/{repo}/languages"
    try:
        r = await gh_get(url)
        if isinstance(r, JSONResponse):  # rate limited
            raise HTTPException(status_code=429, detail="Rate limited")
        data = r.json()
        total = sum(data.values())
        if total == 0:
            return {"languages": {}, "percentages": {}}
        percentages = {lang: round((size / total) * 100, 2) for lang, size in data.items()}
        return {"languages": data, "percentages": percentages}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch languages: {e}")
    
@app.get("/repos/{owner}/{repo}/files")
async def get_repo_files(owner: str, repo: str, path: str = "", recursive: bool = False):
    """
    Fetch the file/directory structure of a repository.
    By default, lists the root. You can pass ?path=subdir to drill deeper.
    """
    if recursive:
        try:
            default_branch = await get_repo_default_branch(owner, repo)
            r = await gh_get(f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1")
            if isinstance(r, JSONResponse):
                raise HTTPException(status_code=429, detail="GitHub rate limit reached")
            payload = r.json()
            tree = payload.get("tree", [])

            base = (path or "").strip("/")
            normalized = []
            for item in tree:
                item_path = (item.get("path") or "").strip("/")
                if not item_path:
                    continue
                if base and not (item_path == base or item_path.startswith(base + "/")):
                    continue
                out_path = item_path[len(base) + 1:] if base and item_path.startswith(base + "/") else item_path
                if not out_path:
                    continue
                if item.get("type") == "tree":
                    out_type = "dir"
                elif item.get("type") == "blob":
                    out_type = "file"
                else:
                    continue
                normalized.append(
                    {
                        "type": out_type,
                        "path": out_path,
                        "size": item.get("size"),
                        "download_url": None,
                    }
                )
            return normalized
        except HTTPException:
            raise
        except Exception:
            # Graceful fallback to root listing if recursive tree API fails.
            pass

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            r = await client.get(url, headers=headers)
            # Retry unauthenticated when token is bad.
            if r.status_code == 401 and GITHUB_TOKEN:
                r = await client.get(url, headers={"Accept": "application/vnd.github.v3+json"})

        if r.status_code == 403 and r.headers.get("X-RateLimit-Remaining") == "0":
            raise HTTPException(status_code=429, detail="GitHub rate limit reached")
        if r.status_code == 409:
            # Empty repository on GitHub
            return []
        if r.status_code == 404:
            raise HTTPException(status_code=404, detail="Repository or path not found")
        if r.status_code >= 400:
            detail = ""
            try:
                detail = r.json().get("message", "")
            except Exception:
                detail = r.text
            raise HTTPException(status_code=r.status_code, detail=detail or "Failed to fetch repository files")

        data = r.json()
        tree = [
            {
                "type": item.get("type"),
                "path": item.get("path"),
                "size": item.get("size"),
                "download_url": item.get("download_url"),
            }
            for item in (data if isinstance(data, list) else [data])
        ]
        return tree
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch repo files: {e}")



@app.post("/logout")
async def logout(request: Request, user=Depends(get_current_user)):
    session_id = None
    try:
        cookie = request.cookies.get("session_id")
        if cookie:
            session_id = serializer.loads(cookie)["session_id"]
    except Exception:
        pass

    # Remove from sessions.json if exists
    if session_id and session_id in sessions:
        sessions.pop(session_id, None)
        save_sessions()

    # Clear cookie
    response = JSONResponse({"message": "Logged out"})
    response.delete_cookie("session_id")
    return response

@app.get("/repos/{owner}/{repo}/file-content")
async def get_file_content(owner: str, repo: str, path: str):
    """Fetches the raw content of a specific file from a GitHub repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {"Accept": "application/vnd.github.v3.raw"}
    
    # Add your GitHub token for authentication and higher rate limits
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0)) as client:
            res = await client.get(url, headers=headers)
            # Retry without auth if token is invalid/revoked; works for public repos.
            if res.status_code == 401 and GITHUB_TOKEN:
                res = await client.get(url, headers={"Accept": "application/vnd.github.v3.raw"})

        if res.status_code == 404:
            raise HTTPException(status_code=404, detail="File not found in repository.")
        if res.status_code == 409:
            raise HTTPException(status_code=409, detail="Repository is empty.")
        if res.status_code >= 400:
            detail = ""
            try:
                detail = res.json().get("message", "")
            except Exception:
                detail = res.text
            raise HTTPException(status_code=res.status_code, detail=detail or "Failed to fetch file content.")

        return Response(content=res.text, media_type="text/plain")
    except httpx.HTTPStatusError as e:
        print(f"Error fetching file content: {e}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail="File not found or access denied."
        )
    except httpx.RequestError as e:
        # Handle other httpx request errors (e.g., network issues)
        print(f"Error fetching file content: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to connect to GitHub API."
        )
    
# --- Asynchronous Chat Endpoint (for long-running tasks) ---
# It receives a user's message and offloads it to a Celery worker.
class ChatQuery(BaseModel):
    message: str
    repo: str
    github_user: str
    file: Optional[str] = None
    file_content: Optional[str] = None
    model: Optional[str] = None

@app.post("/api/chat-async", status_code=status.HTTP_202_ACCEPTED)
async def chat_async(query: ChatQuery):
    # This is the endpoint that the frontend calls
    print(f"Received query: '{query.message}' for repo: {query.repo}")

    try:
        task = process_chat_query.delay(query.message, query.repo, query.github_user, query.file, query.file_content)
        return {"task_id": task.id}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Async worker unavailable: {e}")

# --- Celery Configuration ---
# Celery instance that will be used to run tasks
celery_app = Celery(
    "tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
)

# --- Celery Task Definition ---
# This is the function that the Celery worker will run in the background.
@celery_app.task(name="process_chat_query")
def process_chat_query(message, repo, github_user, file, file_content):
    """
    Simulates a long-running RAG process.
    """
    print(f"Starting to process query: '{message}' in the background...")
    # Simulate a long-running task, like a RAG process
    time.sleep(30)
    print("Finished processing.")

    # In a real implementation, you would:
    # 1. Use the RAG pipeline to get a response and source docs.
    # 2. Return the result.
    
    # Mocking a response for now
    reply = f"Thank you for asking about `{message}`. I've processed your query for the repository `{repo}`. The answer will be available soon."
    
    # Simulate source docs
    sources = [{"file_path": file, "line_numbers": "1-10"}] if file else []
    
    return {"reply": reply, "sources": sources}

# --- Polling Endpoint ---
# This endpoint allows the frontend to check on the status of a Celery task.
@app.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    task_result = celery_app.AsyncResult(task_id)
    if task_result.state == "PENDING":
        return {"status": "PENDING"}
    elif task_result.state == "FAILURE":
        return {"status": "FAILURE", "error": str(task_result.info)}
    elif task_result.state == "SUCCESS":
        return {"status": "SUCCESS", "result": task_result.result}
    else:
        return {"status": task_result.state}

# --- Git Integration (OAuth and Repositories) ---
# The blueprint mentions using python-gitlab for GitLab integration[cite: 63, 64].
# A similar library, PyGithub, is recommended for GitHub integration[cite: 87].
# Your backend should have endpoints to handle the OAuth2 flow[cite: 69].

# --- Production Deployment ---
# To run this code in production, you would need to:
# 1. Containerize the application and Celery worker using Docker[cite: 347, 348, 349].
# 2. Deploy it to a platform like Google Kubernetes Engine (GKE)[cite: 373, 374, 375].
# 3. Use managed services like Vertex AI Vector Search for your database and Vertex AI Endpoints for LLM serving[cite: 417, 422].




