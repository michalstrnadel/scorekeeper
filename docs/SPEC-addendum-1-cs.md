# SCOREKEEPER — Dodatek k zadání iterace 1

*Integrace zjištění z rešerší „Evaluace LLM agentů 2024–2026" a „Vizualizace argumentačních a závazkových struktur" (obě v `docs/research/`). Body níže REFINUJÍ nebo SUPERSEDují konkrétní ustanovení dokumentu ZMENY_ITERACE_1.md; kde je rozpor, platí tento dodatek.*

> **Poznámka správce repa (2026-07-09):** Referencovaný dokument `ZMENY_ITERACE_1.md` nebyl dodán (viz QUESTIONS.md Q7). Dodatek je aplikován samostatně — jeho ustanovení jsou závazná vůči SPEC-cs.md a aktuální implementaci.

---

## A. Změny evaluačního protokolu (mění §3)

### A.1 Judge pipeline — SUPERSEDE §3.3 „judge = silnější model"
Silnější model sám o sobě nestačí; rozhoduje protokol. Závazný design judge:
- **Jiná modelová rodina než agent.** Self-preference bias je doložený a závažný ("Machiavellian judges": sudí ze stejné rodiny až o 50 % častěji maskuje selhání vlastní architektury). Agent běží na Claude → judge NESMÍ být Claude; použij model jiné rodiny, ideálně round-robin dvou rodin (CyclicJudge vzor).
- **Protokol S8 (Combined Budget):** kalibrovaná rubrika (5 kritérií, škála 1–10) + vynucený CoT před verdiktem + position swap tam, kde judge srovnává dvě trajektorie. Empiricky nejsilnější mitigace (+7 až +11 p.b. shody s lidmi). Poznámka k nákladům: střední model s S8 překonává naivní frontier judge při ~15× nižší ceně — judge nemusí být drahý, musí být dobře zapřažený.
- **Blind vůči stylu:** style bias je dominantní zdroj chyby (LLM sudí preferují Markdown/strukturu před správností). Před posouzením SCR normalizuj vstupy judge: strip formátování, porovnávají se propozice, ne úprava.
- **Neutrální framing:** rubrika formulovaná jako neutrální kritérium, ne sugestivní otázka ("Je toto správně?" vs. negativní predikát mění verdikty).
- **Trajektoriální hodnocení, ne jen výsledek** (BiomniBench vzor): judge boduje kroky trajektorie proti rubrice, ne binární konec — chytá reward hacking (agent došel ke konzistentnímu stavu náhodou/okopírováním, ne respektováním závazku).

### A.2 Statistika — SUPERSEDE §3.2 „bootstrap CI"
Paušální bootstrap byl špatný pokyn pro náš režim. Závazná tabulka:
- **Binární metriky (SCR pass/fail per scénář) při malém N (naše situace, <100 datových bodů):** Wilsonovy skórové intervaly nebo Bayesovské kredibilní intervaly. CLT-based metody v malém N prokazatelně selhávají (intervaly mimo [0,1] nebo kolabující k nule).
- **Spojité metriky (tokeny, latence):** smooth bootstrap (500–1000 pseudovzorků).
- **Clustered standard errors:** scénáře sdílející stejné repo/prostředí NEJSOU nezávislé — clusteruj podle scénářového prostředí; naivní SE mohou být až 3× podhodnocené a vyrobí falešný signál zlepšení.
- Inference výhradně na párových rozdílech per instance (potvrzuje §3.2; paired design zůstává).

### A.3 Meta-evaluace pipeline — NOVÝ krok před §3.2
Než se měří cokoliv: 10 identických průchodů se zafixovaným seedem a teplotou 0; koeficient variace ≤ 0.05. Pokud vyšší, měříš infrastrukturní šum (kontejnery, timeouty parserů), ne efekt scoreboardu. Bez splnění tohoto kroku se plná matice nespouští.

### A.4 Reprodukovatelnost — Rollout Cards standard (rozšiřuje §3)
Změna reporting rules dokáže pohnout skóre o ~20 p.b. Pro CommitBench proto adoptuj Rollout Cards: ukládej (1) rollout record — surové logy, přesná pozorování, volání nástrojů, časování; (2) views — skripty extrakce hodnocených částí trajektorie; (3) reporting rules + drops manifest — agregační kód a deklaraci zahozených běhů. Vše verzované v `bench/`.

### A.5 Kontaminace — design CommitBench (rozšiřuje §3.2 held-out disciplínu)
- **Search-Time Contamination:** eval běhy v sandboxu s denylistem (HuggingFace, GitHub, fóra) — agent s web přístupem by mohl dohledat scénáře benchmarku. Pro fázi 2 povinné.
- **Game Engine Separation** (TCG-Bench vzor) pro publikaci: engine, pravidla a generátor scénářů CommitBench jsou veřejné; konkrétní held-out instance eval setu zůstávají privátní (serverové/na vyžádání). Řeší napětí „open source benchmark" vs. „nekontaminovaný benchmark".
- **Concept drift audit:** API modely se tiše mění; fixní zlatá sada se přeběhne při každém minor release a před každým publikovaným číslem.

### A.6 Náklady — REFINE §3.4
Latenci reportuj na percentilech P90/P99, ne průměrem (rekurzivní smyčky se v průměrech ztratí). Token overhead vztahuj k úspěšně dokončenému úkolu. Poziční poznámka do docs: AgentDiet doložil, že principiální redukce kontextu o 40–60 % nesnižuje úspěšnost — scoreboard digest po kompresi je náš kandidát na tentýž efekt s normativní zárukou; formuluj jako testovatelnou hypotézu (H: podmínka D po kompresi ≤ tokeny podmínky A při vyšší konzistenci).

## B. Interoperabilita a vizualizace (mění §4)

### B.1 Datový model — mapování na standardy (NOVÉ, priorita P1 jen jako mapping doc, implementace P2)
Náš model má přesné protějšky v existujících standardech; nevymýšlej vlastní ontologii, napiš `docs/interop.md` s tímto mapováním a implementuj exporty ve fázi 1–2:
- **xAIF (JSON):** promluva v transkriptu = L-node; claim závazku = I-node; akt extrakce („agent tímto tvrdí") = YA-node (Asserting); incompatible_with = CA-node; consequences = RA-node. Export `scorekeeper export --format xaif`. Bonus: xAIF grafy umí zdarma vizualizovat OVA a zpracovat oAMF pipeline — okamžitá interoperabilita s argumentation-mining komunitou (a akademický most pro paper).
- **W3C PROV-O / PROV-JSON:** entitlement je doslova provenience — claim = prov:Entity; extrakce/tah agenta = prov:Activity; agent/uživatel/nástroj = prov:Agent; entitlement.refs → prov:wasDerivedFrom + prov:used; autorství → prov:wasAttributedTo. Supersedes řetězec zarovnej s dcterms:replaces/isReplacedBy. Export `--format prov-json`.
- **OpenTelemetry (P2):** volitelný emitter span-eventů (commitment.asserted, conflict.detected) — uživatelé Langfuse/LangSmith/AgentOps uvidí scorekeeper události ve svých trace, aniž bychom stavěli vlastní observabilitu.

### B.2 Konkurenční kontrola — výsledek (do README/paper)
Rešerše potvrdila mezeru: LangSmith, Langfuse, AgentOps i Braintrust jsou „letoví zapisovači" exekuce (spany, latence, tokeny); žádný neverzuje epistemický/sémantický stav agenta — vývoj tvrzení a rozhodnutí v čase. Nejblíž je LangGraph Time Travel (checkpointy stavu + fork), ale verzuje technický stav grafu, ne normativní strukturu závazků. Formulace pro README: "Observability tools record what the agent did; Scorekeeper records what the agent is committed to."

### B.3 Design `scorekeeper report` — REFINE §4.1
Převezmi ověřené vzory:
- **Split-pane:** vlevo chronologie (lineární osa sessions/tahů, milníky kompresí), vpravo stavově přesný graf závazků k vybranému okamžiku — výběr bodu na ose překreslí graf do stavu „jak vypadal scoreboard tehdy" (time-travel dotaz nad append-only logem; log to už umožňuje, jen ho čti).
- **Životní cyklus vizuálně:** superseded uzly se v aktuálním pohledu upozadí (nezmizí); při time-travel do minulosti se vykreslí jako plně aktivní. Konflikt = CA-vzor: červená hrana mezi dvěma živými uzly, nikoli přepis.
- **Collapsing** (Prov Viewer vzor): trsy závazků jednoho scope sbalitelné do makro-uzlu — jinak graf po delším projektu nebude čitelný.
- Volitelný Sankey pohled (PROV-O-Viz vzor) pro toky provenience: které zdroje (soubory, user zprávy) podpírají nejvíc závazků. P2.

### B.4 Prior art pro theory.md a paper (POVINNÉ doplnění related work)
Hamblin/Mackenzie **Commitment Stores** z formálních dialogových her (+ DGDL/DGEP platforma) jsou přímý předchůdce scoreboardu: závazek jako veřejná, testovatelná propozice (ne psychologické přesvědčení — řeší i Mooreův paradox), nemonotónní aktivní stav definovaný jako view nad immutable historií. To (a) validuje naši architekturu append-only log + generovaný scoreboard.md, (b) musí být citováno, jinak recenzent oprávněně namítne ignoranci 50 let literatury, (c) dává přesnou formulaci diferenciace: Scorekeeper = commitment store aplikovaný na LLM agenta, s dimenzí entitlement provenance a integrací do produkčního harnessu, což DGEP svět nemá.

## C. Backlog (P2) — nové položky
xAIF export, PROV-JSON export, OTel emitter, Sankey pohled, Game Engine Separation infrastruktura pro publikaci CommitBench.

## D. Akceptační kritéria — doplnění k §6
7. Judge pipeline implementuje A.1 (cizí rodina, S8, style-blind, trajektoriální rubrika); volba judge modelu zapsána jako ADR.
8. Statistický modul implementuje A.2 (Wilson/Bayes pro binární, smooth bootstrap pro spojité, clustered SE podle prostředí scénáře); meta-evaluace A.3 proběhla s CV ≤ 0.05 před plnou maticí.
9. `docs/interop.md` s mapováním na xAIF a PROV-O existuje; `docs/theory.md` doplněn o Commitment Stores (Hamblin, Mackenzie, DGDL/DGEP) v related work.
10. Bench ukládá Rollout Cards balíček pro každý publikovaný běh.
