import { useState } from "react";

export default function ChatBox() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const [githubUser, setGithubUser] = useState("");
  const [repos, setRepos] = useState([]);
  const [repoLoading, setRepoLoading] = useState(false);
  const [repoError, setRepoError] = useState("");
  const [selectedRepo, setSelectedRepo] = useState(null);

  // Chat send handler
  const handleSend = async () => {
    if (!input.trim()) return;
    const newMsg = { role: "user", text: input };
    setMessages((prev) => [...prev, newMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: input,
          repo: selectedRepo?.name,
          github_user: githubUser,
        }),
        credentials: "include",
      });

      if (!res.ok) throw new Error("Backend error");

      const data = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", text: data.reply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "⚠️ Could not reach AI backend." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Fetch GitHub repos
  const fetchRepos = async () => {
    if (!githubUser.trim()) return;
    setRepoLoading(true);
    setRepoError("");
    try {
      const res = await fetch(`http://127.0.0.1:8000/repos/${githubUser}`);
      if (!res.ok) throw new Error("User not found");
      const data = await res.json();
      setRepos(data);
    } catch (err) {
      setRepoError(err.message);
      setRepos([]);
    } finally {
      setRepoLoading(false);
    }
  };

  return (
    <div className="flex h-full w-full bg-gray-900 rounded-xl shadow-xl overflow-hidden">
      {/* Sidebar */}
      <div className="w-1/3 bg-gray-800 p-4 flex flex-col">
        <h2 className="text-xl font-semibold mb-3 text-gray-100">
          GitHub Repos
        </h2>
        <div className="flex mb-3">
          <input
            value={githubUser}
            onChange={(e) => setGithubUser(e.target.value)}
            placeholder="Enter username"
            className="flex-1 p-2 rounded-l-xl bg-gray-700 border border-gray-600 text-gray-100 outline-none"
          />
          <button
            onClick={fetchRepos}
            className="bg-green-600 px-4 rounded-r-xl hover:bg-green-700 transition"
          >
            Fetch
          </button>
        </div>
        {repoLoading && <p className="text-gray-400">Loading...</p>}
        {repoError && <p className="text-red-500">{repoError}</p>}
        <ul className="flex-1 overflow-y-auto space-y-2 mt-2">
          {repos.map((repo, idx) => (
            <li
              key={idx}
              onClick={() => setSelectedRepo(repo)}
              className={`p-2 rounded cursor-pointer transition ${
                selectedRepo?.name === repo.name
                  ? "bg-green-600 text-white"
                  : "bg-gray-700 hover:bg-gray-600 text-gray-200"
              }`}
            >
              {repo.name}
            </li>
          ))}
        </ul>
      </div>

      {/* Chat Area */}
      <div className="w-2/3 flex flex-col p-4">
        <div className="mb-2 text-gray-300 font-semibold">
          {selectedRepo
            ? `Selected Repo: ${selectedRepo.name}`
            : "Select a repo to start asking questions"}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto space-y-3 mb-4 pr-2">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`p-3 rounded-lg max-w-xl break-words ${
                msg.role === "user"
                  ? "bg-blue-600 text-white self-end"
                  : "bg-gray-700 text-gray-200 self-start"
              }`}
            >
              {msg.text}
            </div>
          ))}
          {loading && (
            <div className="text-gray-400 text-sm">Assistant is typing...</div>
          )}
        </div>

        {/* Input Box */}
        <div className="flex">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              selectedRepo
                ? "Ask something about this repo..."
                : "Select a repo first"
            }
            disabled={!selectedRepo}
            className={`flex-1 p-2 bg-gray-700 border border-gray-600 rounded-l-xl outline-none text-gray-100 placeholder-gray-400 ${
              !selectedRepo ? "opacity-50 cursor-not-allowed" : ""
            }`}
          />

          <button
            onClick={handleSend}
            className="bg-blue-600 text-white px-4 rounded-r-xl hover:bg-blue-700 transition"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
