"""Turn one hh.uz vacancy page into a Vacancy (no network here, so it is easy to test).

Two sources on the page, used in this order:
1. the schema.org JobPosting JSON-LD block (machine-readable, meant for search engines)
2. hh's data-qa attributes on the visible page (fallback)
"""
import html
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from bs4 import BeautifulSoup

# The search lists all vacancies of a role; we keep a page only when its title or key skills look
# like IT. Loose on purpose: the LLM's is_it_job flag makes the final decision.
IT_PATTERN = re.compile(
    r"develop|разработ|программист|dasturchi|engineer|инженер-программист|software|"
    r"devops|\bsre\b|\bqa\b|тестировщ|tester|analyst|аналитик|\bdata\b|\bml\b|"
    r"machine learning|\bai\b|python|java|kotlin|swift|golang|\bgo\b|php|laravel|\.net|c#|c\+\+|"
    r"node|react|vue|angular|frontend|front-end|backend|back-end|full.?stack|фронтенд|бэкенд|"
    r"\b1c\b|\b1с\b|android|\bios\b|flutter|mobile|web|веб|верстальщик|\bui\b|\bux\b|"
    r"системн\w* администратор|sysadmin|system administrator|network|сетев|security|"
    r"безопасност|архитектор|architect|\bdba\b|database|sql|bitrix|битрикс|\bit\b|айти|"
    r"product manager|project manager|scrum|team ?lead|тимлид|cto|техническ\w* директор|"
    r"help ?desk|техподдерж|technical support|computer vision|nlp|unity|game|"
    r"jira|confluence|\bsap\b|dynamics 365|системн\w* инженер|system engineer|tizim administrator|"
    r"менеджер продукта|продакт|\bmdm\b|anti-?fraud",
    re.IGNORECASE,
)


@dataclass
class Vacancy:
    title: str
    description: str
    salary: dict                      # from / to / currency / period / text / gross
    experience: Optional[str] = None
    skills: list = field(default_factory=list)
    posted_at: Optional[str] = None   # ISO, as on the page

    def looks_it(self) -> bool:
        return bool(IT_PATTERN.search(self.title) or IT_PATTERN.search(" ".join(self.skills)))

    def post_text(self) -> str:
        """One text shaped like a Telegram vacancy post (what users paste into the app), so the
        same extraction, label rule, dedupe and leakage guard work for both sources."""
        lines = [self.title]
        if self.experience:
            lines.append(f"Опыт работы: {self.experience}")
        if self.salary["text"]:
            lines.append(f"Зарплата: {self.salary['text']}")   # removed from model input by strip_salary
        if self.skills:
            lines.append("Навыки: " + ", ".join(self.skills))
        return "\n".join(lines + ["", self.description]).strip()


# --- salary line -----------------------------------------------------------------------------
# e.g. "от 3 000 000 до 10 000 000 so'm за месяц до вычета налогов", "от 300 до 400 $ на руки",
# "до 1 500 $", "2 000 $" (Uzbek pages: "dan" / "gacha").
_CURRENCIES = [("USD", r"\$|usd|долл"), ("UZS", r"so['ʻ’‘`]?m|сум|сўм|uzs"),
               ("RUB", r"₽|руб|rub"), ("EUR", r"€|eur|евро")]
_NUM = r"(\d[\d\s]*\d|\d)"


def _first_number(text, *patterns):
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return float(re.sub(r"\s", "", m.group(1)))
    return None


def parse_salary_text(text: str) -> dict:
    """from / to / currency / period from hh's salary line (None where it does not say)."""
    low = (text or "").lower().replace("\xa0", " ")
    lo = _first_number(low, r"(?:от|from)\s*" + _NUM, _NUM + r"\s*dan\b")
    hi = _first_number(low, r"(?:до|to|up to)\s*" + _NUM, _NUM + r"\s*gacha")
    if lo is None and hi is None:                       # a single number: "2 000 $"
        lo = _first_number(low, _NUM)
    currency = next((code for code, pat in _CURRENCIES if re.search(pat, low)), None)
    period = ("hour" if re.search(r"за час|soat", low) else "year" if re.search(r"за год|yil", low)
              else "month" if (lo or hi) else None)
    return {"from": lo, "to": hi, "currency": currency, "period": period}


def _is_gross(text: str) -> Optional[bool]:
    low = text.lower()
    if "на руки" in low or "after tax" in low:
        return False
    return ("до вычета" in low or "before tax" in low or ("soliq" in low and "oldin" in low)) or None


# --- page parts ------------------------------------------------------------------------------

def _html_to_text(node) -> str:
    """Description HTML -> plain text with line breaks for paragraphs and list items."""
    if isinstance(node, str):
        node = BeautifulSoup(node, "html.parser")
    for br in node.find_all("br"):
        br.replace_with("\n")
    for tag in node.find_all(["p", "li", "div", "h1", "h2", "h3", "h4"]):
        tag.insert_before("\n")
        if tag.name == "li":
            tag.insert(0, "- ")
    text = re.sub(r"[ \t\xa0]+", " ", node.get_text(""))
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def _json_ld_job(soup) -> dict:
    """The schema.org JobPosting block, if the page has one."""
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except json.JSONDecodeError:
            continue
        for item in data if isinstance(data, list) else [data]:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                return item
    return {}


def _number(x) -> Optional[float]:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _salary(ld: dict, line: Optional[str]) -> dict:
    """JSON-LD baseSalary first ({currency, value: {minValue, maxValue, unitText}}),
    else the numbers in the visible salary line."""
    sal = {"from": None, "to": None, "currency": None, "period": None, "text": line,
           "gross": _is_gross(line) if line else None}
    base = ld.get("baseSalary")
    if isinstance(base, dict) and base:
        value = base.get("value") or {}
        sal.update({"from": _number(value.get("minValue")) or _number(value.get("value")),
                    "to": _number(value.get("maxValue")), "currency": base.get("currency"),
                    "period": (value.get("unitText") or "").lower() or None})
    if line and sal["from"] is None and sal["to"] is None:
        sal.update(parse_salary_text(line))
    return sal


def _experience(soup, ld: dict) -> Optional[str]:
    node = soup.select_one('[data-qa="vacancy-experience"]')
    if node:
        return node.get_text(" ", strip=True)
    er = ld.get("experienceRequirements")
    if not er:
        return None
    months = er.get("monthsOfExperience") if isinstance(er, dict) else None
    return f"{int(months) // 12}+ years" if months else str(er)


def parse_vacancy(page: str) -> Vacancy:
    soup = BeautifulSoup(page, "html.parser")
    ld = _json_ld_job(soup)
    qa = lambda name: soup.select_one(f'[data-qa="{name}"]')

    title = html.unescape(ld.get("title") or "").strip()          # JSON-LD keeps &#x27; etc.
    if not title and qa("vacancy-title"):
        title = qa("vacancy-title").get_text(" ", strip=True)
    description = _html_to_text(ld["description"]) if ld.get("description") else ""
    if not description and qa("vacancy-description"):
        description = _html_to_text(qa("vacancy-description"))
    line = qa("vacancy-salary").get_text(" ", strip=True).replace("\xa0", " ") if qa("vacancy-salary") else None
    skills = [s.get_text(" ", strip=True) for s in soup.select('[data-qa="skills-element"]')]
    if not skills and ld.get("skills"):
        skills = [s.strip() for s in re.split(r",|\n", str(ld["skills"])) if s.strip()]

    return Vacancy(title=title, description=description, salary=_salary(ld, line),
                   experience=_experience(soup, ld), skills=skills, posted_at=ld.get("datePosted"))


def to_utc(iso: Optional[str]) -> Optional[str]:
    try:
        dt = datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.replace(tzinfo=dt.tzinfo or timezone.utc).astimezone(timezone.utc).isoformat(timespec="seconds")
