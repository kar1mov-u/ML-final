"""Text cleaning rules.

1. scrub_pii(text)     -> applied BEFORE anything is stored. Removes phone numbers, e-mails,
                          @usernames and links (handbook: never store personal data we don't need).
2. normalize(text)     -> lower-case, collapse spaces; used for duplicate detection.
3. strip_salary(text)  -> applied to the MODEL INPUT at training AND serving time, so the salary
                          model cannot read the answer from the text (leakage guard).
"""
import hashlib
import re

# --- 1. personal data --------------------------------------------------------

# Uzbek phones: +998 90 123 45 67, 998901234567, (90) 123-45-67, 90 123 45 67
_PHONE = re.compile(
    r"(?:\+?998[\s\-()]*)?\(?\d{2}\)?[\s\-]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}(?!\d)"
)
# catch-all for malformed/truncated numbers that still start with +998 ("+998 99 491 28")
_PHONE_LOOSE = re.compile(r"\+\s?998[\d\s\-()]*\d")
# also catches "name@gmail. com" (space before/after the dot)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\s?\.\s?[\w-]+)+")
_URL = re.compile(r"(?:https?://|www\.|t\.me/)\S+", re.IGNORECASE)
_HANDLE = re.compile(r"(?<![\w.])@[A-Za-z][\w]{3,}")
# Contact-person names: "Mas'ul: Azizbek", "Контактное лицо: Анна", "HR: Dilnoza"
# (the name may be on the same line or the next one).
_NAME_LINE = re.compile(
    r"(?im)^(\W*(?:mas['ʻ’`]?ul|xodim|aloqa uchun|контактное лицо|контакт|contact person|hr manager|hr)\s*:)[ \t]*\n?[ \t]*[^\n]+"
)

# Self-introductions typed into the app: "my name is Ali", "меня зовут Анна", "mening ismim Ali"
_SELF_NAME = re.compile(r"(?i)\b(my name is|меня зовут|mening ismim|ismim)\s+[\w'’-]+")


def scrub_pii(text: str) -> str:
    """Replace contacts with placeholders. Order matters: e-mails before @handles."""
    text = _NAME_LINE.sub(r"\1 [name]", text)
    text = _SELF_NAME.sub(r"\1 [name]", text)
    text = _EMAIL.sub("[email]", text)
    text = _URL.sub("[link]", text)
    text = _HANDLE.sub("[contact]", text)
    text = _PHONE.sub("[phone]", text)
    text = _PHONE_LOOSE.sub("[phone]", text)
    return text


# --- 2. normalisation for duplicate detection --------------------------------

def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"#\w+", " ", text)          # hashtags differ between channels
    text = re.sub(r"[^\w\s]", " ", text)       # punctuation / emoji
    return re.sub(r"\s+", " ", text).strip()


def text_hash(text: str) -> str:
    return hashlib.sha1(normalize(text).encode("utf-8")).hexdigest()


# --- 3. salary stripping (leakage guard) -------------------------------------

_CURRENCY = (
    r"\$|usd|у\.?е\.?|долл\w*|dollar\w*|€|eur\w*|евро|"
    r"uzs|сум\w*|сўм\w*|so['ʻ’‘`]?u?m\w*|sum\b|руб\w*|rub\w*|₽|"
    r"млн|mln|million\w*|миллион\w*|тыс\.?|ming|k\b|к\b"
)
# a number followed by a multiplier ("1.5 mln", "2k", "500 тыс")
_NUM_WITH_MULT = re.compile(r"\d+(?:[.,]\d+)?\s*(?:k|к|млн|mln|тыс\.?|ming|million\w*|миллион\w*)\b",
                            re.IGNORECASE)
# any number with 3+ digits, allowing thousand separators: 800, 1500, 1 500 000, 1,500.00
_BIG_NUM = re.compile(r"\d{1,3}(?:[  .,]\d{3})+(?:[.,]\d+)?|\d{3,}(?:[.,]\d+)?")
_CURRENCY_RE = re.compile(rf"(?:{_CURRENCY})", re.IGNORECASE)


def strip_salary(text: str) -> str:
    """Remove salary amounts and currency words. Small numbers (e.g. '3 years') are kept,
    because years of experience are a legitimate signal for level."""
    text = _NUM_WITH_MULT.sub(" ", text)
    text = _BIG_NUM.sub(" ", text)
    text = _CURRENCY_RE.sub(" ", text)
    return re.sub(r"[ \t]+", " ", text).strip()
