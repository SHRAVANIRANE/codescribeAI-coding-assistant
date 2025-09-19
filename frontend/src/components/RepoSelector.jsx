import { useState } from "react";
import { FaSpinner } from "react-icons/fa"; // You'll need to install react-icons if you haven't

export default function RepoSelector({ onRepoSelect }) {
  const [githubUser, setGithubUser] = useState("");
  const [repos, setRepos] = useState([]);
  const [repoLoading, setRepoLoading] = useState(false);
  const [repoError, setRepoError] = useState("");

  const fetchRepos = async () => {
    if (!githubUser.trim()) return;
    setRepoLoading(true);
    setRepoError("");
    try {
      const res = await fetch(`http://127.0.0.1:8000/repos/${githubUser}`);
      if (!res.ok) throw new Error("User not found");
      setRepos(await res.json());
    } catch (err) {
      setRepoError(err.message);
      setRepos([]);
    } finally {
      setRepoLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <h2 className="text-xl font-semibold mb-3 text-gray-100">GitHub Repos</h2>
      <div className="flex mb-3">
        <input
          value={githubUser}
          onChange={(e) => setGithubUser(e.target.value)}
          placeholder="Enter username"
          className="bg-transparent border-none outline-none w-100 py-[10px] px-[20px] text-[16px] rounded-l-full shadow-[inset_2px_5px_10px_rgb(5,5,5)] text-white flex-1"
          onKeyDown={(e) => e.key === "Enter" && fetchRepos()}
        />
        <button
          onClick={fetchRepos}
          className="relative inline-flex items-center justify-center p-4 px-5 py-3 rounded-r-full overflow-hidden font-medium text-indigo-600 transition duration-300 ease-out shadow-xl group hover:ring-1 hover:ring-purple-500"
        >
          <span className="absolute inset-0 w-full h-full bg-gradient-to-br from-blue-600 via-purple-600 to-pink-700"></span>
          <span className="relative text-white">Fetch</span>
        </button>
      </div>

      {repoLoading && (
        <div className="flex items-center justify-center py-6 ">
          <FaSpinner className="animate-spin h-6 w-6 text-blue-500" />
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
            onClick={() => onRepoSelect(repo)}
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
    </div>
  );
}
