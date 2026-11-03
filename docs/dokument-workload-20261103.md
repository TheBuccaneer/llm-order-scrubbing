# Dokumentenanalyse-Pilot: BOS und Scheduler

Stand: 03.11.2026. Alle Anfragen gingen ausschließlich an den eigenen
Qwen2.5-7B-Instruct/vLLM-0.17.1-Server auf der RTX 3090. Das
[vorab festgelegte Protokoll](../results/document-bos-20261103/protocol.json)
steht in Commit `64f66a3`, vor der ersten Messung.

## Forschungsfrage und Aufbau

Trägt der bisherige C0/C1-Unterschied nach BOS W=4 auch bei einer
plausiblen Dokumentenanalyse-Arbeitslast, und bleibt er bei
gegenbalancierter Serverreihenfolge sichtbar? Vier **synthetische**,
inhaltlich unterschiedliche technische Dokumente behandeln
Identitätsdienst, Vorfallarchiv, Deployment und Abrechnung. Sie
enthalten Betriebs- und Sicherheitsanforderungen sowie dieselbe
abschließende Analysefrage. Jedes Prompt hat mit dem lokalen
Qwen-Tokenizer genau 548 Tokens; die Kandidaten unterscheiden sich
bereits im ersten Cacheblock. Das sind plausible Inhalte, keine
aufgezeichneten echten Nutzerdokumente oder Produktionsanfragen.

Je Vierergruppe wurde ein Kandidat mit demselben Prompt und Salt
vorgewärmt; die übrigen Kandidaten waren kalt. Alle Antworten hatten
16 Ausgabetokens. Die bestehende Freigaberegel blieb unverändert.
C0 und C1 nutzten dasselbe Tokenbudget 256; nur
`long_prefill_token_threshold` wechselte zwischen 64 und 0. Die
Serverstarts folgten C0 → C1 → C1 → C0. Die zwei benachbarten
C0/C1-Paare nutzten jeweils dieselbe unabhängig gemischte Fallfolge,
aber frische Salts und getrennte Engine-Starts.

Pro Start liefen 16 positive BOS-Gruppen (vier je warmer
Sendeposition), zwei unvorgewärmte BOS-Kontrollen, vier positive
Direktgruppen und eine unvorgewärmte Direktkontrolle, gemischt in
einer Folge. Insgesamt: **92 Vierergruppen und 368 HTTP-200-Antworten**.
Alle BOS-Gruppen wurden vollständig als Viererblock freigegeben.
Auf jeder warmen Probe meldete das Backend 544 gecachte Tokens;
auf kalten Probes und Kontrollen keine. Das Diagnosefeld war aus
Clientantworten entfernt. Vollständigkeit und Zeitordnung wurden
für jede Antwort anhand der Rohprotokolle geprüft.

## Beobachter und Ergebnisse

Der primäre vierklassige T2-Beobachter verwendet die vier
vollständigen Client-Empfangszeiten. Sein Modelltyp und seine
Parameter blieben unverändert; je Konfiguration wurde er nur auf
32 **alten künstlichen** BOS-Gruppen trainiert. Kein Dokumentenfall
ging ins Training. Das ist daher zugleich ein Test der Übertragung
des Beobachters auf andere Promptinhalte. R1/R2/T1/RT sind die
bisherigen sekundären Beobachter. Die binäre AUC nutzt den ersten
vollständigen Clientempfang, um warme Sendeposition 1 gegen 2–4
zu ordnen; sie setzt keinen über Sitzungen kalibrierten
Millisekunden-Schwellwert voraus.

| Start | C0/C1 | T2, vier Klassen | T1 | R1 | binäre Blockschluss-AUC |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 | C0 | 11/16 | 11/16 | 5/16 | 0,917 |
| 2 | C1 | 8/16 | 7/16 | 1/16 | 0,979 |
| 3 | C1 | 5/16 | 5/16 | 1/16 | 0,896 |
| 4 | C0 | 10/16 | 9/16 | 2/16 | 0,833 |
| **Gesamt C0** | | **21/32** (Wilson 95 %: 48,3–79,6 %) | 20/32 | 7/32 | **0,870** |
| **Gesamt C1** | | **13/32** (25,5–57,7 %) | 12/32 | 2/32 | **0,932** |

Die vorab definierte Entscheidungshilfe wurde erfüllt: C0-T2
mindestens 18/32, C1-T2 höchstens 14/32, Abstand mindestens 6/32
und C0 in beiden gepaarten Startpaaren höher als C1. Das beobachtete
T2-Gefälle beträgt 8/32. Es ist **kein starker statistischer Beweis
für einen Konfigurationseffekt**: In den 32 gepaarten Fällen war
T2 15-mal nur unter C0, siebenmal nur unter C1 korrekt; der
exakte zweiseitige McNemar-Wert beträgt 0,134 (sekundär berechnet).
Die 95-%-Intervalle der Accuracy überlappen. Die Richtung und
Größenordnung des früheren 21/32-gegen-11/32-Befunds bleiben
erhalten, doch der Unterschied ist mit dieser Stichprobe unsicher.

Unter C1 ist der binäre Blockschlusskanal **nicht verschwunden**;
in dieser Arbeitslast ist seine AUC sogar höher als in der früheren
künstlichen Promptserie (0,932 gegenüber 0,813). Der Vergleich
dieser AUCs zwischen Sitzungen beweist keine Zunahme der gesamten
Cacheinformation. Ebenso ist C1-T2 mit 13/32 nicht als völlige
vierklassige Unbeobachtbarkeit zu lesen; das vorab trainierte Modell
liegt nur mäßig über 8/32 Zufallserwartung (einseitiger, unbereinigter
Binomialwert 0,038). Ein stärkerer oder anders kalibrierter
Beobachter wurde hier nicht gesucht.

Die kleine Direktkontrolle bestätigt, dass der Cacheeffekt auch
bei diesen Inhalten entsteht: Unter C0 traf R1 8/8; unter C1
traf die **bereits vor diesem Pilot fixierte** Paarabstandsregel
8/8, während R1 4/8 erreichte. Das sind nur acht positive
Direktgruppen je Konfiguration. BOS-trainierte T2-Modelle wurden
für die Direktbedingung nicht als sinnvolle Angriffszahlen berichtet.

Die tatsächlich gemessene individuelle Proxy-Wartezeit unter BOS
hatte über alle Antworten und Kontrollen hinweg einen Median von
40,54 ms (C0) beziehungsweise 45,77 ms (C1). Diese Kosten sind
an diese Arbeitslast und die 16-Token-Ausgabe gebunden. Ein neuer
fester Slot wurde hier nicht gemessen.

## Entscheidung und Grenzen

**Der Befund rechtfertigt den Manuskriptentwurf als eng gefasste
empirische Anschlussarbeit.** Geänderte Dokumentinhalte zerstören
den beobachteten C0/C1-T2-Kontrast nicht, und die gegenbalancierte
Reihenfolge spricht gegen eine rein monotone zeitliche Drift als
Erklärung. Die Unsicherheit des gepaarten Unterschieds und der
hohe C1-Blockschlusskanal verbieten jedoch die stärkere Aussage,
dass C1 generell weniger Information enthalte oder BOS unter C1
einen bestimmten Angriff zuverlässig verhindere.

Der nächste wissenschaftliche Schritt ist die Manuskriptstruktur
um eine präzise, eingeschränkte Aussage: Rang allein charakterisiert
BOS nicht; vollständige Clientzeiten und Schedulerplanung gehören
zur Evaluation. Die vorhandenen Kosten- und Fallback-Spuren
bilden den zweiten Teil. Eine weitere breite Messkampagne wird
aus diesem Pilot nicht automatisch abgeleitet.

Die vier Dokumente sind synthetisch. Das Experiment nutzt weiterhin
Loopback, eine GPU, ein Modell, eine Ausgabelänge, kontrollierte
Cachezustände und dieselbe Salt-Domäne. Separate geheime
Tenant-Salts würden laut [vLLM-Cache-Design](https://docs.vllm.ai/en/v0.17.1/design/prefix_caching/)
die hier vorausgesetzte Wiederverwendung unterbinden. Der Test
belegt weder Ausnutzbarkeit beliebiger fremder Dienste noch eine
Sicherheitsgarantie für andere Konfigurationen. Gegenbalancierung
reduziert zeitlichen Drift, beseitigt aber nicht alle Sitzungs-
oder Lastunterschiede.

Die enge Literaturgrenze bleibt bestehen: [PROMPTPEEK](https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf)
analysiert einen Reihenfolgekanal unter LPM; [OptiLeak v1](https://arxiv.org/html/2602.20595v1)
nennt Timing-/TTFT-Adaptionen ausdrücklich. Unsere mögliche neue
Aussage betrifft die *Evaluation der Restbeobachtbarkeit nach
vollständiger BOS-Blockfreigabe* unter verschiedenen lokalen
Prefill-Regimen, nicht die Erfindung eines allgemeinen Cache- oder
Timing-Angriffs. Die relevanten Originalabschnitte wurden heute
gezielt nachgelesen; dies ist keine vollständige systematische
Literaturübersicht.

## Reproduktion

Prompts: `data/document-workload-20261103/prompts.json`.
Vorabprotokoll: `results/document-bos-20261103/protocol.json`.
Runner: `src/document_bos_run.py` mit kleinen optionalen
Prompt-Parametern in den bestehenden Clients. Auswertung:
`src/document_bos_analysis.py` (Aufruf mit `PYTHONPATH=src`).
Rohdaten: `results/document-bos-20261103/run1-c0/` bis
`run4-c0/`, jeweils `trials.jsonl`, `proxy.jsonl`, Client-, Proxy-
und Serverlog. Maschinenlesbares Ergebnis:
`results/document-bos-20261103/analysis.json`.
`run_remaining.sh` enthält die lokalen Starts 2–4; Start 1 wurde
mit denselben Optionen manuell ausgeführt. Das ursprüngliche
Aufräumen des Skripts blieb wegen eines Signals an den
Hintergrund-Proxy stehen und wurde während des Laufs gezielt
beendet. Alle Messdateien waren vollständig; die Server/Proxies
liefen am Ende nicht mehr. Das Skript wurde danach für zukünftige
Starts auf TERM korrigiert. Vor einer Wiederholung sind neue
Ausgabeziele und Salt-Tags nötig, da die Programme Rohdaten
absichtlich nicht überschreiben.
