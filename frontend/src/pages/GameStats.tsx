import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../services/api";
import { useAuth } from "../hooks/useAuth";
import { GameLayout } from "../components/shared/GameLayout";
import { CountdownTimer } from "../components/shared/CountdownTimer";

type CanPlayResponse = {
  can_play: boolean;
  next_play_time?: string | null;
  message?: string;
};

type GameHistory = {
  id: number;
  game_type: string; // "Memory" | "Trivia"
  score: number;
  played_at: string; // ISO datetime
};

type DailyCell = {
  dateKey: string; // "YYYY-MM-DD"
  label: string;   // for display
  memoryScore: number | null;
  triviaScore: number | null;
  hasPlay: boolean;
  streakLength: number; // streak length ending on this day (0 if no play)
};

const HistoryTable = ({ title, data }: { title: string; data: GameHistory[] }) => {
  return (
    <div className="bg-white shadow rounded-lg p-6">
      <h3 className="text-2xl font-semibold mb-4">{title}</h3>
      {data.length === 0 ? (
        <p className="text-gray-500 italic">No game history found.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Score
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data.map((record) => {
                const d = new Date(record.played_at);
                return (
                  <tr key={record.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {d.toLocaleDateString()}{" "}
                      at{" "}
                      {d.toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-blue-600">
                      {record.score}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

// Build last 30 days of consistency data from histories
function buildConsistencyBoard(
  memoryHistory: GameHistory[],
  triviaHistory: GameHistory[]
): DailyCell[] {
  // Map dateKey -> { memoryScore?, triviaScore? }
  const byDate: Record<
    string,
    { memoryScore: number | null; triviaScore: number | null }
  > = {};

  const addRecord = (r: GameHistory) => {
    const d = new Date(r.played_at);
    // Normalize to local date string YYYY-MM-DD
    const dateKey = d.toISOString().slice(0, 10);
    if (!byDate[dateKey]) {
      byDate[dateKey] = { memoryScore: null, triviaScore: null };
    }
    if (r.game_type === "Memory") {
      // keep the best score per day for display
      if (
        byDate[dateKey].memoryScore === null ||
        r.score > (byDate[dateKey].memoryScore ?? 0)
      ) {
        byDate[dateKey].memoryScore = r.score;
      }
    } else if (r.game_type === "Trivia") {
      if (
        byDate[dateKey].triviaScore === null ||
        r.score > (byDate[dateKey].triviaScore ?? 0)
      ) {
        byDate[dateKey].triviaScore = r.score;
      }
    }
  };

  memoryHistory.forEach(addRecord);
  triviaHistory.forEach(addRecord);

  // Build last 30 days (including today)
  const today = new Date();
  const days: DailyCell[] = [];
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const dateKey = d.toISOString().slice(0, 10);
    const pretty = d.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
    const entry = byDate[dateKey];

    const memoryScore = entry?.memoryScore ?? null;
    const triviaScore = entry?.triviaScore ?? null;
    const hasPlay = memoryScore !== null || triviaScore !== null;

    days.push({
      dateKey,
      label: pretty,
      memoryScore,
      triviaScore,
      hasPlay,
      streakLength: 0, // fill later
    });
  }

  // Compute streaks: consecutive days with ANY play
  let currentStreak = 0;
  for (let i = 0; i < days.length; i++) {
    if (days[i].hasPlay) {
      currentStreak += 1;
      days[i].streakLength = currentStreak;
    } else {
      currentStreak = 0;
      days[i].streakLength = 0;
    }
  }

  return days;
}

export default function GameStats() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [memoryState, setMemoryState] = useState<CanPlayResponse | null>(null);
  const [triviaState, setTriviaState] = useState<CanPlayResponse | null>(null);
  const [memoryHistory, setMemoryHistory] = useState<GameHistory[]>([]);
  const [triviaHistory, setTriviaHistory] = useState<GameHistory[]>([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // No logged-in user -> nothing to load
    if (!user?.id) return;

    const fetchStates = async () => {
      try {
        setLoading(true);
        setError(null);

        const [memRes, trivRes, memHistRes, trivHistRes] = await Promise.all([
          api.get<CanPlayResponse>(`/v2/games/memory/can_play/${user.id}`),
          api.get<CanPlayResponse>(`/v2/games/trivia/can_play/${user.id}`),
          api.get<GameHistory[]>(`/v2/games/memory/history/${user.id}`),
          api.get<GameHistory[]>(`/v2/games/trivia/history/${user.id}`),
        ]);

        setMemoryState(memRes.data);
        setTriviaState(trivRes.data);
        setMemoryHistory(memHistRes.data);
        setTriviaHistory(trivHistRes.data);
      } catch (err: any) {
        console.error("Failed to load game state", err);
        setError(
          err?.response?.data?.detail ||
            "Failed to load game state. Please try again later."
        );
      } finally {
        setLoading(false);
      }
    };

    void fetchStates();
  }, [user?.id]);

  // If not logged in, tell them to go back and log in
  if (!user) {
    return (
      <GameLayout title="My Game Stats" onExit={() => navigate("/")}>
        <div className="text-center max-w-lg mx-auto">
          <h2 className="text-3xl font-bold mb-4">Login Required</h2>
          <p className="mb-6">
            You need to be logged in to view your game stats.
          </p>
          <button
            onClick={() => navigate("/")}
            className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Go To Login
          </button>
        </div>
      </GameLayout>
    );
  }

  const consistencyData = buildConsistencyBoard(memoryHistory, triviaHistory);
  const currentStreak =
    consistencyData.length > 0
      ? consistencyData[consistencyData.length - 1].streakLength
      : 0;
  const bestStreak = consistencyData.reduce(
    (max, d) => (d.streakLength > max ? d.streakLength : max),
    0
  );

  return (
    <GameLayout
      title="My Game Stats"
      onExit={() => navigate("/")}
      userId={user.name}
    >
      <div className="max-w-3xl mx-auto space-y-8">
        <h2 className="text-3xl font-bold text-center mb-2">
          Daily Play Status
        </h2>
        <p className="text-center text-gray-600 mb-6">
          See whether you can play each game today and when you&apos;ll be able
          to play again.
        </p>

        {/* Prompt the user to play if they haven't played yet today */}
        {!loading &&
          !error &&
          (memoryState?.can_play || triviaState?.can_play) && (
            <div className="mb-6 rounded-lg border border-indigo-300 bg-indigo-50 p-4 text-indigo-900">
              <p className="font-semibold mb-1">
                You haven&apos;t played today yet!
              </p>
              <p className="text-sm mb-3">
                {memoryState?.can_play && triviaState?.can_play
                  ? "Play a round of Memory and Trivia to log today’s scores."
                  : memoryState?.can_play
                  ? "Play a round of Memory to log today’s score."
                  : "Play a round of Trivia to log today’s score."}
              </p>

              <div className="flex flex-wrap gap-2">
                {memoryState?.can_play && (
                  <button
                    onClick={() => navigate("/memory-game")}
                    className="px-4 py-2 rounded bg-pink-600 text-white text-sm font-semibold hover:bg-pink-700"
                  >
                    Play Memory Game
                  </button>
                )}
                {triviaState?.can_play && (
                  <button
                    onClick={() => navigate("/trivia-game")}
                    className="px-4 py-2 rounded bg-green-600 text-white text-sm font-semibold hover:bg-green-700"
                  >
                    Play Trivia Game
                  </button>
                )}
              </div>
            </div>
          )}

        {loading && (
          <div className="text-center text-gray-600">Loading stats...</div>
        )}

        {error && (
          <div className="bg-red-100 text-red-800 p-4 rounded-lg mb-4">
            {error}
          </div>
        )}

        {/* Memory Game Card */}
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-2xl font-semibold mb-2">Memory Game</h3>
          <p className="text-gray-600 mb-4">
            Daily once-per-day limit based on your previous plays.
          </p>

          {memoryState ? (
            <>
              <p className="text-lg mb-2">
                Status:{" "}
                {memoryState.can_play ? (
                  <span className="text-green-600 font-semibold">
                    You can play today ✅
                  </span>
                ) : (
                  <span className="text-red-600 font-semibold">
                    You&apos;ve already played today ❌
                  </span>
                )}
              </p>

              {memoryState.message && (
                <p className="text-gray-700 mb-4">{memoryState.message}</p>
              )}

              {!memoryState.can_play && memoryState.next_play_time && (
                <div className="mt-4">
                  <p className="text-sm text-gray-600 mb-2">
                    Next play available in:
                  </p>
                  <CountdownTimer targetTime={memoryState.next_play_time} />
                </div>
              )}
            </>
          ) : (
            !loading && (
              <p className="text-gray-500 text-sm">
                No data yet. Start by playing a Memory Game round.
              </p>
            )
          )}
        </div>

        {/* Trivia Game Card */}
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-2xl font-semibold mb-2">Trivia Game</h3>
          <p className="text-gray-600 mb-4">
            Daily once-per-day limit based on your previous plays.
          </p>

          {triviaState ? (
            <>
              <p className="text-lg mb-2">
                Status:{" "}
                {triviaState.can_play ? (
                  <span className="text-green-600 font-semibold">
                    You can play today ✅
                  </span>
                ) : (
                  <span className="text-red-600 font-semibold">
                    You&apos;ve already played today ❌
                  </span>
                )}
              </p>

              {triviaState.message && (
                <p className="text-gray-700 mb-4">{triviaState.message}</p>
              )}

              {!triviaState.can_play && triviaState.next_play_time && (
                <div className="mt-4">
                  <p className="text-sm text-gray-600 mb-2">
                    Next play available in:
                  </p>
                  <CountdownTimer targetTime={triviaState.next_play_time} />
                </div>
              )}
            </>
          ) : (
            !loading && (
              <p className="text-gray-500 text-sm">
                No data yet. Start by playing a Trivia Game round.
              </p>
            )
          )}
        </div>

        {/* --- Monthly Consistency Board (Feature 7) --- */}
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-2xl font-semibold">
                Monthly Consistency Board
              </h3>
              <p className="text-gray-600 text-sm">
                Last 30 days of plays for Memory & Trivia. Empty squares mean no
                plays that day.
              </p>
            </div>
            <div className="text-right text-sm text-gray-700">
              <div>Current streak: {currentStreak} day(s)</div>
              <div>Best streak: {bestStreak} day(s)</div>
            </div>
          </div>

          <div className="mb-3 flex items-center gap-4 text-xs text-gray-600">
            <div className="flex items-center gap-1">
              <div className="w-4 h-4 rounded bg-gray-100 border border-dashed border-gray-300" />
              <span>No plays</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-4 h-4 rounded bg-green-300" />
              <span>Played (single day)</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-4 h-4 rounded bg-green-500" />
              <span>In a streak (2+ days)</span>
            </div>
          </div>

          <div className="grid grid-cols-7 gap-2">
            {consistencyData.map((day) => {
              const hasPlay = day.hasPlay;
              const inStreak = day.streakLength >= 2;

              const totalScore =
                (day.memoryScore ?? 0) + (day.triviaScore ?? 0);

              const titleLines = [
                `Date: ${day.dateKey}`,
                day.memoryScore !== null
                  ? `Memory: ${day.memoryScore}`
                  : "Memory: (no play)",
                day.triviaScore !== null
                  ? `Trivia: ${day.triviaScore}`
                  : "Trivia: (no play)",
                hasPlay ? `Total score: ${totalScore}` : "No games played",
                inStreak
                  ? `Streak: ${day.streakLength} day(s)`
                  : day.streakLength === 1
                  ? "Streak: 1 day"
                  : "",
              ].filter(Boolean);

              const title = titleLines.join("\n");

              const baseClasses =
                "w-8 h-8 rounded flex items-center justify-center text-[0.6rem] font-semibold cursor-default transition-colors";
              let colorClasses = "";
              if (!hasPlay) {
                colorClasses =
                  "bg-gray-100 border border-dashed border-gray-300 text-gray-300";
              } else if (inStreak) {
                colorClasses = "bg-green-500 text-white";
              } else {
                colorClasses = "bg-green-300 text-green-900";
              }

              return (
                <div
                  key={day.dateKey}
                  className={`${baseClasses} ${colorClasses}`}
                  title={title}
                >
                  {/* show day of month only */}
                  {day.label.split(" ")[1]}
                </div>
              );
            })}
          </div>
        </div>

        {/* Raw history tables (extra detail) */}
        <HistoryTable title="Memory Game History" data={memoryHistory} />
        <HistoryTable title="Trivia Game History" data={triviaHistory} />
      </div>
    </GameLayout>
  );
}
