// src/components/ProtectedRoute.jsx
import { Navigate } from "react-router-dom";

export default function ProtectedRoute({ children }) {
  const user = JSON.parse(localStorage.getItem("githubUser"));

  if (!user) {
    // Redirect directly to GitHub login
    window.location.href = "http://localhost:8000/login/github";
    return null; // render nothing while redirecting
  }

  return children;
}
