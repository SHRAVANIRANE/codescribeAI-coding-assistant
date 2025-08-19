import time
import json
import os
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


# Load environment variables first
load_dotenv()

# ---- Environment variables ----
# Ensure GITHUB_TOKEN is set in your .env file
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# ---- Ollama API URL ----
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

app = FastAPI()

# ---- Session persistence ----
SESSIONS_FILE = "sessions.json"

# ---- GitHub API URL ----
GITHUB_API_URL = "https://api.github.com/users"

class ChatRequest(BaseModel):
    message: str
    repo: str
    github_user: str

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
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret")
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
    state = os.urandom(16).hex()
    return RedirectResponse(
        f"https://github.com/login/oauth/authorize?"
        f"client_id={GITHUB_CLIENT_ID}&state={state}&scope=repo,user"
    )

@app.get("/auth/github/callback")
async def github_callback(code: str, state: Optional[str] = None):
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

        # Create session
        session_id = str(uuid4())
        sessions[session_id] = {
            "access_token": token_data["access_token"],
            "user": user_data["login"],
            "user_id": user_data["id"],
            "expires": time.time() + 3600
        }
        save_sessions()

        # Store signed cookie
        signed_cookie = serializer.dumps({"session_id": session_id})
        response = RedirectResponse(url="http://localhost:5173")  # frontend landing page
        response.set_cookie(
            key="session_id",
            value=signed_cookie,
            httponly=True,
            samesite="Lax",       # helps avoid CSRF issues
            secure=False,         # True if using https
        
        )
        return response
    
async def gh_get(url: str):
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as c:
        r = await c.get(url, headers=headers)
    # rate limit detection
    if r.status_code == 403 and r.headers.get("X-RateLimit-Remaining") == "0":
        reset = r.headers.get("X-RateLimit-Reset")
        return JSONResponse(
            {"reply": "⚠️ GitHub rate limit reached. Try again in a few minutes."},
            status_code=429
        )
    r.raise_for_status()
    return r

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


# Chat endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    msg = req.message.strip().lower()
    if not msg:
        return ChatResponse(reply="")

    # 1) Local skills (no LLM)
    if "name of" in msg or ("name" in msg and "repo" in msg):
        return ChatResponse(reply=req.repo)

    if "number of files" in msg or "count files" in msg or "how many files" in msg:
        try:
            total = await count_all_files(req.github_user, req.repo)
            return ChatResponse(reply=f"{total} files in {req.github_user}/{req.repo}.", meta={"owner": req.github_user, "repo": req.repo})
        except HTTPException as e:
            if e.status_code == 429:
                return ChatResponse(reply="⚠️ GitHub rate limit reached. Please try again later.")
            raise
        except Exception as e:
            return ChatResponse(reply=f"⚠️ Failed to count files: {e}")

    # 2) “What is this repo about?” → try README first, else LLM
    if "what is this repo about" in msg or "explain this repo" in msg or "summary" in msg:
        try:
            readme = await get_readme_text(req.github_user, req.repo)
        except HTTPException as e:
            if e.status_code == 429:
                return ChatResponse(reply="⚠️ GitHub rate limit reached. Please try again later.")
            return ChatResponse(reply=f"⚠️ GitHub error: {e.detail}")
        except Exception as e:
            readme = None

        if readme:
            # Ask LLM to summarize the README
            prompt = f"Summarize this repository for a beginner in 5-7 lines:\n\n{readme}\n\nSummary:"
        else:
            # fallback: list root files and ask LLM to infer (less accurate)
            try:
                items = await fetch_root_contents(req.github_user, req.repo)
                filelist = "\n".join(f"- {it['path']}" for it in items if it.get("type") == "file")[:3000]
            except Exception:
                filelist = ""
            prompt = f"Given these visible files, infer what the repository is about in 4-6 lines. If unsure, say so.\n\n{filelist}\n\nAnswer:"

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as c:
                ai_res = await c.post(f"{OLLAMA_URL}/api/generate",
                                      json={"model": "phi3:mini", "prompt": prompt, "stream": False})
                ai_res.raise_for_status()
                ai = ai_res.json()
                return ChatResponse(reply=ai.get("response", "").strip() or "⚠️ AI returned empty response.")
        except Exception as e:
            return ChatResponse(reply=f"⚠️ Could not reach AI backend: {e}")

    # 3) Generic fallback → LLM with minimal context
    prompt = f"Answer concisely:\n\nQ: {req.message}\nA:"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as c:
            ai_res = await c.post(f"{OLLAMA_URL}/api/generate",
                                  json={"model": "phi3:mini", "prompt": prompt, "stream": False})
            ai_res.raise_for_status()
            ai = ai_res.json()
            return ChatResponse(reply=ai.get("response", "").strip() or "⚠️ AI returned empty response.")
    except Exception as e:
        return ChatResponse(reply=f"⚠️ Could not reach AI backend: {e}")

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
        
        repos = response.json()
        return [{"name": repo["name"], "url": repo["html_url"]} for repo in repos]

@app.post("/logout")
async def logout(response: Response):
    response.delete_cookie("session_id")
    return {"message": "Logged out"}

import requests
url = "https://api.github.com/repos/SHRAVANIRANE/codescribeAI-coding-assistant/contents"
res = requests.get(url)
print(res.status_code)
print(res.json()[:2])  # show first 2 files
