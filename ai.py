import json
import logging

import edge_tts
from groq import AsyncGroq
from openai import AsyncOpenAI

import config

log = logging.getLogger(__name__)

_groq: AsyncGroq | None = None
_entrim: AsyncOpenAI | None = None


def groq_client() -> AsyncGroq:
    global _groq
    if _groq is None:
        _groq = AsyncGroq(api_key=config.GROQ_API_KEY)
    return _groq


def chat_client() -> AsyncOpenAI | AsyncGroq:
    global _entrim
    if not config.ENTRIM_API_KEY:
        return groq_client()
    if _entrim is None:
        _entrim = AsyncOpenAI(api_key=config.ENTRIM_API_KEY, base_url=config.ENTRIM_BASE_URL)
    return _entrim


def _model_params(max_tokens: int) -> dict:
    params = {"model": config.CHAT_MODEL, "max_tokens": max_tokens}
    # gpt-oss і GLM "думають" перед відповіддю: робимо це коротко і даємо запас токенів
    if "gpt-oss" in config.CHAT_MODEL or "GLM" in config.CHAT_MODEL:
        params.update(reasoning_effort="low", max_tokens=max_tokens + 800)
    return params


async def chat(messages: list[dict], temperature: float = 0.7, max_tokens: int = 700) -> str:
    resp = await chat_client().chat.completions.create(
        messages=messages,
        temperature=temperature,
        **_model_params(max_tokens),
    )
    return (resp.choices[0].message.content or "").strip()


async def ask(prompt: str, system: str | None = None, **kwargs) -> str:
    messages = [{"role": "system", "content": system}] if system else []
    messages.append({"role": "user", "content": prompt})
    return await chat(messages, **kwargs)


async def ask_json(prompt: str) -> dict:
    """Запит, у відповідь на який ШІ повертає JSON-об'єкт."""
    resp = await chat_client().chat.completions.create(
        messages=[
            {"role": "system", "content": "You always answer with a single valid JSON object and nothing else."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.5,
        response_format={"type": "json_object"},
        **_model_params(900),
    )
    text = resp.choices[0].message.content or "{}"
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        log.warning("Не вдалося розібрати JSON: %s", text)
        return {}


async def transcribe(data: bytes, filename: str = "voice.ogg") -> str:
    """Голосове повідомлення -> текст (Whisper на Groq)."""
    result = await groq_client().audio.transcriptions.create(
        file=(filename, data),
        model=config.WHISPER_MODEL,
        language="en",
    )
    return (result.text or "").strip()


async def tts(text: str) -> bytes:
    """Текст -> mp3 (Microsoft Edge TTS, безкоштовно)."""
    communicate = edge_tts.Communicate(text, config.TTS_VOICE)
    audio = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
    return bytes(audio)
