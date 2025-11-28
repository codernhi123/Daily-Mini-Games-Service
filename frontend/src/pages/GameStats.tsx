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
  game_type: string;
  score: number;
  played_at: string;
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
              {data.map((record) => (
                <tr key={record.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {new Date(record.played_at).toLocaleDateString()} at{" "}
                    {new Date(record.played_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-blue-600">
                    {record.score}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

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
          api.get<CanPlayResponse>(
            `/v2/games/memory/can_play/${user.id}`
          ),
          api.get<CanPlayResponse>(
            `/v2/games/trivia/can_play/${user.id}`
          ),
          api.get<GameHistory[]>(
            `/v2/games/memory/history/${user.id}`
          ),
          api.get<GameHistory[]>(
            `/v2/games/trivia/history/${user.id}`
          ),
        ]);

        setMemoryState(memRes.data);
        setTriviaState(trivRes.data);
        setMemoryHistory(memHistRes.data);
        setTriviaHistory(trivHistRes.data);
      } catch (err: any) {
        console.error("Failed to load game state", err);
        setError(
          err.response?.data?.detail ||
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

        {/* History placeholder */}
        <HistoryTable title="Memory Game History" data={memoryHistory} />
        <HistoryTable title="Trivia Game History" data={triviaHistory} />

      </div>
    </GameLayout>
  );
}