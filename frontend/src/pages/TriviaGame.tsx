import {useEffect, useState} from "react";
import {useNavigate} from "react-router-dom";
import {api} from "../services/api";
import {useAuth} from "../hooks/useAuth";
import {GameLayout} from "../components/shared/GameLayout";
import {CountdownTimer} from "../components/shared/CountdownTimer";

type GameState = "ready" | "locked" | "question" | "feedback" | "complete";

interface TriviaQuestion {
  question_number: number;
  total_questions: number;
  question: string;
  choices: string[];
  difficulty: string;
  score: number;
  streak?: number;
  best_streak?: number;
}

export default function TriviaGame() {
  const navigate = useNavigate();
  const {user} = useAuth();
  console.log("user object:", user);
  const [gameState, setGameState] = useState<GameState>("ready");
  const [sessionId, setSessionId] = useState<string | null>(null);

  const [question, setQuestion] = useState<TriviaQuestion | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);

  const [score, setScore] = useState(0);
  const [feedback, setFeedback] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const [nextPlayTime, setNextPlayTime] = useState<string | null>(null);

  const [streak, setStreak] = useState(0);
  const [bestStreak, setBestStreak] = useState(0);
  const [maxScore, setMaxScore] = useState<number | null>(null);

  // Feedback-specific state
  const [lastCorrectIndex, setLastCorrectIndex] = useState<number | null>(null);
  const [wasLastCorrect, setWasLastCorrect] = useState<boolean | null>(null);
  const [explanation, setExplanation] = useState<string>("");

  const startGame = async () => {
    try {
      setIsLoading(true);

      const res = await api.post("/v2/games/trivia/start");

      if (!res.data.can_play) {
        setFeedback(res.data.message || "You already played today.");
        setNextPlayTime(res.data.next_play_time || null);
        setGameState("locked");
        return;
      }

      setSessionId(res.data.session_id);
      setScore(0);
      setFeedback("");
      setSelectedIndex(null);
      setStreak(0);
      setBestStreak(0);
      setMaxScore(null);
      setLastCorrectIndex(null);
      setWasLastCorrect(null);
      setExplanation("");

      await loadQuestion(res.data.session_id);
    } catch (err: any) {
      alert(
        "Failed to start trivia game: " +
          (err.response?.data?.detail || err.message),
      );
    } finally {
      setIsLoading(false);
    }
  };

  const loadQuestion = async (sid: string) => {
    try {
      const res = await api.get(`/v2/games/trivia/question/${sid}`);
      setQuestion(res.data);
      setScore(res.data.score);
      setSelectedIndex(null);
      setGameState("question");
      setFeedback("");
      setExplanation("");
      setLastCorrectIndex(null);
      setWasLastCorrect(null);

      if (typeof res.data.streak === "number") {
        setStreak(res.data.streak);
      }
      if (typeof res.data.best_streak === "number") {
        setBestStreak(res.data.best_streak);
      }
    } catch (err: any) {
      alert(
        "Failed to load question: " +
          (err.response?.data?.detail || err.message),
      );
      setGameState("ready");
    }
  };

  const submitAnswer = async () => {
    if (selectedIndex === null || !sessionId) return;

    try {
      setIsLoading(true);

      const res = await api.post("/v2/games/trivia/submit", {
        session_id: sessionId,
        answer_index: selectedIndex,
      });

      const data = res.data;

      setFeedback(data.message);
      setExplanation(data.explanation || "");
      if (typeof data.score === "number") setScore(data.score);
      if (typeof data.streak === "number") setStreak(data.streak);
      if (typeof data.best_streak === "number") setBestStreak(data.best_streak);
      if (typeof data.correct_index === "number")
        setLastCorrectIndex(data.correct_index);
      if (typeof data.is_correct === "boolean")
        setWasLastCorrect(data.is_correct);

      if (data.game_over) {
        setScore(data.final_score ?? data.score ?? 0);
        if (typeof data.max_score === "number") setMaxScore(data.max_score);
        setGameState("complete");
      } else {
        // Stay on this question, show feedback and highlighting
        setGameState("feedback");
      }
    } catch (err: any) {
      alert(
        "Failed to submit answer: " +
          (err.response?.data?.detail || err.message),
      );
      setGameState("question");
    } finally {
      setIsLoading(false);
    }
  };

  const handleChoiceClick = (i: number) => {
    if (isLoading || gameState === "feedback") return;
    setSelectedIndex(i);
  };

  const goToNextQuestion = () => {
    if (!sessionId) return;
    loadQuestion(sessionId);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (
        e.key === "Enter" &&
        gameState === "question" &&
        selectedIndex !== null
      ) {
        submitAnswer();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [gameState, selectedIndex]);

  const renderChoiceButtonClasses = (index: number) => {
    const base =
      "w-full px-6 py-4 rounded-lg text-lg border-2 transition";

    const isFeedback = gameState === "feedback";
    const isSelected = selectedIndex === index;

    if (!isFeedback) {
      // Normal question state
      return [
        base,
        isSelected
          ? "bg-blue-600 text-white border-blue-700"
          : "bg-white hover:bg-gray-50 border-gray-300",
      ].join(" ");
    }

    // Feedback state
    const isCorrectChoice = lastCorrectIndex === index;
    const isWrongSelected =
      isSelected && wasLastCorrect === false && !isCorrectChoice;

    if (isCorrectChoice) {
      return [
        base,
        "bg-green-600 text-white border-green-700",
      ].join(" ");
    }

    if (isWrongSelected) {
      return [
        base,
        "bg-red-600 text-white border-red-700",
      ].join(" ");
    }

    return [
      base,
      "bg-white border-gray-300 opacity-70",
    ].join(" ");
  };

  // READY
  if (gameState === "ready") {
    return (
      <GameLayout title="Trivia Challenge" onExit={() => navigate("/")} userId={user?.name}>
        <div className="text-center max-w-2xl mx-auto">
          <h2 className="text-4xl font-bold mb-6">Trivia Challenge</h2>

          <div className="bg-green-100 p-6 rounded-lg mb-8">
            <h3 className="text-xl font-bold mb-4">How To Play:</h3>
            <ol className="text-left space-y-2">
              <li>1. You&apos;ll get 5 multiple-choice questions.</li>
              <li>2. Each correct answer is worth 100 points.</li>
              <li>
                3. Streak bonus: +10 per streak level (2 in a row = +10, 3 in a
                row = +20, etc).
              </li>
              <li>4. Question set changes every day of the week.</li>
              <li>5. Logged-in users can play once per day.</li>
            </ol>
          </div>

          {!user && (
            <div className="bg-yellow-100 p-4 rounded mb-6">
              <p className="text-yellow-800">
                WARNING! Playing as guest — score won&apos;t be saved.
              </p>
              <button
                onClick={() => navigate("/")}
                className="underline text-blue-600 hover:text-blue-800"
              >
                Login To Save Your Scores
              </button>
            </div>
          )}

          <button
            onClick={startGame}
            disabled={isLoading}
            className="px-12 py-4 bg-green-600 text-white rounded-lg text-2xl font-bold hover:bg-green-700 disabled:bg-gray-400"
          >
            {isLoading ? "Starting..." : "Start Game"}
          </button>
        </div>
      </GameLayout>
    );
  }

  // LOCKED
  if (gameState === "locked") {
    return (
      <GameLayout title="Trivia Challenge" onExit={() => navigate("/")} userId={user?.name}>
        <div className="text-center">
          <h2 className="text-3xl font-bold mb-4">Already Played Today!</h2>
          <p className="text-xl mb-4">{feedback}</p>

          {nextPlayTime && (
            <div className="mb-8">
              <CountdownTimer targetTime={nextPlayTime} />
            </div>
          )}

          <button
            onClick={() => navigate("/")}
            className="px-8 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
          >
            Back To Main Menu
          </button>
        </div>
      </GameLayout>
    );
  }

  // QUESTION / FEEDBACK
  if ((gameState === "question" || gameState === "feedback") && question) {
    const isFeedback = gameState === "feedback";

    const subtitle = `Question ${question.question_number} of ${question.total_questions} • ${question.difficulty} • Streak: ${streak}`;

    return (
      <GameLayout
        title="Trivia Challenge"
        onExit={() => navigate("/")}
        showScore
        score={score}
        userId={user?.name}
        subtitle={subtitle}
      >
        <div className="text-center max-w-2xl mx-auto">
          <h2 className="text-2xl font-bold mb-6">{question.question}</h2>

          <div className="grid gap-3">
            {question.choices.map((c, i) => (
              <button
                key={i}
                onClick={() => handleChoiceClick(i)}
                disabled={isLoading || isFeedback}
                className={renderChoiceButtonClasses(i)}
              >
                {c}
              </button>
            ))}
          </div>

          {/* Submit or Next button */}
          {!isFeedback ? (
            <button
              onClick={submitAnswer}
              disabled={selectedIndex === null || isLoading}
              className="mt-6 w-full px-8 py-4 bg-green-600 text-white rounded-lg text-xl font-bold hover:bg-green-700 disabled:bg-gray-400"
            >
              {isLoading ? "Submitting..." : "Submit Answer"}
            </button>
          ) : (
            <button
              onClick={goToNextQuestion}
              className="mt-6 w-full px-8 py-4 bg-blue-600 text-white rounded-lg text-xl font-bold hover:bg-blue-700"
            >
              Next Question
            </button>
          )}

          <div className="mt-6 flex flex-col items-center space-y-2">
            <div className="text-lg">
              Current Streak:{" "}
              <span className="font-bold">
                {streak} {streak >= 2 ? "🔥" : ""}
              </span>
            </div>
            <div className="text-sm text-gray-600">
              Best Streak This Game:{" "}
              <span className="font-semibold">{bestStreak}</span>
            </div>
          </div>

          {(feedback || explanation) && (
            <div className="mt-6 bg-blue-100 p-4 rounded-lg text-left">
              {feedback && (
                <p className="text-lg mb-2">
                  <span className="font-semibold">Result: </span>
                  {feedback}
                </p>
              )}
              {explanation && (
                <p className="text-base text-gray-800">
                  <span className="font-semibold">Explanation: </span>
                  {explanation}
                </p>
              )}
            </div>
          )}
        </div>
      </GameLayout>
    );
  }

  // COMPLETE
  if (gameState === "complete") {
    return (
      <GameLayout title="Trivia Challenge" onExit={() => navigate("/")} userId={user?.name}>
        <div className="text-center">
          <h2 className="text-4xl font-bold mb-4">Game Complete!</h2>

          <div className="my-8">
            <div className="text-7xl font-bold text-green-600 mb-2">
              {score}
            </div>
            <div className="text-2xl text-gray-600">
              Out Of {maxScore ?? "?"} Points
            </div>
          </div>

          <p className="text-xl mb-4">{feedback}</p>

          {explanation && (
            <p className="text-base mb-4">
              <span className="font-semibold">Explanation: </span>
              {explanation}
            </p>
          )}

          <p className="text-lg mb-6">
            Best Streak This Game:{" "}
            <span className="font-bold">
              {bestStreak} {bestStreak >= 2 ? "🔥" : ""}
            </span>
          </p>

          {user ? (
            <p className="text-green-600 font-bold mb-8">
              Score Saved To Leaderboard!
            </p>
          ) : (
            <div className="bg-yellow-100 p-4 rounded-lg mb-8">
              <p className="text-yellow-800 mb-2">
                Score Not Saved — guest mode
              </p>
              <button
                onClick={() => navigate("/login")}
                className="underline text-blue-600 hover:text-blue-800"
              >
                Login To Save Future Scores
              </button>
            </div>
          )}

          <div className="space-x-4">
            {user && (
              <button
                onClick={() => window.location.href = 'http://localhost:8000'}
                className="px-8 py-3 bg-blue-600 text-white rounded-lg text-lg hover:bg-blue-700"
              >
                View Leaderboards
              </button>
            )}

            <button
              onClick={() => navigate("/")}
              className="px-8 py-3 bg-gray-600 text-white rounded-lg text-lg hover:bg-gray-700"
            >
              Main Menu
            </button>
          </div>
        </div>
      </GameLayout>
    );
  }

  return <div>Loading...</div>;
}