# Permission to collect from hh.uz

| | |
|---|---|
| Date | 2026-11-22 |
| Asked by | Project student, who sent hh.uz their student ID and a description of this course project |
| Answer from hh.uz | Approved collecting past (archived) vacancies for the project. In their words, as the student reported it: the data is "not state secrets" |
| Instructor | Approved web scraping of hh.uz for this project, including archived vacancies, knowing that hh's robots.txt does not allow it for crawlers in general |

hh's original reply (e-mail or chat screenshot): `docs/hh_permission_reply.png` _(add the file)_.

## What we collect and how (what the permission covers)
- Active vacancies: `/vacancy/<id>` pages found through hh's sitemap and job-title category pages
  (allowed by robots.txt for all crawlers).
- hh's own vacancy search (`/search/vacancy?area=97&professional_role=<IT role>&page=N`), IT roles
  only, Uzbekistan. This is the only query-string URL we request; robots.txt disallows those for
  crawlers in general, so it relies on this permission.
  We meant to use it for past (archived) vacancies of the last 3 months, but tested on 2026-11-22:
  for a logged-out visitor hh ignores `archived=true` and the date filters and shows only ACTIVE
  vacancies. So it gives the complete list of active IT vacancies, not past ones.
- Pace: one request at a time, 3 s between search pages, 2 s between vacancy pages; honest
  User-Agent; the scraper stops on the first 403 / 429 / captcha.
- Stored: vacancy text with contacts removed, salary / experience / skills fields. No employer
  contacts, no people, no résumés. Nothing is republished.
