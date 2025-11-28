import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { MemoryGame } from "./pages/MemoryGame";
import TriviaGame from "./pages/TriviaGame";
import { useState, useEffect } from "react";
import axios from "axios";
import GameStats from "./pages/GameStats";

function Home() {
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [loggedIn, setLoggedIn] = useState(false);
  const [timeLeft, setTimeLeft] = useState<number | null>(null);

  // Format milliseconds to mm:ss
  function formatTime(ms: number) {
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, "0")}`;
  }

  // Fetch current user from the server
  useEffect(() => {
  async function fetchUser() {
    try {
      const response = await axios.get(
        "http://localhost:8000/v2/authentications/me",
        { withCredentials: true }
      );

      if (response.data && response.data.id) {
        setLoggedIn(true);
        setName(response.data.name);

        // Restore countdown from expiry
        const expiry = localStorage.getItem("jwt_expiry");
        if (expiry) {
          const remaining = parseInt(expiry, 10) - Date.now();
          if (remaining > 0) setTimeLeft(remaining);
          else handleLogout();
        }
      } else {
        setLoggedIn(false);
      }
    } catch {
      setLoggedIn(false);
    }
  }
  fetchUser();
}, []);

  // Login function
  async function handleLogin(e: React.FormEvent) {
  e.preventDefault();

  try {
    const expiryDate = new Date(Date.now() + 60 * 60 * 1000); // 1 hour
    const expiry =
      expiryDate.toISOString().replace("T", " ").split(".")[0];

    await axios.post(
      "http://localhost:8000/v2/authentications/",
      { name, password, expiry },
      { withCredentials: true }
    );

    setLoggedIn(true);

    // Store expiry timestamp in localStorage
    localStorage.setItem("jwt_expiry", expiryDate.getTime().toString());
    setTimeLeft(expiryDate.getTime() - Date.now());

    alert("Logged in!");
  } catch {
    alert("Invalid credentials");
  }
}

  // Logout function
  async function handleLogout() {
    try {
      await axios.post(
        "http://localhost:8000/v2/authentications/logout",
        {},
        { withCredentials: true }
      );
    } catch (error) {
      console.error("Logout failed", error);
    }
    setLoggedIn(false);
    setTimeLeft(null);
  }

  // Countdown timer
  useEffect(() => {
    if (!timeLeft) return;

    const intervalId = setInterval(() => {
      setTimeLeft((prev) => {
        if (!prev || prev <= 1000) {
          handleLogout();
          return null;
        }
        return prev - 1000;
      });
    }, 1000);

    return () => clearInterval(intervalId);
  }, [timeLeft]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-8">Mini Games</h1>

        {!loggedIn ? (
          <form
            onSubmit={handleLogin}
            className="flex flex-col gap-4 w-64 mb-10 bg-white p-6 rounded shadow"
          >
            <input
              className="p-2 border rounded"
              placeholder="Username"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <input
              className="p-2 border rounded"
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <button className="p-2 bg-blue-600 text-white rounded hover:bg-blue-700">
              Log In
            </button>
            <button
              type="button"
              className="p-2 bg-green-600 text-white rounded hover:bg-green-700 mt-2"
              onClick={() => (window.location.href = "http://localhost:8000/profile/create")}>
              Create User
            </button>
          </form>
        ) : (
          <div className="mb-10 text-center">
            <p className="text-green-600 font-semibold mb-2">
              Logged in as {name}!
              {timeLeft !== null && (
                <span className="block text-gray-700 text-sm mt-1">
                  Session expires in: {formatTime(timeLeft)}
                </span>
              )}
            </p>
            <button
              onClick={handleLogout}
              className="p-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              Log Out
            </button>
          </div>
        )}

        <div className="flex flex-col gap-4 items-center">
          <Link
            to="/memory-game"
            className="w-64 whitespace-nowrap px-8 py-4 bg-pink-600 text-white rounded-lg text-xl font-semibold text-center hover:bg-pink-700"
          >
            Play Memory Game
          </Link>

          <Link
            to="/trivia-game"
            className="w-64 whitespace-nowrap px-8 py-4 bg-green-600 text-white rounded-lg text-xl font-semibold text-center hover:bg-green-700"
          >
            Play Trivia Game
          </Link>

          <Link
            to="/stats"
            className="w-64 whitespace-nowrap px-8 py-4 bg-indigo-600 text-white rounded-lg text-xl font-semibold text-center hover:bg-indigo-700"
          >
            View My Stats
          </Link>

          <a
            href="http://localhost:8000"
            className="w-64 whitespace-nowrap px-8 py-4 bg-purple-600 text-white rounded-lg text-xl font-semibold text-center hover:bg-purple-700"
          >
            View Leaderboard
          </a>

          <a
            href="http://localhost:8000/profile/friends"
            className="w-64 whitespace-nowrap px-8 py-4 bg-sky-400 text-white rounded-lg text-xl font-semibold text-center hover:bg-sky-400"
          >
            Manage Friends
          </a>
          
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
        <Route path="/stats" element={<GameStats />} />
      </Routes>
    </BrowserRouter>
  );
}