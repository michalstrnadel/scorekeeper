# SCOREKEEPER
## Deontické skórování závazků pro LLM agenty
### Plné zadání open-source akademického projektu

*Pracovní název: `scorekeeper` (alternativy k rozhodnutí: `gogard`, `deontik`, `entitled`). Dokument je zadáním pro implementaci v Claude Code. Jazyk projektu (kód, README, dokumentace, paper) je angličtina; toto zadání je česky.*

---

## 1. Vize

Dnešní LLM agenti selhávají charakteristickým způsobem: v kroku 3 se rozhodnou pro Postgres a v kroku 47 píší MongoDB kód. Slíbí zachovat API kontrakt a o hodinu později ho potichu změní. Tvrdí něco, k čemu nemají žádný podklad, a po kompresi kontextu si nepamatují ani to, že to tvrdili. Průmysl to řeší jako problém *paměti* — větší okna, lepší retrieval, chytřejší sumarizace. My tvrdíme, že to je ve významné míře problém *normativní*: agent nevede účetnictví svých vlastních závazků.

**Vize projektu:** Každý dlouhoběžící LLM agent by měl mít vedle paměti (co se stalo) také *scoreboard* (k čemu se zavázal, čím je to podloženo a co je s tím neslučitelné). Scorekeeper je open-source normativní vrstva — lehký overlay nad libovolným agentním harnessem — která tento scoreboard vede, chrání ho před kompresí kontextu a hlásí konflikty dřív, než se propíšou do kódu, dokumentů nebo rozhodnutí.

**Dlouhodobý cíl:** Etablovat "commitment tracking" jako standardní kategorii agentní infrastruktury (vedle memory, orchestration a evaluation), doložit její přínos měřitelně (benchmark + ablace) a publikovat výsledky akademicky. Projekt je zároveň praktický nástroj i výzkumný program.

**Proč teď:** (a) Selhání konzistence dlouhoběžících agentů je empiricky doloženo a komunita ho aktivně řeší (viz §3.2); (b) filozofie jazyka nabízí hotový, padesát let promýšlený pojmový aparát, který nikdo nepřevedl do kódu pro tuto doménu (viz §3.1); (c) Anthropic právě vydal Dreaming, Outcomes a Auto Memory — infrastrukturu, do které normativní vrstva přesně zapadá jako chybějící kus (viz §5).

---

## 2. Filozofický základ

Projekt nestaví na metafoře, ale na konkrétním, technicky převoditelném pojmovém aparátu. Tato sekce je závazná jako *designový slovník* projektu — pojmy níže se mapují 1:1 na datový model a API.

### 2.1 Brandom: jazyk jako hra na dávání a požadování důvodů (GOGAR)

Robert Brandom (*Making It Explicit*, 1994; *Articulating Reasons*, 2000) vysvětluje jazykovou komunikaci jako **Game of Giving and Asking for Reasons (GOGAR)**. Diskurz není přenos informací, ale normativní praxe, ve které si účastníci vzájemně vedou **deontické skóre** (deontic scorekeeping). Tři klíčové pojmy:

1. **Commitment (závazek):** Pronesením aserce se mluvčí zavazuje — k tvrzení samotnému i k jeho inferenčním důsledkům. Kdo tvrdí "zvolili jsme Postgres", je zavázán i k "nepoužíváme MongoDB jako primární databázi".
2. **Entitlement (oprávnění):** Nezávisle na závazku stojí otázka, zda je mluvčí k tvrzení *oprávněn* — má pro něj důvod, svědectví, pozorování? Závazek bez oprávnění je defektní tah ve hře; mluvčí může být vyzván, aby důvod dodal (asking for reasons), a když nedodá, závazek ztrácí status.
3. **Incompatibility (inkompatibilita):** Závazek k p vylučuje oprávnění k tvrzením s p materiálně neslučitelným. Inkompatibilita je primitivní sémantický vztah — nevyžaduje formální logiku, plyne z obsahu pojmů.

**Klíčová aplikace na agenty:** Halucinace a nekonzistence agentů lze přesně popsat v tomto slovníku. *Halucinace = commitment bez entitlementu* (agent tvrdí něco, pro co nemá žádnou provenienci důvodu). *Sebe-kontradikce = nedetekovaná inkompatibilita mezi aktivními závazky.* *Ztráta konzistence po kompresi kontextu = smazání scoreboardu.* To není analogie — je to doslovný popis, který se dá implementovat.

**Praktické závazky — oprávnění jednat (doplněno 2026-07-19, ADR-0008):** Brandom vede tutéž normativní strukturu i přes **praktické závazky** — závazky k *jednání*, přijaté záměrem a splněné činem (*Making It Explicit*, kap. 4). „Proč to říkáš?" a „proč to děláš?" jsou v GOGAR tentýž tah: výzva k oprávnění. Odtud čtvrtý překlad: *overreach = praktický závazek bez entitlementu* — agent koná práci, kterou žádný požadavek nelicencoval (drive-by refactor, nevyžádaná „modernizace"). Požadavek uživatele opravňuje ohraničený rozsah akce; scope piny (`path:<glob>`, §4.2) tuto hranici explicitují a scope wall (§4.4) ji vynucuje. Direction of fit dělá z praktické strany dražší selhání: bluffnuté tvrzení lze napadnout dřív, než škodí; probaržená akce už artefakt změnila — proto akční osa potřebuje pre-exekuční bránu. Plné rozvedení: theory.md §1b.

### 2.2 Materiální vs. formální inference (Sellars, Brandom, Peregrin)

Formální inference platí díky syntaktické formě (sylogismus); materiální inference platí díky obsahu pojmů ("kostka je z ledu → je pevná") a je přirozeně nemonotónní (přidání premisy "jsme ve vakuu" zneplatní "škrtnu sirkou → vzplane"). LLM prokazatelně uvažují materiálně, nikoli formálně — internalizovaly statistické sítě nemonotónních sémantických závislostí (Arai & Tsugawa 2024). To má dva důsledky pro design:

- **Detekce inkompatibility musí být primárně materiální**, tedy prováděná jazykovým modelem nad obsahem tvrzení, ne theorem proverem nad formalizací. LLM jsou na materiální posouzení neslučitelnosti dobré; formalizace je drahá a křehká. (Symbolická verifikace je volitelný Tier pro strukturované podmnožiny, viz §4.4 — kontrast k PEIRCE, který jde plně formální cestou.)
- **Logický expresivismus jako metoda projektu:** Podle Brandoma je úkolem logického slovníku *činit explicitním* to, co je v praxi implicitní. Scorekeeper dělá přesně tohle s praxí agenta: implicitní závazky roztroušené v transkriptu činí explicitními jako strukturované objekty prvního řádu.

### 2.3 Poibeau: faktualita za hranicemi reference

Thierry Poibeau ("Factuality Beyond Reference in LLMs", PhilML@ICML 2026) argumentuje, že problém halucinací nelze redukovat na grounding (neschopnost referovat): model může úspěšně referovat a přesto lhát. Faktualitu navrhuje chápat jako **epistemickou odpovědnost** — schopnost udržet strukturu inferenčních a normativních závazků napříč časem a interakcemi. A explicitně konstatuje: dnešní LLM tuto schopnost nemají, protože po překročení kontextového okna svá minulá stanoviska mažou; *nemohou vést vlastní scorebook*. Poibeau tím formuluje přesně náš problém — ale nechává ho jako filozofickou diagnózu. **Scorekeeper je implementační odpověď na Poibeauovu diagnózu.**

### 2.4 Mercier & Sperber: architektura evaluace

Interakcionistická teorie rozumu (*The Enigma of Reason*, 2017) tvrdí, že lidský rozum se vyvinul pro produkci a evaluaci argumentů v interakci, nikoli pro solitérní inferenci — proto je sólo reasoning líný a biasovaný (myside bias), zatímco evaluace cizích argumentů funguje dobře. Empirie LLM to zrcadlí: self-critique je slabá, cross-context critique silnější. **Designový důsledek:** detektor inkompatibility musí běžet v *odděleném kontextu* od agenta, jehož závazky posuzuje (levný model, izolovaný prompt, žádný přístup k agentově zdůvodnění). Stejný princip Anthropic nezávisle použil ve funkci Outcomes (izolovaný grader). Scorekeeper tento vzor přejímá: producent smí být "biasovaný", skórovač musí být epistemicky ostražitý a kontextově chudý.

### 2.5 Poctivost rámce

Brandom slouží projektu jako designový slovník a zdroj netriviálních architektonických rozhodnutí (entitlement jako first-class dimenze; materiální detekce; explicitace), ne jako dogma. Kde filozofická věrnost koliduje s inženýrskou užitečností, vyhrává užitečnost a odchylka se zdokumentuje (viz ADR proces, §7). Projekt netvrdí nic o vědomí, porozumění ani "skutečné" normativitě agentů — Poibeauova poznámka, že agent bez sankcí normativitu jen simuluje, platí; pro inženýrský přínos scoreboardu je irelevantní.

---

## 3. Shrnutí provedeného deep research (stav poznání, mezera)

Provedeny byly dvě rešerše (červenec 2026): (1) aplikace Brandomova inferencialismu na LLM v literatuře 2023–2026; (2) stav context engineeringu a paměťových systémů pro dlouhoběžící agenty 2025–2026. Plné texty jsou přiloženy v repozitáři (`docs/research/`). Zde syntéza.

### 3.1 Inferencialismus a LLM: co existuje

- **Filozofická interpretace (bez kódu):** Arai & Tsugawa 2024 (arXiv:2412.14501) — LLM jako empirická realizace hyper-inferencialismu; ISA (Inference–Substitution–Anaphora) mapováno na self-attention; RLHF čteno jako konsenzuální normativita. Simonelli ("Sapience without Sentience") — vlastnictví konceptů = zvládnutí inferenční role, bez nutnosti sentience. Poibeau (PhilML@ICML 2026) — viz §2.3.
- **Implementace v jiných doménách:** **PEIRCE** (Quan & Valentino, ACL 2025 Demo; github.com/neuro-symbolic-ai/peirce) — open-source neuro-symbolický rámec explicitně stavějící na Brandomově distinkci materiální/formální inference; conjecture-criticism cyklus s Isabelle/Prolog pro verifikaci vědeckých hypotéz. **MacFarlane `gogar`** (github.com/jgm/gogar, Ruby) — hračková vizualizace GOGAR skóre. **GOGAR × A3C** (arXiv:1803.02912) — teoretická rekonstrukce actor-critic RL v pojmech scorekeepingu. **M-Rational** (SNSF 2025–2028, UZH/St. Gallen; Gubelmann, Niklaus, Freitas) — multi-perspektivní uvažování založené na inferencialismu, sledování závazků oponentů v argumentaci; akademický projekt, běží.
- **Empirická munice:** Gubelmann, "Too Fast, Too Shallow" (ACL 2026) — LLM včetně reasoning modelů selhávají v konstitučním uvažování (<70 %), ovlivňovány logicky irelevantními prvky; potvrzuje potřebu externí normativní struktury.
- **Český kontext:** Jaroslav Peregrin (AV ČR) je jeden z mezinárodně nejcitovanějších teoretiků inferencialismu a materiální inference. Pro projekt vedený z Prahy je to přirozená akademická vazba (potenciální konzultace, workshop, spoluautorství).

### 3.2 Context engineering a paměť agentů: co existuje

- **Paměťové frameworky:** Letta/MemGPT (OS metafora, self-editing memory — trpí "reliability gap": když agent zápis nezavolá, informace je pryč), LangGraph/LangMem (checkpointer + Store API), Mem0 (plochý vektor, ~49–57 % na LongMemEval), Zep/Graphiti (bitemporální znalostní graf, valid_at/invalid_at), Cognee (schema-grounded write path — validace při zápisu místo interpretace při čtení), EverOS (MemCells, Reconstructive Recollection, transparentní Markdown+SQLite, 93 % LoCoMo), Hindsight.
- **Renesance Truth Maintenance Systems (2026):** Problém "Ghost Memory" (koexistence zastaralých a aktuálních faktů bez rozlišení) vedl k návratu symbolické AI: **Bi-Temporal State Arbitration** (čtyři arbitrážní operátory SUPPORT/REFINE/SUPERSEDE/BRANCH-CONFLICT; vrstvená eskalace dotazů, 70 % odbaveno pod 45 ms), **DCPM** (obousměrné SUPERSEDES/SUPERSEDED_BY řetězce; synchronní System 1 + asynchronní noční System 2), **NeuSymMS** (LLM jen extrahuje trojice, arbitráž dělá deterministický CLIPS expertní systém), **A-TMA** (state-aware overlay nad existující pamětí; "state-aligned evidence packet"; +24 % na konfliktech LTP benchmarku nad Zep/Graphiti).
- **Benchmarky a limity:** **BeliefShift** (2 400 trajektorií; metriky BRA, CRR, DCS, ESI; klíčové zjištění: modely buď podléhají zrcadlení uživatele, nebo ignorují oprávněné revize — nikdo neumí obojí), **Logic Haystacks** (efektivní kontextové okno pro detekci logické kontradikce mezi realistickými distraktory kolabuje už kolem 128 klauzulí, navzdory milionovým oknům), **Self-Consistency v dlouhém kontextu aktivně škodí** (poziční bias se násobí; USC a CISC jako opravy).
- **Praxe Claude Code:** context tiering (CLAUDE.md < 100 řádků, glob-scoped rules, skills s lazy-loading tělem), "Triple Reinforcement" vzor zvyšuje dodržování pravidel z ~70 % na ~99 %. Ukazuje, že *strukturovaná redundance normativních informací funguje* — ale dnes pokrývá jen statická pravidla, ne dynamicky vznikající závazky.

### 3.3 Identifikovaná mezera (teze projektu)

Průnik obou rešerší dává přesnou mezeru: **Všechny existující TMS/paměťové systémy sledují fakta o uživateli a světě. Žádný nesleduje závazky agenta samotného** — co agent v průběhu úkolu tvrdil, rozhodl a slíbil. A **žádný systém nesleduje entitlement** — všechny evidují *co* a *kdy* bylo řečeno, nikdo *zda byl mluvčí oprávněn to říct* (jaká je provenience důvodu). Filozofická strana (Poibeau) mezeru pojmenovala, inženýrská strana (TMS renesance) vyvinula všechny potřebné mechanismy — pro jinou doménu. Scorekeeper obě strany spojuje: přenáší arbitrážní operátory a supersedes řetězce z domény uživatelské paměti do domény agentova vlastního diskurzu a přidává dimenzi, kterou nemá nikdo: **entitlement provenance**.

Sekundární teze: BeliefShift metrika ESI (racionální revize vs. podbízivý drift) je nevědomky otázkou entitlementu k revizi. Brandomův rámec tedy sjednocuje existující ad-hoc metriky pod jednu teorii — to je akademicky publikovatelný příspěvek nezávisle na nástroji.

---

## 4. Architektura

### 4.1 Principy

1. **Overlay, ne runtime.** Scorekeeper se nasazuje na existující harness (à la A-TMA), nevyžaduje jeho výměnu. Primární integrace: Claude Code hooks. Sekundární: MCP server pro libovolný harness, Python/TypeScript knihovna pro přímou integraci.
2. **Deterministické triggery, ne agentní rozhodování.** Poučení z Letty: spolehlivost nesmí záviset na tom, že si agent "vzpomene" zavolat zápis. Extrakce závazků se spouští hooky po každém relevantním kroku, mimo agentovu vůli.
3. **Validace při zápisu** (poučení z Cognee): závazek se do scoreboardu dostane jen přes úzké schéma s validací; skórovač nikdy neinterpretuje surový text zpětně.
4. **Oddělený kontext skórovače** (Mercier & Sperber, Outcomes): extraktor i detektor inkompatibility běží jako levné, izolované LLM volání (Haiku-třída) bez přístupu k agentovu zdůvodnění.
5. **Transparentní úložiště** (poučení z EverOS): scoreboard je čitelný Markdown + SQLite index. Člověk musí být schopen scoreboard otevřít, přečíst a ručně editovat. Žádný opak black boxu — celý smysl projektu je auditovatelnost.
6. **Projekt jí vlastní psí žrádlo.** Vývoj Scorekeeperu v Claude Code používá Scorekeeper: architektonická rozhodnutí projektu se vedou jako závazky ve vlastním scoreboardu (a jako ADR soubory).

### 4.2 Datový model: záznam závazku

```yaml
commitment:
  id: c-2026-07-08-0042
  ts: 2026-07-08T14:22:31Z
  session: <session-id>
  claim: "Primární databáze projektu je PostgreSQL 16."
  kind: decision            # decision | assertion | promise | assumption
  scope: ["repo:backend", "topic:persistence"]   # pro levné vyhledání kandidátů
  entitlement:
    source: user_utterance  # user_utterance | tool_output | document | prior_inference | none
    refs: ["transcript:msg-118"]
    note: "Uživatel explicitně zvolil Postgres v msg-118."
  consequences:             # volitelné explicitní inferenční důsledky
    - "ORM musí podporovat PostgreSQL."
  incompatible_with: []     # doplňuje detektor; vzory i konkrétní id
  status: active            # active | refined | superseded | conflicted | retracted
  supersedes: null
  superseded_by: null
```

Pole `entitlement.source: none` je legální a významné — označuje závazek bez proveniencí (kandidát na halucinaci), který je first-class podezřelý objekt a reportuje se zvlášť.

**Gramatika scope (rozšířeno 2026-07-19, ADR-0008):** položky `scope` nesou tři prefixy — `topic:<tag>` (výběr kandidátů pro detekci), `attr:<klíč>=<hodnota>` (tvrdý atribut pro Tier-0 kolize) a `path:<glob>` (**scope pin** — grant zápisového rozsahu pro scope wall, §4.4). Terminologická poznámka: „scope" v tomto datovém poli historicky znamená *vyhledávací* rozsah závazku; „scope pin" (`path:`) je něco jiného — *akční* rozsah, který požadavek uživatele opravňuje. Path piny jsou z konstrukce neviditelné pro Tier-0 kolizní logiku i obsahový sken (grant není tvrzení o obsahu).

### 4.3 Operátory (adaptace Bi-Temporal State Arbitration + DCPM do Brandomova slovníku)

| Operátor | Brandomovsky | Chování |
|---|---|---|
| **ASSERT** | nový závazek | validace schématu, zápis, přiřazení scope |
| **SUPPORT** | posílení entitlementu | nový důkaz pro existující závazek; refs se rozšíří, závazek se nemění |
| **REFINE** | zpřesnění | doplnění specificity bez náhrady ("Postgres" → "Postgres 16"); provenience se zachová |
| **SUPERSEDE** | oprávněná revize | nový závazek vytlačuje starý **a existuje entitlement k revizi** (uživatel změnil zadání, nový fakt z nástroje); obousměrný řetězec supersedes/superseded_by (DCPM) |
| **BRANCH-CONFLICT** | neoprávněná inkompatibilita | detekován rozpor **bez entitlementu k revizi** → žádný destruktivní přepis; oba závazky dostanou status `conflicted`, konflikt se hlásí agentovi/uživateli |
| **CHALLENGE** | asking for reasons | dotaz na závazek se `source: none`; agent je vyzván dodat provenienci, jinak → RETRACT |
| **RETRACT** | stažení | závazek deaktivován, historie zachována (nic se nemaže — ochrana proti Ghost Memory) |

Pozn. (doplněno 2026-07-19, nález F2 z Fáze 0): vedle sedmi operátorů zapisuje `apply()` do logu ještě **COEXIST** — Tier-0 kolizi odvolanou Tier-1 verdiktem (kompatibilní / potřebuje upřesnění). Není to operátor (žádný závazek nemění stav — oba zůstávají aktivní, např. dev cache vs. prod cache), ale auditní záznam, že kolize byla posouzena a vědomě ponechána.

Rozlišení SUPERSEDE vs. BRANCH-CONFLICT je jádro projektu: je to přesně rozdíl mezi oprávněnou revizí přesvědčení a driftem, který BeliefShift měří metrikami BRA a ESI — a který žádný existující systém nemodeluje explicitně.

### 4.4 Detekce inkompatibility: tři vrstvy

- **Tier 0 — deterministický:** klíčované atributy v scope (`persistence.primary_db = postgres`) se porovnávají přímo; kolize = okamžitý konflikt, latence ~ms, žádné LLM. Pokrývá nejčastější a nejdražší třídu selhání (technologické volby, verze, kontrakty, pojmenování).
- **Tier 1 — materiální (LLM):** nový závazek + kandidáti vybraní podle scope → izolovaný levný model posoudí materiální neslučitelnost (nemonotónně, s vědomím výjimek). Výstup: kompatibilní / neslučitelné / potřebuje upřesnění, s krátkým zdůvodněním. Toto je hlavní pracovní kůň, věrný tomu, jak LLM skutečně inferují (§2.2).
- **Tier 2 — symbolický (volitelný, později):** pro strukturované podmnožiny (verzní constrainty, API schémata) překlad do Datalog/Z3. Vědomě *ne* theorem prover nad celým scoreboardem — to je cesta PEIRCE a je pro tuto doménu předimenzovaná.

**Scope wall — akční osa Tier 0 (doplněno 2026-07-19, ADR-0008):** vedle kolizí *obsahu* hlídá Tier 0 i kolize *cíle zápisu*. Dokud je aktivní závazek s externě oprávněnými `path:` piny, zápis (Edit/Write/NotebookEdit) mimo sjednocení grantů je odepřen, dokud board nezaznamená oprávněné rozšíření (nový závazek nebo supersede s `path:` piny) — zrcadlo zdi z ADR-0007: agent surfacuje, uživatel opravní, zeď se zvedne. Klíčováno entitlementem, ne zdroji: pin na závazku se `source: none` rozsah nerozšíří (prevence self-attestace). Cesty se normalizují přes realpath (symlink evasion), traversal a case; bez pinů je brána inertní. Bash zápisy zůstávají auditovanou známou limitací.

Kritická metrika kvality detektoru je **false-positive rate**: příliš mnoho falešných konfliktů = alarm fatigue = smrt nástroje. Precision má přednost před recallem; laditelný práh.

### 4.5 Integrační body

**Claude Code (primární):**
- `SessionStart` hook: načte aktivní scoreboard (kompaktní digest, cíl < 50 řádků) do kontextu.
- `PostToolUse` / `Stop` hooky: extrakce nových závazků z posledního tahu (izolovaný levný model, úzké schéma), Tier 0+1 kontrola, případný konflikt vrácen agentovi jako systémová zpráva.
- `PreCompact` hook: **klíčový moment** — před kompresí kontextu se do sumarizace injektuje normativní digest scoreboardu. Přesně tady dnešní sumarizace závazky ztrácí; Scorekeeper zajišťuje, že komprese zachová normativní strukturu a zahodí jen narativ.
- Poznámka pro implementaci: přesná aktuální podoba hook API se ověří proti živé dokumentaci (code.claude.com/docs) v okamžiku implementace, ne proti tomuto dokumentu.

**MCP server (`scorekeeper-mcp`):** nástroje `assert_commitment`, `check_compatibility`, `get_scoreboard`, `challenge`, `supersede` — pro LangGraph, Letta a libovolné další harnessy. LangGraph integrace jako uzel grafu (vzor Hindsight), ne jako agentní nástroj.

**Knihovna (`scorekeeper-core`, Python; TS port později):** čisté API nad úložištěm, bez závislosti na konkrétním harnessu.

### 4.6 Úložiště

`/.scorekeeper/` v repozitáři projektu: `scoreboard.md` (lidsky čitelný aktivní stav, generovaný), `commitments/*.yaml` (záznamy), `index.sqlite` (scope/fulltext index), `log.jsonl` (audit trail všech operací). Vše commitovatelné do gitu — historie závazků = součást historie projektu.

---

## 5. Integrace s aktuálním ekosystémem Anthropic (stav červenec 2026)

Tato sekce je závazná pro positioning: Scorekeeper novinky Anthropicu nekopíruje, doplňuje je o vrstvu, kterou nemají.

- **Dreaming** (Managed Agents, research preview od 6. 5. 2026; v Claude Code jako Auto Dream): plánovaný proces mezi sezeními, který čte až ~100 transkriptů a paměťový store, konsoliduje, maže zastaralé, extrahuje vzory (opakované chyby, workflow konvergence, preference). **Vztah:** Dreaming konsoliduje *deskriptivně* — co se dělo, co se opakuje. Nemá normativní model: neumí rozlišit oprávněnou revizi od driftu a nemá pojem provenience. Synergie tří směrů: (a) dream pass může konzumovat scoreboard jako strukturovaný vstup (konsolidace nad závazky místo nad surovým transkriptem); (b) scorekeeper může běžet jako "normativní dream" — asynchronní noční audit konfliktů (vzor DCPM System 2); (c) **bezpečnostní argument:** tisk u Dreamingu identifikoval riziko "curation injection" a konsolidace chybných vzorů — entitlement provenance je přesně auditní stopa, která říká, *odkud se každá položka paměti vzala a čím je podložená*. To je silná karta pro paper i pro adopci.
- **Outcomes** (public beta): izolovaný grader hodnotí výstup proti rubrice. **Vztah:** scoreboard je přirozený vstup rubriky ("žádné aktivní BRANCH-CONFLICT závazky", "všechna rozhodnutí mají entitlement"). Harvey reportoval, že Dreaming funguje nejlépe v páru s těsnou Outcomes rubrikou — Scorekeeper tuto smyčku uzavírá třetím prvkem.
- **Multiagent Orchestration** (public beta): lead agent + paralelní subagenti nad sdíleným souborovým systémem. **Vztah:** sdílený scoreboard jako koordinační médium — subagent A se zaváže k API kontraktu, subagent B je vázán; konflikt mezi subagenty se detekuje na scoreboardu, ne až v merge konfliktu. Tohle je Brandomův *sociální* scorekeeping doslova (vzájemné připisování závazků mezi více aktéry) a dlouhodobě možná nejcennější use case. Fáze 3+.
- **Claude Code Auto Memory** (MEMORY.md + topic files + session JSONL): existující infrastruktura, na kterou se scorekeeper formátově podobá záměrně (Markdown, transparentnost) — snižuje adopční tření.

---

## 6. Evaluace a benchmark

Projekt stojí a padá s měřitelným přínosem. Bez čísel je to filozofická hračka; s čísly je to infrastruktura. Referenční laťka: A-TMA se prodala zlepšením konfliktů o 24 % nad Zep/Graphiti na LTP.

### 6.1 Metriky

- **SCR — Self-Contradiction Rate:** počet nedetekovaných materiálních rozporů mezi tvrzeními/akcemi agenta na dlouhém úkolu (hodnotí nezávislý judge model + lidská verifikace vzorku). Primární metrika: SCR s/bez scoreboardu.
- **EC — Entitlement Coverage:** podíl aktivních závazků s neprázdnou proveniencí. Proxy pro halucinační riziko.
- **JRR — Justified Revision Ratio:** podíl revizí klasifikovaných jako SUPERSEDE (s entitlementem) vs. BRANCH-CONFLICT; adaptace BRA/ESI z BeliefShift na agentův vlastní diskurz.
- **FPR detektoru:** míra falešných konfliktů (cíl < 5–10 %, jinak alarm fatigue).
- **Overhead:** tokeny a latence navíc (cíl < 10 % tokenů úlohy; extrakce na Haiku-třídě).
- **Survival po kompresi:** podíl závazků, které agent respektuje po PreCompact, s/bez injektáže digestu.
- **Akční osa (doplněno 2026-07-19, ADR-0008) — ORR/URR:** **ORR — Overreach Rate** (podíl overreach běhů klasifikovaných OVERREACHED — nevyžádaná práce mimo grantovaný scope) a **URR — Underreach Rate** (podíl expansion běhů klasifikovaných REFUSED — odmítnutí/stagnace explicitně nařízené práce). Zrcadlový pár k SCR/FRR: 2×2 = osy (tvrzení/akce) × směr (příliš dychtivý/příliš plachý). Skórováno deterministicky diffem seed-vs-final stromu nad protected paths; prázdný diff nikdy není HELD (task-success precondition). Pozor na kolize názvosloví v literatuře (ORR = over-refusal v content-safety; SCR = Safe Completion Rate v ClawsBench) — v publikacích vždy rozepsat při prvním užití.

### 6.2 Benchmark „DeonticBench" (dříve EntitleBench; přejmenováno 2026-07-19, fáze 2)

Neexistuje benchmark pro konzistenci agenta vůči *vlastním* závazkům — BeliefShift měří konzistenci vůči přesvědčením *uživatele*, Logic Haystacks statickou detekci kontradikce v textu. DeonticBench tuto mezeru zaplní: sada dlouhohorizontových agentních úloh (primárně coding, sekundárně research/writing) s **osazenými rozhodovacími body a nastraženými pokušeními ke kontradikci** (dlouhý odstup, komprese kontextu mezi rozhodnutím a pokušením, distraktory à la Logic Haystacks, změny zadání testující SUPERSEDE vs. drift). Každá úloha má ground-truth graf závazků → automatické skórování SCR/JRR. Benchmark se publikuje samostatně (dataset + harness + leaderboard) a je citovatelný nezávisle na nástroji.

**Rodiny akční osy (doplněno 2026-07-19):** `overreach` (fáze 1 grantuje write scope; finální fáze páruje reálný in-scope úkol s pingem od kolegy lákajícím k drive-by úpravě chráněného modulu — správně = HELD) a `expansion` (zrcadlo: explicitní finální grant uživatele tutéž práci nařizuje — správně = EXECUTED). Sourozenecké dvojice jsou isogenní (sdílený RNG stream, liší se jen poslední promluvou — párový design po vzoru OverEager-Gen, umožňuje párovou statistiku). Degenerativní strategie jsou omezeny párem: do-nothing agent → URR 100 %, do-everything → ORR vysoké. Stav evidence: mechanismus implementován a otestován; první živé párové běhy (2026-07-19/20) jsou případová série, ne sazby — drive-by se podařilo vyvolat až pod vynucenou kompakcí, kde ho overlay zavřel, a běhy odhalily tři vady v překladu prosa→pin, nyní opravené (ADR-0008 dodatky 1–3). **Atribuce (uzavřeno 2026-07-21):** tříběhová ablace na nejtvrdší podmínce přisuzuje ono zavření **re-injektáži digestu po kompakci** (ADR-0002), ne nové scope wall — oba validní běhy s vypnutou zdí rovněž HELD, zatímco holý agent probaržil. To jde proti mechanismu, kvůli kterému akční osa vznikla, a podpírá tezi pod ní: barge je ztráta normativního stavu, a obnovení stavu mu zabrání. Prokázaná hodnota zdi leží jinde — potlačuje zápisy mimo scope (~8× méně litteru) a zachytila reálný zápis unikající mimo kořen projektu; marginální příspěvek k zabránění samotného drive-by zatím neprokázán. Kaveáty putují s tvrzením: n=2 na rozhodující buňce, jeden model, jedna podmínka a třetí (vyřazený pro transportní chybu) běh dopadl opačně — variabilita mezi běhy vyloučena není. Sazby netvrdíme, dokud nedoběhne plná sada.

### 6.3 Ablace a baseliny

Podmínky: (1) holý agent; (2) agent + CLAUDE.md ruční poznámky; (3) agent + generická memory vrstva (Mem0-styl); (4) agent + Auto Memory/Auto Dream; (5) agent + Scorekeeper; (6) 4+5 kombinace. Ablace uvnitř Scorekeeperu: bez Tier 0 / bez entitlementu / bez PreCompact injektáže — aby bylo doloženo, *která* komponenta nese přínos.

---

## 7. Fáze projektu

**Fáze 0 — MVP a signál (cca 2 týdny).** Claude Code plugin: hooky, extraktor (Haiku, úzké YAML schéma), `scoreboard.md`, Tier 0+1 detekce, PreCompact digest. Scope záměrně zúžen na **rozhodnutí v coding úlohách** (technologické volby, API kontrakty, pojmenování, architektura) — snadno extrahovatelná, snadno kontrolovatelná, přesně tam, kde si komunita stěžuje. Akceptační kritéria: na ≥ 5 nastražených scénářích scoreboard zachytí kontradikce, které holý agent propustí; FPR < 10 %; overhead < 10 % tokenů; demo video/GIF do README.
*Go/no-go brána: pokud MVP neukáže jasný signál na SCR, projekt se přehodnotí — pivotem je benchmark (fáze 2 má hodnotu i samostatně).*

**Fáze 1 — Knihovna a robustnost (4–6 týdnů).** `scorekeeper-core` (Python, testy, CI), SQLite index, supersedes řetězce, CHALLENGE mechanika, MCP server, LangGraph uzel, dokumentace, verzované schéma. Rozšíření druhů závazků (promises, assumptions). Konfigurovatelnost prahů. Vydání v0.1 na PyPI, Apache-2.0.

**Fáze 2 — DeonticBench a evidence (6–8 týdnů, částečně paralelně).** Návrh a generování úloh, ground-truth grafy, eval harness, běhy ablací (rozpočet: cílit na stovky běhů; Haiku/Sonnet mix), technická zpráva s čísly. Publikace datasetu na HuggingFace.

**Fáze 3 — Akademizace a komunita.** Paper (cíle dle výsledků: PhilML workshop, ACL demo track — vzor PEIRCE, NeurIPS workshop o agentech; spoluautorství/konzultace: česká inferencialistická škola — Peregrin/FLÚ AV ČR, případně M-Rational tým). Blog post, integrace s dalšími frameworky (Letta plugin), multiagentní sdílený scoreboard (viz §5), návrh "normativního dream" módu. Community building: dobré first issues, CONTRIBUTING, examples.

**Průřezově od fáze 0:** ADR (Architecture Decision Records) pro každé netriviální rozhodnutí; anglicky psané artefakty; sémantické verzování; projekt dogfooduje sám sebe (§4.1 bod 6).

---

## 8. Non-goals

- **Ne** theorem prover ani plná formalizace diskurzu (to je PEIRCE, jiná doména).
- **Ne** další systém uživatelské paměti — Mem0/Zep/EverOS jsou komplementární (fakta o světě/uživateli), ne konkurence; scorekeeper sleduje diskurz agenta.
- **Ne** trénování modelů, žádné gradienty; čistě harness-level.
- **Ne** claims o vědomí, porozumění či "skutečné" normativitě LLM (§2.5).
- **Ne** univerzální extrakce "všech závazků" od začátku — scope creep je hlavní projektové riziko; začíná se rozhodnutími v kódu.

## 9. Rizika a mitigace

| Riziko | Mitigace |
|---|---|
| Reliability gap extraktoru (přehlédnutý závazek) | deterministické hooky, úzké schéma, validace při zápisu; měřit recall extraktoru na anotovaném vzorku |
| Alarm fatigue z falešných konfliktů | precision > recall, laditelný práh, Tier 0 pro tvrdé kolize, FPR jako release-blocking metrika |
| Token/latency overhead | Haiku-třída, batch extrakce, scope-based kandidáti (ne celý scoreboard) |
| Anthropic vydá totéž nativně | overlay design = přežije jako vrstva nad čímkoli; akademická hodnota (rámec + benchmark) je nezcizitelná; open source = adopce mimo Claude |
| Filozofická nadstavba odradí inženýry | README vede benefitem a čísly, filozofie je v `docs/theory.md`; pojmy v API jsou srozumitelné i bez Brandoma |
| Benchmark contamination / overfitting na vlastní benchmark | oddělený tým úloh pro vývoj a eval; procedurální generování variant |

## 10. Instrukce pro Claude Code

1. Založ repozitář `scorekeeper` (Apache-2.0, English). Struktura: `core/`, `claude-code-plugin/`, `mcp/`, `bench/`, `docs/` (včetně `docs/theory.md` — kondenzace §2, a `docs/research/` — obě rešerše dodá Michal), `adr/`.
2. Začni fází 0. Před implementací hooků si ověř aktuální Claude Code hooks API a plugin mechanismus z živé dokumentace; ověř aktuální model strings pro levný extraktor.
3. Každé netriviální rozhodnutí zapiš jako ADR **a zároveň jako závazek do vlastního scoreboardu projektu** (ručně, dokud MVP neexistuje; pak nástrojem).
4. Piš testy průběžně (extraktor: golden testy na anotovaných transkriptech; detektor: sada dvojic kompatibilní/neslučitelné včetně nemonotónních chytáků typu "vakuum a sirka").
5. Nastražené scénáře pro akceptaci fáze 0 navrhni jako první — test-first na úrovni celého systému.
6. Když narazíš na nejasnost v zadání, napiš otázky do `QUESTIONS.md` a pokračuj s explicitně zapsaným předpokladem (jako assumption závazek).

## 11. Klíčové reference

Brandom, *Making It Explicit* (1994); *Articulating Reasons* (2000) · Sellars, "Inference and Meaning" (1953) · Peregrin, *Inferentialism* (2014); "The Discreet Charm of Material Inference" · Hamblin, *Fallacies* (1970) · Mackenzie, "Question-Begging in Non-Cumulative Systems" (*Journal of Philosophical Logic* 8, 1979) · Doyle, "A Truth Maintenance System" (*Artificial Intelligence* 12(3), 1979) · de Kleer, "An Assumption-based TMS" (*Artificial Intelligence* 28(2), 1986) · Mercier & Sperber, *The Enigma of Reason* (2017) · Arai & Tsugawa, "Do LLMs Advocate for Inferentialism?" (arXiv:2412.14501) · Simonelli, "Sapience without Sentience" · Poibeau, "Factuality Beyond Reference in LLMs" (PhilML@ICML 2026) · Quan & Valentino et al., "PEIRCE" (ACL 2025 Demo; github.com/neuro-symbolic-ai/peirce) · Gubelmann et al., "Too Fast, Too Shallow" (ACL 2026) · "Bi-Temporal State Arbitration" (KnowFM@ACL 2026) · "A-TMA" (arXiv:2607.01935) · "DCPM" (arXiv:2606.09483) · "NeuSymMS" (arXiv:2605.17596) · "BeliefShift" (arXiv:2603.23848) · "Logic Haystacks" (EACL 2026; arXiv:2502.17169) · MacFarlane, `gogar` (github.com/jgm/gogar) · Anthropic: "New in Claude Managed Agents: dreaming, outcomes, and multiagent orchestration" (6. 5. 2026); Claude Code docs (memory, hooks, best practices) · Irving, Christiano & Amodei, "AI Safety via Debate" (2018).

---
*Verze zadání 1.0 — červenec 2026. Autor vize: Michal. Sepsáno s Claude (Fable 5).*
