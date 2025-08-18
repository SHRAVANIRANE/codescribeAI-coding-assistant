// src/components/ChatBox.jsx
import { useState } from "react";

export default function ChatBox() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (!input.trim()) return;
    setMessages([...messages, { role: "user", text: input }]);
    setInput("");
    // Later: integrate backend API call here
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 rounded-xl shadow-xl p-4 text-gray-100">
      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto space-y-3 mb-4 pr-2">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`p-3 rounded-lg max-w-xl break-words ${
              msg.role === "user"
                ? "bg-blue-600 text-white self-end"
                : "bg-gray-800 text-gray-200 self-start"
            }`}
          >
            {msg.text}
          </div>
        ))}
      </div>

      {/* Input Box */}
      <div className="flex">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your code query..."
          className="flex-1 p-2 bg-gray-800 border border-gray-700 rounded-l-xl outline-none text-gray-100 placeholder-gray-400"
        />
        <button
          onClick={handleSend}
          className="bg-blue-600 text-white px-4 rounded-r-xl hover:bg-blue-700 transition"
        >
          Send
        </button>
      </div>
    </div>
  );
}
