import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { materialDark } from "react-syntax-highlighter/dist/esm/styles/prism";

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
    if (!input.trim() || !selectedRepo) return;

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
          repo: selectedRepo.name,
          github_user: githubUser,
        }),
        credentials: "include",
      });

      if (!res.ok) throw new Error("Backend error");

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: data.reply,
          sourceDocs: data.sources || [], // attach retrieved docs if backend sends them
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "⚠️ Could not reach AI backend." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Linkify function to convert URLs in text to clickable links
  const linkify = (text) =>
    text.split(/(https?:\/\/[^\s]+)/g).map((part, i) =>
      part.match(/https?:\/\/[^\s]+/) ? (
        <a
          key={i}
          href={part}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-400 underline"
        >
          {part}
        </a>
      ) : (
        <span key={i}>{part}</span>
      )
    );

  // Render assistant message with code blocks
  const renderAssistantMessage = (text) => {
    return text.split(/```(.*?)```/gs).map((chunk, i) => {
      if (i % 2 === 1) {
        // Code block
        const [lang, ...codeLines] = chunk.split("\n");
        const code = codeLines.join("\n");
        return (
          <SyntaxHighlighter
            key={i}
            language={lang || "text"}
            style={materialDark}
            customStyle={{ borderRadius: "0.5rem", padding: "0.5rem" }}
          >
            {code}
          </SyntaxHighlighter>
        );
      }
      // Regular text with line breaks
      return (
        <pre key={i} className="whitespace-pre-wrap">
          {chunk}
        </pre>
      );
    });
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

        {/* Username Input */}
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

        {/* Repo List */}
        {!selectedRepo && (
          <>
            {repoLoading && <p className="text-gray-400">Loading...</p>}
            {repoError && <p className="text-red-500">{repoError}</p>}
            <ul className="flex-1 overflow-y-auto space-y-2 mt-2">
              {repos.map((repo, idx) => (
                <li
                  key={idx}
                  onClick={() => setSelectedRepo(repo)}
                  className="p-2 bg-gray-700 rounded hover:bg-gray-600 cursor-pointer transition"
                >
                  <div className="text-blue-400 font-medium hover:underline">
                    {repo.name}
                  </div>
                  {repo.description && (
                    <p className="text-gray-400 text-sm truncate">
                      {repo.description}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </>
        )}

        {/* Selected Repo Info */}
        {selectedRepo && (
          <div className="bg-gray-700 rounded p-3">
            <h3 className="text-lg font-semibold text-gray-100">
              {selectedRepo.name}
            </h3>
            {selectedRepo.description && (
              <p className="text-gray-300 text-sm my-1">
                {selectedRepo.description}
              </p>
            )}
            <p className="text-gray-400 text-sm">
              ⭐ Stars: {selectedRepo.stargazers_count || 0}
            </p>
            <button
              onClick={() => setSelectedRepo(null)}
              className="mt-2 bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 transition"
            >
              Back to Repo List
            </button>
          </div>
        )}
      </div>

      {/* Chat Area */}
      <div className="w-2/3 flex flex-col p-4">
        {selectedRepo && (
          <div className="mb-3 bg-gray-700 p-2 rounded text-gray-200">
            Chatting about:{" "}
            <span className="font-semibold">{selectedRepo.name}</span>
          </div>
        )}

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
              {msg.role === "assistant" ? (
                renderAssistantMessage(msg.text)
              ) : (
                <span>{msg.text}</span>
              )}
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
            placeholder="Type your code query..."
            className="flex-1 p-2 bg-gray-700 border border-gray-600 rounded-l-xl outline-none text-gray-100 placeholder-gray-400"
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
          />
          <button
            onClick={handleSend}
            className="bg-blue-600 text-white px-4 rounded-r-xl hover:bg-blue-700 transition"
            disabled={!selectedRepo}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
