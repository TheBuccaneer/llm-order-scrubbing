# Projektstand

Stand: 03.11.2026

## Aktuelle Etappe
Der **Scheduler-/BOS-Entscheidungstest** vom 03.11. steht in
`docs/scheduler-bos-entscheidung-20261103.md`. Auf gepaarter neuer
Fallfolge mit je 32 positiven BOS-Gruppen traf der vollständige
Clientzeit-Beobachter T2 unter C0 21/32 und unter C1 11/32.
C1 behielt einen binären Blockschluss-Rangkanal (AUC 0,813),
obwohl die vorher fixierte absolute 780-ms-Regel in einer getrennten
ersten C1-Sitzung scheiterte. Vier kurze instrumentierte Gruppen
zeigen, wie die unterschiedlichen Prefill-Schritte und gemeinsame
Decode-Schritte zu den Abschlussmustern passen. Ein fester Slot
glättete sie im **idealisierten Replay** gegen zusätzliche
individuelle Wartezeit; keine neue Freigaberegel wurde gebaut.
Empfehlung: ein eng begrenztes empirisches Nachfolgepaper zu
Information nach BOS, Schedulerabhängigkeit und Schutzkosten
entwerfen; noch keine allgemeine Sicherheits- oder Neuheitsgarantie.
Alle neuen Backend- und Proxyprozesse sind beendet.

Die prospektive C1-Direktprüfung vom 03.11. ist in
`docs/c1-cocompletion-20261103.md` dokumentiert. Die zuvor fixierte
Paarabstandsregel bestimmte in einer frischen, balancierten Serie mit
neuem Backend-Start die Cacheposition 32/32 Mal (95-%-Wilson-Intervall
89,3–100 %); R1 erreichte 11/32, T2 und RT je 31/32. Vier
unvorgewärmte Kontrollen zeigten keinen engen Antwortabstand.
Der Befund ist ein lokaler Mechanismuskandidat unter C1-Direktfreigabe,
kein Beleg für BOS-Leakage, allgemeine Übertragbarkeit oder höhere
Genauigkeit als T2. Alle 36 Gruppen und 144 Antworten sind vollständig;
Backend und Proxy sind beendet.

3 – Technische Optionen und Paper-Richtung bewertet. Der lokale BOS-
Mechanismus, seine Konfigurationsabhängigkeit, stärkere Clientbeobachter
und der Fallback eines festen Freigabeslots wurden in begrenzten,
getrennten Messsitzungen geprüft. Entscheidung und alle Grenzen stehen
in `docs/entscheidungsvalidierung-20261102.md`.
Der anschließende Release-Boundary-Test ist in
`docs/release-boundary-20261102.md` dokumentiert: neue Fallfolge,
32 C0-Positive (binäre Früh-/Spätposition 31/32), 16 C1-Positive
(8/16) und 16 markierte Cache-aus-Kontrollen (8/16). Die
Vierklassenregel verbessert T2/RT nicht. Empfehlung: als
Schutzgrenzen-Befund weiterführen, nicht als eigenständigen
Angriffsclaim.
Der nachfolgende Test einer **einheitlich späteren Freigabe nach
1.200 ms** steht in `docs/late-release-20261102.md`: 56/56
Vierergruppen einschließlich Kontrollen vollständig, 0 späte
Einzelfreigaben, im neuen 32er-Holdout höchstens 10/32 für die
geprüften Clientbeobachter. Die gepaarte Nachrechnung auf 108
alten 24-Token-Traces ergibt median 150 ms zusätzliche
individuelle Wartezeit. Das gilt nur, solange alle Antworten
vor dem neuen Slot bereit sind; der bisherige Fallback bleibt
danach bestehen.
Der anschließende **kausale Offline-Pilot** in
`docs/causal-release-pilot-20261102.md` verglich auf 108 vorhandenen
24-Token-Gruppen BOS, feste Slots und zwei periodische Gruppenregeln.
Beide periodischen Regeln verhindern im idealen Replay Einzel-Fallbacks,
geben über den gewählten Freigabetick aber erneut Completion-Information
preis. Ein explorativ auf 1.160 ms kalibrierter fester Slot deckte alle
108 Spuren ab und spart modelliert 40 ms je Antwort gegenüber 1.200 ms.
Das ist weder live bestätigt noch ein neuer Schutzalgorithmus. Die
abgeleiteten Rohzeilen stehen unter `results/causal-release-20261102/`.
Der folgende **Zufallsslot-Pilot** in
`docs/randomized-release-pilot-20261102.md` prüfte drei einfache
zustandsunabhängige 50:50-Mischungen auf denselben 108 Gruppen. Jeder
feste Mitteltermin hatte in den Entwicklungsdaten geringere oder
gleiche mittlere Wartezeit und geringeres oder gleiches Fallback-Risiko;
die breite Mischung zeigte zusätzlich ein clientseitiges Zeitsignal.
Keine der Mischungen begründet derzeit einen Methodenbeitrag. Keine
neue GPU-Messung oder Änderung der produktiven Regel.

## Bisher umgesetzt
- Privates GitHub-Repository erstellt.
- Lokale Git-Verbindung eingerichtet.
- Projektverzeichnisse angelegt.
- .gitignore, AGENTS.md und README.md erstellt.
- Repository am Messrechner unter `/home/rock/projects/llm-order-scrubbing`
  vorgefunden; `main`, Ausgangscommit `7690f03`, Arbeitsbaum vor Beginn sauber.
- Arbeitsauftrag, AGENTS.md, README.md, diesen Stand und docs/quellen.md gelesen.
- Hardware und vorhandene Laufzeitumgebungen lesend erfasst (siehe unten).
- Auf „Dann bitte gleich sichten“: lokale Projekt-/Dokumentablagen sowie den
  dokumentierten ordleak-Commit über die GitHub-Verbindung lesend gesichtet.
- Auf „weiter“: vorhandene Python-3.13-Umgebung auf Importierbarkeit und
  CUDA-Geräteerkennung geprüft; technische Quellen und relevante Abschnitte
  von PROMPTPEEK, OptiLeak und SafeKV gezielt aktuell nachgelesen.
- Auf das nächste „weiter“: lokalen Qwen-Snapshot mit vLLM gestartet, genau
  eine Anfrage mit einem Ausgabetoken beantwortet und Server beendet.
- Auf „vllt nochmal probieren?“: denselben Server erneut gestartet und mit
  einer kurzen Chat-Anfrage eine sichtbare vollständige Antwort geprüft.
- Auf „einfach mal weitermachen“: drei kontrollierte Anfragen zur
  Prefix-Cache-Wiederverwendung und Salt-Trennung ausgeführt; Rohantworten
  und Serverlog im Repository abgelegt.
- Auf „gezielte Machbarkeit“: 108 balancierte Zweier-Durchläufe mit zwei
  Tokenbudgets einschließlich einer Wiederholung durchgeführt und ausgewertet.
- Auf „weiter explorativ“: 188 zusätzliche Zweier-/Vierer-Durchläufe mit
  expliziter Prefill-Schwelle und passender Cache-aus-Kontrolle durchgeführt;
  Rangabstände und Rohdaten in `results/full-order-20261102/auswertung.md`.
- Auf „zwei weitere Möglichkeiten“ und „erst Security-Paper prüfen“:
  PROMPTPEEK, EarlyBird, OptiLeak und die Contention-Arbeit an den
  entscheidenden Originalstellen nachgelesen; danach zwei kleine
  Cache-an-/Cache-aus-Prüfungen mit 16 Ausgabetokens beziehungsweise
  überlappender Zusatzanfrage ausgeführt (80 Durchläufe).
- Auf „nächster Schritt, bis belastbarer Befund“: lokale Python-
  Freigabeschicht gebaut, direkte Antwort, BOS W=4, zwei Ziel-Deadlines
  und festen Freigabezeitpunkt in balancierten Vierergruppen verglichen;
  Client-, Proxy- und Backend-Eingangszeiten getrennt protokolliert.
  Nach Neustart und mit entferntem Cache-Diagnosefeld bestätigt:
  volle Rangmischung verdeckt die Information in der ersten
  Clientantwortzeit nicht. Details in
  `results/bos-sanitized-20261102/auswertung.md`.
- Auf den Daybreak-Blue-Auftrag: bisherige BOS-Daten unabhängig
  nachgerechnet; C1/C2-Konfigurationen, anderen Promptsatz und
  Slot-Fallback in insgesamt 308 neuen Vierer-Durchläufen geprüft;
  fünf Clientbeobachter und gepaarte Offline-Schutzkosten verglichen.
  Der starke Rangkanal ist unter C0 reproduzierbar und nicht an den
  ersten Prompttext gebunden, aber unter C1/C2 stark reduziert.
  Der Slot schützt das einfache T1-Merkmal bei vollständigen Gruppen;
  bei 24 Tokens trat in zwei getrennten Tests häufig Fallback auf,
  und ein vor der Bestätigung fixierter T2-Beobachter traf 20/32.
  Die beiden 24-Token-Testserien nutzten dieselbe deterministische
  Fallfolge, aber neue Salts und getrennte Serverstarts; diese
  Einschränkung ist im Bericht ausgewiesen.
  Die eigene ICCAI-2026-PDF wurde danach vollständig gegen die neue
  Forschungsfrage gelesen und als `references/iccai2026-completion-order.pdf`
  zur Nachprüfung im Repository gesichert. Sie prüfte Ränge ohne
  Clientzeiten und berichtete Gesamtlaufzeit statt individueller
  Antwortwartezeiten.
  Vollständiger Bericht: `docs/entscheidungsvalidierung-20261102.md`.
- Ausschließlicher Schreibort für Ergebnisse: dieses Repository.

## Inventar des Messrechners (02.11.2026)

| Komponente | Tatsächlich vorgefunden |
| --- | --- |
| CPU | AMD Ryzen Threadripper 3970X, 32 physische Kerne, 64 Threads, 1 NUMA-Knoten |
| RAM | 125 GiB nutzbarer Gesamtspeicher (rund 128 GB), bei Aufnahme 118 GiB verfügbar; Swap 511 MiB |
| GPU | NVIDIA GeForce RTX 3090, 24.576 MiB VRAM; bei Aufnahme 821 MiB belegt, Anzeige aktiv |
| Betriebssystem | Ubuntu 26.04.1 LTS, x86_64; Kernel 7.0.0-42-generic |
| NVIDIA | Treiber 580.178.04; `nvidia-smi` erfolgreich, angezeigte CUDA-Unterstützung 13.0 |
| CUDA-Toolkit | `/usr/bin/nvcc`, Release 12.4, V12.4.131; Paket nvidia-cuda-toolkit 12.4.131~12.4.1-8 |
| System-Python | `/usr/bin/python3`, 3.14.4; pip 25.1.1, NumPy 2.3.5; keine aktive virtuelle Umgebung |
| Weitere Werkzeuge | uv 0.12.1; rustc, cargo, conda, docker, ollama, vllm, sglang, llama-server und llama-cli nicht im aktuellen PATH gefunden |

Erfasst mit `lscpu`, `free -h`, `/etc/os-release`, `uname -r`,
`nvidia-smi`, `nvcc --version`, Versionsabfragen und Python-Paketmetadaten.
Die CUDA-Angabe von `nvidia-smi` ist kein Nachweis eines installierten
CUDA-13-Toolkits. Ein CUDA-Rechenlauf oder Engine-Start wurde nicht ausgeführt.
Die GPU dient gleichzeitig dem Desktop; die obige Belegung ist eine Momentaufnahme.

### Vorhandene Python-/LLM-Umgebungen

- Im System-Python fehlen die abgefragten Pakete torch, transformers, vllm,
  sglang, sgl-kernel, llama-cpp-python, triton, cuda-python, flash-attn,
  accelerate und huggingface-hub.
- In `/home/rock/projects/porto/.venv` und
  `/home/rock/projects/porto/.venv-py313-repair` liegen Paketmetadaten für
  vLLM 0.17.1, PyTorch 2.10.0, Transformers 4.57.6, Triton 3.6.0 und
  huggingface-hub 0.36.2 (jeweils site-packages für Python 3.13).
  Das belegt vorhandene Installationsartefakte, noch keine funktionsfähige Engine.
  Versionsabfragen ergeben: `.venv/bin/python` startet inzwischen Python 3.14.4
  trotz Konfiguration für 3.13.7; damit ist die alte Umgebung nicht ohne Weiteres
  als nutzbar anzusehen. `.venv-py313-repair/bin/python` meldet Python 3.13.7
  und ist der passendere Kandidat für eine spätere gezielte Funktionsprüfung.
- Weitere virtuelle Umgebungen in DOS, DOS2, energy, objective-placement-map
  und einem DOS-Unterprojekt enthalten keine der dort abgefragten LLM-Pakete.
  Ihre Konfigurationen verweisen teilweise auf Python 3.12 bzw. 3.13;
  Konfigurationsangaben sind kein aktueller Funktionstest.
- Im vorhandenen Hugging-Face-Cache liegen Verzeichnisse für
  `Qwen/Qwen2.5-7B-Instruct` und `meta-llama/Llama-3.1-8B-Instruct`.
  Bei der anschließenden Artefaktsichtung wurden alle im Index genannten
  Gewichtsdateien vorgefunden; Ladefähigkeit und Dateiinhalte bleiben ungeprüft.
- Das Nachbarprojekt `/home/rock/projects/vllm-offload-profiles` ist vorhanden.
  Befunde zur anschließenden inhaltlichen Sichtung stehen unten.

Die Inventarsuche blieb auf `/home/rock/projects` und naheliegende Laufzeit-/Cachepfade
beschränkt. Es gab keine Installation, Änderung fremder Projekte, Modellladung
oder Messkampagne. Rust ist außerhalb der geprüften Pfade nicht ausgeschlossen.

## Artefaktsichtung (02.11.2026)

### ICCAI 2026 / ordleak

- In `/home/rock/projects`, `/home/rock/Documents` und `/home/rock/Downloads`
  kein ordleak-Checkout bzw. passend benanntes Archiv gefunden. Die gezielte
  Textsuche in Code und Dokumentation ergab außerhalb dieses Projekts nur
  einen historischen BOS-Verweis in `porto/.../results_notes_paper1.md`.
  Keine Aussage über andere Datenträger oder ungeprüfte Archive.
- Über GitHub tatsächlich gelesen: ordleak am festgehaltenen Commit
  `2dad2ecb3116f4826f234d0da550dd83bfdfb474`; kein lokaler Klon angelegt.
  `src/victim.py` enthält `BOSScrubber`, `src/client_rank_only.py` den
  Reihenfolgeclient; `scripts/run_dataset.py` und `scripts/analyze.py`
  liefern Datenerfassung, ODS/GAP_VAR/first_half_ods und einfache Auswertung.
- BOS puffert W abgeschlossene IDs, mischt einen vollen Block und leert am
  Durchlaufende den Rest. W=0 ist ohne Schutz, W=1 ohne Umordnung.
  **W begrenzt eine Anzahl, keine individuelle Wartezeit.** Ein Zeitlimit oder
  Deadline-Flush fehlt. Der PRNG wird pro `RUN` neu mit dem angegebenen Seed
  initialisiert; sein Zustand läuft nur innerhalb dieses Durchlaufs weiter.
- Der vollständig gelieferte Git-Baum enthält 150 CSV-Dateien einschließlich
  Stage-1/2/3-, KDF- und Overhead-Daten, aber keine `.done.log`-Rohreihenfolgen.
  Eine Stage-3-CSV und eine Overhead-CSV wurden stichprobenartig gelesen:
  Kennzahlen, Labels, W und Seed sind erhalten, vollständige Permutationen und
  individuelle Zeitstempel fehlen. Der alte Client erfasst ausdrücklich keine
  Zeitstempel. Das Overhead-Skript misst die Gesamtlaufzeit vieler Durchläufe,
  nicht die individuelle BOS-Zusatzwartezeit. `.gitignore` schließt Logs aus.
- Wiederverwendbar sind der kleine Python-BOS-Kern, die Reihenfolgebehandlung
  und Kennzahlfunktionen. LLM-Anbindung, Zeitbudget und individuelle
  Fertigstellungs-/Freigabe-/Empfangszeiten sind damit noch nicht implementiert.
  Alte AUC-/Schwellwertauswertung ist keine Validierung eines neuen Beobachters.

### Lokale LLM-Artefakte

- `/home/rock/projects/vllm-offload-profiles`, Commit
  `547be9005dd6483d21e15e32416ffab96d1a2e63`, enthält kuratierte Start-/Clientskripte,
  Rohdaten, Konfigurationsevidenz und Auswertung für Offload, Profilvariation,
  GPU-Hintergrundlast und KV-/VRAM-Druck. Das ist ein anderes Experiment als BOS.
- In `data/raw/baseline/{llama,qwen}` liegen jeweils 180 JSON-Dateien.
  Je eine Datei wurde gelesen: je 20 Anfragen mit `start_times`, `ttfts`,
  `itls`, Ausgabelängen und Fehlern. Die Arrays werden laut lokalem vLLM-Code
  in Anfragefolge gespeichert, nicht in Abschlussfolge. Aus
  `start_times[i] + ttfts[i] + sum(itls[i])` lässt sich die Reihenfolge letzter
  Token ableiten; das ist kein direkt protokollierter HTTP-Abschluss oder
  BOS-Freigabezeitpunkt. Bisher keine neue Auswertung durchgeführt.
- `/home/rock/projects/porto`, Commit `72b9272c59ca0738ffe7fb012b9a33169b3b941f`,
  enthält zusätzliche HTTP-Streaming-Clients und historische Serverlogs.
  `paper1_workspace/step3_policy_gating/victim_worker.py` erfasst pro Anfrage
  ID, `start_time`, `e2el_ms`, TTFT und Tokenabstände. Eine vorhandene
  `.../policy_runs_offload0_20260416_092616/naive_threshold/offload0_naive_threshold_run4_victim.json`
  bestätigt 399 individuelle Datensätze; daraus sind Empfangsabschlusszeiten
  innerhalb dieses Workers ableitbar. Kein BOS-Versuch.
- Ein Qwen-Serverlog vom 27.07. belegt vLLM 0.17.1, bfloat16,
  Prefix-Caching, asynchrones Scheduling und erfolgreiche API-Antworten.
  Lokaler vLLM-Code nennt FCFS als Standard und außerdem Priorität;
  ein LPM-Scheduler oder ein ausnutzbarer Reihenfolgekanal ist damit nicht belegt.
  Die frühere Messumgebung war laut Artefaktdokumentation Kubuntu 25.10,
  Kernel 6.17 und ein älterer NVIDIA-Treiber: historischer Erfolg ersetzt keinen
  aktuellen Starttest nach dem Systemwechsel.
- Modellcache geprüft: Qwen-Snapshot `a09a35458c702b33eeacc393d103063234e8bc28`
  und Llama-Snapshot `0e9e39f249a16976918f6564b8830bc894c89659` enthalten jeweils
  alle vier im Index genannten Gewichtsdateien sowie Konfiguration und Tokenizer.
  Nur Existenz/Dateigröße geprüft, keine Inhaltsprüfung oder Modellladung.
- Die alten Skripte schreiben in ihre eigenen Arbeitsverzeichnisse und starten
  teils ganze Matrizen. Sie wurden ausschließlich gelesen, nicht ausgeführt.

**Entscheidungsrelevanter Befund:** Vorhandene vLLM-/Python-Komponenten können
den Neuaufbau voraussichtlich verkleinern. Vollständige alte BOS-Reihenfolgen
sind in den gesichteten Beständen nicht verfügbar; individuelle Schutzkosten
müssen neu erfasst werden. Eine funktionsfähige LLM-BOS-Freigabeschicht wurde
nicht vorgefunden. Es wurde nichts aus fremden Projekten kopiert oder verändert.

## Wissenschaftlicher Stand
- Nachfolgeprojekt zur ICCAI-2026-Arbeit.
- Forschungsfrage und vorläufiger Versuchsplan dokumentiert.
- Ein lokaler, konfigurationsabhängiger Rang-Basiskanal mit Cache-aus-
  Kontrolle ist nachgewiesen. Ein BOS-Pilot zeigt einen konkreten
  Rang-/Zeit-/Kostenkonflikt; Übertragbarkeit und Novelty sind noch offen.

## Machbarkeit und Entscheidungsvorlage (02.11.2026)

**Gezielte Funktionsprüfung:** Mit
`/home/rock/projects/porto/.venv-py313-repair/bin/python -B` lassen sich
PyTorch **2.10.0+cu128** und vLLM **0.17.1** importieren. Python ist **3.13.7**,
PyTorch meldet seine CUDA-Version **12.8**, `torch.cuda.is_available()` ist
`True` und das Gerät wird als RTX 3090 erkannt. Die Python-Prüfung lief ohne
Bytecode-Schreibzugriffe und mit Offline-Modus für Hugging Face. Kein
Modell-/Serverstart, kein GPU-Rechentest und keine Installation. Der erfolgreiche
vLLM-Paketimport allein belegt noch nicht die vollständige
Server-Abhängigkeitskette. Der nachfolgende Starttest prüfte diese separat.

**Einzelner Server-/Modellstart (02.11.2026):** Der vorhandene
Qwen2.5-7B-Instruct-Snapshot ließ sich mit vLLM 0.17.1 unter Python 3.13.7
auf der RTX 3090 laden. Für diesen Machbarkeitstest: lokaler OpenAI-Server
auf `127.0.0.1:8765`, `max-model-len=2048`, `gpu-memory-utilization=0.80`,
`cpu-offload-gb=0`, Eager-Modus, Offline-Modus. Die einzige
`/v1/completions`-Anfrage erhielt HTTP 200 und `completion_tokens=1`;
das eine ausgegebene Token war ein Zeilenumbruch. Die 0,167 s HTTP-Gesamtzeit
ist eine Einzelbeobachtung, keine Latenzmessung. Anschließend wurde der
Server beendet; Port und GPU-Speicherbelegung kehrten auf den Ausgangszustand
zurück. Keine Installation, kein Kanal- oder BOS-Test.

Der erste Startversuch scheiterte vor der Modellladung, weil der unter
`results/qwen-single-20261102/tmp` vorgesehene IPC-Socket-Pfad die
107-Zeichen-Grenze überschritt. Mit `results/tmp` innerhalb des Repositorys
gelang derselbe Start. Belege:
`results/qwen-single-20261102/server.log` (Fehler),
`server-second.log` (erfolgreicher Start und Shutdown), `response.json` und
`response.headers`. Laufzeit-Caches liegen ebenfalls nur unter
`results/qwen-single-20261102/cache`; die vorhandene Modellablage und
Python-Umgebung wurden lediglich gelesen. Dieser Start mit verkürzter
Kontextlänge und Eager-Modus bestätigt noch keine spätere Pilotkonfiguration.

**Wiederholung auf Wunsch (02.11.2026):** Mit derselben lokalen Konfiguration
und einer einzigen Anfrage an `/v1/chat/completions` antwortete Qwen auf
„Antworte mit genau einem Wort: TEST“ mit `TEST` (HTTP 200,
`finish_reason=stop`, zwei Ausgabetokens bei höchstens acht erlaubten).
Die HTTP-Gesamtzeit von 0,201 s ist wiederum nur eine Einzelbeobachtung.
Der Server wurde anschließend beendet. Belege:
`results/qwen-single-20261102/server-third.log`,
`response-repeat.json` und `response-repeat.headers`. Die Wiederholung
bestätigt eine sichtbare Chat-Antwort, keinen Cache-/Reihenfolgekanal.

**Cache-Kontrolle (02.11.2026):** Derselbe Qwen/vLLM-Server lief mit
aktiviertem Prefix-Caching und `--enable-prompt-tokens-details`. Drei
nicht gestreamte Anfragen hatten denselben Prompt mit 258 Tokens und je
höchstens ein Ausgabetoken; zuerst Salt A, dann erneut Salt A, zuletzt Salt B.
Alle drei erhielten HTTP 200. Die zweite Antwort meldete
`cached_tokens=256`; die erste und dritte meldeten kein positives
`cached_tokens`-Feld. Der lokale vLLM-Code setzt das Feld nur bei einem
positiven Wert. Damit sind Wiederverwendung bei gleichem Salt und Trennung
bei verschiedenem Salt in diesem Einzeltest sichtbar. Die beobachteten
HTTP-Gesamtzeiten (0,170 / 0,074 / 0,114 s) sind nicht für einen
Leistungs- oder Kanalbefund belastbar. Anfragen, Antworten und Log liegen
unter `results/cache-control-20261102`; der Server wurde beendet.
Dieser Test erfasst weder konkurrierende Anfragen noch Antwortreihenfolgen.

**Gezielter Machbarkeitspilot (02.11.2026):** 108 Durchläufe mit jeweils zwei
konkurrierenden Probes; 72 davon mit A oder B vorgewärmt, 36 ohne Vorwärmung
als Kontrolle. A/B hatten je 548 Prompt-Tokens, maximal ein Ausgabetoken,
neuen Salt pro Durchlauf und rund 10 ms tatsächlichen Sendeabstand. Die
Vorwärmung führte in allen 72 passenden Probes zu 544 gemeldeten
Cache-Tokens. Unter dem ursprünglichen Tokenbudget 2048 gewann stets die
zuerst gesendete Probe; bei Budget 256 kamen spätere Cache-Treffer in
8/12 und bei der Wiederholung in 5/12 Fällen zuerst, aber mit höchstens
0,093 ms Empfangsabstand. Das ist kein robuster Rangbefund. Dagegen war die
Clientzeit der zuerst gesendeten Probe bei Vorwärmung in allen beobachteten
Fällen unter 77 ms, ohne deren Vorwärmung über 137 ms. Eine nachträglich
gewählte 100-ms-Grenze trennt die binären A/B-Zustände innerhalb dieser
Messdaten, ohne unabhängige Validierung. `cached_tokens` diente nur als
Kontrolle und wurde nicht als Rang-/Timing-Beobachtung verwendet.
Versuchsaufbau, Tabellen, Grenzen, Rohdaten und Logs:
`results/order-feasibility-20261102/auswertung.md`; Client:
`src/cache_order_pilot.py`. Die beiden Server wurden nach den Serien beendet.

**Explorativer Rangpilot mit Prefill-Grenze (02.11.2026):** Bei Qwen/vLLM
0.17.1, FCFS, Tokenbudget 256 und ausdrücklich gesetzter
`long_prefill_token_threshold=128` gewann der 10 ms später gesendete,
vorgewärmte Treffer in zwei unabhängigen Fallfolgen **24/24** Zweier-Durchläufe
mit 51,00–88,66 ms Empfangsvorsprung. Mit Prefix-Caching aus gewann er
**0/12** Mal. Bei Schwelle 64 und vier Probes stand die vorgewärmte Probe
in **32/32** Durchläufen auf Empfangsrang 1, selbst bei Sendeposition 4
(**8/8**, Vorsprung 297,68–310,07 ms vor der ersten kalten Antwort).
Mit Cache aus entsprach ihr Rang in **32/32** der Sendeposition. Weitere
Kontrollen ohne Vorwärmung zeigten keine systematische Bevorzugung der
markierten Probe; unter vier kalten Probes trat allerdings je einmal eine
Vertauschung auf. Alle vorgewärmten Probes meldeten 544 gecachte von 548
Prompt-Tokens, kalte keine. Diagnosefeld `cached_tokens` war nicht Teil der
Rangentscheidung. Der Mechanismus ist mit Chunked Prefill konsistent, aber
intern nicht instrumentiert; der Effekt gilt nur für diese gezielte lokale
Konfiguration. Vollständiger Versuchsbericht, Rohdaten und Logs:
`results/full-order-20261102/auswertung.md` und
`results/prefill-threshold-20261102/`. Beide Server sind beendet.

**Zwei literaturgeleitete Anschlüsse (02.11.2026):** PROMPTPEEK nutzt
ein Token pro Anfrage; die Contention-Arbeit zeigt, dass konkurrierende
Arbeit Cache-Timing erheblich verändern kann. Deshalb wurden bei derselben
gezielten vLLM-Konfiguration einmal **16-Tokens-Antworten** und einmal
**eine tatsächlich überlappende 64-Token-Zusatzanfrage** getestet,
jeweils gegen Cache aus. In beiden Cache-an-Bedingungen gewann die später
gesendete vorgewärmte Probe **12/12** Mal; bei Cache aus **0/12**
beziehungsweise **2/12**, letztere nur an Sendeposition 2 und mit
nahezu gleichen kalten Antwortzeiten. Als vierte gesendet lag der Treffer
bei Cache an in **4/4** Fällen vorn, bei Cache aus in **4/4** Fällen
auf Rang 4. Der Vorsprung bei Sendeposition 4 betrug 101,34–105,43 ms
für 16 Tokens und 173,77–176,19 ms unter Zusatzlast. Die
Zusatzanfrage überdeckte in **20/20** zugehörigen Durchläufen die
Probe-Sendezeitpunkte und erste Antwort. Volle Rohdaten, Kontrolle und
Grenzen: `results/two-extensions-20261102/auswertung.md`. Das ist ein
lokaler Robustheitsbefund, keine allgemeine Last- oder BOS-Aussage.

**Durchgängiger Schutz-/Kostenpilot (02.11.2026):** Vier vollständige
16-Token-Antworten durch eine lokale Python-Freigabeschicht geleitet.
Die Hauptserie umfasste 272 balancierte Durchläufe / 1.088 Probes:
direkt war der Cache-Treffer 64/64 Mal auf Rang 1; BOS W=4 nur
19/64; mit 100-ms-Ziel 64/64, weil die vorgewärmte Antwort 64/64
Mal allein freigegeben wurde; mit 250-ms-Ziel 18/64 in vollen
Viererblöcken. Eine vorgezogene Timer-Auslösung hielt die
**gemessene** Zusatzwartezeit bei 100 ms unter dem Ziel (Maximum
95,03 ms), ist aber kein harter Echtzeitbeweis. Die frühe Antwort
wartete beim vollen W=4 median 193,79 ms zusätzlich.

Der wichtige **Restkanal**: Das Mischen verändert die Rangfolge,
nicht den Zeitpunkt, zu dem die letzte Backend-Antwort den Block
freigabefähig macht. Eine nur aus dem ersten Clientempfang nach
dem ersten Versand gebildete, vor dem Test fixierte Vierfachregel
erkannte nach Neustart des Modellservers 53/64 W=4- und 56/64
250-ms-Zustände; die zuerst empfangene ID traf 21/64 und 15/64.
Ein fester Freigabezeitpunkt 1.050 ms nach erstem Anfrageeingang
glättete dieses eine Zeitsignal im lokalen Pilot, erhöhte aber die
mediane individuelle Wartezeit der frühen Antwort auf 362,50 ms.
Im abschließenden 204-Durchlauf-Vergleich wurde das direkt
clientseitig sichtbare `cached_tokens`-Feld entfernt; die
Zeitregel traf weiterhin 41/64 bzw. 43/64 bei BOS und 250 ms,
eine einfache Slot-Zeitregel nur 12/64. Alle 816 Clientantworten
waren ohne Cache-Diagnosefeld; intern protokollierte Treffer,
API-IDs und Zeiten stimmten. Bericht, Grafik, Rohdaten und Grenzen:
`results/bos-sanitized-20261102/auswertung.md`.

**Quellenbefund und Grenze:** PROMPTPEEK (§IV-A, S. 5–6; §VIII, S. 13)
untersucht LPM und gezielt aufgebaute Warteschlangen. OptiLeak v1 (§4.2/§5.1)
nutzt ebenfalls LPM/Positionsfeedback und SGLang. Der dortige Mechanismus ist
kein Nachweis für die lokale vLLM-FCFS-Konfiguration. vLLM 0.17.1 dokumentiert
Prefix-Wiederverwendung voller Blöcke und optionale Cache-Salts; APC spart
Prefill, nicht Decode. Die historischen Aussagen über andere Scheduler aus
PROMPTPEEK dürfen deshalb nicht pauschal auf heutiges vLLM übertragen werden.
SafeKV v2 (§6) schützt an der Cache-Wiederverwendung und untersucht TTFT;
es ist eine Vergleichsbasis, kein Beleg für BOS-Restinformation.
Dies war eine begrenzte, entscheidungsorientierte Quellenprüfung, kein neuer
umfassender Literatur-/Novelty-Audit; Fundstellen und Lesestände in docs/quellen.md.

| Option | Aussagekraft / vorhandene Basis | Aufwand bis zum ersten Befund |
| --- | --- | --- |
| A: vLLM + Python-Client/Freigabe | Lokal umgesetzt; konfigurationsabhängiger Basiskanal und erste Schutz-/Kostenmessung vorhanden | Geringster Zusatzaufwand für gezielte Übertragbarkeitsprüfung |
| B: vLLM + Rust-Freigabe | Gleiche Forschungsfrage; präzisere Freigabe wäre zu messen, kein automatischer Vorteil | Höher: Rust nicht gefunden, zusätzliche Schnittstelle; derzeit kein belegter Bedarf |
| C: andere Engine | Keine zusätzliche funktionsfähige lokale Engine gefunden; SGLang dokumentiert LPM und wäre näher an PROMPTPEEK | Erst Einrichtung/Kompatibilitätsprüfung erforderlich; kein vorhandener schnellerer Weg belegt |

**Aktualisierte Empfehlung:** A mit dem vorhandenen Qwen2.5-7B-Instruct-
Snapshot und der kleinen Python-Freigabeschicht weiterführen. Der
konfigurationsabhängige Basiskanal ist bei 16 Ausgabetokens sichtbar,
und der erste Schutzversuch liefert einen konkreten Restzeitkanal.
Rust oder Engine-Wechsel erst bei einem konkreten Hindernis neu
bewerten. SGLangs aktuelle Dokumentation führt LPM als wählbar,
inzwischen FCFS als Standard; LPM nicht stillschweigend voraussetzen.

**Vorläufiger Erkenntniskandidat, noch kein Neuheitsclaim:** Ein
voller BOS-Block mischt bei vollständigen LLM-Antworten die Ränge,
verrät aber über seinen Fertigstellungszeitpunkt weiter den
kontrollierten Cachezustand. Eine kurze Deadline zerstört die
Blockmischung; eine vom Anfrageeingang verankerte Ausgabe glättet
das beobachtete Zeitsignal zu höheren individuellen Kosten.
Cache-Leakage, Blockmischung und zeitgebundene Ausgabe als solche
sind bereits bekannt.

**Versuchsentscheidung nach dem Rangpilot:** Gleiche tokenisierte Promptlänge,
ein Ausgabetoken, frischer gemeinsamer Salt je Durchlauf und getrennte
Cache-an-/Cache-aus-Serien haben den Basiskanal nachvollziehbar gemacht.
Die Vorbelegung und ihre gemeldeten 544 Cache-Tokens wurden nur als
Kontrolle ausgewertet. Im Schutzversuch blieben Antwort-ID,
vollständige Empfangsreihenfolge und individuelle Zeiten getrennte Felder.
Das API-Diagnosefeld `cached_tokens` wurde im letzten Vergleich
clientseitig entfernt. Der Proxyversuch zeigt die lokale Verringerung
des Rangkanals und die Wartezeiten; ein Deadline-Flush ist eine
ausdrückliche Mechanismusänderung. Er beweist keine allgemeine Sicherheit.

## Offen
- Starker Vierklassenkanal und BOS-Restzeitbefund sind weiterhin nur
  für die gezielte C0-Konfiguration auf einem Rechner belegt. C1 ist
  wesentlich schwächer; C2 zeigte keinen entsprechenden Rangkanal.
- Realistische Mehrnutzerlast, andere Netze und Modelle sind ungeprüft.
  Gemeinsame Salt-Domäne bleibt eine ausdrückliche Voraussetzung.
- Der Slot-Fallback ist nun gemessen, aber eine alternative sichere
  Spätantwortregel und harte Wartezeitgrenzen sind ungeprüft.
- Frühere T1-Zahlen sind reproduzierbar, doch die Prospektivität
  ihrer ursprünglichen Regelauswahl ist aus den Artefakten nicht
  sicher nachweisbar. Die neue Fallback-Bestätigungsserie wurde
  nach Auswahl von T2 getrennt gefahren.

## Nächster Schritt
Die empirische BOS-/Fallback-Richtung mit einem expliziten
Latenz-/Verfügbarkeitsbudget und vollständiger Client-Trace-Auswertung
prospektiv stärken. Dafür einen kleinen, frisch randomisierten Live-Test
eines vorab fixierten Slots nach neuem Backend-Start planen; C1 und
längere Completion-Tails als Geltungsgrenzen behandeln. Auf den
bereits explorierten Spuren keine weitere Slot-/Münzoptimierung.
