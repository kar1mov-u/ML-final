# Error analysis: salary (smart_keyword_median)

Validation = newest 20% of the train part (632 posts, from 2025-11-16). Fit on the older 2525 posts.
Causes: wrong label, missing feature, rare case, typo or outlier, duplicate or leakage, other.

| Example ID | True | Predicted | Error | Cause | Note | Post (start) |
|---|---|---|---|---|---|---|
| 454 | 6400 | 800 | -5600.0 |  |  | #frontend Frontend Developer Kompaniya: Hippo.uz Ish turi: Offline Oylik-maosh: 8 000 0000 |
| 3038 | 6500 | 1000 | -5500.0 |  |  | Senior/Lead Python developer (AI App Studio) В связи с расширением команды ищем Senior/Lea |
| 5696 | 5050 | 600 | -4450.0 |  |  | Xodim kerak: 🏢 Idora: Real Estete 📚 Texnologiya: Ai Engineer 🇺🇿 Telegram: [contact] 📞 Aloq |
| 481 | 5750 | 1675 | -4075.0 |  |  | #java #lead We’re hiring a Java Technical Lead in Tashkent! Accesa — a European tech compa |
| 244 | 5000 | 1000 | -4000.0 |  |  | #backend #python Backend Architect (Python) We are hiring a senior backend architect to de |
| 331 | 4620 | 1200 | -3420.0 |  |  | #lead #backend Tech Lead / Senior Backend (E-commerce Integration) Удалёнка / Проектная 20 |
| 3922 | 4000 | 600 | -3400.0 |  |  | Senior Go Developer kerak! — Ish holati: #aktiv — Hudud: Remote — Ish turi: online — Maosh |
| 488 | 4500 | 1200 | -3300.0 |  |  | #golang We are looking for Senior Golang Engineers to design and develop high-performance  |
| 5589 | 4348 | 1310 | -3038.0 |  |  | Xodim kerak: 🏢 Idora: Sigli 📚 Texnologiya: NodeJs, NextJs, Tailwind Css, Zod, Graphql 🇺🇿 T |
| 5732 | 4000 | 1000 | -3000.0 |  |  | Middle/Senior Python Developer it-bench.work [link] Middle / Senior Python Engineer Role:  |
| 480 | 4000 | 1060 | -2940.0 |  |  | #csharp AMC Bridge is looking for talented professionals with at least two years of experi |
| 261 | 4400 | 1600 | -2800.0 |  |  | #devops #senior Компания: Tez (современный онлайн-банк, создан Fintech Farm и HamkorBank)  |
| 209 | 3500 | 1000 | -2500.0 |  |  | #python #senior Kompaniya: Iqtisodiyot va moliya vazirligi huzuridagi Axborot texnologiyal |
| 190 | 3500 | 1000 | -2500.0 |  |  | #javascript #middle #senior Middle/Senior Javascript Developer It-bench [link] Position: M |
| 3016 | 3500 | 1000 | -2500.0 |  |  | Senior Machine Learning Engineer vakansiyasi Jamoamizga tajribali Senior Machine Learning  |
| 241 | 3500 | 1000 | -2500.0 |  |  | #fullstack #next We are looking for a Full-Stack Developer (Rails + Next.js) Small, high-s |
| 210 | 3500 | 1000 | -2500.0 |  |  | #ml #python #ai #senior Kompaniya: Iqtisodiyot va moliya vazirligi huzuridagi Axborot texn |
| 134 | 4000 | 1600 | -2400.0 |  |  | #devops Ищем DevOps Engineer в команду ХБ на проект TEZ Мы ищем DevOps Engineer, который п |
| 118 | 3000 | 600 | -2400.0 |  |  | #qa #remote Должность: QA Engineer Город: Узбекистан, г. Ташкент Формат: офис/гибрид/удале |
| 5676 | 3500 | 1200 | -2300.0 |  |  | Xodim kerak: 🏢 Idora: Logistika 📚 Texnologiya: Golang, Sql, Jwt&rbac 🇺🇿 Telegram: [contact |

## Cause counts
| Cause | Count |
|---|---|
|  |  |

**Decision:** (fix the data or change the model, and why)
