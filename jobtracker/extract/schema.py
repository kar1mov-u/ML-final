"""What the LLM must return for every post, plus the extraction prompt.

The LLM is a DATA-CLEANING step: it turns messy posts (uz/ru/en, emoji, free format) into
the same fields every time. It never makes the prediction served to users.
Change anything here -> bump PROMPT_VERSION in config.py and note it in the experiment log.
"""
from typing import List, Literal, Optional

from pydantic import BaseModel

Level = Literal["intern", "junior", "middle", "senior", "lead", "unknown"]
Currency = Literal["USD", "UZS", "RUB", "EUR"]
Period = Literal["month", "year", "hour"]


class Extraction(BaseModel):
    is_job_post: bool                 # an employer looking for a worker (not ads, courses, job seekers)
    is_it_job: bool                   # software, data, QA, DevOps, design of digital products, IT PM ...
    title: Optional[str]              # job title in English, short ("Python Developer")
    level: Level
    level_evidence: Literal["title", "experience", "none"]
    years_experience_min: Optional[float]
    salary_min: Optional[float]       # numbers exactly as stated, expanded ("1.5 mln" -> 1500000)
    salary_max: Optional[float]
    currency: Optional[Currency]
    salary_period: Optional[Period]
    skills: List[str]                 # normalised tech names ("Python", "PostgreSQL", "React")
    work_format: Literal["office", "remote", "hybrid", "unknown"]
    city: Optional[str]
    language: Literal["uz", "ru", "en", "mixed"]


class PostExtraction(Extraction):
    """One item of the list Gemini returns: the fields above plus the id of the post they
    belong to (several posts are sent in one request)."""
    post_id: int


SYSTEM_PROMPT = """You extract structured data from job posts published in Uzbek Telegram channels.
Posts are in Uzbek (Latin or Cyrillic), Russian or English and are often informal.
Return only the fields of the schema. Extract what the post states; never guess numbers.

is_job_post: true only when an employer is looking for someone to hire. False for ads, courses,
events, internships programs without a job, news, and people looking for work.
is_it_job: true for software development, data/ML, QA, DevOps/SRE, security, UI/UX for digital
products, IT project/product management, IT support/sysadmin. False for sales, accounting,
teaching (unless teaching programming), call centres, marketing without a tech role.

title: the role in short English, e.g. "Python Developer", "QA Engineer", "Data Analyst".

level (one fixed rule, apply in this order):
1. If the title or text names the level, use it: intern/стажер/amaliyotchi -> intern;
   junior -> junior; middle -> middle; senior -> senior; lead/team lead/head/CTO -> lead.
   Set level_evidence = "title".
2. Otherwise use the required experience: under 1 year or "no experience" -> junior;
   1 to under 3 years -> middle; 3 or more years -> senior. Set level_evidence = "experience".
3. Otherwise level = "unknown", level_evidence = "none".
years_experience_min: the minimum years of experience required, if stated. Use 0 when the post
says no experience is needed or targets students/fresh graduates. null when nothing is said.

salary:
- Copy amounts as numbers, expanding shorthand: "1.5 mln so'm" -> 1500000, "2k$" -> 2000,
  "5 000 000" -> 5000000.
- Range "X-Y" -> salary_min X, salary_max Y. "from X"/"от X"/"X dan" -> salary_min X only.
  "up to Y"/"до Y"/"Y gacha" -> salary_max Y only.
- currency: $/USD/dollar -> USD; so'm/сум/sum/UZS -> UZS; руб/RUB -> RUB; €/EUR -> EUR.
- salary_period: "month" unless the post says per year or per hour.
- "negotiable", "по договоренности", "kelishiladi", or no amount -> all salary fields null.
- Ignore amounts that are not the salary (prices, course fees, bonuses only).

skills: concrete technologies and tools, normalised names ("Postgres" -> "PostgreSQL",
"JS" -> "JavaScript", "DRF" -> "Django REST Framework"). No soft skills.
city: the city if stated (e.g. "Tashkent"), else null.
language: main language of the post; "mixed" if two languages carry the content."""
