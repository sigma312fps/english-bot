"""Лічильники порушень у груповому чаті: мова і спам смайликами/стікерами."""
import time
from collections import defaultdict, deque

# --- Мова ---
WARNINGS_BEFORE_MUTE = 2          # перші 2 порушення — лише попередження
LANG_MUTES = [1, 3, 5]            # далі мут: 1 хв, 3 хв, потім щоразу 5 хв
LANG_RESET_SEC = 30 * 60          # якщо 30 хв без порушень — лічильник обнуляється

# --- Спам смайликами / стікерами ---
SPAM_WINDOW_SEC = 20              # вікно, у якому рахуємо смайлики/стікери
SPAM_FREE = 4                     # стільки підряд можна без питань
SPAM_MUTE_AT = 7                  # на 7-му — мут
SPAM_MUTES = [2, 5]               # перший мут за спам 2 хв, далі 5 хв
SPAM_RESET_SEC = 30 * 60

_lang: dict[tuple[int, int], dict] = {}
_spam_times: dict[tuple[int, int], deque] = defaultdict(deque)
_spam_mutes: dict[tuple[int, int], dict] = {}


def language_violation(chat_id: int, user_id: int, now: float | None = None) -> tuple[int, int]:
    """Реєструє повідомлення не англійською. Повертає (номер порушення, хвилин муту або 0)."""
    now = now or time.time()
    key = (chat_id, user_id)
    state = _lang.get(key)
    if not state or now - state["last"] > LANG_RESET_SEC:
        state = {"count": 0, "last": now}
    state["count"] += 1
    state["last"] = now
    _lang[key] = state
    over = state["count"] - WARNINGS_BEFORE_MUTE
    minutes = 0 if over <= 0 else LANG_MUTES[min(over, len(LANG_MUTES)) - 1]
    return state["count"], minutes


def spam_hit(chat_id: int, user_id: int, now: float | None = None) -> tuple[str, int]:
    """Реєструє смайлик/стікер. Повертає дію: ("ok"|"warn"|"delete"|"mute", хвилин муту)."""
    now = now or time.time()
    key = (chat_id, user_id)
    times = _spam_times[key]
    times.append(now)
    while times and now - times[0] > SPAM_WINDOW_SEC:
        times.popleft()
    n = len(times)
    if n <= SPAM_FREE:
        return "ok", 0
    if n == SPAM_FREE + 1:
        return "warn", 0
    if n < SPAM_MUTE_AT:
        return "delete", 0
    times.clear()
    state = _spam_mutes.get(key)
    if not state or now - state["last"] > SPAM_RESET_SEC:
        state = {"count": 0, "last": now}
    state["count"] += 1
    state["last"] = now
    _spam_mutes[key] = state
    return "mute", SPAM_MUTES[min(state["count"], len(SPAM_MUTES)) - 1]
