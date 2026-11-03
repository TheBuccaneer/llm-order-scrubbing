# Öffentliche Präfixstruktur × Scheduler × BOS

Stand: 03.11.2026. Dieser abschließende explorative Pilot vergleicht
zwei Anordnungen derselben synthetischen Dokumentenanalyse-Prompts
auf dem eigenen Qwen2.5-7B-Instruct/vLLM-0.17.1-Server. Das
[Protokoll](../results/prefix-structure-20261103/protocol.json),
die Prompts und die Beobachter standen in Commit `bae5770` vor
den Messungen fest; die lokalen Startbefehle in `fdd1c92`.

## Frage und Abgrenzung

Ändert ein gemeinsamer **öffentlicher** Promptanfang die
Cache-Wiederverwendung, Fertigstellung und nach BOS sichtbare
Clientinformation? In P0 steht der individuelle Dokumentabschnitt
zuerst; die Kandidaten unterscheiden sich schon im ersten
16-Token-Cacheblock. In P1 steht derselbe öffentliche Betriebs-
und Instruktionskontext zuerst; die ersten **304 Tokens = 19 volle
Cacheblöcke** sind bei allen vier Kandidaten identisch. Alle
inhaltlichen Abschnitte und die abschließende Frage bleiben
erhalten, nur die Reihenfolge ändert sich. Jede Variante jedes
Dokuments hat genau 548 Tokens. Die Text- und Tokenprüfung ist
über die gespeicherten Promptdateien reproduzierbar.

Die Strukturierung von Prompts als Sicherheits- und
Leistungsvariable ist [bereits beschrieben](https://developer.nvidia.com/blog/structuring-applications-to-secure-the-kv-cache/).
[Gu et al., ICML 2025, §4.3/Fig. 5](https://arxiv.org/pdf/2502.07776)
untersuchen bereits den Einfluss der Länge eines passenden
Präfixes auf Cache-Timing-Audits. Unsere engere Frage betrifft
die vollständigen Clientantworten **nach BOS W=4** und die
Wechselwirkung mit zwei lokalen Prefill-Regimen. Diese Arbeit
beansprucht keinen neuen allgemeinen Präfix-Cache-Kanal.

## Aufbau und Integrität

C0: `max_num_batched_tokens=256`,
`long_prefill_token_threshold=64`. C1: dasselbe Tokenbudget,
Schwelle 0. Sonst dieselbe lokale Engine, Prefix-Caching an,
16 Ausgabe-Tokens, BOS W=4 unverändert, nominell 10 ms Abstand
zwischen den vier Probes. Die Starts liefen C0 → C1 → C1 → C0.
P0 und P1 wurden innerhalb jedes Starts in einer vorher
gemischten Fallfolge ausgeführt, aber jede Vierergruppe hatte
einen frischen Salt. Je Start und Struktur: 16 positive Gruppen
(vier pro warmer Sendeposition) und zwei ohne Vorwärmanfrage.
Die C0/C1-Paare verwendeten dieselbe Fallfolge mit anderen Salts.
Grenze: **128 positive und 16 Kontrollgruppen**, keine Erweiterung.

Alle **144 Gruppen und 576 Antworten** sind vollständig (HTTP 200,
16 Ausgabe-Tokens), und sämtliche BOS-Freigaben waren volle
Viererblöcke. Das Proxy-Diagnosefeld war für den Client entfernt.
Die Angriffsauswertung verwendet nur eigene Anfrageparameter,
Antwort-IDs und vollständige Client-Sende-/Empfangszeiten. Die
internen Cache- und Proxyzeiten dienen ausschließlich der
Integritäts- und Mechanismusprüfung.

| Backend-Cachetreffer je positive Gruppe | P0 | P1 |
| --- | ---: | ---: |
| Vorbereiteter Kandidat | 544 Tokens | 544 Tokens |
| Jeder der drei anderen Kandidaten | 0 | **304 Tokens** |

Das gilt für alle positiven Gruppen in beiden Konfigurationen:
je Struktur und Konfiguration 32 warme und 96 andere Probes.
P1-Kontrollen ohne Vorwärmanfrage waren **nicht cachefrei**:
innerhalb der Vierergruppe wurde der gemeinsame Kontext teils
bereits durch eine frühere Probe verfügbar. Unter C0 meldeten
die 16 Kontrollantworten pro Struktur viermal 0 und sonst
128–304 gecachte Tokens; unter C1 viermal 0 und zwölfmal 304.
Solche Kontrollen prüfen die fehlende gezielte Vorwärmung,
nicht einen ausgeschalteten Cache.

## Zeiten und individuelle Kosten

| Positive BOS-Gruppen, Median in ms | C0 P0 | C0 P1 | C1 P0 | C1 P1 |
| --- | ---: | ---: | ---: | ---: |
| Letzter Backend-Eingang relativ zur ersten Proxy-Ankunft | 887,6 | **580,7** | 755,5 | **536,0** |
| Erster vollständiger Clientempfang relativ zum ersten eigenen Senden | 888,6 | **581,7** | 756,5 | **536,9** |
| Abstand erster bis letzter Backend-Eingang | 188,5 | **84,2** | 82,2 | **51,1** |
| Individuelle Client-Endzeit, alle Antworten inkl. Kontrollen | 880,5 | **569,1** | 756,0 | **526,3** |
| Individuelle zusätzliche Proxy-Wartezeit, alle Antworten inkl. Kontrollen | 40,5 | 41,4 | 45,3 | **25,3** |

Bei **gepaarten** Fällen schloss der erste Clientblock unter P1
in allen 32/32 Gruppen je Konfiguration früher. Der Median von
P1 minus P0 beträgt C0 **−309,9 ms** (nach Start und Position
stratifiziertes Bootstrap-95-%-Intervall −323,0 bis −306,8 ms)
und C1 **−229,7 ms** (−233,3 bis −225,5 ms). Der letzte
Backend-Eingang verschob sich nahezu gleich stark (−310,1/
−229,7 ms). Die kürzere Zeit entsteht damit überwiegend vor
der BOS-Freigabe. Der Backend-Abschlussspann verringerte sich
gepaart median um 104,0 ms (C0) und 40,4 ms (C1). Unter C1
verringerte sich außerdem die individuelle BOS-Wartezeit; unter
C0 blieb ihr Median ähnlich. Diese Intervalle beschreiben
lokale Wiederholungen, keine Geräte- oder Lastübertragbarkeit.

## Was sieht der Angreifer?

Die **vorher fixierten** vierklassigen R2- und T2-Modelle wurden
je Konfiguration auf 32 älteren P0-Dokumentgruppen trainiert.
Keine aktuelle P0- oder P1-Gruppe floss in dieses Training.
Die binäre AUC trennt warme Sendeposition 1 von 2–4 anhand des
ersten vollständigen Clientempfangs; sie ist keine über Sitzungen
kalibrierte absolute Angriffsregel.

| BOS, je 32 positive Gruppen | C0 P0 | C0 P1 | C1 P0 | C1 P1 |
| --- | ---: | ---: | ---: | ---: |
| R2, vier Klassen | 6/32 | 10/32 | 8/32 | 8/32 |
| **T2, vier Klassen, auf P0 trainiert** | **19/32** | **8/32** | 13/32 | **8/32** |
| R1, erste Antwort-ID | 7/32 | 10/32 | 5/32 | 8/32 |
| Binäre Blockschluss-AUC | 0,938 | **0,875** | 0,953 | **0,818** |
| AUC-Bootstrap-95 %, nach Start geschichtet | 0,844–1,000 | 0,750–1,000 | 0,865–1,000 | 0,656–0,948 |

Je Start fiel T2 unter P1 auf 4/16; unter P0 erreichte es in
den vier Starts 11, 6, 7 und 8/16. Unter C0 beträgt die
gepaarte P0/P1-Diskordanz elf nur unter P0 korrekte gegen null
nur unter P1 korrekte Fälle (exakter zweiseitiger McNemar-
Wert 0,00098). Das ist ein klarer **Transferfehler des P0-Modells**,
noch kein Beweis für weniger Information unter P1.

Der vorab geplante P1-Test mit Neukalibrierung trainiert nur
auf einem der beiden Starts derselben Konfiguration und prüft
auf dem anderen, dann umgekehrt. T2 erreicht unter C0
**22/32** (12/16 und 10/16; Wilson 95 %: 51,4–82,1 %), unter
C1 **14/32** (7/16 und 7/16; 28,2–60,7 %). Als **nachträglich
ergänzter fairer Vergleich** ergab dieselbe Kreuzstart-Methode
für P0 19/32 (C0) und 14/32 (C1). Die Stichproben sind klein;
insbesondere wird aus 22 gegen 19 kein Vorteil von P1 abgeleitet.
Sie widerlegen aber die Interpretation, dass das Absinken des
eingefrorenen P0-T2 auf 8/32 eine Schutzwirkung belege.
Auch der binäre Blockschlusskanal bleibt unter P1 in beiden
Konfigurationen sichtbar. Eine feste Millisekunden-Regel wurde
nicht neu kalibriert oder getestet.

## Mechanismus und wissenschaftliche Entscheidung

Die Logs zeigen die Kette **Promptanordnung → Cachetreffer →
kürzere und enger beieinanderliegende Backend-Abschlüsse →
früheren BOS-Blockschluss**. Sie zeigen zugleich, dass die
absolute Lage des Client-Zeitsignals stark wandert. Das erklärt,
warum der alte Zeitklassifikator unter P1 scheitert und eine
neue Kalibrierung wieder Positionen erkennen kann. Dies ist
eine mit Cache- und Proxyspuren vereinbare Erklärung, kein
isolierter Kausalbeweis aller Schedulerentscheidungen: Die
Promptumstellung ändert auch die Tokenpositionen des Inhalts,
und im neuen Pilot wurden keine Scheduler-Schritte instrumentiert.

**Entscheidung:** P1 ist eine wertvolle Anwendungs- und
Gültigkeitskontrolle für das ICCAI-2027-Paper, aber derzeit
**kein eigener neuer Schutz- oder Angriffsbeitrag**. Der starke
Latenzgewinn ist durch bekannte Präfix-Wiederverwendung
erwartbar; die BOS-spezifische Erkenntnis lautet, dass die
Signalform und Kalibrierung wechseln, während Restinformation
auch unter geteilter öffentlicher Präfixstruktur erkennbar
bleibt. Dieses Ergebnis gehört als gezielte Ablation in den
empirischen Beitrag. Wir beenden damit die zusätzliche
Exploration und strukturieren das Manuskript anhand der
nachgewiesenen Befunde.

Die Daten gelten für synthetische Dokumente, eine Promptfamilie,
ein Modell, eine GPU, Loopback, 16 Ausgabetokens, kontrollierte
Vorwärmung und eine gemeinsame Salt-Domäne. [vLLM beschreibt
tenantgetrennte Salts](https://docs.vllm.ai/en/v0.17.1/design/prefix_caching/)
als Cache-Isolation. Die Beobachtbarkeit fremder Dienste oder
die Sicherheit anderer Konfigurationen wurde hier nicht
gemessen. Die Bootstrap-Intervalle und McNemar-Werte sind
lokale Unsicherheitsangaben; mehrere sekundäre Beobachter
wurden betrachtet.

## Reproduktion

- Vorabprotokoll und Startskript: `results/prefix-structure-20261103/protocol.json`, `run.sh`.
- Prompts: `data/document-workload-20261103/prompts.json` (P0) und `data/prefix-structure-20261103/prompts-p1.json` (P1); SHA-256-Werte im Protokoll.
- Client und Auswertung: `src/prefix_structure_run.py`, `src/prefix_structure_analysis.py` (`PYTHONPATH=src`).
- Rohdaten: `results/prefix-structure-20261103/run1-c0/` bis `run4-c0/`, je `trials.jsonl`, `proxy.jsonl` und Client-/Proxy-/Serverlogs.
- Maschinenlesbare Gruppenmerkmale und Auswertung: `results/prefix-structure-20261103/analysis.json`. Backend-/Proxyfelder in dieser Datei sind ausschließlich Mechanismusdiagnostik.

Alle Prozesse wurden beendet. Keine Daten aus früheren Sitzungen
überschrieben und kein fremder Dienst angesprochen.
