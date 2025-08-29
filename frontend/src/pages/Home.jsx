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
        className="relative inline-flex items-center justify-center px-6 py-3 overflow-hidden font-medium text-indigo-600 transition duration-300 ease-out rounded-full shadow-xl group hover:ring-1 hover:ring-purple-500"
      >
        {/* Gradient Background */}
        <span className="absolute inset-0 w-full h-full bg-gradient-to-br from-blue-600 via-purple-600 to-pink-700"></span>

        {/* Hover Animation Blob */}
        <span className="absolute bottom-0 right-0 block w-64 h-64 mb-32 mr-4 transition duration-500 origin-bottom-left transform rotate-45 translate-x-24 bg-pink-500 rounded-full opacity-30 group-hover:rotate-90 ease"></span>

        {/* Text Layer */}
        <span className="relative text-white text-lg font-semibold">
          🚀 Try Playground →
        </span>
      </Link>
    </div>
  );
}
