"""Data checks for the cleaning rules (handbook 'advanced': at least 3 automated tests)."""
from jobtracker.clean import normalize, scrub_pii, strip_salary
from jobtracker.salary import to_usd_month


# --- personal data is removed before storage ---------------------------------

def test_scrub_phone_formats():
    for phone in ["+998 90 123 45 67", "+998901234567", "998(90)123-45-67", "90 123 45 67",
                  "+998 99 123 28", "+99850 003-123-62"]:      # malformed ones seen in real posts
        assert "123" not in scrub_pii(f"Call {phone} today"), phone


def test_scrub_email_handle_link():
    out = scrub_pii("Write to hr@company.uz or @hr_manager, apply: https://t.me/somejob")
    assert "hr@company.uz" not in out
    assert "@hr_manager" not in out
    assert "https://" not in out
    assert "gmail" not in scrub_pii("pochta orqali pmu@gmail. com manziliga")


def test_scrub_contact_person_names():
    out = scrub_pii("Mas'ul:\nAzizbek\nHudud: Toshkent\nКонтактное лицо: Анна")
    assert "Azizbek" not in out and "Анна" not in out
    assert "Toshkent" in out                       # other lines untouched
    assert "Xodim kerak" in scrub_pii("Xodim kerak:\nIdora: Mediik")   # header is not a name


def test_scrub_self_introduction():
    assert "usmon" not in scrub_pii("hello my name is usmon, i know golang")
    assert "Анна" not in scrub_pii("Меня зовут Анна")
    assert scrub_pii("I am looking for a Python developer") == "I am looking for a Python developer"


def test_scrub_keeps_salary():
    # salary amounts are labels, they must survive PII scrubbing
    assert "1 500 000" in scrub_pii("Oylik: 1 500 000 so'm")
    assert "15 000 000" in scrub_pii("Maosh 15 000 000 сум")


# --- leakage guard: salary disappears from model input -----------------------

def test_strip_salary_removes_amounts():
    cases = [
        "Зарплата: от 1500$ до 2500$",
        "Maosh: 15 000 000 so'm",
        "Salary 2k USD, 3 years of experience",
        "ЗП 1.5 млн сум",
        "Oylik 800 dollar",
        "Maosh 8 000 000 so‘mdan",          # ‘ (U+2018) apostrophe
        "до 25 000 000 сўм",                # Uzbek Cyrillic
        "Salary 5 000 000 soums",
    ]
    for text in cases:
        out = strip_salary(text)
        for token in ["1500", "2500", "15 000 000", "2k", "1.5", "800", "$", "USD", "сум", "so'm", "dollar", "so‘m", "сўм", "soum"]:
            assert token not in out, (text, out)


def test_strip_salary_keeps_small_numbers():
    assert "3" in strip_salary("3+ years of Python experience")


def test_normalize_ignores_hashtags_and_case():
    assert normalize("#python Python Developer!") == normalize("PYTHON developer")


# --- salary target rule -------------------------------------------------------

def test_salary_rules():
    assert to_usd_month(1000, 2000, "USD") == 1500          # range -> midpoint
    assert to_usd_month(1500, None, "USD") == 1500          # "from X" -> X
    assert to_usd_month(None, 25_000_000, "UZS") == 2000    # UZS converted
    assert to_usd_month(24_000, None, "USD", "year") == 2000
    assert to_usd_month(5, None, "USD") is None             # absurd -> None
    assert to_usd_month(1000, None, None) is None           # unknown currency -> None
