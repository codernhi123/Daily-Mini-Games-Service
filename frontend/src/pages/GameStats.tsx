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

export default function GameStats() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [memoryState, setMemoryState] = useState<CanPlayResponse | null>(null);
  const [triviaState, setTriviaState] = useState<CanPlayResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // No logged-in user -> nothing to load
    if (!user?.id) return;

    const fetchStates = async () => {
      try {
        setLoading(true);
        setError(null);

        const [memRes, trivRes] = await Promise.all([
          api.get<CanPlayResponse>(
            `/v2/games/memory/can_play/${user.id}`
          ),
          api.get<CanPlayResponse>(
            `/v2/games/trivia/can_play/${user.id}`
          ),
        ]);

        setMemoryState(memRes.data);
        setTriviaState(trivRes.data);
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
        <div className="bg-gray-50 border border-dashed border-gray-300 rounded-lg p-6">
          <h3 className="text-xl font-semibold mb-2">
            Play History (Coming from backend)
          </h3>
          <p className="text-gray-600">
            Backend already stores history in <code>game_history</code>. Once an
            API endpoint is exposed (e.g.{" "}
            <code>/v2/games/history/&lt;game_type&gt;?days=30</code>) we can
            show your last 30 days of scores here.
          </p>
        </div>
      </div>
    </GameLayout>
  );
}