# C1: Cacheposition aus gemeinsamem Abschluss vollständiger Antworten

Stand: 03.11.2026. Lokaler Entscheidungstest für einen möglichen
ICCAI-2027-Beitrag. Alle Anfragen gingen ausschließlich an den eigenen
Qwen2.5-7B-Instruct/vLLM-0.17.1-Server auf der RTX 3090.

## Frage und Vorabfestlegung

Unter C1 (FCFS, Prefix-Caching an, Prefill-Tokenbudget 256,
`long_prefill_token_threshold=0`) war der **erste Antwort-Rang** in den
früheren Daten schwach. Die neue Hypothese lautet: Ein Cachetreffer, der
nach einer kalten Anfrage gesendet wird, holt diese beim Decoding ein.
Dann werden zwei vollständige HTTP-Antworten beinahe gleichzeitig beim
Client empfangen. Diese relative Zeitstruktur könnte die Cacheposition
weiterhin verraten.

Nach explorativer Auswahl an zwei älteren C1-Serien wurde die einfache
Regel **vor dem neuen Live-Lauf** in
`results/novelty-c1-20261102/protocol.json` und Commit `5793db6`
fixiert: Die drei benachbarten Empfangszeitabstände werden in eigener
Sendereihenfolge berechnet. Ist ihr kleinster Betrag größer als 10 ms,
gilt Position 1 als Treffer. Sonst gilt die Position unmittelbar nach
dem engsten Antwortpaar als Treffer. Der Beobachter nutzt nur eigene
Anfrageparameter, IDs, Sendereihenfolge und vollständige
Client-Empfangszeiten. Cache-Diagnosefelder wurden vor der Clientantwort
entfernt. Die älteren 32/32- und 32/32-Treffer waren **explorativ**;
erst der vorliegende Lauf ist prospektiv für diese Regel.

## Versuch

- Neuer Backend-Start, frisches Triton-Cacheverzeichnis und neue,
  unabhängig gemischte Fallfolge (`case_seed=202611020327`). Die erste
  Wiederaufnahme scheiterte vor der API-Bereitschaft an einer
  unvollständigen Cache-Metadatendatei des abgebrochenen Vortags;
  sie erzeugte keine Messfälle. Die erfolgreiche Sitzung verwendete
  dieselben Modell- und Schedulerparameter.
- Vier gleich lange Kandidatenprompts zu je 548 Tokens, nominell 10 ms
  Sendeabstand, 16 Ausgabetokens, ein frischer gemeinsamer Salt pro
  Gruppe. In 32 Gruppen war genau ein Kandidat vorher warm; seine vier
  Sendepositionen waren mit je acht Fällen balanciert. Vier weitere
  Gruppen blieben unvorgewärmt. Die Sendelücken lagen tatsächlich
  zwischen 9,72 und 10,29 ms.
- Die Proxy-Rohdaten bestätigen bei allen 32 Positiven 544 gecachte
  Tokens für genau die vorgewärmte Probe. Alle 144 Antworten waren
  vollständig und HTTP 200. Die internen Angaben dienten nur zur
  Integritätskontrolle, nicht als Angriffsmerkmal.
- Der vorher definierte Entscheidungspunkt war mindestens 24/32
  korrekte Positionen mit intakten Cachetreffern. Keine automatische
  Erweiterung der Messserie war vorgesehen.

## Ergebnis

| Beobachter | Korrekt / 32 | 95-%-Wilson-Intervall | Bemerkung |
| --- | ---: | ---: | --- |
| Vorab fixierte Paarabstandsregel | **32/32** | 89,3–100 % | 8/8 auf jeder Sendeposition; keine Fehler |
| R1, erste Antwort-ID | 11/32 | 20,4–51,7 % | Vor allem Sendeposition 1 erkannt |
| R2, vollständige Rangfolge | 19/32 | 42,3–74,5 % | Auf alter C1-Primärserie trainiert |
| T2, vier Clientzeiten | 31/32 | 84,3–99,5 % | Auf alter C1-Primärserie trainiert |
| RT, Ränge plus Zeiten | 31/32 | 84,3–99,5 % | Auf alter C1-Primärserie trainiert |

Für warme Sendepositionen 2–4 betrug der kleinste benachbarte
**Client**-Abstand 0,035–0,332 ms (Median 0,061 ms). Bei warmer
Position 1 waren es 40,299–41,728 ms (Median 40,407 ms), in den vier
unvorgewärmten Kontrollen 39,931–40,487 ms (Median 40,279 ms).
Die nur zur Ursachenprüfung geloggten vollständigen
**Backend-HTTP-Empfangszeiten** zeigen dieselbe Trennung:
bei warmer Position 2–4 lag der kleinste Abstand bei 0,056–0,149 ms,
bei Position 1 und Kontrollen ungefähr 40 ms. Das spricht dafür,
dass das enge Paar bereits vor der Proxy-Freigabe entsteht; es ist
noch kein instrumentierter Nachweis gemeinsamer Scheduler-Iterationen.

Die Regel übertrifft R1 auf denselben 32 Fällen deutlich. Ihr
Ein-Fall-Vorsprung vor T2/RT erlaubt **keine** Behauptung höherer
Genauigkeit. Vor allem liefert sie eine sehr einfache, im neuen Lauf
stabile Beschreibung eines bislang übersehenen C1-Signals. Die
vier Kontrollen zeigen noch keine verlässliche Cachetreffer-Erkennung:
Ein unvorgewärmter Fall und ein Treffer auf Position 1 sehen nach
diesem Merkmal ähnlich aus. Das Experiment bewertet die **Position
unter der Voraussetzung genau eines Treffers**.

## Abgrenzung zur Vorarbeit

Die gezielte Originaltextprüfung ist keine systematische
Vollständigkeitsgarantie und kein besonderer „Deep-Research“-Lauf.

| Primärquelle, geprüfte Fassung | Bereits bekannt | Hier konkret zusätzlich geprüft |
| --- | --- | --- |
| [PROMPTPEEK, NDSS 2025](https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf), §IV-A, §VIII, L2 | LPM-gestützte Reihenfolge von Ein-Token-Probes in gezielt gefüllter Warteschlange | Vier vollständige 16-Token-Antworten unter lokalem vLLM-FCFS/Chunked Prefill; Verlust von R1 und Erhalt relativer Abschlusszeiten |
| [OptiLeak v1](https://arxiv.org/html/2602.20595v1), §4.2, §6, L2 | Positionsfeedback; FCFS/Timing/TTFT wird ausdrücklich als mögliche Adaption genannt | Kleine konkrete FCFS-Positionsregel aus vollständigen Antwortpaaren; allgemeine Timing-Inferenz wird nicht als neu beansprucht |
| [PrefixWall v2](https://arxiv.org/html/2603.10726v2), §§2.2–2.4, 5, L2 | Cachetreffer über TTFT; Last und Schutzkosten werden behandelt | Relative Abschlusszeiten von vier nicht gestreamten Antworten statt TTFT-Klassifikation einzelner Probes |
| [Contention-Induced Reliability Collapse](https://arxiv.org/html/2609.06853), §§IV-B, XIV–XV, L2 | Auch vollständige, nicht gestreamte Client-Endzeiten wurden bereits gemessen, allerdings für Ein-Token-Probes; Lastgrenzen | 16-Token-Vierergruppe, Positionsinferenz aus beinahe gemeinsamem Abschluss; Lastrobustheit bleibt offen |
| [Eigene ICCAI-2026-Arbeit](../references/iccai2026-completion-order.pdf), zuvor L3 | ODS/BOS und Rangfolgen ohne individuelle Clientzeiten | C1 zeigt, dass schwache Ränge keine schwache vollständige Zeitfolge bedeuten |

Das tragfähige **Erkenntniskandidaten-Statement** lautet daher eng:
*Eine Scheduler-Einstellung, die den ersten Antwort-Rang als
Cachepositionssignal stark abschwächt, kann bei vollständigen
LLM-Antworten eine fast deterministische relative Abschlussstruktur
erzeugen.* Die vorliegenden Daten belegen diese Aussage nur für den
lokalen C1-Aufbau. Ein eigenständiger neuer Angriffsbeitrag ist noch
nicht gesichert: T2 war nahezu ebenso gut, andere Lasten und Modelle
sind ungeprüft und C1-BOS wurde mit dieser Regel nicht angegriffen.

## Entscheidung und nächste Prüfung

Der vorab festgelegte 24/32-Punkt ist mit 32/32 überschritten.
**Empfehlung:** Diese Richtung als *Mechanismus- und
Schutzevaluationsfrage* weiterverfolgen. Der kleinste nächste Test
instrumentiert wenige Backend-Scheduler-Schritte und prüft eine
frisch fixierte Regel unter einer zusätzlichen, weniger speziellen
Konfiguration und unter tatsächlicher BOS-Freigabe. Erst wenn das
relative Signal dort bestehen bleibt oder eine klare Schutz-/Kosten-
Grenze zeigt, sollte es zum Paper-Hauptbeitrag werden. Keine Änderung
der bisherigen Freigaberegel folgt aus diesem Versuch.

Rohdaten: `results/novelty-c1-20261102/confirm/trials.jsonl`,
`proxy.jsonl`, `analysis.json`, `client.log` und
`server-fresh-cache.log`. Der Startfehler ist in `server.log`
dokumentiert. Das vorab fixierte Protokoll und die Auswertung liegen
unter `results/novelty-c1-20261102/protocol.json` beziehungsweise
`src/c1_cocompletion_analysis.py`. Die Live-Messung und Auswertung
lassen sich mit der im Protokoll genannten Konfiguration und dem
fixierten Seed wiederholen; ein neuer Lauf benötigt neue Ausgabeziele.

## Reproduktion auf diesem Messrechner

Die erfolgreiche Server-Kommandozeile und Paketversionen sind im
`server-fresh-cache.log` dokumentiert. Erforderlich sind ein **neuer**
vLLM-Start mit den oben genannten C1-Parametern, ein leerer lokaler
Triton-Cache und die vorhandene Python-3.13-Umgebung aus `porto`.
Danach genügen aus dem Repository diese drei Aufrufe mit neuen
Ausgabedateien (der Proxy läuft parallel zum Client):

```sh
/home/rock/projects/porto/.venv-py313-repair/bin/python src/order_release_proxy.py results/novelty-c1-20261102/confirm/proxy.jsonl
/home/rock/projects/porto/.venv-py313-repair/bin/python src/bos_pilot.py results/novelty-c1-20261102/confirm/trials.jsonl novelty-c1-20261102 2 direct 16 4 202611020327
PYTHONPATH=src /home/rock/projects/porto/.venv-py313-repair/bin/python src/c1_cocompletion_analysis.py results/novelty-c1-20261102/confirm/trials.jsonl results/novelty-c1-20261102/confirm/proxy.jsonl results/novelty-c1-20261102/confirm/analysis.json
```

Diese konkreten Zieldateien existieren bereits und werden von den
Programmen absichtlich nicht überschrieben. Für eine Wiederholung
werden neue Dateinamen und ein neuer Salt-Tag benötigt. Der Quellcode
liegt im Repository; Modellgewichte und die vorhandene Laufzeitumgebung
sind lokale Voraussetzungen, keine mitgelieferten Artefakte.
