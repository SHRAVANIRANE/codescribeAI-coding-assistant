import { useState, useRef, useEffect } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { materialDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { FaSpinner } from "react-icons/fa";

export default function ChatInterface({
  messages,
  loading,
  onSendMessage,
  selectedRepo,
}) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = () => {
    if (!input.trim()) return;
    onSendMessage(input);
    setInput("");
  };

  const renderAssistantMessage = (text) =>
    text.split(/```(.*?)```/gs).map((chunk, i) => {
      if (i % 2 === 1) {
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
      return (
        <pre key={i} className="whitespace-pre-wrap">
          {chunk}
        </pre>
      );
    });

  return (
    <div className="flex-1 flex flex-col bg-gradient-to-br from-gray-900 to-gray-800 rounded-xl shadow-lg border border-gray-700">
      {selectedRepo && (
        <div className="mb-2 bg-gray-800 px-4 py-2 rounded-lg text-gray-300 border-b border-gray-700 text-sm">
          Chatting about:{" "}
          <span className="font-semibold text-blue-400">
            {selectedRepo.name}
          </span>
        </div>
      )}

      <div className="flex-1 overflow-y-auto max-h-screen space-y-4 p-4 pr-2 custom-scrollbar">
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
                  ? "bg-gradient-to-r from-blue-500 to-blue-700 text-white rounded-br-none"
                  : "bg-gradient-to-r from-gray-700 to-gray-800 text-gray-100 rounded-bl-none"
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
            <FaSpinner className="animate-spin" />
            <span className="animate-pulse">Generating response</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

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
  );
}
