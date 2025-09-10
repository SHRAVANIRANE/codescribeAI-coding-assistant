// src/pages/Home.jsx
import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { FaGithub, FaLinkedin, FaTwitter } from "react-icons/fa";

export default function Home() {
  const [typedText, setTypedText] = useState("");
  const fullText =
    "The AI-powered coding assistant that helps you explore, debug, and understand repositories — faster and smarter.";

  // Typing animation effect
  useEffect(() => {
    let index = 0;
    const interval = setInterval(() => {
      setTypedText(fullText.slice(0, index + 1));
      index++;
      if (index === fullText.length) clearInterval(interval);
    }, 25);
    return () => clearInterval(interval);
  }, []);

  const features = [
    {
      title: "🔍 Explore Repositories",
      desc: "Browse and search your GitHub projects with a clean interface.",
    },
    {
      title: "🤖 AI-Powered Q&A",
      desc: "Ask natural language questions and get precise answers from your codebase.",
    },
    {
      title: "📂 File Insights",
      desc: "Understand project structure and dive deep into specific files instantly.",
    },
    {
      title: "📝 Code Summarization",
      desc: "Get AI summaries of README and code files within seconds.",
    },
    {
      title: "🔧 Debug Suggestions",
      desc: "AI highlights potential issues and suggests improvements in your code.",
    },
    {
      title: "📊 Repo Analytics",
      desc: "View languages, contributors, stars, and file count for your repositories.",
    },
  ];

  return (
    <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-black text-white ">
      {/* Hero Section */}
      <section className="flex flex-col items-center justify-center h-screen text-center px-6">
        <h1 className="text-6xl md:text-7xl font-extrabold tracking-tight mb-6 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 bg-clip-text text-transparent ">
          CodeScribeAI
        </h1>
        <p className="text-lg md:text-xl text-gray-400 max-w-2xl mb-10">
          {typedText}
        </p>

        <div className="flex flex-wrap gap-6 justify-center">
          <Link
            to="/playground"
            className="relative inline-flex items-center justify-center px-6 py-3 overflow-hidden font-medium text-indigo-600 transition duration-300 ease-out rounded-full shadow-xl group hover:ring-1 hover:ring-purple-500"
            aria-label="Try CodeScribeAI Playground"
          >
            <span className="absolute inset-0 w-full h-full bg-gradient-to-br from-blue-600 via-purple-600 to-pink-700"></span>
            <span className="absolute bottom-0 right-0 block w-64 h-64 mb-32 mr-4 transition duration-500 origin-bottom-left transform rotate-45 translate-x-24 bg-pink-500 rounded-full opacity-30 group-hover:rotate-90 ease"></span>
            <span className="relative text-white text-lg font-semibold">
              🚀 Try Playground
            </span>
          </Link>

          <a
            href="https://github.com/your-repo"
            target="_blank"
            rel="noopener noreferrer"
            className="px-6 py-3 text-lg font-medium rounded-lg border border-gray-600 hover:border-white transition"
          >
            View on GitHub
          </a>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 px-6 border-t border-gray-800 ">
        <div className="max-w-6xl mx-auto text-center">
          <h2 className="text-4xl font-bold mb-16">What You Can Do</h2>
          <div className="grid md:grid-cols-3 gap-12 text-left">
            {features.map((f, i) => (
              <div
                key={i}
                className="space-y-4 p-6 rounded-xl bg-gray-800 hover:bg-gray-700 transition transform hover:scale-105 shadow-lg"
              >
                <h3 className="text-xl font-semibold">{f.title}</h3>
                <p className="text-gray-400">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-24 px-6">
        <div className="max-w-6xl mx-auto text-center">
          <h2 className="text-4xl font-bold mb-16">What Developers Say</h2>
          <div className="grid md:grid-cols-3 gap-12">
            {[
              {
                name: "Alex T.",
                role: "Full-Stack Developer",
                quote: "CodeScribeAI saved me hours debugging my Node.js app!",
                img: "https://randomuser.me/api/portraits/men/32.jpg",
              },
              {
                name: "Priya S.",
                role: "Data Scientist",
                quote:
                  "The AI summaries make understanding complex repos a breeze.",
                img: "https://randomuser.me/api/portraits/women/44.jpg",
              },
              {
                name: "Sam K.",
                role: "Open-Source Contributor",
                quote:
                  "Exploring GitHub projects has never been this intuitive.",
                img: "https://randomuser.me/api/portraits/men/65.jpg",
              },
            ].map((t, i) => (
              <div
                key={i}
                className="p-6 rounded-xl bg-gray-800 hover:bg-gray-700 transition transform hover:scale-105 shadow-lg flex flex-col items-center"
              >
                <img
                  src={t.img}
                  alt={t.name}
                  className="w-20 h-20 rounded-full border-4 border-gray-700 mb-4 object-cover"
                />
                <p className="text-gray-400 italic">"{t.quote}"</p>
                <p className="mt-4 font-semibold">{t.name}</p>
                <p className="text-gray-500">{t.role}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Newsletter Signup */}
      <section className="py-16 px-6 text-center">
        <h2 className="text-3xl font-bold mb-6">Join our Community</h2>
        <p className="text-gray-400 mb-6 max-w-xl mx-auto">
          Subscribe to our newsletter for updates, tips, and exclusive AI coding
          insights.
        </p>
        <form className="flex justify-center gap-4 max-w-md mx-auto">
          <input
            type="email"
            placeholder="Enter your email"
            className="px-4 py-3 rounded-lg bg-gray-800 text-white border border-gray-600 focus:outline-none focus:border-purple-500"
          />
          <button
            type="submit"
            className="px-6 py-3 text-lg font-semibold rounded-lg bg-gradient-to-br from-blue-600 via-purple-600 to-pink-700 hover:ring-1 hover:ring-purple-500 transition"
          >
            Subscribe
          </button>
        </form>
      </section>

      {/* Footer */}
      <footer className="py-10 text-center text-gray-500 border-t border-gray-800">
        <p>
          © {new Date().getFullYear()} CodeScribeAI. Built with ❤️ for
          developers.
        </p>
        <div className="flex justify-center gap-6 text-2xl text-gray-400 mt-4">
          <a
            href="https://github.com/your-repo"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-white transition"
          >
            <FaGithub />
          </a>
          <a
            href="https://linkedin.com/in/your-profile"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-white transition"
          >
            <FaLinkedin />
          </a>
          <a
            href="https://twitter.com/your-profile"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-white transition"
          >
            <FaTwitter />
          </a>
        </div>
      </footer>
    </div>
  );
}
