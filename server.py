from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import os, requests, re, json
from dotenv import load_dotenv

# 🔑 LOAD ENV
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

app = FastAPI()

# 🌐 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= MODELS =================
class CodeRequest(BaseModel):
    code: str
    language: str

class RepoRequest(BaseModel):
    repo_url: str

# ================= JSON PARSER =================
def extract_json(text):
    match = re.search(r'\{[\s\S]*\}', text)
    if not match:
        raise HTTPException(500, "AI returned invalid JSON")
    return json.loads(match.group())

# ================= CODE REVIEW =================
@app.post("/api/review/code")
async def review_code(req: CodeRequest):
    try:
        model = genai.GenerativeModel("gemini-flash-lite-latest")

        prompt = f"""
Analyze this {req.language} code and return JSON:
{req.code}

Return:
issues, improvements, fixed_code, explanation, score
"""

        res = model.generate_content(prompt)
        return extract_json(res.text)

    except Exception as e:
        raise HTTPException(500, str(e))

# ================= GITHUB REVIEW (FIXED) =================
@app.post("/api/review/github")
async def review_repo(req: RepoRequest):
    try:
        # ✅ CLEAN URL
        repo_url = req.repo_url.strip().replace(".git", "").rstrip("/")

        parts = repo_url.split("github.com/")[-1].split("/")
        if len(parts) < 2:
            raise HTTPException(400, "Invalid GitHub URL")

        owner, repo = parts[0], parts[1]

        headers = {
            "Accept": "application/vnd.github+json"
        }

        # ✅ TRY BOTH BRANCHES
        branches = ["main", "master"]
        tree_data = None

        for branch in branches:
            url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
            res = requests.get(url, headers=headers)

            if res.status_code == 200:
                tree_data = res.json()
                break

        if not tree_data:
            raise HTTPException(400, "Repo not accessible")

        files = []
        count = 0

        # ✅ LOOP FILES PROPERLY
        for item in tree_data.get("tree", []):
            if count >= 5:
                break

            if item["type"] == "blob" and item["path"].endswith(
                (".py", ".js", ".ts", ".java", ".cpp", ".c", ".cs", ".rb")
            ):

                file_content = None

                # ✅ TRY RAW FILE FROM BOTH BRANCHES
                for branch in branches:
                    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{item['path']}"
                    r = requests.get(raw_url)

                    if r.status_code == 200:
                        file_content = r.text[:1000]
                        break

                if file_content:
                    files.append(file_content)
                    count += 1

        # ✅ HANDLE EMPTY
        if not files:
            raise HTTPException(400, "No code files found")

        combined = "\n\n".join(files)

        # ✅ SAME MODEL
        model = genai.GenerativeModel("gemini-flash-lite-latest")

        prompt = f"""
Analyze this repository code and return JSON:
{combined}

Return:
issues, improvements, fixed_code, explanation, score
"""

        res = model.generate_content(prompt)
        return extract_json(res.text)

    except Exception as e:
        raise HTTPException(500, str(e))
