# 🔥 FETCH TREE (main → fallback to master)
tree_url = f'https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1'
tree_response = requests.get(tree_url, headers=headers, timeout=15)

if tree_response.status_code != 200:
    tree_url = f'https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1'
    tree_response = requests.get(tree_url, headers=headers, timeout=15)

if tree_response.status_code != 200:
    raise HTTPException(status_code=400, detail="Failed to fetch repository tree")

tree_data = tree_response.json()

# 🔥 INIT
code_files = []
files_analyzed = []

important_extensions = [
    '.py', '.js', '.ts', '.jsx', '.tsx',
    '.java', '.cpp', '.c', '.go', '.rs'
]

skip_dirs = [
    'node_modules', 'dist', 'build',
    '.git', 'vendor', '__pycache__'
]

file_count = 0
max_files = 10

# 🔥 SAFETY CHECK
tree_items = tree_data.get('tree')
if not tree_items:
    raise HTTPException(status_code=400, detail="Invalid repo structure")

# 🔥 LOOP FILES
for item in tree_items:
    if file_count >= max_files:
        break

    if item['type'] == 'blob' and any(item['path'].endswith(ext) for ext in important_extensions):

        # ✅ FIXED skip logic
        if any(skip_dir in item['path'] for skip_dir in skip_dirs):
            continue

        # 🔥 TRY MAIN BRANCH
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{item['path']}"
        file_response = requests.get(raw_url, headers=headers, timeout=10)

        # 🔁 FALLBACK TO MASTER
        if file_response.status_code != 200:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/{item['path']}"
            file_response = requests.get(raw_url, headers=headers, timeout=10)

        # ✅ SUCCESS
        if file_response.status_code == 200:
            code_files.append({
                'name': item['path'],
                'content': file_response.text[:3000]  # limit size
            })
            files_analyzed.append(item['path'])
            file_count += 1

# 🔥 FINAL CHECK
if not code_files:
    raise HTTPException(status_code=400, detail="No code files found in repository")
