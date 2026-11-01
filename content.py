"""Статичний контент: рівні, сценарії, теми граматики, тест рівня."""

LEVELS = {
    "A1": "A1 — Beginner",
    "A2": "A2 — Elementary",
    "B1": "B1 — Intermediate",
    "B2": "B2 — Upper-Intermediate",
    "C1": "C1 — Advanced",
}

CORRECTION_MODES = {
    "all": "усі помилки",
    "major": "тільки грубі",
    "none": "не виправляти",
}

# key: (назва кнопки, опис ролі для ШІ)
SCENARIOS = {
    "cafe": ("☕ У кафе", "You are a friendly barista in a busy coffee shop in London. The learner is a customer ordering drinks and food."),
    "airport": ("✈️ Аеропорт", "You are a check-in agent at an international airport. The learner is a passenger checking in for a flight."),
    "hotel": ("🏨 Готель", "You are a hotel receptionist. The learner is a guest checking in and asking about the hotel."),
    "shop": ("🛍 Магазин одягу", "You are a shop assistant in a clothes shop. The learner wants to buy something."),
    "doctor": ("🩺 У лікаря", "You are a doctor. The learner is a patient who doesn't feel well and describes symptoms."),
    "directions": ("🗺 Спитати дорогу", "You are a friendly local in New York. The learner is a tourist asking for directions."),
    "smalltalk": ("🗣 Small talk", "You are a friendly stranger at a party. Make casual small talk with the learner."),
    "friend": ("🎉 Знайомство", "You are a new international student at a university, meeting the learner for the first time."),
    "interview": ("💼 Співбесіда", "You are an HR manager conducting a job interview. First ask which position the learner is applying for, then ask typical interview questions one by one."),
    "presentation": ("🎤 Презентація", "You are a teacher listening to the learner's project presentation. First ask what the project is about, then ask follow-up questions like a real audience."),
    "negotiation": ("🤝 Переговори", "You are a business partner negotiating the price and terms of a contract with the learner. Be polite but firm."),
    "conflict": ("😤 Вирішення конфлікту", "You are a colleague who is upset because the learner missed a deadline that affected your work. Let the learner practise calming the situation and finding a solution."),
}

# key: (назва теми, рівень)
GRAMMAR = {
    "present_simple": ("Present Simple", "A1"),
    "present_continuous": ("Present Continuous", "A1"),
    "past_simple": ("Past Simple", "A2"),
    "future": ("Future: will / going to", "A2"),
    "articles": ("Артиклі a / an / the", "A2"),
    "comparatives": ("Ступені порівняння", "A2"),
    "present_perfect": ("Present Perfect", "B1"),
    "modals": ("Модальні дієслова", "B1"),
    "conditionals": ("Умовні речення (0–3)", "B1"),
    "passive": ("Пасивний стан", "B1"),
    "past_perfect": ("Past Perfect", "B2"),
    "reported": ("Непряма мова", "B2"),
    "gerund_inf": ("Герундій чи інфінітив", "B2"),
    "phrasal": ("Фразові дієслова", "B2"),
}

# (питання, варіанти, індекс правильної відповіді)
PLACEMENT_TEST = [
    ("She ___ a teacher.", ["am", "is", "are", "be"], 1),
    ("I ___ coffee every morning.", ["drink", "drinks", "drinking", "am drink"], 0),
    ("There ___ two cats in the garden.", ["is", "be", "are", "am"], 2),
    ("Yesterday we ___ to the cinema.", ["go", "goes", "gone", "went"], 3),
    ("He is ___ than his brother.", ["tall", "taller", "tallest", "more tall"], 1),
    ("I have lived here ___ 2015.", ["for", "from", "since", "during"], 2),
    ("If it rains tomorrow, we ___ at home.", ["will stay", "stay", "would stay", "stayed"], 0),
    ("The letter ___ by my grandmother.", ["wrote", "was written", "has write", "is writing"], 1),
    ("I'm looking forward ___ you.", ["to see", "seeing", "see", "to seeing"], 3),
    ("If I ___ rich, I would travel the world.", ["am", "will be", "were", "be"], 2),
    ("She suggested ___ a taxi.", ["taking", "to take", "take", "took"], 0),
    ("Hardly ___ the house when it started to rain.", ["I had left", "I left", "had I left", "did I leave"], 2),
]


def level_by_score(score: int) -> str:
    if score <= 3:
        return "A1"
    if score <= 6:
        return "A2"
    if score <= 8:
        return "B1"
    if score <= 10:
        return "B2"
    return "C1"
