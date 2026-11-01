"""Слово дня і тема дня (генеруються ШІ один раз на день)."""
from datetime import date

import ai
import prompts
from utils import esc

_cache: dict[str, tuple[str, object]] = {}


async def _daily(kind: str, make):
    today = date.today().isoformat()
    cached = _cache.get(kind)
    if not cached or cached[0] != today:
        _cache[kind] = (today, await make(today))
    return _cache[kind][1]


async def word_of_day() -> dict:
    return await _daily("wod", lambda seed: ai.ask_json(prompts.word_of_day(seed)))


async def topic_of_day() -> str:
    return await _daily("topic", lambda seed: ai.ask(prompts.discussion_topic(seed), temperature=1.0))


def word_card(w: dict) -> str:
    text = f"<b>{esc(w.get('word'))}</b>"
    if w.get("transcription"):
        text += f"  {esc(w['transcription'])}"
    text += f"\n🇺🇦 {esc(w.get('translation'))}"
    if w.get("example"):
        text += f"\n\n📝 {esc(w['example'])}"
    if w.get("example_uk"):
        text += f"\n<i>{esc(w['example_uk'])}</i>"
    return text
