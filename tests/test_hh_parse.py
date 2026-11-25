"""hh.uz parser on a small hand-made page (no network). Data check + PII check."""
import json

from jobtracker.collect.hh_parse import Vacancy, parse_salary_text, parse_vacancy

LD = {
    "@context": "http://schema.org/", "@type": "JobPosting",
    "title": "Middle Python Developer",
    "description": "<p>Мы ищем разработчика.</p><ul><li>Django</li><li>PostgreSQL</li></ul>"
                   "<p>Пишите: hr@example.com, +998 90 123 45 67</p>",
    "datePosted": "2026-11-10T12:30:00+03:00",
    "baseSalary": {"@type": "MonetaryAmount", "currency": "USD",
                   "value": {"@type": "QuantitativeValue", "minValue": 1500, "maxValue": 2500,
                             "unitText": "MONTH"}},
}
PAGE = f"""<html><head><script type="application/ld+json">{json.dumps(LD)}</script></head><body>
<h1 data-qa="vacancy-title">Middle Python Developer</h1>
<span data-qa="vacancy-salary">от 1 500 до 2 500 $ на руки</span>
<span data-qa="vacancy-experience">1–3 года</span>
<li data-qa="skills-element">Python</li><li data-qa="skills-element">Django</li>
</body></html>"""


def test_parse_fields():
    v = parse_vacancy(PAGE)
    assert v.title == "Middle Python Developer"
    assert v.salary["from"] == 1500 and v.salary["to"] == 2500
    assert v.salary["currency"] == "USD" and v.salary["gross"] is False
    assert v.experience == "1–3 года"
    assert v.skills == ["Python", "Django"]
    assert "- Django" in v.description


def test_fallback_without_json_ld():
    page = PAGE.split("</head>")[1].replace("<body>", "<body><div data-qa='vacancy-description'>"
                                                       "<p>Описание вакансии достаточно длинное для проверки.</p></div>")
    v = parse_vacancy(page)
    assert v.title == "Middle Python Developer"
    assert "Описание" in v.description


def test_stored_text_is_scrubbed(tmp_path):
    from jobtracker.collect.hh_web import store
    from jobtracker.db import connect
    conn = connect(tmp_path / "t.db")
    assert store(conn, 1, parse_vacancy(PAGE)) == "stored"
    text = conn.execute("SELECT text FROM raw_posts").fetchone()[0]
    assert "hr@example.com" not in text and "123 45 67" not in text
    assert text.startswith("Middle Python Developer")


def looks_it(title, skills):
    return Vacancy(title, "", {}, skills=skills).looks_it()


def test_it_filter():
    assert looks_it("Senior Java разработчик", [])
    assert looks_it("Специалист", ["SQL", "Python"])
    assert not looks_it("Менеджер по продажам", ["Переговоры"])


def test_salary_text():
    assert parse_salary_text("от 3 000 000 до 10 000 000 so'm за месяц до вычета налогов") == \
        {"from": 3_000_000, "to": 10_000_000, "currency": "UZS", "period": "month"}
    assert parse_salary_text("от 300 до 400 $ за месяц на руки")["to"] == 400
    assert parse_salary_text("до 1 500 $") == {"from": None, "to": 1500, "currency": "USD", "period": "month"}
    assert parse_salary_text("2 000 $")["from"] == 2000


def test_search_is_the_only_query_url():
    from jobtracker.collect.hh_web import Client, search_url
    c = Client()
    c._robots["https://hh.uz"] = __import__("urllib.robotparser").robotparser.RobotFileParser()
    c._robots["https://hh.uz"].parse(["User-agent: *", "Disallow: *?*"])
    assert c._allowed(search_url(96, 0))
    assert not c._allowed("https://hh.uz/search/resume?text=python")
    assert not c._allowed("https://hh.uz/vacancy/1?from=x")


def test_restricted_vacancy_is_skipped_not_a_block():
    """hh answers 403 for restricted vacancies; that must not stop the crawl."""
    from unittest.mock import MagicMock
    from jobtracker.collect.hh_web import Blocked, Client
    import pytest
    c = Client(delay=0)
    c._allowed = lambda url: True
    page = MagicMock(status_code=403, url="https://hh.uz/vacancy/1", text="Вам недоступна эта вакансия.")
    c.session.get = MagicMock(return_value=page)
    assert c.get("https://hh.uz/vacancy/1") is None
    page.text = "Access denied"
    with pytest.raises(Blocked):
        c.get("https://hh.uz/vacancy/1")


def test_it_filter_catches_it_support_and_product_roles():
    for title in ["Специалист Help Desk", "Администратор Jira\\Confluence", "Старший консультант SAP HR (PY)",
                  "Tizim Administratori (Texnik qo'llab quvatlash)", "Менеджер продукта"]:
        assert looks_it(title, []), title
    assert not looks_it("Omborchi", [])
