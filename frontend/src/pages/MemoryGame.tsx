import {useState, useEffect} from 'react';
import {useNavigate} from 'react-router-dom';
import {api} from '../services/api';
import {useAuth} from '../hooks/useAuth';
import {GameLayout} from '../components/shared/GameLayout';
import { CountdownTimer } from '../components/shared/CountdownTimer';

interface ImageData {
    filename: string;
    x: number;
    y: number;
    size: number;
    color?: string;
    mirror?: boolean
}

export function MemoryGame() {
    const navigate = useNavigate();
    const {user} = useAuth();

    const [gameState, setGameState] = useState('ready');
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [level, setLevel] = useState(1);
    const [levelDescription, setLevelDescription] = useState('');
    const [score, setScore] = useState(0);
    const [question, setQuestion] = useState('');
    const [answer, setAnswer] = useState('');
    const [feedback, setFeedback] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    const [images, setImages] = useState<ImageData[]>([]);
    const [canvasWidth, setCanvasWidth] = useState(800);
    const [canvasHeight, setCanvasHeight] = useState(800);
    const [countdown, setCountdown] = useState(5);

		const [nextPlayTime, setNextPlayTime] = useState<string | null>(null);

    const startGame = async () => {
    try {
        	setIsLoading(true);

        	const response = await api.post('/v2/games/memory/start');
      	if (!response.data.can_play) {
        	setFeedback(response.data.message);
					setNextPlayTime(response.data.next_play_time || null);
        	setGameState('locked');
        	return;
      	}

      	setSessionId(response.data.session_id);
      	setLevel(response.data.level);
      	setLevelDescription(response.data.level_description);
      	setScore(0);

      	await displayCurrentLevel(response.data.session_id)

    }
    catch (error: any) {
      	alert('Failed to start the game: ' + (error.response?.data?.detail || error.message));
    }
    finally {
      	setIsLoading(false);
    }
	};

	const displayCurrentLevel = async (sid: string) => {
		try {
			const response = await api.post(`/v2/games/memory/display/${sid}`);
			const data = response.data;

			setImages(data.images);
			setCanvasWidth(data.canvas_width);
			setCanvasHeight(data.canvas_height);
			setQuestion(data.question);
			setLevel(data.level);
			setLevelDescription(data.level_description);
			setCountdown(data.display_duration);
			setGameState('displaying');
		}
		catch (error: any) {
			alert('Failed to start the game: ' + (error.response?.data?.detail || error.message));
			setGameState('ready');
		}
	};

	useEffect(() => {
		if (gameState === 'displaying' && countdown > 0) {
			const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
			return () => clearTimeout(timer);
		}
		else if (gameState === 'displaying' && countdown === 0) {
			setGameState('answering');
			setFeedback('');
		}
	}, [gameState, countdown]);

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

			setFeedback(result.message);
			setScore(result.score);

			if (result.game_over) {
				setScore(result.final_score);
				setGameState('complete');
			}
			else {
				setAnswer('')
				setLevel(result.current_level);
				setLevelDescription(result.level_description);

				setTimeout(async () => {
					await displayCurrentLevel(sessionId!);
				}, 2000);
			}
 
		}
		catch (error: any) {
			alert('Failed to start the game: ' + (error.response?.data?.detail || error.message));
			setGameState('ready');
		}
		finally {
      		setIsLoading(false);
    	}
	};

	const handleKeyPress = (e: React.KeyboardEvent) => {
		if (e.key === 'Enter' && !isLoading) {
			submitAnswer();
		}
	};

	if (gameState === 'ready') {
		return (
			<GameLayout title="Memory Challenge" onExit={() => navigate('/')} userId={user?.name}>
				<div className='text-center max-w-2xl mx-auto'>
					<h2 className='text-4xl font-bold mb-6'>Memory Challenge</h2>
					<div className='bg-blue-100 p-6 rounded-lg mb-8'>
						<h3 className='text-xl font-bold mb-4'>How To Play:</h3>
						<ol className='text-left space-y-2'>
						<li>1. Images will appear for 5 seconds</li>
						<li>2. Memorize how many of each image you see</li>
						<li>3. Next answer the question given</li>
						<li>4. Progress through 4 increasingly difficult levels</li>
						<li>5. Goodluck and press start when you are ready!</li>
						</ol>
					</div>
					{!user && (
						<div className='bg-yellow-100 p-4 rounded mb-6'>
							<p className='text-yellow-800'>
								WARNING! Playing as guest - score won't be saved to leaderboard
							</p>
							<button 
								onClick={() => navigate('/')}
								className='underline text-blue-600 hover:text-blue-800'>
									Login To Save Your Scores
								</button>
						</div>
					)}
					<button
						onClick={startGame}
						disabled={isLoading}
						className='px-12 py-4 bg-green-600 text-white rounded-lg text-2xl font-bold hover:bg-green-700 disabled:bg-gray-400'
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
				<div className='text-center'>
					<h2 className='text-3xl font-bold mb-4'>Already Played Today!</h2>
					<p className='text-xl mb-4'>{feedback}</p> 

					{nextPlayTime && (
						<div className='mb-8'>
							<CountdownTimer targetTime={nextPlayTime} />
						</div>
        	)}

					<button 
						onClick={() => navigate('/')}
						className='px-8 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700'>
							Back To Main Menu
						</button>
				</div>
			</GameLayout>
		);
	}

	if (gameState === 'displaying') {
		return (
			<GameLayout title="Memory Challenge" onExit={() => navigate('/')} showScore score={score} userId={user?.name}>
				<div className='text-center'>
					<h2 className='text-3xl font-bold mb-4'>Level {level}</h2>
					<p className='text-lg text-gray-600 mb-4'>{levelDescription}</p>
					
					{/* Countdown Timer */}
					<div className='text-6xl font-bold text-red-600 mb-4'>{countdown}</div>
					<p className='text-sm text-gray-600 mb-8'>Memorize The Images!</p>

					{/* Image Display Canvas */}
					<div 
						className='relative mx-auto bg-white border-4 border-gray-300 rounded-lg overflow-hidden'
						style={{width: canvasWidth, height: canvasHeight}}>
						
						{images.map((img, index) => (
							<img
								key={index}
								src={`/images/${img.filename}`}
								alt=""
								className='absolute object-contain'
								style={{
									left: img.x,
									top: img.y,
									width: img.size,
									height: img.size,
									transform: img.mirror ? 'scaleX(-1)' : 'none',
									mixBlendMode: 'darken',
									filter: img.color
										? `sepia(100%) saturate(300%) hue-rotate(${index * 45}deg) brightness(90%)` : 'none'


							
								}}
							/>
						))}
					</div>
				</div>
			</GameLayout>
		);
	}

	if (gameState === 'answering') {
		return (
			<GameLayout title="Memory Challenge" onExit={() => navigate('/')} showScore score={score} userId={user?.name}>
				<div className='text-center max-w-lg mx-auto'>
					<h2 className='text-2xl font-bold mb-2'>Level {level}</h2>
					<p className='text-sm text-gray-600 mb-8'>{levelDescription}</p>
					<div className='bg-gray-100 p-8 rounded-lg mb-8'>
						<p className='text-2xl font-bold mb-6'>{question}</p>
						<input
							type="number"
							value={answer}
							onChange={(e) => setAnswer(e.target.value)}
							onKeyPress={handleKeyPress}
							placeholder='?'
							className='text-5xl text-center p-4 border-4 border-blue-500 rounded-lg w-40 mb-6 focus:outline-none focus:border-blue-700'
							autoFocus
							disabled={isLoading}
						/>
						<button
							onClick={submitAnswer}
							disabled={isLoading || !answer.trim()}
							className='block w-full px-8 py-4 bg-green-600 text-white rounded-lg text-xl font-bold hover:bg-green-700 disabled:bg-gray-400'>
								{isLoading ? 'Submitting...' : 'Submit Answer'}
							</button>
					</div>
					
					{feedback && (
						<div className='bg-blue-100 p-4 rounded-lg'>
							<p className='text-lg'>{feedback}</p>
						</div>
					)}
				</div>
			</GameLayout>
		);
	}

	if (gameState === 'complete') {
		return (
			<GameLayout title="Memory Challenge" onExit={() => navigate('/')} userId={user?.name}>
				<div className='text-center'>
					<h2 className='text-4xl font-bold mb-4'> Congratulations! Game Complete! </h2>
					<div className='my-8'>
						<div className='text-7xl font-bold text-blue-600 mb-2'>{score}</div>
						<div className='text-2xl text-gray-600'>Out Of 100 Points</div>
					</div>

					<p className='text-xl mb-8'>{feedback}</p>
					{user? (
						<p className='text-green-600 font-bold mb-8'> Score Saved To Leaderboard!</p>) : (
							<div className='bg-yellow-100 p-4 rounded-lg mb-8'>
								<p className='text-yellow-800 mb-2'>
									Score Not Saved - in guest mode 
								</p>
								<button
									onClick={() => navigate('/login')}
									className='underline text-blue-600 hover:text-blue-800'>
									Login To Save Future Scores
								</button>
							</div>
					)}

					<div className='space-x-4'>
						{user && (
							<button
								onClick={() => window.location.href = 'http://localhost:8000'}
								className='px-8 py-3 bg-blue-600 text-white rounded-lg text-lg hover:bg-blue-700'>
								View Leaderboards
							</button>
						)}

						<button
							onClick={() => navigate('/')}
							className='px-8 py-3 bg-gray-600 text-white rounded-lg text-lg hover:bg-gray-700'>
							Main Menu
						</button>
					</div>
				</div>
			</GameLayout>
		);
	}
	return <div>Loading...</div>;
}
