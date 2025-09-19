import { useState, useEffect } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { materialDark } from "react-syntax-highlighter/dist/esm/styles/prism";

export default function FilePreview({ owner, repo, filePath, askAI }) {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);

  const getLanguage = (path) => {
    if (!path) return "javascript";
    const ext = path.split(".").pop();
    switch (ext) {
      case "js":
      case "jsx":
        return "javascript";
      case "ts":
      case "tsx":
        return "typescript";
      case "py":
        return "python";
      case "java":
        return "java";
      case "cpp":
      case "cc":
      case "cxx":
      case "h":
        return "cpp";
      case "css":
        return "css";
      case "html":
        return "html";
      case "json":
        return "json";
      case "md":
        return "markdown";
      default:
        return "text";
    }
  };

  useEffect(() => {
    if (!filePath || !owner || !repo) return;
    setLoading(true);

    // Use a new, dedicated endpoint for raw file content
    fetch(
      `http://127.0.0.1:8000/repos/${owner}/${repo}/file-content?path=${encodeURIComponent(
        filePath
      )}`
    )
      .then((res) => {
        if (!res.ok) {
          throw new Error("Failed to fetch file content.");
        }
        return res.text(); // Get the raw text content
      })
      .then((data) => {
        setContent(data); // Set the raw content directly
      })
      .catch((err) => {
        console.error(err);
        setContent("No content available.");
      })
      .finally(() => setLoading(false));
  }, [owner, repo, filePath]);
  if (loading) {
    return <p className="text-gray-400">Loading {filePath}...</p>;
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex justify-between items-center mb-2">
        <p className="text-gray-500 text-sm md:text-base font-semibold truncate max-w-xs md:max-w-md">
          {filePath}
        </p>
        <button
          onClick={() =>
            askAI?.(
              `Explain the code in the file ${filePath}`, // Message for AI
              filePath, // File path
              content // File content
            )
          }
          className="relative inline-flex items-center justify-center px-6 py-3 overflow-hidden font-medium text-indigo-600 transition duration-300 ease-out rounded-full shadow-xl group hover:ring-1 hover:ring-purple-500"
        >
          <span className="absolute inset-0 w-full h-full bg-gradient-to-br from-blue-600 via-purple-600 to-pink-700"></span>
          <span className="absolute bottom-0 right-0 block w-64 h-64 mb-32 mr-4 transition duration-500 origin-bottom-left transform rotate-45 translate-x-24 bg-pink-500 rounded-full opacity-30 group-hover:rotate-90 ease"></span>
          <span className="relative text-white text-sm font-semibold">
            🤖 Ask AI
          </span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {content ? (
          <SyntaxHighlighter
            language={getLanguage(filePath)}
            style={materialDark}
            wrapLongLines={true}
            showLineNumbers={true}
            customStyle={{
              margin: 0,
              background: "transparent",
              fontSize: "14px",
            }}
          >
            {content}
          </SyntaxHighlighter>
        ) : (
          <p className="text-gray-400">No content</p>
        )}
      </div>
    </div>
  );
}
