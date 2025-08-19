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

# Load environment variables first
load_dotenv()

app = FastAPI()

# ---- Session persistence ----
SESSIONS_FILE = "sessions.json"

# ---- GitHub API URL ----
GITHUB_API_URL = "https://api.github.com/users"


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
    
# Chat endpoint
@app.post("/api/chat")
async def chat(request: Request):
    data = await request.json()
    message = data.get("message", "")
    repo = data.get("repo")
    github_user = data.get("github_user")  # optional if you want to fetch private repos later

    if not message.strip():
        return JSONResponse({"reply": ""})

    if not repo:
        return JSONResponse({"reply": "⚠️ Please select a repo first."}, status_code=400)

    # Step 1: Fetch repo contents
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"https://api.github.com/repos/{github_user}/{repo}/contents")
            if res.status_code != 200:
                raise HTTPException(status_code=res.status_code, detail="Error fetching repo files")
            files = res.json()

            # Step 2: Get code of main files (for MVP, limit to .py)
            code_combined = ""
            for file in files:
                if file["type"] == "file" and file["name"].endswith(".py"):
                    file_res = await client.get(file["download_url"])
                    file_res.raise_for_status()
                    code_combined += f"# File: {file['name']}\n{file_res.text}\n\n"

            if not code_combined:
                code_combined = "# No Python files found in repo."

            # Step 3: Build prompt for AI
            prompt = f"Repository: {repo}\n\nCode:\n{code_combined}\n\nQuestion: {message}"

            # Step 4: Send prompt to AI backend
            ai_res = await client.post(
                "http://localhost:11434/api/generate",  # your local AI backend
                json={"model": "phi3:mini", "prompt": prompt, "stream": False},
                timeout=30.0
            )
            ai_res.raise_for_status()
            ai_data = ai_res.json()
            reply = ai_data.get("response", "⚠️ AI could not generate a response.")

            return JSONResponse({"reply": reply})

    except httpx.RequestError as e:
        print("RequestError:", e)
        return JSONResponse({"reply": "⚠️ Could not reach GitHub or AI backend."}, status_code=500)
    except httpx.HTTPStatusError as e:
        print("HTTPStatusError:", e)
        return JSONResponse({"reply": f"⚠️ Backend returned {e.response.status_code}"}, status_code=500)
    except Exception as e:
        print("Unexpected Error:", e)
        return JSONResponse({"reply": "⚠️ Something went wrong."}, status_code=500)

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
