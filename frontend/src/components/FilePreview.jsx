import { useState, useEffect } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { materialDark } from "react-syntax-highlighter/dist/esm/styles/prism";

export default function FilePreview({ owner, repo, filePath }) {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);

  // get file extension for language
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
    if (!filePath) return;
    setLoading(true);
    fetch(`https://api.github.com/repos/${owner}/${repo}/contents/${filePath}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.content) {
          setContent(atob(data.content)); // decode base64
        }
      })
      .finally(() => setLoading(false));
  }, [owner, repo, filePath]);

  if (loading) {
    return <p className="text-gray-400">Loading {filePath}...</p>;
  }

  return (
    <div className="h-full overflow-y-auto custom-scrollbar">
      {content ? (
        <SyntaxHighlighter
          language={getLanguage(filePath)}
          showLineNumbers={true}
          lineNumberStyle={{ color: "#555", fontSize: "12px" }}
          style={materialDark}
          customStyle={{
            margin: 0,
            background: "transparent",
            fontSize: "14px",
            whiteSpace: "pre-wrap", // ✅ forces wrapping
            wordBreak: "break-word", // ✅ prevents overflow
            overflowX: "hidden", // ✅ no horizontal scroll
          }}
          wrapLongLines={true}
        >
          {content}
        </SyntaxHighlighter>
      ) : (
        <p className="text-gray-400">No content</p>
      )}
    </div>
  );
}
