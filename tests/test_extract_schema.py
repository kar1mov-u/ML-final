"""The extraction schema: an example validates, and bad values are rejected."""
import pytest
from pydantic import ValidationError

from jobtracker.extract.llm_extract import final_level
from jobtracker.extract.schema import Extraction, PostExtraction

EXAMPLE = {
    "is_job_post": True, "is_it_job": True, "title": "Data Engineer", "level": "senior",
    "level_evidence": "experience", "years_experience_min": 3, "salary_min": 2500,
    "salary_max": 4500, "currency": "USD", "salary_period": "month",
    "skills": ["SQL", "Python", "Airflow"], "work_format": "office", "city": "Tashkent",
    "language": "ru",
}


def test_example_validates():
    Extraction.model_validate(EXAMPLE)
    assert PostExtraction.model_validate({**EXAMPLE, "post_id": 7}).post_id == 7


def test_unknown_level_rejected():
    with pytest.raises(ValidationError):
        Extraction.model_validate({**EXAMPLE, "level": "rockstar"})


def test_level_rule():
    def lvl(**kw):
        return final_level(Extraction.model_validate({**EXAMPLE, **kw}))
    assert lvl(level="junior", level_evidence="title", years_experience_min=4) == "junior"  # named level wins
    assert lvl(level="unknown", level_evidence="none", years_experience_min=0.5) == "junior"
    assert lvl(level="unknown", level_evidence="none", years_experience_min=2) == "middle"
    assert lvl(level="unknown", level_evidence="none", years_experience_min=3) == "senior"
    assert lvl(level="unknown", level_evidence="none", years_experience_min=None) == "unknown"
