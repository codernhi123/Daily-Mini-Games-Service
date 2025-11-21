// src/App.tsx
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { MemoryGame } from "./pages/MemoryGame";
import TriviaGame from "./pages/TriviaGame";

function Home() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-8">Mini Games</h1>

        <div className="flex flex-col gap-4 items-center">
          <Link
            to="/memory-game"
            className="w-64 whitespace-nowrap px-8 py-4 bg-blue-600 text-white rounded-lg text-xl font-semibold text-center hover:bg-blue-700"
          >
            Play Memory Game
          </Link>

          <Link
            to="/trivia-game"
            className="w-64 whitespace-nowrap px-8 py-4 bg-green-600 text-white rounded-lg text-xl font-semibold text-center hover:bg-green-700"
          >
            Play Trivia Game
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/memory-game" element={<MemoryGame />} />
        <Route path="/trivia-game" element={<TriviaGame />} />
      </Routes>
    </BrowserRouter>
  );
}