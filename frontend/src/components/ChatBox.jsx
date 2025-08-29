import { useState, useEffect, useRef } from "react";
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

  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

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
            className="bg-transparent border-none outline-none w-100 py-[10px] px-[20px] text-[16px] rounded-l-full shadow-[inset_2px_5px_10px_rgb(5,5,5)] text-white"
          />
          <a
            href="#_"
            onClick={fetchRepos}
            className="relative inline-flex items-center justify-center p-4 px-5 py-3 rounded-r-full overflow-hidden font-medium text-indigo-600 transition duration-300 ease-out shadow-xl group hover:ring-1 hover:ring-purple-500"
          >
            <span className="absolute inset-0 w-full h-full bg-gradient-to-br from-blue-600 via-purple-600 to-pink-700"></span>
            <span className="absolute bottom-0 right-0 block w-64 h-64 mb-32 mr-4 transition duration-500 origin-bottom-left transform rotate-45 translate-x-24 bg-pink-500 rounded-full opacity-30 group-hover:rotate-90 ease"></span>
            <span className="relative text-white">Fetch</span>
          </a>
        </div>

        {/* Repo List */}
        {!selectedRepo && (
          <>
            {repoLoading && (
              <div className="flex items-center justify-center py-6">
                <span className="animate-spin h-6 w-6 border-2 border-blue-500 border-t-transparent rounded-full"></span>
                <p className="ml-3 text-blue-400 font-medium">
                  Fetching repositories...
                </p>
              </div>
            )}

            {repoError && (
              <p className="text-red-400 bg-red-900/30 border border-red-700 px-4 py-2 rounded-lg text-sm mt-2">
                {repoError}
              </p>
            )}

            <ul className="flex-1 overflow-y-auto space-y-3 mt-4 pr-2">
              {repos.map((repo, idx) => (
                <li
                  key={idx}
                  onClick={() => setSelectedRepo(repo)}
                  className="group p-4 bg-gradient-to-r from-gray-800 to-gray-700 rounded-xl shadow-md hover:from-gray-700 hover:to-gray-600 cursor-pointer transition-all duration-300 border border-gray-600 hover:border-blue-500"
                >
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-white group-hover:text-blue-400 transition">
                      {repo.name}
                    </h3>
                    <span className="text-xs text-gray-400 bg-gray-900 px-2 py-1 rounded-md">
                      ⭐ {repo.stargazers_count || 0}
                    </span>
                  </div>
                  {repo.description && (
                    <p className="text-gray-400 text-sm mt-2 line-clamp-2">
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
          <div className="bg-gradient-to-br from-gray-800 to-gray-700 rounded-xl p-6 shadow-lg border border-gray-600">
            {/* Repo Header */}
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-bold text-white">
                {selectedRepo.name}
              </h3>
              {selectedRepo.stargazers_count !== undefined && (
                <span className="text-sm bg-gray-900 px-3 py-1 rounded-md text-gray-300 border border-gray-600">
                  ⭐ {selectedRepo.stargazers_count}
                </span>
              )}
            </div>

            {/* Description */}
            {selectedRepo.description ? (
              <p className="text-gray-300 text-sm mt-3 leading-relaxed">
                {selectedRepo.description}
              </p>
            ) : (
              <p className="text-gray-500 italic mt-3 text-sm">
                No description available
              </p>
            )}

            {/* Extra Info */}
            <div className="flex flex-wrap gap-3 mt-4 text-sm text-gray-400">
              {selectedRepo.language && (
                <span className="px-3 py-1 rounded-full bg-gray-900 border border-gray-600">
                  {selectedRepo.language}
                </span>
              )}
              {selectedRepo.forks_count !== undefined && (
                <span className="px-3 py-1 rounded-full bg-gray-900 border border-gray-600">
                  🍴 {selectedRepo.forks_count} Forks
                </span>
              )}
              {selectedRepo.open_issues_count !== undefined && (
                <span className="px-3 py-1 rounded-full bg-gray-900 border border-gray-600">
                  🐛 {selectedRepo.open_issues_count} Issues
                </span>
              )}
            </div>

            {/* Actions */}
            <div className="mt-6 flex gap-3">
              {selectedRepo.html_url && (
                <a
                  href={selectedRepo.html_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 text-center bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition"
                >
                  View on GitHub
                </a>
              )}
              <button
                onClick={() => setSelectedRepo(null)}
                className="flex-1 text-center bg-gray-600 hover:bg-gray-500 text-white font-medium py-2 px-4 rounded-lg transition"
              >
                Back
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Chat Area */}
      <div className="w-2/3 flex flex-col bg-gradient-to-br from-gray-900 to-gray-800 rounded-xl shadow-lg border border-gray-700">
        {selectedRepo && (
          <div className="mb-2 bg-gray-800 px-4 py-2 rounded-lg text-gray-300 border-b border-gray-700 text-sm">
            Chatting about:{" "}
            <span className="font-semibold text-blue-400">
              {selectedRepo.name}
            </span>
          </div>
        )}

        {/* Messages (scrollable only) */}
        <div className="flex-1 overflow-y-auto space-y-4 p-4 pr-2 custom-scrollbar">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`p-3 rounded-2xl max-w-xl shadow-md text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white rounded-br-none"
                    : "bg-gray-700 text-gray-200 rounded-bl-none"
                }`}
              >
                {msg.role === "assistant"
                  ? renderAssistantMessage(msg.text)
                  : msg.text}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex items-center space-x-2 text-gray-400 text-sm">
              <span className="animate-pulse">Generating response</span>
              <span className="animate-bounce">.</span>
              <span className="animate-bounce delay-150">.</span>
              <span className="animate-bounce delay-300">.</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Box (always visible at bottom) */}
        <div className="border-t border-gray-700 bg-gray-900 p-3">
          <div className="flex items-center gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your code query..."
              className="flex-1 p-3 bg-gray-800 border border-gray-700 rounded-xl outline-none text-gray-100 placeholder-gray-500 focus:ring-2 focus:ring-blue-500 transition"
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
            />
            <button
              onClick={handleSend}
              disabled={!selectedRepo}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl shadow-md transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
