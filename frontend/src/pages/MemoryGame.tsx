// pages/MemoryGame.tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../hooks/useAuth';
import { GameLayout } from '../components/shared/GameLayout';

export function MemoryGame() {
  const navigate = useNavigate();
  const { user } = useAuth();  // Can be null for guests
  
  const [gameState, setGameState] = useState('ready');  // ready, locked, displaying, answering, complete
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [level, setLevel] = useState(1);
  const [levelDescription, setLevelDescription] = useState('');
  const [score, setScore] = useState(0);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [feedback, setFeedback] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const startGame = async () => {
    try {
      setIsLoading(true);
      
      // Start game (user?.id is undefined for guests)
      const response = await api.post('/v2/games/memory/start', null, {
        params: { user_id: user?.id }
      });
      
      if (!response.data.can_play) {
        setFeedback(response.data.message);
        setGameState('locked');
        return;
      }
      
      setSessionId(response.data.session_id);
      setLevel(response.data.level);
      setLevelDescription(response.data.level_description);
      setScore(0);
      
      // Immediately display first level
      await displayCurrentLevel(response.data.session_id);
      
    } catch (error: any) {
      alert('Failed to start game: ' + (error.response?.data?.detail || error.message));
    } finally {
      setIsLoading(false);
    }
  };
  
  const displayCurrentLevel = async (sid: string) => {
    try {
      setGameState('displaying');
      setFeedback('A window will open showing images for 5 seconds...');
      
      // This triggers Pygame window
      const response = await api.post(`/v2/games/memory/display/${sid}`);
      
      // After Pygame closes, show question
      setQuestion(response.data.question);
      setLevel(response.data.level);
      setLevelDescription(response.data.level_description);
      setGameState('answering');
      setFeedback('');
      
    } catch (error: any) {
      alert('Failed to display images: ' + (error.response?.data?.detail || error.message));
      setGameState('ready');
    }
  };
  
  const submitAnswer = async () => {
    if (!answer.trim()) {
      alert('Please enter an answer');
      return;
    }
    
    try {
      setIsLoading(true);
      
      const response = await api.post('/v2/games/memory/submit', {
        session_id: sessionId,
        answer: parseInt(answer)
      });
      
      const result = response.data;
      
      // Show feedback
      setFeedback(result.message);
      setScore(result.score);
      
      if (result.game_over) {
        // Game complete
        setGameState('complete');
      } else {
        // Next level
        setAnswer('');
        setLevel(result.current_level);
        setLevelDescription(result.level_description);
        
        // Wait 2 seconds to show feedback, then display next level
        setTimeout(async () => {
          await displayCurrentLevel(sessionId!);
        }, 2000);
      }
      
    } catch (error: any) {
      alert('Failed to submit answer: ' + (error.response?.data?.detail || error.message));
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isLoading) {
      submitAnswer();
    }
  };
  
  // --- RENDER STATES ---
  
  if (gameState === 'ready') {
    return (
      <GameLayout title="Memory Challenge" onExit={() => navigate('/')}>
        <div className="text-center max-w-2xl mx-auto">
          <h2 className="text-4xl font-bold mb-6">Memory Challenge</h2>
          
          <div className="bg-blue-100 p-6 rounded-lg mb-8">
            <h3 className="text-xl font-bold mb-4">How to Play:</h3>
            <ol className="text-left space-y-2">
              <li>1. A window will open showing images for 5 seconds</li>
              <li>2. Memorize how many of each type you see</li>
              <li>3. Answer the question in your browser</li>
              <li>4. Progress through 4 increasingly difficult levels</li>
            </ol>
          </div>
          
          {!user && (
            <div className="bg-yellow-100 p-4 rounded mb-6">
              <p className="text-yellow-800">
                ⚠️ Playing as guest - score won't be saved to leaderboard
              </p>
              <button 
                onClick={() => navigate('/login')} 
                className="underline text-blue-600 hover:text-blue-800"
              >
                Login to save your scores
              </button>
            </div>
          )}
          
          <button
            onClick={startGame}
            disabled={isLoading}
            className="px-12 py-4 bg-green-600 text-white rounded-lg text-2xl font-bold hover:bg-green-700 disabled:bg-gray-400"
          >
            {isLoading ? 'Starting...' : 'Start Game'}
          </button>
        </div>
      </GameLayout>
    );
  }
  
  if (gameState === 'locked') {
    return (
      <GameLayout title="Memory Challenge" onExit={() => navigate('/')}>
        <div className="text-center">
          <h2 className="text-3xl font-bold mb-4">Already Played Today!</h2>
          <p className="text-xl mb-8">{feedback}</p>
          <button 
            onClick={() => navigate('/')} 
            className="px-8 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
          >
            Back to Main Menu
          </button>
        </div>
      </GameLayout>
    );
  }
  
  if (gameState === 'displaying') {
    return (
      <GameLayout title="Memory Challenge" onExit={() => navigate('/')} showScore score={score}>
        <div className="text-center">
          <h2 className="text-3xl font-bold mb-4">Level {level}</h2>
          <p className="text-lg text-gray-600 mb-8">{levelDescription}</p>
          
          <div className="text-6xl mb-8 animate-pulse">👀</div>
          
          <div className="bg-blue-100 p-6 rounded-lg">
            <p className="text-xl">{feedback}</p>
            <p className="text-sm text-gray-600 mt-2">Watch the popup window carefully!</p>
          </div>
        </div>
      </GameLayout>
    );
  }
  
  if (gameState === 'answering') {
    return (
      <GameLayout title="Memory Challenge" onExit={() => navigate('/')} showScore score={score}>
        <div className="text-center max-w-lg mx-auto">
          <h2 className="text-2xl font-bold mb-2">Level {level}</h2>
          <p className="text-sm text-gray-600 mb-8">{levelDescription}</p>
          
          <div className="bg-gray-100 p-8 rounded-lg mb-8">
            <p className="text-2xl font-bold mb-6">{question}</p>
            
            <input
              type="number"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="?"
              className="text-5xl text-center p-4 border-4 border-blue-500 rounded-lg w-40 mb-6 focus:outline-none focus:border-blue-700"
              autoFocus
              disabled={isLoading}
            />
            
            <button
              onClick={submitAnswer}
              disabled={isLoading || !answer.trim()}
              className="block w-full px-8 py-4 bg-green-600 text-white rounded-lg text-xl font-bold hover:bg-green-700 disabled:bg-gray-400"
            >
              {isLoading ? 'Submitting...' : 'Submit Answer'}
            </button>
          </div>
          
          {feedback && (
            <div className="bg-blue-100 p-4 rounded-lg">
              <p className="text-lg">{feedback}</p>
            </div>
          )}
        </div>
      </GameLayout>
    );
  }
  
  if (gameState === 'complete') {
    return (
      <GameLayout title="Memory Challenge" onExit={() => navigate('/')}>
        <div className="text-center">
          <h2 className="text-4xl font-bold mb-4">🎉 Game Complete!</h2>
          
          <div className="my-8">
            <div className="text-7xl font-bold text-blue-600 mb-2">{score}</div>
            <div className="text-2xl text-gray-600">out of 70 points</div>
          </div>
          
          <p className="text-xl mb-8">{feedback}</p>
          
          {user ? (
            <p className="text-green-600 font-bold mb-8">✅ Score saved to leaderboard!</p>
          ) : (
            <div className="bg-yellow-100 p-4 rounded-lg mb-8">
              <p className="text-yellow-800 mb-2">
                ⚠️ Score not saved (guest mode)
              </p>
              <button 
                onClick={() => navigate('/login')} 
                className="underline text-blue-600 hover:text-blue-800"
              >
                Login to save future scores
              </button>
            </div>
          )}
          
          <div className="space-x-4">
            {user && (
              <button
                onClick={() => navigate('/leaderboards')}
                className="px-8 py-3 bg-blue-600 text-white rounded-lg text-lg hover:bg-blue-700"
              >
                View Leaderboards
              </button>
            )}
            <button
              onClick={() => navigate('/')}
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