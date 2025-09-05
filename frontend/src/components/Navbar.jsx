import { useState, useEffect } from "react";

export default function Navbar() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    async function fetchUser() {
      try {
        const res = await fetch("http://localhost:8000/me", {
          credentials: "include",
        });
        if (!res.ok) throw new Error("Not logged in");
        const data = await res.json();
        setUser(data); // data.avatar_url will be your real GitHub avatar
        localStorage.setItem("githubUser", JSON.stringify(data));
      } catch (err) {
        console.log("No user logged in yet");
      }
    }
    fetchUser();
  }, []);

  return (
    <nav className="w-full bg-gray-900 text-white px-6 py-3 flex items-center justify-between shadow-md">
      <h1 className="text-xl font-bold">CodeScribeAI</h1>
      <div className="flex items-center gap-6">
        <a href="/" className="hover:text-gray-400">
          Home
        </a>
        <a href="/playground" className="hover:text-gray-400">
          Playground
        </a>

        {user ? (
          <div className="flex items-center gap-3">
            <img
              src={user.avatar_url}
              alt="GitHub Avatar"
              className="w-10 h-10 rounded-full border border-gray-700"
            />
          </div>
        ) : (
          <a
            href="http://localhost:8000/login/github"
            className="hover:text-gray-400"
          >
            Login with GitHub
          </a>
        )}
      </div>
    </nav>
  );
}
