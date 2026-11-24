# ICCAI 2027: Contributions und Manuskriptstruktur

**Durch den Auftrag vom 05.11.2026 für das nächste Manuskript ersetzt:**
`paper/short-paper-plan-20261105.md` plant fünf zweispaltige Seiten mit
C1/C2 als Hauptbeiträgen. Der einmalige C2-Lasttest ergänzt den Befund;
die folgende Drei-Contribution-Struktur bleibt als frühere Planung erhalten.

Stand: 04.11.2026. Entscheidung: Protected-Prefill-Entwicklung gestoppt;
Manuskript aus bestehenden Ergebnissen. Keine neuen Messungen, Beobachter,
Parametersuchen oder Schutzalgorithmen für diese Struktur erforderlich.

**Abschließender Nachtrag vom 04.11.:** Die beauftragte fehlende
ungeschützte C3-Positivkontrolle ist durchgeführt. Beide trainierten und
vor dem unabhängigen Test eingefrorenen Rezepte erreichen unter `direct`
48/48, BA/AUC=1, gemeinsamer Paar-Labeltausch-p=0,000200. Die alten drei
Policies bleiben unverändert. Das erlaubt eine bessere Einordnung,
begründet aber bei breiten alten Schutzintervallen und getrennten
Messsitzungen keinen neuen Timing-Sicherheitsclaim. Auswertung und
Vergleich: `results/protected-prefill-direct-20261104-01/analysis.json`;
Methodik und Entscheidung im aktualisierten Prototypbericht.
**Die experimentelle Arbeit ist beendet.** Nächster verbindlicher Schritt
ist Schreiben und Satz im offiziellen ICCAI-Format mit **höchstens zehn
einspaltigen Seiten einschließlich Referenzen**; das bisherige
Achtseitenbudget unten bleibt ein mögliches kompaktes Ziel.

## 1. Paperkern und Abgrenzung

**Arbeitstitel:** *Residual Client Timing Leakage and Mitigation Costs in LLM Serving*

**Zentrale Aussage:** In den untersuchten LLM-Serving-Szenarien genügt es
nicht, Antwortreihenfolgen zu mischen oder mandantenübergreifende
Cachetreffer zu verhindern: vollständige Clientzeiten können weiterhin
über verborgene Cachezustände informieren. Eine implementierte
Protected-Prefill-Konstruktion erhält private Wiederverwendung und
normalisiert den logischen Wiedereintritt in gemeinsames Decode, zeigt
aber im konfigurationsgleichen Vergleich einen Rechen-/Latenzkonflikt
und keine nachgewiesene vollständige Timingvertraulichkeit.

Das Paper ist eine empirische Security-Systems-Studie mit implementierter
Schutzfallstudie. Seine drei Beiträge sind überprüfbare Befunde und ihre
Geltungsgrenzen. Es beansprucht weder den ersten LLM-Cacheangriff noch
einen neuen allgemein sicheren Scheduler oder eine fundamentale
Privacy-Performance-Untergrenze. Die Annahme durch ICCAI ist damit nicht
vorweggenommen; die verbleibende Neuheitsfrage betrifft den zusätzlichen
empirischen Erkenntniswert gegenüber den unten benannten Vorarbeiten.

**Abstand zur eigenen ICCAI-2026-Arbeit:** *Completion Order for Workload
Inference in Asynchronous Services* untersucht CPU-/Speicher-Workloads
mit einem Beobachter, dessen Modell Zeitstempel und Dauern ausdrücklich
ausschließt. BOS und das Grundprinzip der Ranginferenz stammen aus dieser
Arbeit. Neu untersucht werden hier GPU-LLM-Serving, vollständige
Clientempfangszeiten, getrennte Cache-Namensräume und die individuellen
Kosten einer realen Enginekonstruktion. Die frühere geringe
Gesamtlaufzeitänderung unter Angriff ist kein Nachweis geringer
individueller Antwortlatenz. Alte CPU-Messungen und Abbildungen werden
nicht als neue LLM-Evidenz wiederverwendet. [Original und DOI](https://doi.org/10.1145/3821244.3821268),
lokales Original: `references/iccai2026-completion-order.pdf`.

## 2. Die drei Contributions

### C1 — Rangmischung lässt vollständige Clientzeitbeobachtungen offen

**Formulierung für die Einleitung:**

> We evaluate Budgeted Order Scrubbing against both rank-vector and
> complete-response-time observers in LLM serving. In a held-out Qwen
> document workload, a frozen time observer identifies the cached
> candidate in 21/32 groups under S64, while the rank observer succeeds
> in 7/32. A separate Llama workload exhibits the same separation. We
> relate this residual observation to block closure at the proxy and
> distinguish reduced rank predictability from protection of the full
> client-visible timing trace.

**Beleg:** Qwen-Dokumenttransfer mit vier Kandidaten, je 548 Prompt- und
16 Ausgabetokens, BOS-Fenster vier; vorher eingefrorene R2-/T2-Beobachter.
Unter S64: R2 7/32, T2 21/32; unter S0: 9/32 bzw. 13/32. Vier Klassen,
Zufall 25 %. Die nominalen Wilson-Intervalle stehen in Abbildung 1 und
der zugehörigen CSV. Separate Llama-Validierung mit synthetischen
549-Token-Prompts: S64 5/32 gegen 21/32; S0 10/32 gegen 14/32.
Qwen-Dokument- und Llama-Synthetikdaten sind unterschiedliche Workloads,
kein kausaler Modellvergleich und kein gemeinsamer Schätzer.

**Mechanismus:** Bei vollständigen BOS-Blöcken öffnet die Freigabe erst,
wenn der Proxy die letzte vollständige Backendantwort empfangen hat.
Somit enthält die erste vollständige Clientantwort Information über die
Blockschließzeit. Eine Permutation verändert die Zuordnung zu Rängen,
entfernt diese Blockzeit aber nicht. Das ist eine aus dem Ablauf
abgeleitete Erklärung, keine instrumentierte Messung des exakten
GPU-Fertigstellungszeitpunkts.

**Engste Vorarbeit und Zusatz:** Die eigene BOS-Arbeit ist der direkte
Ausgangspunkt; PROMPTPEEK und OptiLeak etablieren LLM-Rang-/Zeitinferenz.
Pacer §3.2 erläutert bereits, warum sichtbare Ausgabepläne und ihre
Aktivierung geheimnisunabhängig sein müssen. Unser Zusatz ist der
konkrete BOS-Vergleich mit eingefrorenen, reicheren Beobachtern in zwei
LLM-Workloads und die belegte Begrenzung der Rangmetrik. Kein Erstanspruch
für die allgemeine Einsicht, dass Shuffling Zeitinformation belassen kann.
[PROMPTPEEK, §IV](https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf),
[OptiLeak v1](https://arxiv.org/html/2602.20595v1),
[Pacer, §3.2](https://www.usenix.org/system/files/sec22-mehta.pdf).

**Grenze:** Wenige Serverstarts, lokale Verbindung, bekannte kontrollierte
Cachezustände und kurze Antworten. Niedrige R2-Genauigkeit beweist keine
Rangsicherheit. Der Konfigurationsvergleich von Qwens T2 ist gepaart
nicht signifikant (`p=0,1338`); wir behaupten keine gesicherte
Leakagereduktion durch S0. Ein binärer Blockzeitbeobachter erreicht in
denselben Qwen-Daten AUC 0,870/0,932; dies ist eine andere Aufgabe als
Vierklassenidentifikation und wird nicht mit deren Genauigkeit vermischt.

**Nachweisorte:** `docs/dokument-workload-20261103.md`,
`results/document-bos-20261103/analysis.json`;
`docs/llama-referenzvalidierung-20261103.md`,
`results/llama-reference-20261103/bos-analysis.json`.

### C2 — Namensraumtrennung verhindert nicht jede konditionale Zeitinferenz

**Formulierung für die Einleitung:**

> We demonstrate conditional cache-state inference through a shared LLM
> execution path despite separate tenant cache namespaces and zero cache
> hits for the observer's probes. In eight fresh warm/cold pairs with
> hidden victim-start offsets, a previously trained first-response-time
> observer classifies 14/16 cases. Absent-victim and unrelated-cold-work
> controls delimit this result: it exposes competing work under a known
> victim-request condition, rather than an unrestricted document oracle.

**Beleg:** Zwei Mandanten mit festen unterschiedlichen Salts. 24 neue
Backendstarts: acht Warm/Kalt-Paare, vier Abwesenheitskontrollen und vier
Kontrollen mit anderer kalter A-Arbeit. A beginnt mit für B verborgenem
Versatz 0/150/300/450 ms. B sendet vier eigene Anfragen und hat in allen
96 Antworten backendseitig bestätigte null Cachetreffer; entfernte
Clientfelder allein sind dafür kein Beleg.

Ein auf älteren Entwicklungsdaten eingefrorener T1 trifft 14/16
Hauptfälle (Wilson 95 % 64,0–96,5 %); R2 trifft 8/16. Der ebenfalls vorher
trainierte sekundäre T2 trifft 16/16 (80,6–100 %). Alle acht gepaarten
Differenzen liegen in der vorher festgelegten Richtung: kalt minus warm
71,2–146,0 ms, einseitiger Vorzeichentest `p=0,003906`. Die zwei
T1-Fehlklassifikationen sind **warme** Fälle bei Versatz null, als kalt
klassifiziert; eine Schwelle wurde nicht nachangepasst.

Die vier Abwesenheitskontrollen sehen für T1 wie warm aus, die vier Fälle
mit anderer kalter A-Arbeit wie kalt. Das ist zentral für die
Interpretation und bleibt im Haupttext, statt nur im Anhang zu stehen.

**Engste Vorarbeit und Zusatz:** KVGov §4.1 trennt Cache-Schlüssel nach
Principal und verhindert dadurch direkte fremde Treffer. FairInference
§2.2 beschreibt bereits gegenseitige Latenzbeeinflussung im LLM-Serving.
Unser Zusatz ist die kontrollierte Verbindung dieser beiden Ebenen:
verbleibende Inferenz des bekannten A-Cachezustands aus ausschließlich
eigenen B-Empfangszeiten, bei tatsächlicher Treffertrennung, mit
verborgenen Startlagen und Lastkontrollen. Das ist kein Brechen der
Schlüsseltrennung und kein vollständiger Angriff auf das implementierte
KVGov-System. Dessen §7 trennt Simulation von realer Konkurrenz.
[KVGov v1, §§4.1, 7](https://arxiv.org/html/2608.09225v1),
[FairInference v1, §2.2](https://arxiv.org/html/2609.18112v1).

**Grenze:** Konditioniert auf bekannte A-Anfrage/Versuchsanordnung;
beliebige andere kalte Arbeit ist ein Confounder. Kein allgemeines
Dokumentmitgliedschafts-, Inhaltsrekonstruktions- oder Anwesenheitsorakel.
Nur zwei Paare je Versatz, eine GPU und Konfiguration. Die HTTP-Serie
traced keine einzelnen internen Schedulerentscheidungen: deshalb
„shared execution/scheduling path“, keine bewiesene einzelne
Schedulerregel. Diese Versatzserie verwendet kein BOS; ihre Robustheit
wird nicht auf BOS übertragen.

**Nachweisorte:** `docs/tenant-zeitfenster-20261103.md`,
`results/tenant-offset-20261103/analysis.json`, `case-00` bis `case-23`;
vorherige Trainingsdaten `results/tenant-scheduler-20261103/dev/trials.jsonl`.

### C3 — Rechenvorteil und Latenzkosten einer konkreten Schutzkonstruktion

**Formulierung für die Einleitung:**

> We implement protected private prefill followed by canonical state
> normalization and shared decode in vLLM. Under matched scheduling
> parameters, private reuse saves a mean 108 ms of the measured warm
> CUDA execution-and-copy interval relative to recomputation, but adds
> about 110 ms and 109 ms to A's and B's response latency. Source-bound
> invariants explain logical convergence for successful closed cohorts;
> held-out timing tests and an overrun counterexample delimit the
> construction's security claims. An independently acquired unprotected
> positive control confirms that the frozen observer recipes can detect
> the cache state under the same scheduling parameters.

**Beleg:** Der konfigurationsgleiche Contribution-Gate ist die einzige
primäre Kostenquelle: alle drei Policies 512-Token-Schwelle und
2048-Token-Budget. Je Policy zwölf Trainings- und 24 Prüfpaarungen;
Kosten aus den 24 Warm- und 24 Kalt-Prüfkohorten. Protected Prefill
verwendet J=700 ms, Ignore-Hits rechnet neu, Release-only verzögert B
auf 1240 ms. Private Treffer A: 512 bei Protected Prefill, 544 bei der
nativen Release-only-Policy, null bei Ignore-Hits; B immer null.

| Warmer Prüfzustand; Median, ms | Protected Prefill | Ignore-Hits | Release-only |
| --- | ---: | ---: | ---: |
| A: vollständige Antwort verfügbar | 1024,69 | 912,94 | 784,63 |
| B: Median der vier Antworten je Kohorte | 1021,61 | 910,87 | 1240,07 |
| CUDA-Ausführungsintervalle inklusive Normalisierungskopie | 814,52 | 922,82 | 795,03 |

Die **gepaarten Mittelwertdifferenzen**, nicht Differenzen dieser Mediane,
betragen für Ignore minus Protected −110,02 ms bei A, −108,82 ms bei B
und +107,99 ms beim CUDA-Intervall. Letzteres hat eine vorhandene
simultane einseitige 95-%-Untergrenze von 102,67 ms. Das entspricht im
warmen Median ungefähr 11,7 % Intervallersparnis; die geplante
Modellarbeit sinkt um 512/2815 Tokens, also 18,2 %. Kalte Ausführung
zeigt keinen entsprechenden Kostenvorteil. CUDA-Eventintervalle enthalten
Dispatchlücken: keine Messung reiner Kernelarbeit, Energie oder frei
nutzbarer GPU-Kapazität.

**Schutzbefund:** Die zwei vor dem Test eingefrorenen Beobachter liegen
bei BA/AUC 0,542/0,530 und 0,583/0,528. Die AUC-Intervalle reichen
ungefähr von 0,35 bis 0,72. Der gemeinsame Permutationstest ergibt
`p=0,595`; die vorab verlangte Begrenzung der Beobachterleistung ist
wegen breiter Unsicherheit nicht belegt. Null beobachtete Overruns in
72 geschützten Trainings- und Prüfkohorten, kleinste Reserve 8,75 ms,
begründen keine allgemeine Deadlinegarantie.

Die abschließende neue `direct`-Kontrolle nutzt zwölf eigene Trainings-
und 24 Prüfpaare unter demselben unveränderten Pilotcode. Beide Rezepte
erreichen 100 % BA und AUC 1,00 auf 48 neuen Prüfkohorten; 360 Antworten
vollständig, keine Fehler, A warm544/kalt0, alle 288 B-Antworten ohne Hits.
Erste-B-Differenz kalt minus warm im Mittel 113,39 ms (nominales
Paarbootstrapintervall 103,96–123,03 ms). Die nominalen BA-/AUC-
Paarbootstrapintervalle [1,1] degenerieren bei perfektem empirischem
Ergebnis und sind keine Populationsgarantie. Die Kontrolle bestätigt
Sensitivität der Rezepte in dieser Konfiguration. Die alten Policies
wurden nicht gleichzeitig erneut randomisiert; weder neue gepaarte
Kostenvergleiche noch ein bewiesener Schutzvorteil werden daraus abgeleitet.

**Unterstützendes formales Resultat:** Neun implementierungsgebundene
Invarianten leiten die B-relevante Gleichheit am Join aus privaten
KV-Pools, Kopie/Löschung, frischen Managern, festen Quoten und
Workerinstallation her. Im funktionalen Backendmodell folgt gleiche
B-Antwortzuordnung und gleiche logische Decodeentscheidung für
erfolgreiche geschlossene Kohorten. Das ist ein hinreichender Vertrag,
kein Nachweis notwendiger oder minimaler Normalisierung. Die schwächere
inhaltliche Isolation könnte auch ohne die vollständige Kopie gelten.
Reale Zeit, HTTP-Reihenfolge und Fehler-Nichtinterferenz sind nicht
bewiesen. Das dokumentierte Warm-Erfolg/Kalt-Overrun-Gegenbeispiel ist
eine analytische Codeinstanz, keine gemessene 500-Fehlerrate bei J=700.

**Engste Vorarbeit und Zusatz:** SafeKV ist die direkte Vorarbeit für
geschützte Cache-Wiederverwendung; Time Protection und IFS behandeln
zeitliche Isolation und kontrollierte gemeinsame Ausführung. Predictive
Mitigation etabliert geheimnisunabhängige Freigabepläne. Unser Zusatz ist
die implementierte vLLM-Fallstudie mit konfigurationsgleicher Rechnung
für beide Mandanten und expliziter Trennung von logischem Vertrag,
empirischer Beobachterleistung und realer Timinggarantie. Kein neuer
allgemeiner Isolationssatz und keine bewiesene Überlegenheit gegenüber
diesen Systemen; sie wurden nicht hier als vollständige Implementierungen
verglichen. [SafeKV v2, §§4.3, 6](https://arxiv.org/html/2508.08438v2),
[Time Protection, §§3.2, 4.3](https://yuval.yarom.org/pdfs/GeYCH19.pdf),
[IFS, §§3–4](https://www.cis.upenn.edu/~sga001/papers/ifs-ccs21.pdf),
[Predictive Mitigation, §§2–4](https://www.cs.cornell.edu/andru/papers/ccs11.pdf).

**Grenze:** Ein konkreter Mechanismus, geschlossene Kohorten, zwei
Mandanten, ein Modell/GPU. Kosten aus einem EngineCore-Prozessharness,
nicht HTTP-Ende-zu-Ende-Messung. Keine Gesamtdominanz über beide Baselines,
keine Paretooptimalität oder universelle Unmöglichkeitsaussage.

**Nachweisorte:** `docs/protected-prefill-prototyp-20261103.md`,
`results/protected-prefill-gate-20261103-01/` einschließlich Protokoll,
eingefrorener Beobachter, `test-start.json`, `trials.jsonl`, Analyse und
Verifikation; `docs/protected-prefill-nichtinterferenz-20261103.md`.

## 3. Struktur für acht Seiten

Arbeitsformat: **acht einspaltige ACM-Manuskriptseiten inklusive
Referenzen**. Die aktuelle ICCAI-Seite nennt 8–10 einspaltige bzw.
4–5 zweispaltige Seiten als regulären Umfang; acht zweispaltige Seiten
sind daher keine stillschweigende Vorgabe. Das offizielle LaTeX-Paket
enthält das ACM-Manuskriptformat. Der folgende Plan ist ein
Satzbudget, noch kein gerenderter Achtseitennachweis.
[ICCAI Submission](https://www.iccai.net/submission.html),
[Umfang](https://www.iccai.net/registration.html),
[offizielles LaTeX-Paket](https://www.iccai.net/LaTeX-Template.zip).

| Manuskriptteil | Seiten | Konkreter Inhalt und Ergebnis |
| --- | ---: | --- |
| Titel, Abstract, 1 Introduction | 0,80 | Drei Beobachtungsebenen; Forschungsfragen; drei obige Contribution-Absätze; expliziter Abstand zu 2026 |
| 2 Related Work | 0,60 | BOS/LLM-Seitenkanäle; Cache-Namensräume versus Ausführungsisolation; bekannte Ausgabeformung. Keine neue Literaturmatrix |
| 3 System, Threat Models, and Method | 1,10 | Setup und Definition vollständiger Empfänge; zwei verschiedene Inferenzaufgaben; Splits, Protokolle, Konfigurationen; Tabelle 1 |
| 4 Rank Scrubbing and Residual Timing | 1,25 | RQ1/C1, Abbildung 1, Blockschließmechanismus; konfigurationsabhängige Evidenz ohne gesicherten Konfigurationseffekt |
| 5 Conditional Leakage Across Cache Namespaces | 1,15 | RQ2/C2, Abbildung 2; null B-Hits; verborgene Versätze; Lastkontrollen bestimmen die Reichweite |
| 6 Protected Prefill: Implementation and Costs | 1,45 | RQ3/C3, Abbildung 3 und Tabelle 2; ca. 100 Wörter Ablauf, ca. 100 Wörter logischer Vertrag, Fehlergegenbeispiel |
| 7 Discussion and Threats to Validity | 0,60 | Wenige Sitzungen, Loopback, bekannte A-Arbeit, keine allgemeine Privacyschranke; nicht vergleichbare Beobachtungsräume |
| 8 Conclusion | 0,20 | Belegte drei Erkenntnisse; Timingvertrag und Admission als offenes Folgeprojekt |
| References | 0,85 | Etwa 14–16 gezielt verwendete Quellen, eigene Vorarbeit klar zitiert |
| **Summe** | **8,00** | Drei Abbildungen, zwei Tabellen; ca. 2400 Haupttextwörter plus ca. 170 Wörter Abstract als Startziel |

**RQ1:** Welche zusätzliche Cacheinformation liefern vollständige
Clientempfangszeiten nach BOS gegenüber den getesteten Rangbeobachtern?
**RQ2:** Bleibt unter getrennten Cache-Namensräumen konditionale Inferenz
aus eigenen Anfragezeiten möglich, und was identifiziert sie tatsächlich?
**RQ3:** Welche Wiederverwendung, Ausführungskosten, Antwortlatenzen und
begründbaren Schutzgrenzen hat der implementierte normalisierte Übergang?

Die Abschnitte verwenden die gleiche Erzählfolge: untersuchte Behauptung,
kleinster passender Versuch, Ergebnis, begrenzte Folgerung. Die
Entwicklungsgeschichte von J=940 zu J=700 und gescheiterte Zwischenläufe
bleiben in den vorhandenen Artefakten, statt den Haupttext zu dominieren.

## 4. Tabellen und fertige Abbildungen

### Tabelle 1 — Experimental design and observation boundaries

| Serie | Geheimnis / Aufgabe | Trainings- und Prüfgrenze | Einheit / Konfiguration |
| --- | --- | --- | --- |
| Qwen Dokumente + BOS | Position des warmen Kandidaten, vier Klassen | Alte 32 synthetische Gruppen je Konfiguration zum Training; neue 32 positive Dokument-Prüfgruppen je Konfiguration | Vollständige HTTP-Empfänge; 548 Prompttokens; S64 und S0 |
| Llama synthetisch + BOS | Position des warmen Kandidaten, vier Klassen | 16 positive Trainings- und 32 positive Prüfgruppen je Konfiguration; getrennte Engines/Salts und Kontrollen | Vollständige HTTP-Empfänge; 549 Prompttokens; S64 und S0 |
| Getrennte Namensräume | Bekannter A-Cachezustand, binär | Alte 16 Entwicklungsgruppen; neue acht Prüfpaare plus acht Lastkontrollen | Nur Bs vier eigene HTTP-Empfänge; Qwen, S64 |
| Protected-Prefill-Gate | A warm/kalt; Kosten und binäre Zeitbeobachter | Je Policy zwölf Trainings- und 24 Prüfpaare, Beobachter vor Test eingefroren | Vollständige Antwortverfügbarkeit im EngineCore-Harness; Qwen, S512 |
| Abschließende Direct-Kontrolle | A warm/kalt, binäre Zeitbeobachter | Zwölf neue Trainings- und 24 neue Prüfpaare, eigene eingefrorene Modelle | Gleicher EngineCore-Harness und Qwen/S512; separate spätere Messsitzung |

Unter die Tabelle: S64 = Budget/Schwelle 256/64, S0 = 256/0;
S0 hebt nur die per-Request-Schwelle auf, nicht das Tokenbudget oder
sämtliches Chunking. S512 = 2048/512 für **alle** Gate-Policies.
Diese Aliase ersetzen im Manuskript die bisherigen C0/C1-Konfigurationsnamen,
damit sie nicht mit Contributions C1–C3 verwechselt werden. Unterschiedliche
Serien werden weder für Genauigkeitsnenner noch für Latenzen gepoolt.

### Abbildung 1 — Rank observers versus full-time observers

Fertig: `assets-20261103/fig1_rank_and_time.pdf` (PNG-Vorschau daneben),
Daten: `c1_observers.csv`.

**Caption:** *Frozen rank-vector (R2) and complete-response-time (T2)
observers after four-response BOS. Left: Qwen document transfer; right:
Llama synthetic holdout, a different workload. Each marker summarizes
32 positive held-out groups; bars are existing nominal 95% Wilson
intervals. The dashed line is four-class chance accuracy (25%). S64
and S0 denote budget/threshold 256/64 and 256/0. Low rank accuracy does
not establish rank noninterference, and the two model panels are not
a controlled model comparison.*

### Abbildung 2 — Conditional timing despite separate namespaces

Fertig: `assets-20261103/fig2_separate_namespaces.pdf`,
Daten: `c2_client_times.csv`, `c2_observers.csv`.

**Caption:** *First complete B-response time under separate fixed tenant
salts. Left: eight fresh warm/cold pairs at hidden A-start offsets;
orange circles denote warm A, blue triangles cold A, with horizontal
jitter only for visibility. All paired cold-minus-warm differences are
positive (71.2–146.0 ms). Right: individual observations and medians,
including absent-A and unrelated-cold-A controls. All 96 B responses
have zero backend-confirmed cache hits. The controls limit the inference
to competing work under a known A-request condition.*

### Abbildung 3 — Matched costs of the implemented construction

Fertig: `assets-20261103/fig3_matched_costs.pdf`,
Daten: `c3_test_cohorts.csv`, `c3_medians.csv`.

**Caption:** *Configuration-matched protected prefill, ignore-hits and
release-only (B release at 1240 ms), all using budget/threshold 2048/512.
Points show 24 held-out cohorts per cache state and policy; bars mark
medians. Endpoints are A response availability, the within-cohort median
of four B responses, and summed CUDA execution intervals plus the
protected normalization copy. Latencies are measured in an in-process
engine harness. Warm private reuse reduces the CUDA interval relative
to recomputation but increases both tenants' response latency. CUDA
event intervals are not energy or pure-kernel-work measurements.*

### Tabelle 2 — What the protected transition establishes

| Eigenschaft | Vorhandene Evidenz | Zulässige Aussage |
| --- | --- | --- |
| Private Wiederverwendung | 512 A-Tokens; 2303 statt 2815 geplante Modelltokens im warmen Fall | Wiederverwendung funktional vorhanden |
| Warme Intervallkosten | 107,99 ms gepaarte mittlere Ersparnis, Untergrenze 102,67 ms | Vorteil in dieser Metrik gegenüber Ignore-Hits |
| Individuelle Latenz | A +110,02 ms, B +108,82 ms gepaarter Mittelwert gegenüber Ignore-Hits | Kein Latenzvorteil |
| Ungeschützte Positivkontrolle | Beide Rezepte BA=AUC=1 auf 48 neuen Prüfkohorten; gemeinsamer p=0,000200 | Rezepte unter ungeschütztem S512 sensitiv; keine neue simultane Vier-Policy-Serie |
| Zeitbeobachter | 48 Prüfkohorten, BA/AUC 0,542/0,530 und 0,583/0,528; breite Intervalle | Schutzgate unentschieden/nicht bestanden |
| Logischer Wiedereintritt | Neun quellcodegebundene Invarianten und Induktion; ergänzende KV-/Tokenprüfungen | Bedingter logischer Vertrag für erfolgreiche geschlossene Kohorten |
| Laufzeit und Fehler | 0/72 beobachtete Overruns, minimale Reserve 8,75 ms; analytisches Warm-Erfolg/Kalt-Fehler-Gegenbeispiel | Keine reale Zeit- oder Fehler-Nichtinterferenz |

Bei Platzmangel die ersten drei Kostenzeilen in den Begleittext von
Abbildung 3 verschieben; die drei Schutz-/Garantiezeilen bleiben sichtbar.
Nominale Unsicherheitsintervalle stammen unverändert aus den vorhandenen
Analysen; sie kompensieren keine geringe Zahl unabhängiger Sitzungen.

## 5. Redaktionelle Entscheidungen und Nachvollziehbarkeit

**Haupttext:** die drei genannten Serien plus die separate Llama-Stützung,
die matched Gate-Kosten, begrenzter logischer Vertrag und Fehlerbeispiel.
Der Beweis bekommt keinen eigenständigen Contribution-Punkt. Sein
vollständiges Zustandsmodell und die neun Invarianten bleiben im
vorhandenen Bericht als ergänzendes Artefakt.

**Nicht als zusätzliche Hauptbefunde aufnehmen:** frühe ungleiche
64/256-gegen-512/2048-Kostenvergleiche; die daraus abgeleitete vermeintliche
Latenzüberlegenheit; alle Zwischenprototypen; sämtliche Llama-P0/P1-
Transfers; alte CPU-BOS-Ergebnisse; der negative CUDA-Pilot als vierte
Contribution. Letzterer kann einen Satz zur verworfenen
Weiterentwicklung mit Artefaktverweis erhalten. Ein Offline-Release-Replay
ist weder neue Messung noch gemessene neue Verteidigung.

**Quellenarbeit für das Schreiben:** Die engsten Vorarbeiten sind oben
pro Claim benannt; die breitere vorhandene Quellenkarte bleibt
`docs/quellen.md`. Die Neuheitsmatrix wird nicht erweitert. SIDE ist
weiterhin nur auf Abstractniveau zugänglich und wird nicht als Beweis
für vorhandene oder fehlende Methodenneuheit verwendet. Die Quellenliste
für das Manuskript enthält nur tatsächlich für eine Aussage gelesene
Arbeiten; zusätzliche bibliografische Hinweise sind keine fehlenden
Experimente.

**Artefaktprüfung:** `assets-20261103/manifest.json` bindet jeden
verwendeten Analyse-/Rohdateneingang per SHA-256 an die Abbildungen und
CSVs. `render_existing_results.py` liest ausschließlich vorhandene
Ergebnisse, passt keine Beobachter an und verweigert das Überschreiben
eines bestehenden Zielverzeichnisses. Es berechnet nur beschreibende
Ansichten und übernimmt vorhandene Intervalle. Die drei PNG-Vorschauen
wurden visuell geprüft. Offline-Reproduktion in einem neuen Verzeichnis:

```bash
/home/rock/projects/porto/.venv-py313-repair/bin/python \
  paper/render_existing_results.py paper/assets-NEW
```

**Nächster Arbeitsschritt:** Ein englisches Manuskript entlang dieser
Struktur schreiben und im ACM-Manuskriptformat auf acht Seiten setzen.
Die Ergebnisse und Claimgrenzen sind festgelegt; die Satzprüfung darf
verdichten, aber keine neuen Experimente zur Voraussetzung machen.
Falls der Platz knapp wird, entfällt zuerst zusätzlicher Entwicklungskontext,
nicht die Kontrollen oder die Einschränkung der Schutzbehauptungen.
