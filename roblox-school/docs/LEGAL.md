# Проверенные факты: реклама, DevEx, налоги

Всё ниже проверено по первоисточникам 27 августа 2026 года. У каждого пункта —
ссылка. Там, где источник вторичный или вопрос не закрывается публично, это
сказано явно.

**Я не налоговый консультант.** Раздел о налогах — фактура для разговора со
специалистом, а не готовая схема.

---

## 1. Реклама: требование, от которого зависит вся архитектура

Официальный список требований к rewarded video содержит строку **«Offer no
free-form user creation»** — наравне с 2000 уникальных посетителей в месяц,
13+, ID-верификацией и 2FA.

Определение free-form creation и исключение из него — в документации по
content maturity:

> Free-form user creation refers to features that allow players to create
> anything within an experience, such as writing words or making illustrations
> on a chalkboard. […] does not apply to in-experience creations that players
> assemble with 3D assets, such as building a house or creating an outfit, **or
> anything that goes through Roblox moderation before it's published or
> replicated**.

Выделенная часть — то, на чём держится наш пайплайн авторства.

**Но есть расхождение, которое надо знать.** Формулировка внутри самой анкеты
Maturity & Compliance короче документации:

> Free-form drawing or creation (e.g., writing or drawing on a chalkboard,
> whiteboard, or with spray paint).
> Do NOT measure: In-experience user creations assembled with 3D assets […]

То есть анкета повторяет **только 3D-половину** исключения. Модерационной
половины в ней нет. На девфоруме есть тред ровно про наш случай — текстовая
табличка с фильтром, — и **ответа от Roblox в нём нет**: только мнения
разработчиков. В другом треде разработчик описывает отказ модератора с
формулировкой «players have a white board where they can write anything and
visible to everyone».

**Вывод:** исключение существует и написано в официальной документации, но
письменного подтверждения, что фильтрация через `TextService` его активирует,
публично нет. Поэтому:

- в коде есть выключатель `Authoring.FreeTextEnabled` (`src/shared/Config/Authoring.luau`);
- `false` убирает свой текст целиком — остаются банк, сборка из префабов и
  полосы препятствий, и анкета отвечается «нет» без спора;
- доход преподавателя не зависит от авторских вопросов, так что переключение
  ничего не ломает.

Порог рекламы (2000 MAU) наступает сильно позже запуска — время на письменный
ответ Roblox Support есть.

Остальное подтвердилось как есть:

| Правило | Статус |
|---|---|
| 2000 уникальных посетителей в месяц | подтверждено |
| Создатель 13+ (раньше 18+), ID-верификация, 2FA | подтверждено |
| Награда — dev product, **не Robux**, не случайная | подтверждено |
| Ориентир ценности награды 3–10 Robux | подтверждено |
| Реклама не гейтит прогресс | подтверждено |
| Явное действие игрока и раскрытие награды до показа | подтверждено |
| Rewarded video только 13+; `PolicyService` — обязателен | подтверждено |
| Также дисквалифицирует: **AI interaction** | новое, у нас его нет |

Источники: [Rewarded video ads](https://create.roblox.com/docs/production/promotion/rewarded-video-ads),
[Content maturity](https://create.roblox.com/docs/production/promotion/content-maturity),
[Experience guidelines](https://create.roblox.com/docs/production/promotion/experience-guidelines),
[анонс расширения доступа](https://devforum.roblox.com/t/rewarded-video-ads-are-now-available-to-all-ads-eligible-creators/4063278),
[тред про табличку с фильтром](https://devforum.roblox.com/t/is-text-sign-with-filter-is-free-form-user-creation/3507743).

---

## 2. Tipalti платит в Узбекистан — вопрос закрыт

Страница покрытия отдаёт 403 браузеру, но её содержимое доступно через Zendesk
API. В таблице «Payment methods coverage — US & ROW», раздел «когда валюта
фондирования — USD» (Roblox — американский плательщик в USD):

| Payee country | Wire transfer | Global ACH | Check | PayPal |
|---|---|---|---|---|
| **Uzbekistan** | **USD (T to T+1)** | — | USD | — |

Global ACH и PayPal для Узбекистана недоступны. Рабочий канал — **USD-перевод
по SWIFT**, зачисление день в день или на следующий.

Условия DevEx подтверждают: 13+, **30 000 Earned Robux**, верифицированный
email, аккаунт в DevEx-портале, форма W-9 или W-8, соблюдение ToU. Курс —
**$0.0038** за Robux; **$0.0054** — для покупок игроков из США, подтвердивших
возраст 18+.

Источники: [Tipalti payment methods coverage](https://help.tipalti.com/hc/en-us/articles/31314361313815-Payment-methods-coverage-US-ROW),
[DevEx Terms of Use](https://en.help.roblox.com/hc/en-us/articles/115005718246-Developer-Exchange-Terms-of-Use),
[DevEx Portal](https://create.roblox.com/docs/production/monetization/devex-portal).

---

## 3. Налог США: 0%, а не 30%

Раньше здесь стояла оценка «по американской доле полные 30%, потому что в
унаследованном соглашении 1973 года пониженной ставки по роялти нет». **Это
неверно.** В соглашении не пониженная ставка — там полное освобождение.

Конвенция США–СССР от 20 июня 1973 года, Статья III(1)(a):

> The following categories of income derived from sources within one Contracting
> State by a resident of the other Contracting State shall be **subject to tax
> only in that other Contracting State**: (a) rentals, royalties, or other
> amounts paid as consideration for the use of or right to use literary,
> artistic, and scientific works, or for the use of copyrights of such works, as
> well as the rights to inventions (patents, author's certificates), industrial
> designs, processes or formulae, **computer programs**, trademarks, service
> marks, and other similar property or rights […]

«Subject to tax only in that other Contracting State» = **0% удержания в США**.
Компьютерные программы названы прямо.

Подтверждается с трёх сторон:

- IRS Publication 901: «The U.S.-U.S.S.R. income tax treaty remains in effect
  for the following members of the C.I.S.: Armenia, Azerbaijan, Belarus,
  Georgia, Kyrgyzstan, Moldova, Tajikistan, Turkmenistan, **and Uzbekistan**».
- IRS Table 1 в изложении PwC: строка «Commonwealth of Independent States» —
  роялти **0 / 0 / 0 / 0 / 0** по всем пяти категориям.
- Статья II(3)(b) определяет резидента как «an individual resident in the
  Soviet Union for purposes of its tax» — узбекский ИП, налоговый резидент
  Узбекистана, под определение попадает как физлицо.

**Что это меняет практически.** Разница между 0% и 30% по американской доле
перестаёт быть структурным вопросом — ставка на США больше не наказывается
налогом. Это влияет на выбор локалей: `$0.0054` вместо `$0.0038` за покупки
верифицированных 18+ игроков из США — это **+42% к курсу**, и теперь без
налоговой платы за него.

Источники: [текст конвенции (IRS)](https://www.irs.gov/pub/irs-trty/ussr.pdf),
[Uzbekistan tax treaty documents](https://www.irs.gov/businesses/international-businesses/uzbekistan-tax-treaty-documents),
[Publication 901](https://www.irs.gov/publications/p901),
[PwC: US withholding taxes](https://taxsummaries.pwc.com/united-states/corporate/withholding-taxes).

---

## 4. Дедлайн 31 октября 2026 — остаётся

С 1 ноября 2026 выплаты DevEx переклассифицируются в роялти.

- Нет валидной формы к 31 октября → **24% backup withholding со всей выплаты**.
- Форма подана → **0–30% только с доли выручки от игроков из США**; по
  соглашению 1973 года для узбекского резидента это **0%**.
- Тогда же управление налоговыми данными переезжает из Tipalti на страницу
  Taxes в Creator Hub; Tipalti остаётся только процессингом выплат.

**Форму надо подать независимо от готовности игры.** Без неё удерживается
четверть всего, а не доля от американской части.

**Какую форму.** ИП в Узбекистане — не юрлицо, а физлицо, ведущее
предпринимательскую деятельность. По правилам IRS иностранные физлица и
sole proprietors подают **W-8BEN**, а не W-8BEN-E; W-8BEN-E — для иностранных
юрлиц. То есть **раньше я говорил W-8BEN-E — это, скорее всего, неверно для
ИП**. Подтвердить у бухгалтера до подачи: ошибка в типе формы = невалидная
форма = 24%.

Для льготы по соглашению в W-8BEN нужен иностранный TIN (строка 6a) — узбекский
ИНН/СТИР. Сертификат налогового резидентства форма не требует, но налоговый
агент вправе его запросить.

Источники: [DevEx tax information](https://create.roblox.com/docs/production/monetization/tax-information),
[Instructions for Form W-8BEN](https://www.irs.gov/instructions/iw8ben).

---

## 5. Узбекистан: налог с оборота падает до 1%

С 1 января 2026 для ИП и самозанятых с годовым оборотом **до 1 млрд сумов**
ставка налога с оборота — **1%** вместо 4%. При превышении порога — переход на
НДС и налог на прибыль. ИП освобождаются от подоходного налога в фиксированном
размере.

Валютный контроль под роялти из США публичные источники детально не описывают —
общая рамка разрешительная, но конкретный порядок зачисления определяет банк как
агент валютного контроля. **Это к местному бухгалтеру**, оценка по открытым
данным здесь ненадёжна.

Источники: [Gazeta.uz](https://www.gazeta.uz/ru/2025/08/11/business/),
[Buxgalter.uz](https://buxgalter.uz/publish/doc/text212712_nk-2026_izmeneniya_po_nalogu_s_oborota_dlya_ip_i_samozanyatyh).

---

## 6. Platega по-прежнему не подключается

Формулировка из DevEx Terms of Use, дословно:

> By way of example, the following will disqualify you from DevEx: scamming,
> phishing, false advertising, **attempting to exchange Robux for real currency
> other than through DevEx**, and any illegal or unethical activities.

Плюс ToU: «the sale of Robux or Virtual Content outside the Services is not
permitted». Ничего не изменилось: Platega остаётся у seller ai и к игре не
подключается.

---

## 7. Что осталось выяснить

| Вопрос | К кому | Когда |
|---|---|---|
| Считается ли наш пайплайн исключением из free-form creation | Roblox Support, письменно | до 2000 MAU |
| Какая форма для узбекского ИП — W-8BEN или W-8BEN-E | бухгалтер | **до 31 октября 2026** |
| Порядок зачисления валюты по роялти | банк / бухгалтер в Узбекистане | до первой выплаты |

Экономические ориентиры игрока не изменились: ~$12.50 за 1000 R$ → 700 R$
разработчику после комиссии магазина → × $0.0038 = **$2.66**. Разница в том, что
американская доля теперь не режется удержанием.
