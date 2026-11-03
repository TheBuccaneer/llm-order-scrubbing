# ICCAI 2027 – Gesamtüberblick für die externe Validierung

Stand: 03.11.2026. Dieser Überblick fasst die bisherigen lokalen Arbeiten
zusammen. Die detaillierten Berichte und die Quellenkarte sind ebenfalls als
Markdown-Dateien im Übergabe-ZIP enthalten. Messrohdaten, Logs, Grafiken und
Programme liegen **nur im Repository**, nicht im Markdown-ZIP.

**Aktueller Nachtrag am selben Tag:**
`docs/entscheidungsvalidierung-20261102.md` prüft die hier noch offenen
Konfigurations-, Prompt- und Slot-Fallback-Fragen. Danach folgten
`docs/release-boundary-20261102.md`, `docs/late-release-20261102.md`,
`docs/causal-release-pilot-20261102.md` und zuletzt
`docs/randomized-release-pilot-20261102.md` und nun
`docs/c1-cocompletion-20261103.md`. Der letzte Bericht bestätigt
prospektiv eine neue **lokale C1-Beobachtung**: Die vorab fixierte
Regel für fast gleichzeitig vollständig empfangene Antwortpaare
bestimmte in einer frischen balancierten Direktserie die Cacheposition
32/32 Mal. R1 traf 11/32, T2 und RT je 31/32. Vier unvorgewärmte
Kontrollen zeigten keinen engen Paarabstand. Diese Messung prüft noch
weder C1-BOS noch Übertragbarkeit unter anderer Last oder anderen
Modellen. Ein überlegener neuer Angreifer gegenüber T2 ist nicht
belegt. Die folgenden Abschnitte dokumentieren den früheren
Zwischenstand.

## Forschungsfrage und heutige Antwort

Das Projekt knüpft an die eigene ICCAI-2026-Arbeit zu Completion Order und
Budgeted Order Scrubbing (BOS) an. Untersucht wird, welche Information über
einen geteilten LLM-Prefix-Cache aus der **Reihenfolge vollständiger
Antworten** und ihrer **Empfangszeit** sichtbar bleibt, wenn fertige
Antworten blockweise gemischt oder zeitgesteuert freigegeben werden.

**Bisheriger Befund:** In einer gezielt eingestellten lokalen Qwen/vLLM-
Konfiguration erzeugt ein vorgewärmter Prefix einen deutlichen Rangkanal.
Eine tatsächlich arbeitende BOS-Freigabeschicht mischt die Antwort-IDs,
aber der Zeitpunkt, zu dem der Viererblock vollständig und freigabefähig
wird, bleibt clientseitig sichtbar. Eine feste Freigabezeit glättet genau
dieses gemessene Zeitsignal, erhöht aber die individuelle Wartezeit. Das
ist ein wiederholter **lokaler Mechanismusbefund**, kein nachgewiesener
Angriff auf einen fremden Dienst und noch kein geprüfter Paper-Claim.

## System und Beobachter

- Messrechner: AMD Threadripper 3970X, 125 GiB RAM, RTX 3090 mit 24 GiB VRAM,
  Ubuntu 26.04.1. Vorhandene Python-3.13.7-Umgebung mit PyTorch 2.10.0+cu128
  und vLLM 0.17.1; Qwen2.5-7B-Instruct wurde aus dem vorhandenen lokalen
  Modellcache geladen. Es wurde nichts installiert.
- API und Probes: lokaler OpenAI-kompatibler HTTP-Endpunkt, vier bekannte,
  gleich lange Prompt-Kandidaten A–D mit je 548 Tokens und nominell 10 ms
  Sendeabstand. Pro Durchlauf neuer Salt; genau ein Kandidat wird zuvor
  vorgewärmt oder keiner als Kontrolle. Die Kandidaten teilen innerhalb
  eines Durchlaufs absichtlich eine Salt-Domäne. Bei erfolgreicher
  Vorwärmung meldete vLLM intern 544 gecachte Tokens.
- Prägnante Servereinstellung des positiven Viererkanals:
  `max-num-batched-tokens=256`, `long-prefill-token-threshold=64`, FCFS,
  aktiviertes Prefix-Caching, `max-model-len=2048`, Eager-Modus. Die
  Prefill-Schwelle wurde ausdrücklich gesetzt; es handelt sich **nicht**
  um einen allgemeinen vLLM-Standardbefund.
- Der Rangbeobachter sieht nur die Reihenfolge vollständiger HTTP-Antworten.
  Der Zeitbeobachter nutzt nur `T = erste vollständig empfangene
  Clientantwort − erster Clientversand`. Er benutzt weder Proxy-/Backend-
  Zeitstempel noch das Cache-Diagnosefeld. Im letzten Kontrolllauf wurde
  dieses Diagnosefeld aus **allen 816 Clientantworten** entfernt.
- Proxy-Zusatzwartezeit beginnt beim vollständigen Eingang der
  Backend-HTTP-Antwort am Proxy und endet beim Beginn ihrer Freigabe.
  Das ist **kein** instrumentierter interner Modell-Fertigstellungszeitpunkt.

## Versuchskette und Ergebnisse

| Schritt | Aufbau und Umfang | Aussage |
| --- | --- | --- |
| Funktions- und Cacheprüfung | Qwen/vLLM startete auf der RTX 3090; eine Ein-Token- und eine Chat-Antwort waren erfolgreich. Drei Cache-Anfragen zeigten 256 wiederverwendete Tokens bei gleichem Salt und keinen positiven Treffer bei neuem Salt. | Der vorhandene Stack ist lokal nutzbar; aus Einzelzeiten folgt noch kein Kanal. |
| Erster Zweierpilot | 108 balancierte Durchläufe bei Scheduler-Tokenbudget 2048 oder 256. Bei 2048 gewann stets die zuerst gesendete Probe; bei 256 wechselte der Gewinner nahe gleichzeitiger Antworten. | Ein klares Cache-Timing-Signal, aber zunächst **kein belastbarer Rangkanal**. Die nachträglich gewählte 100-ms-Schwelle ist keine extern validierte Regel. |
| Gezielter Rangpilot | 188 weitere Zweier-/Vierer-Durchläufe mit expliziter Prefill-Schwelle und Cache-aus-Kontrollen. Im Viereraufbau mit Cache an kam die vorgewärmte Probe **32/32** Mal zuerst, sogar von Sendeposition 4 in **8/8** Fällen. Mit Cache aus entsprach ihr Rang **32/32** Mal der Sendeposition. | Ein deutlicher, konfigurationsabhängiger Basiskanal; mit Chunked Prefill vereinbar, ohne internen Scheduler-Trace. |
| Zwei Anschlussprüfungen | 80 Durchläufe insgesamt: einmal 16 Ausgabetokens, einmal eine tatsächlich überlappende 64-Token-Zusatzanfrage, jeweils mit Cache-aus-Kontrolle. Bei Cache an gewann die später gesendete vorbereitete Probe in beiden positiven Serien **12/12** Mal; bei Cache aus **0/12** bzw. **2/12** mit fast gleichzeitigen kalten Antworten. | Der lokale Rangkanal überlebt längere vollständige Antworten und eine einzelne Zusatzanfrage; das belegt keine allgemeine Lastrobustheit. |
| BOS-Hauptserie | 272 balancierte Vierer-Durchläufe / 1.088 Probes, je Freigaberegel 64 positive und vier unvorgewärmte Fälle; alle IDs, Zeiten und Cachekontrollen konsistent. | Direkt: vorbereitete Probe **64/64** auf Rang 1. BOS W=4: **19/64**. 100-ms-Ziel: **64/64** allein freigegeben und Rang 1. 250-ms-Ziel: **18/64** bei vollen Viererblöcken. |
| Unabhängige Zeitregelprüfung | 136 weitere Durchläufe / 544 Probes nach Neustart von Backend und Proxy. Eine vorab aus der Hauptserie festgelegte Vierklassenregel nutzte nur T. | W=4: Zeitregel **53/64**, erste Antwort-ID **21/64** richtig. 250-ms-Ziel: **56/64** gegenüber **15/64**. Zufälliges Raten bei vier balancierten Klassen: 16/64 im Erwartungswert. |
| Feste Freigabe und bereinigter Vergleich | Fester Slot 1.050 ms nach erstem Proxy-Anfrageeingang; 64 positive Slot-Fälle in einer eigenen Serie. Danach 204 gemischte Durchläufe / 816 Probes mit W=4, 250 ms und Slot, ohne sichtbares Cachefeld. | Im bereinigten Lauf traf dieselbe ältere W=4-Zeitregel **41/64** bei W=4 und **43/64** bei 250 ms; erste ID **14/64** bzw. **16/64**. Eine aus 16 früheren Slot-Fällen gelernte Zeitregel traf beim Slot **12/64**. Alle Gruppen waren vollständig, kein später Fallback. |

Die Hauptserie misst für die vorbereitete Antwort eine mediane
Proxy-Zusatzwartezeit von **193,79 ms** bei BOS W=4 und **194,31 ms** bei
250 ms Ziel. Das 100-ms-Ziel hielt in dieser Serie die **gemessene**
Zusatzwartezeit aller zugeordneten Probeantworten unter 100 ms
(Maximum 95,03 ms), löste aber den Viererblock in 64/64 positiven Fällen
vorzeitig auf. Es ist keine harte Echtzeitgrenze. Im bereinigten Lauf
lag die mediane Zusatzwartezeit bei **190,62 ms** für BOS W=4 und
**363,24 ms** für den festen Slot; die Differenz der getrennten Mediane
ist **172,62 ms**. Der Slot ist auf diese Last eingestellt, nicht
universell. Bei später Antwort würde sein dokumentierter Fallback die
Freigabe ändern.

Die Zeitregel war auf **denselben** 64 Testfällen deutlich häufiger richtig
als die erste ID: nach Neustart bei W=4 in 36 Fällen ausschließlich die
Zeitregel gegenüber vier Fällen ausschließlich der Rangindikator; im
bereinigten W=4-Lauf 32 gegenüber fünf. Die Regel wurde nicht anhand der
Testfälle nachgestellt. Ihre Trefferquote sank dennoch zwischen den
Läufen von 53/64 auf 41/64; absolute Clientzeiten sind also driftempfindlich.

## Mechanismus, Sicherheit und wissenschaftliche Einordnung

Ein voller BOS-Block wird in diesem Proxy erst freigegeben, wenn seine
**letzte** vollständige Backend-Antwort eingetroffen ist. Die zufällige
Permutation verdeckt, welche Antwort früh fertig war. Der gemeinsame
Freigabezeitpunkt folgt jedoch dem Blockschluss. Im W=4-Hauptlauf
unterschieden sich die Mediane von T je nach vorgewärmter Sendeposition
(1–4): **914,79 / 903,03 / 884,45 / 860,87 ms**. Der Proxy-Backend-
Eingang der letzten Antwort folgte demselben Muster; bis zum ersten
Clientempfang verging danach median rund 0,55 ms. Das erklärt den
beobachteten Restkanal **in diesem Aufbau**. Der feste Slot löste die
Freigabe dagegen am ersten Anfrageeingang aus; in seinem separaten
64er-Lauf lagen die T-Mediane über alle vier Positionen eng bei
**1.051,33–1.051,36 ms**. Das belegt nur die Glättung dieses einen
Zeitmerkmals und keine Abwesenheit stärkerer Kanäle.

Für einen Angreifer wäre der Kanal hier explorierbar, wenn er Kandidaten,
Anfragefolge und gemeinsame Cache-Domäne kontrolliert und präzise Zeiten
misst. Das lokale Ergebnis lässt sich nicht unmittelbar auf unbekannte
Prompts, fremde Nutzer, andere Netze oder Dienste übertragen.
Tenantgetrennte Salts würden gerade diesen Wiederverwendungsweg
unterbinden. Ebenso sind reale Mehrnutzerlast, andere Modelle und weniger
stark eingestellte Serving-Konfigurationen noch ungeprüft.

[PROMPTPEEK](https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf)
und [OptiLeak](https://arxiv.org/html/2602.20595v1) behandeln bekannte
LLM-Reihenfolge-/Positionskanäle; ersteres nutzt LPM und eine gefüllte
Warteschlange, anders als unser FCFS-/Chunked-Prefill-Aufbau.
[Accumulate and Serve](https://arxiv.org/pdf/1302.6123) und
[Pacer](https://www.usenix.org/system/files/sec22-mehta.pdf) sind
Vorarbeiten zu Pufferung und von geheimen Rechenzeiten entkoppelter
Ausgabe. Das Projekt erfindet weder Cache-Leakage noch Mischen noch
Zeitformung. **Möglicher enger Beitrag:** quantitative Restinformation
aus dem Blockschluss bei vollständig freigegebenen LLM-Antworten und
die gemessenen individuellen Kosten einer wirksameren Freigaberegel.
Die bisherige Literaturprüfung war gezielt und abschnittsbezogen;
eine vollständige Neuheitsprüfung fehlt.

## Was als Nächstes wissenschaftlich nötig ist

1. Den vorab festgelegten Beobachter mit anderen gleich langen
   Promptinhalten und mindestens einer weniger stark eingestellten
   vLLM-Konfiguration wiederholen; die bisherige positive
   Prefill-Einstellung darf nicht zum allgemeinen Dienstbefund werden.
2. Verschiedene kontrollierte Lasten und spätere Antworten testen,
   besonders den `late_fallback` des festen Slots und dessen eigenen
   Informationskanal. Erst dann sind Aussagen über praktische
   Angreiferbedingungen und Wartezeitgrenzen möglich.
3. Eine genaue Literaturabgrenzung und ein explizites Bedrohungsmodell
   vor einem Paper-Claim ausarbeiten. Reale Promptrekonstruktion wurde
   bislang **nicht** durchgeführt.

## Konkrete Fragen an die externe Validierung

- Tragen die berichteten Kontrollen und getrennten Testläufe den engen
  Schluss, dass **der Blockschluss** in diesem Aufbau ein Restzeitsignal
  liefert? Welche alternative Erklärung ist mit den dokumentierten
  Zeitpunkten noch vereinbar?
- Ist der Vergleich von W=4, den zwei Ziel-Deadlines und dem festen Slot
  methodisch fair genug für einen **lokalen Schutz-Kosten-Befund**?
  Besonders prüfen: für diese Last gewählter 1.050-ms-Slot,
  `late_fallback`, serielle Ausgabe und absolute Laufzeitdrift.
- Welche präzise Aussage wäre gegenüber PROMPTPEEK, OptiLeak,
  Accumulate-and-Serve, Pacer und der eigenen ICCAI-2026-Arbeit
  tatsächlich neu? Welche Originalarbeit fehlt für diese Abgrenzung?
- Welche kleinste zusätzliche Prüfung würde am meisten über
  Übertragbarkeit und realistische Angreiferbedingungen aussagen?

Die Markdown-Dateien ermöglichen eine **inhaltliche und methodische**
Begutachtung. Eine unabhängige Neuberechnung der Zahlen erfordert die
im Repository verbliebenen JSONL-Dateien und Logs.

## Wo die Belege liegen

| Inhalt | Datei im Repository |
| --- | --- |
| Laufender Projektstand und Quellenprüfungen | `docs/stand.md`, `docs/quellen.md` |
| Erster Machbarkeitspilot | `results/order-feasibility-20261102/auswertung.md` und dort genannte Rohdaten |
| Deutlicher Vierer-Rangkanal | `results/full-order-20261102/auswertung.md` und dort genannte Rohdaten |
| 16 Tokens und Zusatzanfrage | `results/two-extensions-20261102/auswertung.md` und dort genannte Rohdaten |
| BOS, Zeitregel, Slot, bereinigter Lauf | `results/bos-sanitized-20261102/auswertung.md`; Rohdaten in `results/bos-pilot-20261102/`, `results/bos-holdout-20261102/`, `results/bos-slot-20261102/` und `results/bos-sanitized-20261102/` |
| Mess- und Auswerteprogramme | `src/` |
| Spätere Angriffs-/Schutzentscheidung und kausaler Offline-Pilot | `docs/entscheidungsvalidierung-20261102.md`, `docs/release-boundary-20261102.md`, `docs/late-release-20261102.md`, `docs/causal-release-pilot-20261102.md`; abgeleitete Pilotdaten unter `results/causal-release-20261102/` |
| Zufallsslot-Pilot mit negativem Methodenbefund | `docs/randomized-release-pilot-20261102.md`; abgeleitete Pilotdaten unter `results/randomized-release-20261102/` |

Alle genannten Rohdateien bleiben im Repository. Das neue Übergabe-ZIP
enthält ausschließlich Markdown-Dateien; damit kann ein anderer Chat die
Argumentation und Quellenlage prüfen, aber **nicht** die Zahlen aus den
Rohdaten neu berechnen. Zum Zeitpunkt dieser Zwischenbilanz war der
Git-Stand Branch `main`, letzter vorhandener Commit `7690f03`;
die hier beschriebenen Änderungen waren damals noch nicht committet
oder gepusht.
