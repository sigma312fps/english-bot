import html
import re

_CYRILLIC = re.compile(r"[а-яА-ЯіІїЇєЄґҐёЁ]")
_LATIN = re.compile(r"[a-zA-Z]")


def esc(value) -> str:
    return html.escape(str(value or ""))


def cut(text: str, limit: int = 4000) -> str:
    return text if len(text) <= limit else text[:limit] + "…"


def is_mostly_cyrillic(text: str) -> bool:
    cyr = len(_CYRILLIC.findall(text))
    lat = len(_LATIN.findall(text))
    return cyr >= 3 and cyr > lat
