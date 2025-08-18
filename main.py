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

# Load environment variables first
load_dotenv()

app = FastAPI()

# ---- Session persistence ----
SESSIONS_FILE = "sessions.json"

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
    allow_origins=["http://localhost:3000"],  # frontend
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
async def github_callback(code: str, state: Optional[str] = None, response: Response = None):
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
        response = RedirectResponse(url="http://localhost:3000")  # frontend landing page
        response.set_cookie(
            key="session_id",
            value=signed_cookie,
            httponly=True,
            samesite="Lax"
        )
        return response

@app.post("/logout")
async def logout(response: Response):
    response.delete_cookie("session_id")
    return {"message": "Logged out"}
