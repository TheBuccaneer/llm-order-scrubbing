# Llama-3.1-8B-Instruct als zweites Referenzmodell

Stand: 03.11.2026. Lokale Validierung der bisherigen Qwen/vLLM-Befunde.
Nur der eigene Messrechner und die bestehende BOS-Implementierung
werden verwendet; alte Rohdaten bleiben unverändert.

## Phase A: Modellstart

Der lokale Snapshot `0e9e39f249a16976918f6564b8830bc894c89659`
enthält die vier im Safetensors-Index genannten Gewichtsshards
(291 Tensoren), Konfiguration und Tokenizer. Die vorhandene
Python-3.13.7-Umgebung lädt vLLM 0.17.1, PyTorch 2.10.0+cu128
und Transformers 4.57.6. CUDA erkennt die RTX 3090. Es wurde
nichts installiert.

Der Server startete lokal mit maximal 2.048 Modell-Tokens,
`gpu_memory_utilization=0.8`, Eager-Modus, Prefix-Caching,
Tokenbudget 256 und Prefill-Schwelle 64 (C0). Ein erster roher
`/v1/completions`-Test lieferte HTTP 200 und die vollständige
nicht gestreamte JSON-Antwort, endete aber wegen `max_tokens=16`
mit `finish_reason=length` und einem unpassenden Fortsetzungstext.
Der unmittelbar folgende Chat-Test lieferte HTTP 200,
`finish_reason=stop` und die Antwort „Ready“. Der rohe Test
ist deshalb nur ein Server-/API-Nachweis, der Chat-Test der
erfolgreiche Instruktionsmodell-Funktionstest. Beide Anfragen
und Antworten sowie das Serverlog stehen unter
`results/llama-reference-20261103/phase-a/`. Der Server wurde
danach beendet.

## Phase B: Tokenisierung, vor der Cacheprüfung

Der lokale Llama-Tokenizer fügt beim Completion-Endpunkt ein
BOS-Token hinzu. Der alte künstliche Qwen-Prompt hat unter Llama
für alle vier Kandidaten 549 Prompttokens statt 548. Die vier
Dokumenten-Prompts hätten 549, 547, 547 und 549 Tokens.
Für Llama wurde bei Dokument B und C vor der abschließenden
Frage nur „Reviewed.“ ergänzt. Damit haben alle vier Kandidaten
in P0 und P1 jeweils 549 Tokens inklusive BOS. P0 teilt
keinen vollständigen ersten 16-Token-Block; P1 teilt 305
Anfangstokens und damit 19 volle Blöcke (304 Tokens).

Prompts und Tokenbefund stehen unter
`data/llama-reference-20261103/`. Die Qwen-Prompts wurden
nicht geändert. Ein kleiner C0-Cachetest mit gleichem und
verschiedenem Salt ist in
`results/llama-reference-20261103/phase-b/protocol.json`
vor der Ausführung festgelegt.

### Cacheprüfung abgeschlossen

Die sieben vorab festgelegten direkten Anfragen erhielten HTTP 200
und je 549 Prompttokens. Bei wiederholtem P0- oder P1-Prompt mit
demselben Salt meldete vLLM jeweils **544 gecachte Tokens**.
P0-Dokument B mit demselben Salt hatte keinen Treffer;
P1-Dokument B nutzte **304 gemeinsame Tokens**. P1-Dokument A
mit einem neuen Salt hatte keinen Treffer. Die tatsächlichen
Cacheblöcke entsprechen damit der Tokenprüfung. Rohantworten,
Anfrageparameter und Zeitpunkte stehen in
`results/llama-reference-20261103/phase-b/cache-check.jsonl`;
das Serverlog liegt daneben. Der Server wurde beendet.

Die Cachemechanik rechtfertigt einen kleinen direkten C0/C1-Pilot.
Sein Protokoll steht in
`results/llama-reference-20261103/phase-c-protocol.json`.

## Phase C: direkter Basiskanal

Je Konfiguration liefen 16 balancierte positive Vierergruppen und
vier unvorgewärmte Kontrollen mit neuer Engine und identischer
Fallfolge bei frischen Salts. Alle 160 Antworten waren vollständig
und hatten je 549 Prompt- und 16 Ausgabetokens. Nur die warme
Probe hatte 544 gecachte Tokens; das Cache-Diagnosefeld wurde
aus allen Clientantworten entfernt.

| Direkte Freigabe | C0 | C1 |
| --- | ---: | ---: |
| R1, warme Antwort zuerst | **16/16** | 7/16 |
| Alte Qwen-Paarabstandsregel | 4/16 | **16/16** |
| Warme Backend-Antwort zuerst (Mechanismus) | 16/16 | 7/16 |
| Unvorgewärmte Kontrollen mit engem Paarabstand | 0/4 | 0/4 |

Die Wilson-95-%-Intervalle für 16/16 reichen von 80,6 bis 100 %.
Der C0/C1-Formunterschied der direkten Clientbeobachtung zeigt
sich damit auch unter Llama in diesem kleinen lokalen Pilot.
Die bereits vorab festgelegte Entscheidungshilfe wurde erfüllt;
ein gezielter BOS-Vergleich ist gerechtfertigt. Rohdaten und
Auswertung liegen unter `results/llama-reference-20261103/direct-c0/`,
`direct-c1/` und `direct-analysis.json`. Beide Server wurden beendet.

## Phase D: vollständige BOS-Freigabe W=4

Das [vorab festgelegte Protokoll](../results/llama-reference-20261103/phase-d-protocol.json)
und die Angreifer standen in Commit `fa3adce` vor den Live-Messungen.
Die Serverreihenfolge war Entwicklung C0 → C1, danach unabhängige
Prüfung C1 → C0. Je Entwicklungsstart liefen 16 balancierte positive
Gruppen und zwei unvorgewärmte Kontrollen; je Prüfstart 32 positive
Gruppen und vier Kontrollen. Die Prüfung nutzte neue Fallfolgen,
Salts und Engines. Insgesamt waren **108 Vierergruppen und 432
vollständige HTTP-200-Antworten** gültig. Alle BOS-Blöcke enthielten
vier Antworten; intern hatte nur der vorgewärmte Kandidat 544
Cachetokens. Das Cachefeld fehlte in sämtlichen Clientantworten.
Die bestehende BOS-Regel wurde nicht geändert.

R1 nimmt die zuerst empfangene ID. R2 nutzt die vier Ränge,
T1 den ersten vollständigen Empfang relativ zum ersten eigenen
Senden, T2 alle vier vollständigen Empfangszeiten und RT beides.
R2/T1/T2/RT wurden je Konfiguration ausschließlich auf den 16
Llama-Entwicklungsfällen mit `StandardScaler` und logistischer
Regression (`C=1`) trainiert und dann auf 32 neuen Fällen geprüft.
Proxy-, Cache- und Backendfelder waren keine Angreifermerkmale.

| Llama BOS, unabhängige Prüfung | C0 | C1 |
| --- | ---: | ---: |
| R1 | 6/32 | 8/32 |
| R2 | 5/32 | 10/32 |
| T1 | **22/32** | 15/32 |
| T2 | **21/32** (Wilson 95 %: 48,3–79,6 %) | **14/32** (28,2–60,7 %) |
| RT | 11/32 | 14/32 |
| Blockschluss-AUC, warme Position 1 gegen 2–4 | **0,911** (Bootstrap 95 %: 0,797–0,990) | **0,953** (0,865–1,000) |
| Individuelle BOS-Zusatzwartezeit, Median / p95 | 44,30 / 230,33 ms | 47,28 / 139,02 ms |

Die Richtung des binären Blockschlussmaßes („Position 1 später“)
stammt aus den Entwicklungsfällen; die AUC setzt keinen festen
Millisekunden-Schwellwert voraus. Das vorab benannte
Entscheidungskriterium wurde erfüllt. Unter C0 sind die vier
Clientzeiten deutlich informativer als der erste Rang. C1 zeigt
mit T2 14/32 weniger vierklassige Treffer, aber auch dort einen
ausgeprägten binären Restzeitkanal. Der C0/C1-Unterschied der
Accuracy ist bei nur 32 Fällen je Bedingung **nicht als gesicherter
Modelleffekt** zu lesen; die Intervalle überlappen. Einseitige
unbereinigte Binomialwerte gegen 25 % Zufall sind für T2 C0
0,0000015 und C1 0,0159. Fünf Beobachter wurden betrachtet;
diese Werte sind keine multipel korrigierte Beweisführung.

Die Prüfserie hatte mediane erste Clientzeiten in ms nach warmer
Sendeposition 1–4 von 953,9 / 950,8 / 940,9 / 892,6 (C0) und
784,6 / 760,9 / 772,8 / 765,3 (C1). Der Blockschluss hängt mit
der warmen Sendeposition zusammen, obwohl BOS die Antwort-IDs
mischt. Die intern protokollierten Abschlusszeiten sind damit
vereinbar; Scheduler-Schritte wurden für Llama nicht erneut
instrumentiert. Der genaue C0/C1-Unterschied in Prefill und Decode
bleibt eine plausible, nicht isoliert bewiesene Erklärung.

## Phase E: synthetische Dokumente und öffentlicher Präfix

Weil der BOS-Restkanal unter Llama sichtbar war, folgte ein kleiner
Transfer gemäß [vorab festgelegtem Protokoll](../results/llama-reference-20261103/phase-e-protocol.json)
(Commit `4b05321`). Je frischem C0- und C1-Start wurden P0 und P1
gemischt gemessen: pro Struktur 16 positive, vierfach balancierte
BOS-Gruppen und zwei Kontrollen, insgesamt **72 Gruppen und 288
Antworten**. P0 und P1 haben jeweils 549 Llama-Tokens. P0 teilt
keinen ganzen Anfangsblock; P1 teilt 304 Tokens im öffentlichen
Anfang. Alle Antworten waren vollständig; alle Blöcke waren W=4;
alle warmen Probes hatten 544 Cachetokens und das Clientfeld war
entfernt. Bei P1 nutzten auch kalte Probes gemeinsame Blöcke:
unter C0 meldeten 50/56 solche Probes 304 Tokens, unter C1
54/56. Die restlichen C0-Probes meldeten 0, 128 oder 256 Tokens.
P0 meldete auf allen 56 kalten/Kontrollprobes je Bedingung keinen
Cachetreffer. P1-Kontrollen sind wegen der gemeinsamen Struktur
nicht als cachefrei zu interpretieren.

| Llama-Dokumente, je 16 positive Gruppen | C0 P0 | C0 P1 | C1 P0 | C1 P1 |
| --- | ---: | ---: | ---: | ---: |
| R1 | 4/16 | 5/16 | 3/16 | 6/16 |
| T2, **unverändert auf künstlichen Llama-Prompts trainiert** | **14/16** | 4/16 | 6/16 | 4/16 |
| Binäre Blockschluss-AUC, Entwicklungsrichtung | 0,917 | 0,875 | 0,938 | 0,792 |
| Bootstrap 95 % der AUC | 0,688–1,000 | 0,667–1,000 | 0,750–1,000 | 0,521–0,979 |
| Erster vollständiger Clientempfang, Median | 949,6 ms | **626,5 ms** | 774,0 ms | **550,4 ms** |
| Letzter Backend-Eingang, Median | 948,6 ms | **625,5 ms** | 773,1 ms | **549,3 ms** |
| Individuelle BOS-Zusatzwartezeit, Median inkl. Kontrollen | 43,0 ms | 43,0 ms | 46,2 ms | 26,8 ms |

Bei gepaarten Fällen verschob P1 den letzten Backend-Eingang
median um **−321,6 ms** unter C0 (nach warmer Position
geschichtetes Bootstrap 95 %: −326,2 bis −318,5 ms) und um
**−230,9 ms** unter C1 (−231,9 bis −224,2 ms). Der erste
vollständige Clientempfang verschob sich nahezu gleich: −321,5 ms
(−326,2 bis −318,4 ms) und −231,0 ms (−231,6 bis −224,0 ms).
Das spricht für die kürzere Backendarbeit als Hauptursache der
früheren BOS-Freigabe. Die strukturelle Änderung verschiebt
gleichzeitig Tokenpositionen des Inhalts; eine vollständige
kausale Zerlegung liefern diese zwei Starts nicht.

Das eingefrorene T2-Modell überträgt sich auf P1 schlecht.
**4/16 ist keine Sicherheitsmessung für P1**: Die binäre AUC
bleibt unter beiden Konfigurationen über 0,5, wenngleich C1 P1
mit nur vier Position-1-Fällen sehr unsicher ist. Eine P1-spezifische
Neukalibrierung wurde in diesem begrenzten Llama-Transfer nicht
gemessen; Qwens separate Kreuzstart-Kalibrierung erreichte dagegen
unter P1 22/32 (C0) und 14/32 (C1). Genau diese Trennung verhindert,
den Transferfehler fälschlich als Schutzgewinn zu behaupten.

## Modellvergleich und Entscheidung für das Paper

| Kerngröße | Qwen2.5-7B-Instruct | Llama-3.1-8B-Instruct |
| --- | ---: | ---: |
| Künstliche Prompts, BOS C0 T2 | 21/32 | 21/32 |
| Künstliche Prompts, BOS C1 T2 | 11/32 | 14/32 |
| Künstliche Prompts, BOS C1 Blockschluss-AUC | 0,813 | 0,953 |
| Künstliche Prompts, BOS C0/C1 Wartezeit-Median | 43,3 / 45,5 ms | 44,3 / 47,3 ms |
| Dokumente P1, gepaarter Client-Blockschluss P1−P0 | −309,9 / −229,7 ms | −321,5 / −231,0 ms |

Die Qwen-Werte stammen aus den vorhandenen Berichten und anderen
Sitzungen. Wegen unterschiedlicher Tokenizer (548 gegen 549 Tokens),
Modellgewichte, kleiner Stichproben und teils unterschiedlicher
Entwicklungsgrößen ist die Tabelle **deskriptiv**, kein
modellübergreifender Signifikanztest. Auffällig ist die wiederholte
Form: BOS reduziert einfache Ränge, vollständige Clientzeiten
behalten einen Cachebezug, und ein geteilter öffentlicher Präfix
verkürzt Backend- und sichtbaren Blockschluss stark. Llama bestätigt
damit **Entscheidung A**: eine begrenzte Übertragbarkeit der
empirischen Geschichte. Die höhere C1-AUC unter Llama ist ein
interessanter möglicher **B**-Unterschied, aber mit überlappender
Unsicherheit und ohne Llama-Scheduler-Instrumentierung kein eigener
Mechanismusclaim. **C** trifft nicht zu: der Kanal ist klar
beobachtbar.

Für die drei geplanten Beiträge bedeutet das: (1) Die Evaluation
vollständiger BOS-Clienttraces gewinnt ein zweites Modell; reine
Rangmetriken reichen in beiden nicht. (2) Der Scheduler-/Schutzkosten-
Kontrast erhält eine Modellkontrolle, aber keine allgemeine Aussage
über C1-Sicherheit; individuelle Wartezeiten bleiben vergleichbar.
(3) Die öffentliche Präfixstruktur gehört als kompakte
Anwendungsablation hinein; sie ist weder eine neue allgemeine
Cacheidee noch für sich ein Schutz. Ein ICCAI-2027-Manuskript sollte
die Llama-C0/C1-BOS-Tabelle, die C1-Rest-AUC und die gepaarte
P0/P1-Zeitverschiebung aufnehmen. Weitere Llama-Messungen sind für
diese Entscheidung vorerst nicht erforderlich.

Die Versuche liefen auf einer RTX 3090 im lokalen Loopback, ohne
fremde Hintergrundlast, mit 16 Ausgabetokens und absichtlich
gemeinsamer Salt-Domäne innerhalb der Gruppe. Das ist kein Nachweis
für Angriffe auf beliebige Dienste. [vLLM 0.17.1](https://docs.vllm.ai/en/v0.17.1/design/prefix_caching/)
dokumentiert Wiederverwendung nur voller Blöcke und die Isolation
durch unterschiedliche Cache-Salts. Die
[Llama-Modellkarte](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct)
stützt die Modellidentität; die tatsächliche lokale Lade- und
Cachefähigkeit wurde hier gemessen.

## Reproduktion und Daten

Alle neuen Protokolle, Client-/Proxy-/Serverlogs und JSONL-Rohdaten
liegen unter `results/llama-reference-20261103/`. Die Teilordner
`bos-dev-*`, `bos-test-*` und `docs-*` werden von den lokalen
Startskripten `run-bos.sh` und `run-docs.sh` erzeugt. Die
Auswertungen stehen in `bos-analysis.json`, `document-analysis.json`
und `uncertainty.json`; der letzte Bootstrap ist eine nach der
Messung ergänzte Unsicherheitsrechnung und ändert keine
Angreiferregel. Die Programme liegen unter `src/llama_bos_analysis.py`,
`src/llama_document_analysis.py` und `src/llama_uncertainty.py`.
Die Rohdaten werden absichtlich nicht überschrieben; für eine
Wiederholung sind neue Ausgabeordner und Salts erforderlich.
Alle lokalen Server und Proxies wurden beendet. Kein Push.
