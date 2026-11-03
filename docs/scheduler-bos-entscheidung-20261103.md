# Forschungsentscheidung: Scheduling und BOS bei vollständigen LLM-Antworten

Stand: 03.11.2026. Alle Live-Anfragen gingen nur an den eigenen lokalen
Qwen2.5-7B-Instruct/vLLM-0.17.1-Server. Diese Auswertung entscheidet
über die **Paper-Richtung**, nicht über eine allgemeine Schutzgarantie.

## Entscheidung

**Ein eng gefasstes empirisches Nachfolgepaper ist jetzt sinnvoll.**
Die neue Aussage ist der Wechsel der *Form* der Restinformation nach
BOS W=4: Unter C0 bleibt die vierklassige Cacheposition aus der
vollständigen Clientzeitfolge oft erkennbar. Unter C1 ist der einfache
Rang und die getestete vierklassige Zeitklassifikation deutlich
schwächer, doch der Zeitpunkt des BOS-Blockschlusses trennt weiterhin
„vorgewärmt an Sendeposition 1“ von „an Position 2–4“.

Das ist eine lokale Scheduler-/Freigabe-Interaktion, **kein** neuer
allgemeiner Cache-Timing-Angriff und **kein** Beweis, dass C1-BOS sicher
ist. Die absolute 780-ms-Angriffsregel scheiterte in der ersten neuen
Sitzung; ein über Sitzungen stabiler öffentlicher Schwellwert ist nicht
belegt. Das kontinuierliche Rangmaß des Blockschlusses und der
Konfigurationsunterschied wurden danach mit neuer Fallfolge geprüft.

## Aufbau und Vorabfestlegung

| Größe | C0 | C1 |
| --- | --- | --- |
| `max_num_batched_tokens` | 256 | 256 |
| `long_prefill_token_threshold` | 64 | 0 |
| Modell, Prompt und Ausgabe | Qwen2.5-7B-Instruct; vier 548-Token-Kandidaten; 16 Ausgabetokens | identisch |
| Cache und Freigabe | Prefix-Caching an, BOS W=4 | identisch |
| Anfragen | nominell 10 ms versetzt, gemeinsamer frischer Salt je Vierergruppe | identisch |

Die alte C1-Direktserie hatte mit der vorab fixierten
Paarabstandsregel 32/32 Treffer, aber noch kein C1-BOS-Ergebnis für
diese Struktur. Zuerst wurden vorhandene Backend-Spuren mit dem
bestehenden `offline_gate_replay.py` durch direkte Freigabe, BOS W=4
und einen festen 1.050-ms-Slot geschickt. Das Replay-Protokoll und die
erste C1-BOS-Regel wurden in Commit `801be59` **vor** der neuen
Live-Messung fixiert.

Danach liefen 32 positive C1-BOS-Gruppen plus vier unvorgewärmte
Kontrollen mit neuem Backend und Seed `202611030531`. Die fixierte
780-ms-Regel scheiterte. Der kontinuierliche binäre AUC-Wert war
hingegen hoch. Für die separate Bestätigung wurden in Commit
`d27ac97` **vor** weiteren Messungen gleiche neue Fallfolgen unter
C0 und C1 festgelegt: Seed `202611030901`, je 32 positive Gruppen
(acht pro warmer Sendeposition), vier unvorgewärmte Kontrollen,
frische Salts und getrennte Engine-Starts. Die Angreifer sehen nur
eigene IDs, Anfrageparameter und vollständige Client-Sende-/
Empfangszeiten. Proxy-/Backenddaten prüfen Integrität und Mechanismus.
Die bestehende BOS-Regel blieb unverändert.

Alle drei neuen Live-Sitzungen waren vollständig: je 36 Gruppen,
144 HTTP-200-Antworten, volle BOS-Viererblöcke und intern genau
544 gecachte Tokens auf der vorgewärmten Probe. Das Cache-Diagnosefeld
wurde aus allen Clientantworten entfernt. Die beiden letzten Serien
haben dieselbe Fallfolge, aber verschiedene Salt-Tags. Die
Engine-Konfigurationen liefen nacheinander; es gab keine
randomisierte Crossover-Reihenfolge.

## Teil A: Offline-Replay auf vorhandenen Direktspuren

Das Replay nutzt 68 C0-Direktgruppen (64 positive) und 36
C1-Direktgruppen (32 positive). Es setzt für BOS den letzten
vollständigen Backend-HTTP-Eingang als idealen Gruppenschluss,
für den Slot `erste Proxy-Ankunft + 1.050 ms` und modelliert danach
2 ms serielle Ausgabe je Antwort. Es enthält weder Timer-/Netz-Jitter
noch Rückkopplung in die Engine. **Die so erzeugten Clientzeiten
sind keine gemessenen Antworten.**

| Idealisierte Größe | C0-Direktspuren | C1-Direktspuren |
| --- | ---: | ---: |
| Volle BOS-Gruppen | 68/68 | 36/36 |
| Fester Slot vollständig / später Fallback | 68/68 / 0 Antworten | 36/36 / 0 Antworten |
| Paarabstandsregel bei direkter Freigabe | 12/64 | 32/32 |
| Paarabstandsregel nach modelliertem BOS | 21/64 | 8/32 |
| Median individueller BOS-Wartezeit | 40,29 ms | 41,48 ms |
| Median individueller Slot-Wartezeit | 204,83 ms | 315,40 ms |
| Gepaarter Median: Slot minus BOS je Antwort | +151,82 ms | +276,15 ms |

Die Paarabstandsregel verliert unter vollständigem BOS ihren
direkten Bezug zum Backend-Abschlusspaar; die sichtbaren Abstände
entstehen nun durch das serielle Freigeben des gemischten Blocks.
Der ideale BOS-Blockschluss bleibt dagegen vom letzten vollständigen
Backend-Eingang abhängig. In den C1-Direktspuren lag seine
modellierte erste Clientzeit im Median bei **779,56 ms** für
warme Position 1 und bei **759,11–765,98 ms** für Position 2–4.
Der Slot glich diese vier modellierten Mediane bei etwa 1.050,5 ms
an. Die 1.050-ms-Deckung gilt nur für diese 16-Token-Spuren;
bei älteren 24-Token-C0-Serien wurde ein echter Slot-Fallback
bereits häufig gemessen.

## Teil B: Neue Clientmessungen

Im ersten frischen C1-BOS-Lauf traf die **vorher fixierte** Regel
`erste vollständige Antwort - erste eigene Sendung >= 780 ms`
nur **4/8** Positions-1-Fälle und verursachte **3/24** Fehlalarme
bei Position 2–4. Sie verfehlte ihr Erfolgskriterium. Der
Schwellwert war an alten C1-Sitzungen gewählt worden; sein Versagen
ist ein reales Generalisierungsproblem. Der vorher ebenfalls
benannte kontinuierliche Blockschlusswert ergab AUC **0,906**
(8 gegenüber 24 Fällen; einseitiger exakter Mann-Whitney-p-Wert
0,000125). Die vierklassigen Beobachter trafen nur R1 5/32,
R2 8/32, T1 8/32, T2 8/32 und RT 10/32.

In der separaten **gepaarten Fallfolge** wurden R2/T1/T2/RT je
Konfiguration mit derselben logistischen Modellklasse (`C=1`,
StandardScaler) auf **32 balancierten älteren BOS-Gruppen** trainiert.
Keine neue Messung floss ins Training. R1 ist die erste Antwort-ID.
T1 ist der erste vollständige Client-Empfangszeitpunkt relativ zum
ersten eigenen Versand; T2 nutzt alle vier Zeiten, RT zusätzlich
alle Ränge. Vierklassiges Zufallsraten erwartet 8/32 Treffer.

| Neuer Live-Test, 32 positive Gruppen je Bedingung | C0 BOS | C1 BOS |
| --- | ---: | ---: |
| R1 | 6/32 | 8/32 |
| R2 | 9/32 | 7/32 |
| T1 | **23/32** | 10/32 |
| T2 | **21/32** (Wilson 48,3–79,6 %) | **11/32** (20,4–51,7 %) |
| RT | 14/32 | 9/32 |
| AUC: Blockschluss, Position 1 gegen 2–4 | 0,896 (Bootstrap 0,760–1,000) | **0,813** (0,646–0,948) |
| Median tatsächlicher individueller Proxy-Wartezeit unter BOS | 43,30 ms | 45,53 ms |

Die vorab festgelegte Entscheidungshilfe (C0-T2 mindestens 20/32,
C1-T2 höchstens 12/32, C1-binäre AUC mindestens 0,8) wurde mit
21/32, 11/32 und 0,813 erfüllt. Ein nachträglich berechneter
gepaarter McNemar-Test für T2 hat 15 nur unter C0 und fünf nur
unter C1 korrekte Fälle (zweiseitig p=0,041); dies ist wegen
mehrerer betrachteter Beobachter **stützende, keine allein tragende**
Evidenz. Die T1-Differenz ist größer, RT unterscheidet sich
weniger klar. Die Daten beweisen keine Abwesenheit eines stärkeren
C1-Vierklassenbeobachters.

**Geltungsgrenzen:** Der „Opferzustand“ wurde lokal durch eine
eigene Vorwärmanfrage erzeugt. Alle vier Kandidaten teilten
absichtlich denselben Salt-Bereich; getrennte, geheime Tenant-Salts
würden diese Wiederverwendung gemäß dem
[vLLM-Prefix-Cache-Design](https://docs.vllm.ai/en/v0.17.1/design/prefix_caching/)
verhindern. Die Probes liefen über
Loopback ohne fremde Hintergrundlast, mit einer Engine, einem Modell,
einer Promptfamilie und einer Ausgabelänge. Die vier
unvorgewärmten Kontrollen pro neuer Bedingung prüfen den
Mechanismus, schätzen aber keine seltenen Fehlalarme präzise.
Insbesondere sagt eine schwache vierklassige Accuracy nichts
Abschließendes über andere Angreifer oder Beobachtungsbudgets.

Die vier Zellen des Forschungsvergleichs sind damit belegt, aber
stammen nicht alle aus derselben Sitzung:

|  | Direkte Freigabe | BOS W=4 |
| --- | --- | --- |
| C0 | R1 64/64 auf der älteren Direktserie | T2 21/32 im neuen gepaarten Test |
| C1 | Paarabstandsregel 32/32 und T2 31/32 im frischen Direkttest | T2 11/32 und binäre Blockschluss-AUC 0,813 im neuen gepaarten Test |

Diese Zahlen beschreiben verschiedene Beobachter und Stichproben;
die Tabelle ist eine Mechanismuskarte, keine gemeinsame
Accuracy-Rangliste.

Unter C1 liegen die Mediane des **gemessenen** ersten vollständigen
Clientempfangs bei 784,57, 771,40, 764,79 und 760,20 ms für warme
Sendeposition 1–4. Der alte 780-ms-Schwellwert traf in dieser
Sitzung 7/8 Positions-1-Fälle bei 6/24 Fehlalarmen. Zusammen mit
seinem Versagen in der vorherigen Sitzung ist er als stabiler
Angriffsschwellenwert ungeeignet. Der Rangzusammenhang bleibt
innerhalb der Sitzungen sichtbar; die AUC benötigt keinen festen
Millisekunden-Schwellwert, aber ein nutzbarer Angreifer müsste die
Richtung und eine Kalibrierstrategie kennen.

## Teil C: Mechanismus aus vier instrumentierten Gruppen

In Commit `3ccd058` wurde vor der Instrumentierung eine optionale
`Scheduler.schedule`-Protokollierung fixiert. Je Konfiguration
wurden nur zwei erklärende Gruppen gefahren: warme Probe A zuerst
(`ABCD`) und zuletzt (`BCDA`). Die Instrumentierung loggte pro
Engine-Schritt Request-ID, geplante Tokenzahl, berechnete Tokens
vor dem Schritt und Promptlänge. Diese Felder wurden **nie** als
Angreifermerkmale verwendet. Python-Logging kann selbst Laufzeiten
verschieben; die Spuren dienen nur zur qualitativen Erklärung.

| Beobachtung in den instrumentierten Schritten | C0 | C1 |
| --- | --- | --- |
| Kalte Probe, 548 Prompttokens | neun Prefill-Teile: achtmal 64 und zuletzt 36 | etwa drei Teile; z. B. 256, 256, 36 Tokens |
| Warme Probe | 544 Tokens bereits berechnet, 4 Tokens Rest-Prefill | ebenso |
| Warme A zuletzt in `BCDA` | letzter Decode-Schritt A: 61; D: 68; getrennte Backend-Antworten | A und D beginnen Decode beide in Schritt 36 und enden beide in Schritt 50; Backend-Abstand 0,081 ms |
| Warme A zuerst in `ABCD` | A endet vor kalten Probes; letzte Antwort aus B/C/D | A endet Schritt 18; kalte B/C/D in Schritten 21/23/25; Blockschluss später |

Die tatsächlichen Tokenpläne sind mit dem beobachteten Wechsel
vereinbar: C1 erlaubt bei diesem Tokenbudget größere kalte
Prefill-Schritte; eine später eintreffende warme Probe kann mit
einem Vorgänger in dieselben Decode-Schritte fallen. BOS entfernt
dann den sichtbaren engen Einzelantwort-Abstand, übernimmt aber die
Zeit des letzten vollständigen Backend-Eingangs als Blockschluss.
Vier instrumentierte Gruppen erklären die Möglichkeit, nicht die
Verteilung aller Messfälle oder die Robustheit unter Mehrnutzerlast.

## Literaturgrenze und Contribution Statement

Die Recherche las gezielt die relevanten Originalabschnitte (RDNA
L2); sie ist **kein** vollständiger systematischer Neuheitsnachweis
und kein gesondert verfügbares „Deep-Research“-Produkt.

| Quelle | Bekanntes Ergebnis | Abgrenzung unserer Aussage |
| --- | --- | --- |
| [PROMPTPEEK, NDSS 2025](https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf), §IV-A, §VIII | Antwortreihenfolge mit Ein-Token-Probes unter LPM | Keine dortige Evaluation der vollständigen BOS-Clientzeitfolge unter den hier gemessenen vLLM-Regimen. Die damalige Aussage über FCFS wird nicht auf vLLM 0.17.1 übertragen. |
| [OptiLeak v1](https://arxiv.org/html/2602.20595v1), §4.2, §6 | Positionsfeedback; FCFS-Timing/TTFT als Adaption ausdrücklich genannt | Timing-Inferenz an sich ist Vorarbeit; untersucht wird hier der Informationswechsel **nach** Blockfreigabe. |
| [Pacer, USENIX Security 2022](https://www.usenix.org/system/files/sec22-mehta.pdf), §3.2 | Geheimnisunabhängiger sichtbarer Sendeplan und Abweichungen sind bekannte Schutzprinzipien | Unsere Daten quantifizieren konkrete lokale LLM-Blockschluss- und Wartekosten; kein neuer allgemeiner Padding-Algorithmus. |
| [SafeKV v2](https://arxiv.org/html/2508.08438v2), §7.2, und [PrefixWall v2](https://arxiv.org/html/2603.10726v2), §§2.2, 5.2 | Schutz der Cache-Wiederverwendung und TTFT-basierte Prüfung | Andere Schutzfläche als die Freigabe vollständiger HTTP-Antworten. |
| [Contention-Induced Reliability Collapse](https://arxiv.org/html/2609.06853), §§IV-B, XIV–XV | Nicht gestreamte vollständige Client-Endzeiten sind für Ein-Token-Probes und Konkurrenzlast bereits untersucht | Vollantwortzeit an sich ist nicht neu; hier zählt der Vierer-Blockschluss nach BOS bei 16 Ausgabetokens. Lastrobustheit bleibt offen. |
| [One-Sided Bounded Noise, CCS 2025](https://people.csail.mit.edu/devadas/pubs/one_sided_noise.pdf), §§1–2, 5 | Positive beschränkte Verzögerung und ihre Optimierung sind Vorarbeit | Der feste Slot wird nur als bekannter Kosten-/Schutzvergleich genutzt. |
| [Sarathi-Serve](https://arxiv.org/html/2403.02310), §§4.1–4.2, und [vLLM 0.17.1](https://docs.vllm.ai/en/v0.17.1/api/vllm/config/scheduler/) | Chunked Prefill und Tokenbudget bestimmen die Planung | Scheduling-Technik ist nicht neu; der gemessene Einfluss auf die **BOS-Restinformation** ist unser enger Kandidat. Sarathi-Serve wird nicht als Implementierung unseres vLLM behauptet. |
| [Eigene ICCAI-2026-Arbeit](../references/iccai2026-completion-order.pdf), zuvor L3 | ODS/BOS aus Antwort-Rängen, ohne vollständige Clientzeiten | Der Nachfolger bewertet die ganze Clientzeitfolge und individuelle Freigabekosten. |

**Vorläufiger Beitragssatz:** *Bei lokalem vLLM/Qwen kann dieselbe
BOS-Viererfreigabe je nach Prefill-Planung von einem vierklassigen
Clientzeitkanal zu einem schwächeren, aber messbaren binären
Blockschlusskanal wechseln; ein fester Antwortslot glättet diesen
Wechsel in den beobachteten Spuren nur gegen zusätzliche individuelle
Wartezeit und mit einer bekannten Fallback-Grenze.*

Damit passen drei zusammenhängende Forschungsfragen: (1) Wohin
wandert Information von Rang zu vollständiger Clientzeit nach BOS?
(2) Welche Prefill-/Decode-Planung bestimmt das Restsignal?
(3) Welche individuelle Wartezeit und welcher Fallback entstehen,
wenn die Freigabe vom Blockschluss entkoppelt wird?

**Paper-Entscheidung:** Einen Manuskriptentwurf zu dieser engen
empirischen Aussage beginnen. Vor einem endgültigen allgemeinen
Claim fehlen mindestens ein unabhängig anderer Prompt-/Lastfall
und eine saubere quantitative Schutz-/Kostenabbildung über mehrere
Ausgabelängen. Ohne diese Ergänzung soll das Manuskript die
Geltung auf diesen lokalen Aufbau begrenzen. Ein neuer Angreifer,
ein sicherer C1-BOS-Schutz oder ein neuer Delay-Algorithmus werden
derzeit nicht beansprucht.

### Antworten auf die sechs Entscheidungsfragen

1. **C1 nach BOS:** Ja, ein binäres Client-Zeitrangsignal trat in
   getrennten Sitzungen und im neuen gepaarten Test auf; ein fixer
   780-ms-Angriffsschwellenwert generalisierte nicht zuverlässig.
2. **C0 gegenüber C1:** Für die getesteten vierklassigen T1-/T2-
   Beobachter ja, lokal und mit gleicher neuer Fallfolge. R1 und RT
   stützen keinen pauschalen Unterschied aller Beobachter.
3. **Mechanismus:** Die vier instrumentierten Gruppen zeigen
   unterschiedliche Prefill-Teilung und gemeinsames Decoding als
   plausible unmittelbare Erklärung; eine umfassende Kausalstudie
   sind sie nicht.
4. **Schutzkosten:** BOS wartet hier im Median ungefähr 43–46 ms
   nach vollständigem Proxy-Backend-Eingang. Ein fester 1.050-ms-Slot
   kostet im idealen Replay zusätzlich gepaart median 152 ms (C0)
   beziehungsweise 276 ms (C1) je Antwort; bei längeren Antworten
   bleibt der dokumentierte Fallback relevant.
5. **Neuheit:** Der enge Kandidat ist die gemessene
   Schedulerabhängigkeit der **Restinformation nach BOS** mit
   individuellen Kosten. Cache-/Timing-Inferenz, Batching und feste
   Sendepläne sind Vorarbeit.
6. **Paper:** Ja, als begrenzte empirische Anschlussarbeit mit den
   drei genannten Forschungsfragen. Ein allgemeiner Sicherheitsclaim
   benötigt weitere Prompt-/Lastbedingungen und einen präziseren
   Vergleich der Freigabekosten.

Die [offizielle ICCAI-2027-Startseite](https://www.iccai.net/)
nennt für reguläre Einreichungen **10. Dezember 2026**; die
[Sondersitzungsseite](https://www.iccai.net/special.html) nennt
**10. November 2026** für Beiträge zu Sondersitzungen. Der im
eingefügten Vorschlag angenommene allgemeine 10.-November-Termin
gilt nach dieser aktuellen Prüfung nicht für reguläre Beiträge.

## Reproduktion und Daten

Offline-Modell und seine Grenzen: `src/scheduler_bos_replay.py`,
`results/scheduler-bos-decision-20261103/replay.json` und
`replay-rows.jsonl`. Die beiden Live-Protokolle wurden vor den
zugehörigen Messungen als `protocol.json` und
`matched-protocol.json` fixiert. Für den ersten C1-Lauf liegen
`live/trials.jsonl`, `live/proxy.jsonl` und `live/analysis.json`
vor; für den gepaarten Vergleich `matched-c0/` und `matched-c1/`
mit je `trials.jsonl`, `proxy.jsonl`, Client-/Serverlog und
`matched-analysis.json`. Die Angriffs- und Integritätsauswertung
ist in `src/scheduler_bos_live_analysis.py` und
`src/scheduler_bos_matched_analysis.py` festgehalten.

Die vier Mechanismusspuren stehen unter `trace-c0/` und
`trace-c1/` (`scheduler.jsonl`, `trials.jsonl`, `proxy.jsonl`);
der opt-in-Wrapper liegt unter `instrument/sitecustomize.py`.
Alle Rohdaten bleiben im Repository. Die Laufzeit-Caches sind
ignorierbar und enthalten keine Messfälle. Nach jeder Sitzung
wurden Backend und Proxy beendet; die Freigaberegel wurde nicht
geändert.
