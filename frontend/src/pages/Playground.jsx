// src/pages/Playground.jsx
import ChatBox from "../components/ChatBox";

export default function Playground() {
  return (
    <div className="h-screen flex flex-col ">
      <div className="flex-1">
        <ChatBox />
      </div>
    </div>
  );
}
