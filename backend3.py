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

        branches = ["main", "master"]
        tree_data = None

        # 🔥 GET REPO TREE (RECURSIVE)
        for branch in branches:
            url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
            res = requests.get(url, headers=headers)

            if res.status_code == 200:
                tree_data = res.json()
                break

        if not tree_data:
            raise HTTPException(400, "Repo not accessible")

        tree_items = tree_data.get("tree")
        if not tree_items:
            raise HTTPException(400, "Invalid repo structure")

        code_files = []
        file_count = 0
        max_files = 8   # 🔥 limit for speed

        skip_dirs = [
            "node_modules", "dist", "build",
            ".git", "__pycache__", "venv"
        ]

        # 🔥 LOOP ALL FILES (NO EXTENSION FILTER ❗)
        for item in tree_items:
            if file_count >= max_files:
                break

            if item["type"] != "blob":
                continue

            path = item["path"].lower()

            # ✅ SKIP USELESS DIRS
            if any(skip in path for skip in skip_dirs):
                continue

            file_content = None

            # 🔁 TRY BOTH BRANCHES
            for branch in branches:
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{item['path']}"
                r = requests.get(raw_url)

                if r.status_code == 200 and r.text.strip():
                    file_content = r.text[:2000]
                    break

            if file_content:
                code_files.append(f"FILE: {item['path']}\n{file_content}")
                file_count += 1

        # 🔥 FALLBACK IF STILL EMPTY
        if not code_files:
            code_files.append("Repository structure found but no readable code files detected.")

        combined_code = "\n\n".join(code_files)

        # 🔥 STRICT PROMPT (VERY IMPORTANT)
        model = genai.GenerativeModel("models/gemini-2.0-flash")

        prompt = f"""
You are a strict code reviewer.

Analyze this repository:

{combined_code}

Return ONLY valid JSON in this format:

{{
  "issues": ["..."],
  "improvements": ["..."],
  "fixed_code": "...",
  "explanation": "..."
}}

Do NOT add any extra text.
"""

        res = model.generate_content(prompt)

        print("AI RAW:", res.text)  # 🔥 DEBUG

        # 🔥 SAFE JSON PARSER
        match = re.search(r'\{[\s\S]*\}', res.text)
        if not match:
            raise HTTPException(500, "AI returned invalid JSON")

        return json.loads(match.group())

    except Exception as e:
        raise HTTPException(500, str(e))
