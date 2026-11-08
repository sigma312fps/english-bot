"""Промпти для ШІ."""
import json

from content import GRAMMAR, SCENARIOS

CORRECTIONS_MARK = "###"

_LEVEL_STYLE = {
    "A1": "Use very simple words and very short sentences (Present Simple mostly).",
    "A2": "Use simple everyday vocabulary and short sentences.",
    "B1": "Use common vocabulary and natural, medium-length sentences.",
    "B2": "Speak naturally, you may use idioms and phrasal verbs sometimes.",
    "C1": "Speak like a native speaker, use rich vocabulary and idioms.",
}

_CORRECTION_RULE = {
    "all": "Correct ALL grammar, vocabulary and spelling mistakes in the learner's LAST message.",
    "major": "Correct only serious mistakes in the learner's LAST message (basic grammar, wrong words). Ignore small typos, capitalization and punctuation.",
    "none": f"Never correct mistakes and never add the {CORRECTIONS_MARK} block.",
}


def tutor_system(user: dict, voice: bool = False) -> str:
    scenario = SCENARIOS.get(user.get("scenario") or "")
    if scenario:
        role = (f"ROLE-PLAY: {scenario[1]} Stay in character the whole time, "
                "drive the scene forward and react naturally to what the learner says.")
    else:
        role = ("You are Emma, a friendly English conversation partner. Chat about anything: hobbies, "
                "studies, films, travel, daily life. Show interest in the learner and ask follow-up questions.")
    voice_note = ("The learner's message was transcribed from speech, so ignore punctuation and "
                  "capitalization; correct only spoken grammar and word choice.") if voice else ""
    return f"""You are an English tutor inside a Telegram bot for Ukrainian learners.
Learner level: {user.get('level', 'A2')}. {_LEVEL_STYLE.get(user.get('level'), '')}
{role}

Rules:
- Your reply is YOUR OWN turn in the conversation: react to what the learner said (answer their
  question, share something about yourself, show interest) and keep the conversation going.
  NEVER repeat, rephrase or rewrite the learner's message in your reply — corrections go ONLY
  into the corrections block below.
- Reply in English only. Keep it short: 1-4 sentences, like a real chat. Usually end with a question.
- If the learner writes in Ukrainian, kindly ask them to try in English and show how to say it in English.
- {_CORRECTION_RULE.get(user.get('correction', 'all'))}
- This is a casual chat: informal abbreviations and slang that native speakers really use
  (gf, bf, bro, u, ur, pls, thx, btw, idk, lol, gonna, wanna, gotta, kinda, etc.), missing capital
  letters and missing final punctuation are NOT mistakes — never correct them.
{voice_note}

Answer format:
<your reply in English>
If the learner's last message had mistakes, add a new line with exactly "{CORRECTIONS_MARK}" and then
one line per mistake in this form:
❌ wrong phrase → ✅ correct phrase — коротке пояснення українською
If there were no mistakes, do NOT write "{CORRECTIONS_MARK}" at all. No markdown (no ** or #).

Example:
Learner: I was been in Lviv last summer, it was very beautiful
You:
Oh, Lviv is lovely! What did you like the most there — the old town or the coffee?
{CORRECTIONS_MARK}
❌ I was been in Lviv → ✅ I was in Lviv — у Past Simple достатньо «was», «been» тут зайве"""


TUTOR_REMINDER = (
    "Now write your next turn. Respond to the MEANING of the learner's last message like a real "
    "conversation partner (e.g. if they tell you what they did, react and ask about it). Do NOT repeat "
    f"or correct their sentence in your reply — corrections only after the \"{CORRECTIONS_MARK}\" line."
)


def scenario_opening() -> str:
    return "(Start the role-play now: greet me and say your first line in character.)"


def summary(history: list[dict], level: str) -> str:
    dialog = "\n".join(f"{'Learner' if h['role'] == 'user' else 'Tutor'}: {h['content']}" for h in history)
    return f"""Here is a conversation between an English learner (level {level}) and a tutor:

{dialog}

Analyse ONLY the learner's messages and return JSON:
{{
  "score": <integer 1-10, how well the learner communicated for their level>,
  "feedback": "<2-4 sentences of feedback in Ukrainian: what was good and what to improve>",
  "mistakes": ["<typical mistake: wrong → correct (пояснення українською)>", ...up to 4],
  "words": [{{"word": "<useful English word or phrase for this topic>", "translation": "<Ukrainian>", "example": "<short English example>"}}, ...exactly 5]
}}"""


def enrich_word(text: str, level: str) -> str:
    return f"""A Ukrainian learner (level {level}) wants to add this to their English vocabulary: "{text}".
If it is in Ukrainian, translate it into English first. If it has a typo, fix it.
Return JSON:
{{
  "word": "<English word or phrase, lowercase unless it is a proper noun>",
  "transcription": "<IPA transcription, like /ˈwɔːtə/>",
  "translation": "<1-3 Ukrainian translations separated by commas>",
  "example": "<one simple natural English example sentence>",
  "example_uk": "<Ukrainian translation of the example>"
}}
If it is not a real word or phrase, return {{"error": "<коротке пояснення українською>"}}."""


def check_sentence(word: str, translation: str, sentence: str) -> str:
    return f"""A Ukrainian learner had to write an English sentence using the word "{word}" ({translation}).
Their sentence: "{sentence}"
Answer in Ukrainian, plain text without markdown, max 5 lines:
first line "✅ Чудово!" or "⚠️ Майже!" or "❌ Не зовсім.",
then a short explanation of mistakes (if any) and how the word is used,
then a line "✍️ Правильно: <corrected English sentence>"."""


def grammar_explain(topic_key: str, level: str) -> str:
    name, _ = GRAMMAR[topic_key]
    return f"""Explain the English grammar topic "{name}" to a Ukrainian learner of level {level}.
Write in Ukrainian with English examples. Plain text with emoji, NO markdown symbols (no **, no #).
Structure:
📌 Коли вживається
🧩 Як утворюється (формули для +, -, ?)
💡 4-5 прикладів з перекладом
⚠️ Типові помилки українців
Maximum 1500 characters."""


def grammar_exercise(topic_key: str, level: str) -> str:
    name, _ = GRAMMAR[topic_key]
    return f"""Create an exercise on the English grammar topic "{name}" for level {level}.
Write a short instruction in Ukrainian, then 5 numbered English sentences with a gap "___"
and the base form of the verb/word in brackets where needed. Do NOT give the answers.
Plain text, no markdown."""


def grammar_check(topic_key: str, exercise: str, answers: str) -> str:
    name, _ = GRAMMAR[topic_key]
    return f"""Grammar topic: {name}.
Exercise:
{exercise}

Learner's answers:
{answers}

Check each answer. Reply in Ukrainian, plain text, no markdown:
for each item one line: "1. ✅" or "1. ❌ правильно: <answer> — коротке пояснення".
Last line: "Результат: X/5" and a short encouraging phrase."""


def word_of_day(theme: str, letter: str, used: list[str]) -> str:
    return f"""Pick one useful, interesting English word for B1-B2 learners (avoid very common words).
It should be related to the theme "{theme}" and start with the letter "{letter}".
Do not pick any of these words: {", ".join(used) or "none"}.
Return JSON:
{{"word": "...", "transcription": "/.../", "translation": "<Ukrainian>", "example": "<English sentence>", "example_uk": "<Ukrainian translation>"}}"""


def discussion_topic(theme: str, used: list[str]) -> str:
    return (f'Give ONE interesting discussion question about "{theme}" for an English-learning group chat. '
            "It should be easy to answer for B1 learners and make people share opinions or stories. "
            f"It must be different from these earlier questions: {' | '.join(used) or 'none'}. "
            "Reply with just the question and one relevant emoji, nothing else.")


def translate_to_english(text: str) -> str:
    return ("Translate this message into natural, simple English. Reply with the translation only, "
            f"no quotes, no comments:\n{text}")


def to_json(data) -> str:
    return json.dumps(data, ensure_ascii=False)
