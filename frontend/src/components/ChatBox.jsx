import { useMemo, useState, useEffect } from "react";
import RepoSelector from "./RepoSelector";
import ChatInterface from "./ChatInterface";
import FilePreview from "./FilePreview";
import { getCookie } from "@/lib/utils";

function sortNodes(nodes) {
  return [...nodes].sort((a, b) => {
    if (a.type !== b.type) return a.type === "dir" ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
}

function buildFileTree(items) {
  const root = { name: "", path: "", type: "dir", childrenMap: new Map() };

  for (const item of items) {
    const rawPath = (item.path || "").trim();
    if (!rawPath) continue;
    const parts = rawPath.split("/").filter(Boolean);
    let current = root;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isLeaf = i === parts.length - 1;
      const nodePath = current.path ? `${current.path}/${part}` : part;

      if (!current.childrenMap.has(part)) {
        current.childrenMap.set(part, {
          name: part,
          path: nodePath,
          type: isLeaf ? item.type : "dir",
          childrenMap: new Map(),
        });
      }

      const next = current.childrenMap.get(part);
      if (isLeaf) {
        next.type = item.type;
      }
      current = next;
    }
  }

  const toArray = (node) => {
    const children = sortNodes(
      [...node.childrenMap.values()].map((child) => toArray(child))
    );
    return { name: node.name, path: node.path, type: node.type, children };
  };

  return sortNodes([...root.childrenMap.values()].map((child) => toArray(child)));
}

export default function ChatBox() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState("");
  const [githubUser, setGithubUser] = useState("");
  const [fileTree, setFileTree] = useState([]);
  const [fileTreeError, setFileTreeError] = useState("");
  const [expandedDirs, setExpandedDirs] = useState({});
  const [availableModels, setAvailableModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(
    () => localStorage.getItem("aiModel") || ""
  );

  useEffect(() => {
    const user = JSON.parse(localStorage.getItem("githubUser"));
    if (user) {
      setGithubUser(user.login);
    }
  }, []);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8000/api/ai-status");
        if (!res.ok) return;
        const data = await res.json();
        const models = data?.available_models || [];
        setAvailableModels(models);
        if (!selectedModel && models.length > 0) {
          setSelectedModel(models[0]);
          localStorage.setItem("aiModel", models[0]);
        }
      } catch {
        // Keep defaults if AI status is unavailable.
      }
    };
    fetchModels();
  }, [selectedModel]);

  useEffect(() => {
    if (!selectedRepo) return;

    const fetchFileTree = async () => {
      try {
        const res = await fetch(
          `http://127.0.0.1:8000/repos/${selectedRepo.owner.login}/${selectedRepo.name}/files?recursive=true`
        );
        if (!res.ok) {
          let detail = "Failed to fetch file tree.";
          try {
            const errJson = await res.json();
            if (errJson?.detail) detail = errJson.detail;
          } catch {
            // Ignore JSON parse issues and keep default message.
          }
          throw new Error(detail);
        }
        const treeData = await res.json();
        setFileTree(treeData);
        const initiallyExpanded = {};
        for (const item of treeData) {
          if (item.type === "dir" && !item.path.includes("/")) {
            initiallyExpanded[item.path] = true;
          }
        }
        setExpandedDirs(initiallyExpanded);
        setFileTreeError("");
      } catch (err) {
        console.error(err);
        setFileTree([]);
        setFileTreeError(err.message || "Failed to fetch file tree.");
      }
    };

    fetchFileTree();
  }, [selectedRepo]);

  const treeNodes = useMemo(() => buildFileTree(fileTree), [fileTree]);

  const toggleDir = (dirPath) => {
    setExpandedDirs((prev) => ({ ...prev, [dirPath]: !prev[dirPath] }));
  };

  const handleRepoSelect = (repo, user) => {
    setSelectedRepo(repo);
    setGithubUser(user || repo?.owner?.login || "");
    setSelectedFile(null);
    setFileContent("");
    setMessages([]);
    setFileTreeError("");
    setExpandedDirs({});
  };

  const handleSendMessage = async (input, filePath = null, content = null) => {
    if (!input.trim() || !selectedRepo) return;

    const newMsg = { role: "user", text: input };
    setMessages((p) => [...p, newMsg]);
    setLoading(true);

    try {
      const csrfToken = getCookie("csrf_token");
      const res = await fetch("http://127.0.0.1:8000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-csrf-token": csrfToken ?? "",
        },
        body: JSON.stringify({
          message: input,
          repo: selectedRepo.name,
          github_user: selectedRepo.owner.login,
          file: filePath,
          file_content: content,
          model: selectedModel || undefined,
        }),
        credentials: "include",
      });

      if (!res.ok) throw new Error("Backend error");

      const result = await res.json();
      setMessages((p) => [
        ...p,
        {
          role: "assistant",
          text: result.reply || "No response received.",
          sourceDocs: result.sources || [],
        },
      ]);
    } catch (err) {
      console.error(err);
      setMessages((p) => [
        ...p,
        {
          role: "assistant",
          text: "An error occurred while fetching your request.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const onFileSelect = (file) => {
    if (file?.type !== "file") return;
    setSelectedFile(file);
  };

  const renderTreeNodes = (nodes, depth = 0) => {
    return nodes.map((node) => {
      const isDir = node.type === "dir";
      const isExpanded = !!expandedDirs[node.path];

      return (
        <div key={node.path || node.name}>
          <div
            onClick={() => (isDir ? toggleDir(node.path) : onFileSelect(node))}
            className={`text-xs py-0.5 ${
              isDir ? "cursor-pointer text-gray-300 hover:text-blue-300" : "cursor-pointer text-gray-400 hover:text-blue-400"
            } ${selectedFile?.path === node.path ? "text-blue-400" : ""}`}
            style={{ paddingLeft: `${depth * 14}px` }}
          >
            {isDir ? (isExpanded ? "[-]" : "[+]") : "[FILE]"} {node.name}
          </div>
          {isDir && isExpanded && node.children?.length > 0 && renderTreeNodes(node.children, depth + 1)}
        </div>
      );
    });
  };

  const renderFileExplorer = () => {
    return (
      <div className="mt-4 p-3 bg-gray-900 rounded-lg border border-gray-700">
        <h4 className="text-sm text-gray-300 font-semibold mb-2">File Explorer</h4>
        <div className="space-y-1 max-h-64 overflow-y-auto custom-scrollbar">
          {!treeNodes.length && !fileTreeError && (
            <p className="text-xs text-gray-500">No files found in this repository.</p>
          )}
          {renderTreeNodes(treeNodes)}
        </div>
        {fileTreeError && <p className="mt-2 text-xs text-red-400">{fileTreeError}</p>}
      </div>
    );
  };

  return (
    <div className="flex h-full w-full bg-gray-900 max-h-172 shadow-xl custom-scrollbar">
      <div className="w-1/4 bg-gray-800 p-4 flex flex-col">
        {selectedRepo ? (
          <div className="flex flex-col h-full">
            <h3 className="text-xl font-bold text-white mb-4">{selectedRepo.name}</h3>
            <p className="text-gray-300 text-sm mt-3 leading-relaxed">
              {selectedRepo.description || "No description available"}
            </p>
            <div className="mt-3">
              <label className="block text-xs text-gray-400 mb-1">AI Model</label>
              <select
                value={selectedModel}
                onChange={(e) => {
                  setSelectedModel(e.target.value);
                  localStorage.setItem("aiModel", e.target.value);
                }}
                className="w-full bg-gray-900 border border-gray-700 rounded-md px-2 py-1 text-sm text-gray-200"
              >
                {availableModels.length === 0 ? (
                  <option value="">Default</option>
                ) : (
                  availableModels.map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))
                )}
              </select>
            </div>
            {renderFileExplorer()}
            <button
              onClick={() => setSelectedRepo(null)}
              className="mt-6 text-center bg-gray-600 hover:bg-gray-500 text-white font-medium py-2 px-4 rounded-lg transition"
            >
              Back to Repos
            </button>
          </div>
        ) : (
          <RepoSelector onRepoSelect={handleRepoSelect} currentUser={githubUser} />
        )}
      </div>

      {selectedRepo && selectedFile && (
        <div className="w-2/5 bg-gray-900 border-x border-gray-700 p-4">
          <FilePreview
            owner={selectedRepo.owner.login}
            repo={selectedRepo.name}
            filePath={selectedFile.path}
            askAI={handleSendMessage}
            fileContent={fileContent}
          />
        </div>
      )}

      <div className={`flex-1 flex flex-col ${selectedFile ? "" : "w-3/4"}`}>
        <ChatInterface
          messages={messages}
          loading={loading}
          onSendMessage={handleSendMessage}
          selectedRepo={selectedRepo}
        />
      </div>
    </div>
  );
}
