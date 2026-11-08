"""Слово дня і тема дня (генеруються ШІ один раз на день і зберігаються в базі)."""
import random
from datetime import date

import ai
import db
import prompts
from utils import esc

# Без випадкової теми й літери ШІ щодня обирає те саме слово, навіть якщо дата в запиті інша
THEMES = ["work and career", "travel", "food", "health", "emotions", "technology", "nature", "money",
          "relationships", "education", "city life", "home", "sports", "art and culture", "science", "news and society"]
LETTERS = "abcdefghilmnoprstuw"
ATTEMPTS = 3


async def _daily(kind: str, make):
    today = date.today().isoformat()
    value = db.get_daily(kind, today)
    if value is None:
        db.save_daily(kind, today, await make())
        value = db.get_daily(kind, today)
    return value


async def _new_word() -> dict:
    used = {w["word"].strip().lower() for w in db.recent_daily("wod")}
    for _ in range(ATTEMPTS):
        word = await ai.ask_json(prompts.word_of_day(random.choice(THEMES), random.choice(LETTERS), sorted(used)))
        if word.get("word") and word["word"].strip().lower() not in used:
            return word
    raise ValueError("ШІ не зміг підібрати нове слово дня")


async def word_of_day() -> dict:
    return await _daily("wod", _new_word)


async def topic_of_day() -> str:
    return await _daily("topic", lambda: ai.ask(
        prompts.discussion_topic(random.choice(THEMES), db.recent_daily("topic", 30)), temperature=1.0))


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
