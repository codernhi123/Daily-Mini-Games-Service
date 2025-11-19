import { useEffect, useState } from 'react';

interface CountdownTimerProps {
  targetTime: string; // ISO string, e.g. "2025-11-14T00:00:00Z"
}

export function CountdownTimer({ targetTime }: CountdownTimerProps) {
  const target = new Date(targetTime).getTime();
  const [remainingMs, setRemainingMs] = useState(target - Date.now());

  useEffect(() => {
    const id = setInterval(() => {
      setRemainingMs(target - Date.now());
    }, 1000);
    return () => clearInterval(id);
  }, [target]);

  if (remainingMs <= 0) {
    return (
      <p className="text-xl text-green-700">
        A new daily game should now be available. Try refreshing!
      </p>
    );
  }

  const totalSeconds = Math.floor(remainingMs / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  return (
    <p className="text-xl">
      Next game in{' '}
      <span className="font-bold">
        {hours}h {minutes}m {seconds}s
      </span>
    </p>
  );
}
