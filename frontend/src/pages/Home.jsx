// src/pages/Home.jsx
import { Link } from "react-router-dom";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-black text-white text-center px-6">
      <h1 className="text-5xl font-bold mb-4">Welcome to CodeScribeAI</h1>
      <p className="text-lg text-gray-300 mb-6">
        Your AI-powered coding assistant. Generate, debug, and learn faster.
      </p>
      <Link
        to="/playground"
        className="bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-xl text-lg"
      >
        Try Playground →
      </Link>
    </div>
  );
}
