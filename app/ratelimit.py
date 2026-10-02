import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.config import get_settings


class SlidingWindowLimiter:
    """Janela deslizante em memória (1 processo). Em produção: Redis / gateway."""

    def __init__(self) -> None:
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window: int) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self.hits[key]
            while q and now - q[0] > window:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True

    def reset(self) -> None:
        self.hits.clear()


limiter = SlidingWindowLimiter()


def rate_limit(scope: str):
    """Dependência: limite por IP, diferenciado por rota sensível (login 5/min, M2M 20/min)."""

    def dep(request: Request) -> None:
        s = get_settings()
        limit = s.login_rate_limit if scope == "login" else s.m2m_rate_limit
        ip = request.client.host if request.client else "desconhecido"
        if not limiter.allow(f"{scope}:{ip}", limit, s.login_rate_window_seconds):
            raise HTTPException(
                429, "Muitas tentativas. Aguarde.", headers={"Retry-After": str(s.login_rate_window_seconds)}
            )

    return dep
