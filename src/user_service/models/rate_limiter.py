import time
from typing import Dict, Optional, Tuple
from fastapi import Request, HTTPException
from dataclasses import dataclass

@dataclass
class RateLimitWindow:
    count: int
    window_start: float

class RateLimiter:
    window_size = 10
    anynomous_limit = 1

    def __init__(self):
        self.authenticated_windows: Dict[int, RateLimitWindow] = {}

        self.unauthenticated_windows: Dict[str, RateLimitWindow] = {}

    def _new_window(self, window_start: float) -> bool:
        current_time = time.time()
        elapsed = current_time - window_start
        return elapsed >= self.window_size
    
    def check_authenticated_limit(self, id: int, tier: int) -> bool:
        limit = 2*tier
        current_time = time.time()

        if id not in self.authenticated_windows:
            self.authenticated_windows[id] = RateLimitWindow(count=1, window_start=current_time)
            return True
        window = self.authenticated_windows[id]

        if self._new_window(window.window_start):
            self.authenticated_windows[id] = RateLimitWindow(count=1,window_start=current_time)
            return True
        
        if window.count >= limit:
            return False
        
        window.count += 1
        return True

    
    def check_unauthenticated_limit(self, address: str) -> bool:
        current_time = time.time()

        if address not in self.unauthenticated_windows:
            self.unauthenticated_windows[address] = RateLimitWindow(count=1, window_start=current_time)
            return True
        window = self.unauthenticated_windows[address]

        if self._new_window(window.window_start):
            self.unauthenticated_windows[address] = RateLimitWindow(count=1,window_start=current_time)
            return True
        
        if window.count >= self.anynomous_limit:
            return False
        
        window.count += 1
        return True
    
    def cleanup_windows(self):
        current_time = time.time()

        self.authenticated_windows = {
            id: window
            for id, window in self.authenticated_windows.items()
            if (current_time - window.window_start) < self.window_size
        }

        self.unauthenticated_windows = {
            address: window
            for address, window in self.unauthenticated_windows.items()
            if (current_time - window.window_start) < self.window_size
        }

rate_limiter = RateLimiter()

def extract_user_JWT(request: Request) -> Optional[Tuple[int, int]]:
    return None

async def check_rate_limiter(request: Request):
    user = extract_user_JWT(request)

    if user:
        id, tier = user

        if not rate_limiter.check_authenticated_limit(id, tier):
            raise HTTPException(status_code=429, detail=None)
        
    else:
        client_address = request.client.host

        if not rate_limiter.check_unauthenticated_limit(client_address):
            raise HTTPException(status_code=429, detail=None)
        
def temp_JWT_test(id: int, tier: int):
    global extract_user_JWT
    def mock_extract_user_JWT(request: Request):
        return (id, tier)
    
    extract_user_JWT = mock_extract_user_JWT

