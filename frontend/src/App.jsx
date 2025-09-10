// src/App.jsx
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import "./index.css";
import Playground from "./pages/Playground";
import ProtectedRoute from "./components/ProtectedRoute";

export default function App() {
  return (
    <Router>
      <div className="flex flex-col h-screen bg-black">
        <Navbar />
        <Routes>
          {/* Protect Playground */}
          <Route
            path="/playground"
            element={
              <ProtectedRoute>
                <Playground />
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<Home />} />
          <Route path="/playground" element={<Playground />} />
        </Routes>
      </div>
    </Router>
  );
}
