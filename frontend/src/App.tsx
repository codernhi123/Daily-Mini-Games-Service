import {BrowserRouter, Routes, Route, Link} from 'react-router-dom';
import { MemoryGame } from './pages/MemoryGame';

function Home() {
  return (
    <div className='min-h-screen flex items-center justify-center bg-gray-100'>
      <div className='text-center'>
        <h1 className='text-4xl font-bold mb-8'>Mini Games</h1>
        <Link 
        to="/memory-game"
        className='px-8 py-4 bg-blue-600 text-white rounded-lg text-xl hover:bg-blue-700'>
          Play Memory Game 
        </Link>
      </div>
    </div>
  )
}


function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/memory-game" element={<MemoryGame />} />
      </Routes>
    </BrowserRouter>
  );
}
export default App;
