from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import requests
import re
import json
import google.generativeai as genai

# load env
load_dotenv()

# configure gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

app = FastAPI()
api_router = APIRouter(prefix="/api")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= MODELS =================

class CodeReviewRequest(BaseModel):
    code: str
    language: str

class GitHubReviewRequest(BaseModel):
    repo_url: str
    github_token: Optional[str] = None

class CodeReviewResponse(BaseModel):
    issues: List[Dict[str, Any]]
    security_risks: List[Dict[str, Any]]
    code_smells: List[Dict[str, Any]]
    improvements: List[str]
    improved_code: str
    beginner_explanation: str
    quality_score: int

class GitHubReviewResponse(BaseModel):
    issues: List[Dict[str, Any]]
    security_risks: List[Dict[str, Any]]
    code_smells: List[Dict[str, Any]]
    improvements: List[str]
    improved_code: str
    beginner_explanation: str
    quality_score: int
    files_analyzed: List[str]
    repo_summary: str

# ================= ROUTES =================

@api_router.get("/")
async def root():
    return {"message": "API running"}

# 🔥 SAFE JSON PARSER
def extract_json(ai_text):
    try:
        match = re.search(r'\{[\s\S]*\}', ai_text)
        if match:
            return json.loads(match.group())
        else:
            raise ValueError("No JSON found")
    except Exception:
        print("RAW AI RESPONSE:\n", ai_text)
        raise HTTPException(status_code=500, detail="AI response parsing failed")

# 🔥 CODE REVIEW
@api_router.post("/review/code", response_model=CodeReviewResponse)
async def review_code(request: CodeReviewRequest):
    try:
        # ✅ FIXED MODEL
        model = genai.GenerativeModel("gemini-flash-lite-latest")

        prompt = f"""
Analyze this {request.language} code and return ONLY JSON.

Code:
{request.code}

Return JSON with:
issues, security_risks, code_smells, improvements, improved_code, beginner_explanation, quality_score
"""

        response = model.generate_content(prompt)
        result = extract_json(response.text)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🔥 GITHUB REVIEW
@api_router.post("/review/github", response_model=GitHubReviewResponse)
async def review_github(request: GitHubReviewRequest):
    try:
        # ✅ VALIDATE URL
        repo_parts = request.repo_url.replace('https://github.com/', '').split('/')
        if len(repo_parts) < 2:
            raise HTTPException(status_code=400, detail="Invalid GitHub URL")

        owner, repo = repo_parts[0], repo_parts[1]

        headers = {}
        if request.github_token:
            headers['Authorization'] = f'token {request.github_token}'

        # 🔥 FETCH TREE
        tree_url = f'https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1'
        tree_response = requests.get(tree_url, headers=headers)

        if tree_response.status_code != 200:
            tree_url = f'https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1'
            tree_response = requests.get(tree_url, headers=headers)

        if tree_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch repo")

        tree_data = tree_response.json()

        code_files = []
        files_analyzed = []

        extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c']

        count = 0
        max_files = 10

        # 🔥 LOOP FILES
        for item in tree_data.get('tree', []):
            if count >= max_files:
                break

            if item['type'] == 'blob' and any(item['path'].endswith(ext) for ext in extensions):

                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{item['path']}"
                res = requests.get(raw_url)

                if res.status_code != 200:
                    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/{item['path']}"
                    res = requests.get(raw_url)

                if res.status_code == 200:
                    code_files.append(f"# {item['path']}\n{res.text[:1500]}")
                    files_analyzed.append(item['path'])
                    count += 1

        # ✅ EMPTY CHECK
        if not code_files:
            raise HTTPException(status_code=400, detail="No code files found in repo")

        combined = "\n\n".join(code_files)

        # ✅ FIXED MODEL
        model = genai.GenerativeModel("gemini-flash-lite-latest")

        prompt = f"""
Analyze this GitHub repo code and return ONLY JSON.

{combined}

Return JSON with:
issues, security_risks, code_smells, improvements, improved_code, beginner_explanation, quality_score, repo_summary
"""

        response = model.generate_content(prompt)
        result = extract_json(response.text)

        result["files_analyzed"] = files_analyzed

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# include router
app.include_router(api_router)
