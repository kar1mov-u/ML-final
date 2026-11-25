# Error analysis: level (logistic_regression)

Validation = newest 20% of the train part (518 posts, from 2025-09-15). Fit on the older 2072 posts.
Causes: wrong label, missing feature, rare case, typo or outlier, duplicate or leakage, other.

| Example ID | True | Predicted | Error | Cause | Note | Post (start) |
|---|---|---|---|---|---|---|
| 5535 | senior | junior | 2 |  |  | Xodim kerak: 🏢 Idora: Huquqni Muhofaza Qilish Akademiyasi 📚 Texnologiya: Ava, Oop, Spring  |
| 116 | junior | senior | 2 |  |  | #intern AI Engineer Intern Company: zehnmind.ai Location: Tashkent (Office-based) Duration |
| 511 | junior | senior | 2 |  |  | #pm Компания: НааS Platform Вакансия: Project Manager Занятость: полная Грейд: Джуниор+\ М |
| 322 | junior | senior | 2 |  |  | #java We are looking for an Entry Level Java Developer who is eager to grow into a Salesfo |
| 164 | junior | senior | 2 |  |  | #oracle #postgres Junior DBA (Oracle / PostgreSQL) ООО WEBASE от 7 000 000 сум График: 5/2 |
| 5437 | senior | junior | 2 |  |  | Xodim kerak: 🏢 Idora: Data365 📚 Texnologiya: Typescript · React, Next. Js, Postgresql, Clo |
| 274 | junior | senior | 2 |  |  | #prompt #ai AI Prompt Engineer Employment type: Full-time / Project based Format: On-Site  |
| 3953 | junior | senior | 2 |  |  | Junior Java Developer kerak! — Ish holati: #aktiv — Kompaniya: Andersen — Kompaniya haqida |
| 395 | junior | senior | 2 |  |  | #java Andersen is hiring a Junior Java Developer in Tashkent to build and support core fin |
| 3918 | senior | junior | 2 |  |  | C/C++ dasturchi kerak! — Ish holati: #aktiv — Kompaniya: Lan Master Vision — Kompaniya haq |
| 5421 | senior | junior | 2 |  |  | Xodim kerak: 🏢 Idora: Promtchi 📚 Texnologiya: Go And Python 🇺🇿 Telegram: [contact] 📞 Aloqa |
| 506 | junior | senior | 2 |  |  | #internship Kickstart Your IT Career with AMC Bridge! Are you studying programming at univ |
| 585 | junior | senior | 2 |  |  | #remote #pm Младший менеджер проектов (удалённо) Мы — AI-стартап CastleBlack, который авто |
| 3962 | senior | junior | 2 |  |  | Raqamlashtirish bo‘lim boshlig‘i kerak! — Ish holati: #aktiv — Kompaniya: Davlat tashkilot |
| 3040 | junior | senior | 2 |  |  | Backend Developer (Strong Junior) Компания: ORB IT ORB IT — IT-компания полного цикла разр |
| 5703 | senior | junior | 2 |  |  | Xodim kerak: 🏢 Idora: Miracle Academy 📚 Texnologiya: Python Java 🇺🇿 Telegram: [contact] 🌐  |
| 5395 | senior | junior | 2 |  |  | Xodim kerak: 🏢 Idora: 1c Holding 📚 Texnologiya: 1c 📞 Aloqa: [phone] 🌐 Hudud: Toshkent sh ( |
| 5571 | senior | junior | 2 |  |  | Xodim kerak: 🏢 Idora: Xcode 📚 Texnologiya: React, Javascript 🇺🇿 Telegram: Xodim topildi 🌐  |
| 5589 | senior | junior | 2 |  |  | Xodim kerak: 🏢 Idora: Sigli 📚 Texnologiya: NodeJs, NextJs, Tailwind Css, Zod, Graphql 🇺🇿 T |
| 316 | junior | senior | 2 |  |  | #devops DevOps Engineer (Junior) Формат: Полная занятость Опыт: от 6 месяцев – 1 года (или |

## Cause counts
| Cause | Count |
|---|---|
|  |  |

**Decision:** (fix the data or change the model, and why)
