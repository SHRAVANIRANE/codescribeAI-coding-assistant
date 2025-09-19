import { useState, useEffect } from "react";
import RepoSelector from "./RepoSelector";
import ChatInterface from "./ChatInterface";
import FilePreview from "./FilePreview";

export default function ChatBox() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState("");
  const [githubUser, setGithubUser] = useState("");
  const [fileTree, setFileTree] = useState([]);

  // Use the logged-in user's username
  useEffect(() => {
    const user = JSON.parse(localStorage.getItem("githubUser"));
    if (user) {
      setGithubUser(user.login);
    }
  }, []);

  // Fetch file tree when a repository is selected
  useEffect(() => {
    if (selectedRepo) {
      const fetchFileTree = async () => {
        try {
          const res = await fetch(
            `http://127.0.0.1:8000/repos/${selectedRepo.owner.login}/${selectedRepo.name}/files`
          );
          if (!res.ok) throw new Error("Failed to fetch file tree.");
          setFileTree(await res.json());
        } catch (err) {
          console.error(err);
          setFileTree([]);
        }
      };
      fetchFileTree();
    }
  }, [selectedRepo]);

  const handleRepoSelect = (repo, user) => {
    setSelectedRepo(repo);
    setGithubUser(user);
    setSelectedFile(null);
    setFileContent("");
    setMessages([]);
  };

  const handleSendMessage = async (input, filePath = null, content = null) => {
    if (!input.trim() || !selectedRepo) return;
    // Your existing code to add the user's message and set loading state
    const newMsg = { role: "user", text: input };
    setMessages((p) => [...p, newMsg]);
    setLoading(true);

    try {
      // Step 1: Send the request to the new endpoint that dispatches a Celery task
      const res = await fetch("http://127.0.0.1:8000/api/chat-async", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: input,
          repo: selectedRepo.name,
          github_user: selectedRepo.owner.login,
          file: filePath,
          file_content: content,
        }),
        credentials: "include",
      });
      if (!res.ok) throw new Error("Backend error during task submission");

      // Step 2: Receive the task ID from the backend
      const data = await res.json();
      const taskId = data.task_id; // The backend should return an object like { "task_id": "..." }

      // Step 3: Begin polling for the task's status
      pollForTaskResult(taskId);
    } catch (err) {
      console.error(err);
      setMessages((p) => [
        ...p,
        {
          role: "assistant",
          text: "⚠️ An error occurred while queuing your request.",
        },
      ]);
      setLoading(false);
    }
  };
  const pollForTaskResult = async (taskId) => {
    let isComplete = false;
    let result = null;
    let attempts = 0;
    const maxAttempts = 30; // Poll for up to 30 times
    const delay = 3000; // 3 seconds between polls

    while (!isComplete && attempts < maxAttempts) {
      attempts++;
      try {
        const statusRes = await fetch(
          `http://127.0.0.1:8000/tasks/${taskId}/status`
        );
        if (!statusRes.ok) throw new Error("Failed to get task status.");

        const statusData = await statusRes.json();
        if (statusData.status === "SUCCESS") {
          isComplete = true;
          result = statusData.result; // The final answer from the Celery task
        } else if (statusData.status === "FAILURE") {
          isComplete = true;
          throw new Error("Task failed on the backend.");
        }
      } catch (err) {
        console.error("Polling error:", err);
        isComplete = true;
        setMessages((p) => [
          ...p,
          {
            role: "assistant",
            text: "⚠️ Could not retrieve the AI's response.",
          },
        ]);
        setLoading(false);
        return;
      }
      if (!isComplete) {
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }

    setLoading(false);
    if (result) {
      setMessages((p) => [
        ...p,
        {
          role: "assistant",
          text: result.reply,
          sourceDocs: result.sources || [],
        },
      ]);
    } else {
      setMessages((p) => [
        ...p,
        { role: "assistant", text: "⚠️ The request timed out." },
      ]);
    }
  };

  // Function to handle file clicks
  const onFileSelect = (file) => {
    setSelectedFile(file);
    // You'll need to update the FilePreview component to fetch its own content
    // and call handleAskAIFromFile when the button is clicked.
    // This is the correct state update for file selection.
  };

  const renderFileExplorer = (files) => {
    return (
      <div className="mt-4 p-3 bg-gray-900 rounded-lg border border-gray-700">
        <h4 className="text-sm text-gray-300 font-semibold mb-2">
          📂 File Explorer
        </h4>
        <ul className="space-y-1 text-xs text-gray-400 max-h-48 overflow-y-auto custom-scrollbar">
          {files.map((file, idx) => (
            <li
              key={idx}
              onClick={() => onFileSelect(file)}
              className="cursor-pointer hover:text-blue-400"
            >
              {file.type === "dir" ? "📁" : "📄"} {file.path}
            </li>
          ))}
        </ul>
      </div>
    );
  };

  return (
    <div className="flex h-full w-full bg-gray-900 max-h-172 shadow-xl custom-scrollbar">
      {/* Sidebar: Repo Selector & Info */}
      <div className="w-1/4 bg-gray-800 p-4 flex flex-col">
        {selectedRepo ? (
          <div className="flex flex-col h-full">
            <h3 className="text-xl font-bold text-white mb-4">
              {selectedRepo.name}
            </h3>
            <p className="text-gray-300 text-sm mt-3 leading-relaxed">
              {selectedRepo.description || "No description available"}
            </p>
            {renderFileExplorer(fileTree)}
            <button
              onClick={() => setSelectedRepo(null)}
              className="mt-6 text-center bg-gray-600 hover:bg-gray-500 text-white font-medium py-2 px-4 rounded-lg transition"
            >
              Back to Repos
            </button>
          </div>
        ) : (
          <RepoSelector
            onRepoSelect={handleRepoSelect}
            currentUser={githubUser}
          />
        )}
      </div>

      {/* Middle Column: File Preview */}
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

      {/* Main Chat Interface */}
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
