# Historical-cast audit (2026-11-27/28)

RG: "make sure historical casts don't get mixed into the contemporary casts." Nothing has been changed in the database.

## Method

`detect.py` (read-only, on a copy of production) flags review blocks that hold linked person mentions, are not already in
`docs/eval/review_historical_passages.csv`, are not plate captions, and show an earlier time: old-cast wording, an earlier
year in the block or the 2 before it, a quoted journal/chronicler, or a block right after a listed historical block. The
2026-11-03 sweep only looked for a year inside the block, which is how the 1895-96 SP 1864 «Конекъ-Горбунокъ» cast was
missed (its year sits in the paragraph before). 161 candidates; 5 are the «Конекъ» blocks (`../konek_1864_cast_1895-96_2026-11-27/`).
The other 156 were read in context (block + 3 before + 2 after) by three agents, each linked mention classified;
`classified_all.csv` (one row per block). Checked by Claude: every mention id exists, is linked, and sits in its block;
boundaries of the mixed blocks read in the text; the «Конекъ» passage read on the scans. The others were read in the
transcription, not yet on the scans.

## Result

156 blocks: 102 current (false alarms), 28 historical, 24 mixed, 2 unclear. Linked names to unlink: 90 (+ 21 «Конекъ»).
Creator links inside historical passages kept: 52. Unclear mentions: 12.

**Group A — quoted old casts (78 links in 18 blocks + 21 «Конекъ»)**, `group_A_quoted_old_casts.csv`: the cast of a dated
earlier performance (premiere, old revival, quoted old review). Largest: 1902-03 SP p019 (1890 «Спящая красавица» casts,
21, continuing the already-listed p018__b002); 1903-04 SP p007__b001 (quoted 1851 «Наяда и рыбакъ» review, 12); 1900-01
SP p032/p037 (1855 «Маркитантка» premiere and 1861 revival, 14, incl. Marius Petipa and Л. Ивановъ as dancers); 1893-94
and 1901-02 Moscow (1866 «Конекъ-горбунокъ» premiere, 5 + 4); 1892-93 SP (1851 «Наяда», 1847 «Пахита», 5 + 2);
1894-95 SP (1818 «Тщетная предосторожность», 3); 1896-97 Moscow (1849 «Сатанилла», 3).

**Group B — career retrospectives (12 links)** and the unclear mentions, `group_B_and_unclear.csv`: a benefit, farewell or
jubilee review recalls the honoree's earlier partners or roles: Кшесинская's 1904 farewell (the six foreign ballerinas she
danced with, 6), her 1911 jubilee (Бріанца, Дель-Эра, Леньяни, Замбелли, 5), М. М. Петипа's 1907 farewell (Гердтъ in her
1875 debut, 1); unclear: Горшенкова 1892-93 and Андерсонъ 1894-95 role lists, Гердтъ's 1906 jubilee career (6 incl. his
1858-65 teachers), Гримальди at the end of a «Жизель» role history (1901-02), М. И. Чайковскій cited as biographer
(1902-03), and 1900-01 SP p004__b003 «При послѣднемъ возобновленіи» (1895 or 1900?).

## Wrong links seen on the way (not historical; not changed)

«Ольгиномъ (островѣ)» → Ольгина, Е. М. (a place); «Вилли» → Виль, Е. И. (a character); «Антоніо», «Готье», «Принцъ» ×2
(role names); Снѣткова, Яковлева, Шульгина ×2 linked to men; «А. Н. Лядовымъ» → Лядовъ, К.; «г-нъ Чекетти» as Пиѳія →
Жозефина; 1859 Лизетта «М. Петипа» (М. С.) → Марія Маріусовна; «П. П. Лебедева» (1864) → Клавдія Петровна;
Шуманъ → Отто Рейнгольдовичъ, Глазуновъ → Николай Лукичъ (1910-11); is the 1851 Вагнеръ Конрадъ Робертовичъ?
