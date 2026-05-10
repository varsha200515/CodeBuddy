import { useState } from "react";
import axios from "axios";
import { toast, Toaster } from "sonner";

// ✅ SIMPLE API (no import.meta issues)
const API = "http://127.0.0.1:8000/api";

export default function App() {
  const [activeTab, setActiveTab] = useState("code");
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("javascript");
  const [repoUrl, setRepoUrl] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);

  // ✅ CLEAN ERROR HANDLER
  const handleError = (err) => {
    const msg =
      err.response?.data?.detail ||
      err.message ||
      "Something went wrong";

    console.error(msg);
    toast.error(msg);
  };

  // ✅ CODE ANALYSIS
  const analyzeCode = async () => {
    if (!code.trim()) {
      toast.error("Enter code first");
      return;
    }

    setLoading(true);
    try {
      const res = await axios.post(`${API}/review/code`, {
        code,
        language,
      });

      setResults({ ...res.data, type: "code" });
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  };

  // ✅ GITHUB ANALYSIS
  const analyzeRepo = async () => {
    if (!repoUrl.trim()) {
      toast.error("Enter repo URL");
      return;
    }

    setLoading(true);
    try {
      const res = await axios.post(`${API}/review/github`, {
        repo_url: repoUrl,
        github_token: githubToken || null,
      });

      setResults({ ...res.data, type: "github" });
    } catch (err) {
      handleError(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 20 }}>
      <Toaster />

      <h1>🔥 AI Code Reviewer</h1>

      {/* 🔁 TAB SWITCH */}
      <div style={{ marginBottom: 20 }}>
        <button onClick={() => setActiveTab("code")}>Code</button>
        <button onClick={() => setActiveTab("github")}>GitHub</button>
      </div>

      {/* 💻 CODE TAB */}
      {activeTab === "code" && (
        <>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
          >
            <option value="javascript">JavaScript</option>
            <option value="python">Python</option>
          </select>

          <textarea
            placeholder="Paste code..."
            value={code}
            onChange={(e) => setCode(e.target.value)}
            style={{ width: "100%", height: 200, marginTop: 10 }}
          />

          <button
            onClick={analyzeCode}
            disabled={loading}
            style={{ marginTop: 10 }}
          >
            {loading ? "Analyzing..." : "Analyze Code"}
          </button>
        </>
      )}

      {/* 🔗 GITHUB TAB */}
      {activeTab === "github" && (
        <>
          <input
            placeholder="GitHub repo URL"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            style={{ display: "block", marginBottom: 10 }}
          />

          <input
            placeholder="GitHub Token (optional)"
            value={githubToken}
            onChange={(e) => setGithubToken(e.target.value)}
            style={{ display: "block", marginBottom: 10 }}
          />

          <button onClick={analyzeRepo} disabled={loading}>
            {loading ? "Analyzing..." : "Analyze Repo"}
          </button>
        </>
      )}

      {/* 📤 OUTPUT */}
      {results && (
        <pre
          style={{
            marginTop: 20,
            whiteSpace: "pre-wrap",
            background: "#111",
            padding: 10,
            borderRadius: 8,
          }}
        >
          {JSON.stringify(results, null, 2)}
        </pre>
      )}
    </div>
  );
}
