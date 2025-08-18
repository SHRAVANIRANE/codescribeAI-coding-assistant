// src/components/Navbar.jsx
export default function Navbar() {
  return (
    <nav className="w-full bg-gray-900 text-white px-6 py-3 flex items-center justify-between shadow-md">
      <h1 className="text-xl font-bold">CodeScribeAI</h1>
      <div className="space-x-6 text-lg">
        <a href="/" className="hover:text-gray-400">
          Home
        </a>
        <a href="/playground" className="hover:text-gray-400">
          Playground
        </a>
      </div>
    </nav>
  );
}
