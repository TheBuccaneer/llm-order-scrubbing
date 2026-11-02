# Kausale Gruppenfreigabe: kleiner Offline-Pilot

Stand: 02.11.2026. Dieser Pilot prüft eine **konstruktive Fortsetzung**
von BOS an vollständigen LLM-Antworten. Er verwendet ausschließlich
bereits aufgezeichnete lokale Qwen/vLLM-C0-Spuren mit vier Probes und
24 Ausgabetokens. Es gab keinen neuen GPU-Lauf und keine Änderung der
produktiven Freigaberegel.

## Forschungsentscheidung

**Die beiden geprüften periodischen Gruppenregeln sind hier keine
belegte Verbesserung des Schutz-Kosten-Verhältnisses.** Sie vermeiden
im idealen Replay zwar jeden Einzel-Fallback und warten kürzer als der
1.200-ms-Slot. Der Zeitpunkt, an dem die vollständige Gruppe den
nächsten Tick erreicht, bleibt aber von ihrer letzten Backend-Antwort
abhängig. Der clientseitige Gesamtzeitverlauf enthält dadurch wieder
ein Signal. Eine auf den vorhandenen Spuren enger kalibrierte feste
Freigabezeit von 1.160 ms sparte modelliert 40 ms je Antwort gegenüber
1.200 ms und behielt auf allen 108 Gruppen die vollständige Freigabe.
Das ist eine **explorative Parametereinstellung einer bekannten Regel**,
keine neue Schutzmethode und kein prospektiver Sicherheitsnachweis.

Die sinnvolle Paper-Richtung ist deshalb zunächst eine präzise
**Completion-/Kosten-Grenze unter einem festgelegten Bedrohungs- und
Verfügbarkeitsmodell**, nicht ein Algorithmusclaim für periodisches
Zurückstellen. Ein solcher Claim verlangt entweder einen belegten
Vorteil gegenüber einem gut kalibrierten festen Slot oder eine formale
Garantie unter klaren Annahmen. Beides liegt hier noch nicht vor.

## Daten und kausale Regeln

Die beiden älteren 24-Token-Serien enthalten je 32 positive und vier
unvorgewärmte Vierergruppen. Die getrennte C0-Sitzung enthält weitere
32 positive und vier unvorgewärmte Gruppen: zusammen 108 Gruppen / 432
Antworten. Der Angreifervergleich trainiert ausschließlich auf den 64
positiven älteren Gruppen und prüft auf den 32 positiven der getrennten
C0-Sitzung; die Kostenstatistik umfasst auch die zwölf Kontrollen.
Diese C0-Sitzung wurde in früheren Auswertungen bereits betrachtet.
Sie ist daher **kein unberührter prospektiver Holdout**, insbesondere
nicht für die nachträglich gewählte 1.160-ms-Zahl.

Für Antwort `i` ist `A` die erste Proxy-Ankunft, `C_i` die vollständige
Backend-Antwort und `R_i` ihre geplante Freigabe. Alle Regeln erfüllen
`R_i >= C_i`; sie dürfen nur die bisher angekommenen, vollständig
bereiten Antworten und eine öffentliche Uhr nutzen. In der
Implementation würde ein Timer bei jeder Fälligkeit prüfen, ob vier
Antworten vorliegen. Das Replay berechnet denselben Termin effizient
aus den aufgezeichneten `C_i`, **ohne diesen Zukunftswert einer
laufenden Regel bereitzustellen**.

| Regel | Entscheidung bei Verfügbarkeit |
| --- | --- |
| BOS W=4 | Vollständige Gruppe sofort bei `max(C_i)` mischen. |
| Slot 1.050/1.200 ms | Bereite Antworten am bei `A` verankerten Termin; spätere einzeln bei `C_i`. |
| Slot 1.160 ms | Dieselbe bekannte Slot-Regel, nur explorativ enger kalibriert. |
| Periodisch 100 ms | Nach vollständiger Gruppe am nächsten **globalen** 100-ms-Tick mischen. |
| Zurückstellen 100 ms | Bei `A+1.050 ms` beginnen; ist die Gruppe unvollständig, vollständig bis zum nächsten bei `A` verankerten 100-ms-Tick zurückstellen. |

Der modellierte Client erhält die vier IDs in einer vom geheimen Label
unabhängigen, für alle Regeln pro Gruppe gleich gezogenen Permutation.
Zwischen serialisierten Antworten liegen idealisierte 2 ms.
Netzverzögerung, Timer-Jitter, Backend-Rückkopplung durch andere
Freigaben und Python-Schreibaufwand fehlen. Für den alten
1.050-ms-Slot stimmt die vorhergesagte Slot-Mitgliedschaft in **108/108**
Gruppen mit den Live-Logs überein; die reale Freigabe liegt im Median
0,52–0,61 ms und am P95 5,08–7,09 ms nach dem idealen Termin. Das
validiert die grobe Fallback-Struktur, **nicht** die modellierten
Client-Accuracy-Werte neuer Regeln.

## Gepaarter Vergleich

Die Tabelle bezieht sich auf die getrennte C0-Sitzung mit 36 Gruppen.
`Wait` ist die individuelle Zusatzwartezeit **nach** vollständigem
Backend-Eingang am Proxy; `T2` verwendet alle vier Client-Empfangszeiten
und `RT` zusätzlich die vollständige ID-Rangfolge. Die Klassifikatoren
sind kleine, auf den älteren Sitzungen trainierte logistische Modelle.
`R1` und `R2` sind ebenfalls in der Rohzusammenfassung enthalten.
Zufallserwartung bei 32 balancierten Positiven: acht Treffer.

| Regel | Volle Gruppen | Wait Median / P95 | Warme Antwort Median | T2 | RT |
| --- | ---: | ---: | ---: | ---: | ---: |
| BOS W=4 | 36/36 | 40,60 / 228,46 ms | 189,43 ms | 26/32 | 17/32 |
| Slot 1.050 ms | 6/36 | 15,54 / 183,04 ms | 178,74 ms | 24/32 | 21/32 |
| Slot 1.160 ms | 36/36 | 125,54 / 293,04 ms | 288,74 ms | 6/32 | 9/32 |
| Slot 1.200 ms | 36/36 | 165,54 / 333,04 ms | 328,74 ms | 6/32 | 9/32 |
| Global periodisch 100 ms | 36/36 | 88,77 / 274,04 ms | 235,88 ms | 11/32 | 13/32 |
| Zurückstellen 100 ms | 36/36 | 93,01 / 283,04 ms | 278,74 ms | 16/32 | 13/32 |

Der gepaarte Unterschied zum 1.200-ms-Slot beträgt für 1.160 ms
**exakt −40 ms je Antwort**. Beim Zurückstellen beträgt der Median
−50 ms, bei globaler Periodik −80,26 ms. Die periodischen Regeln
tauschen folglich zusätzliche Zeitersparnis gegen eine variierende,
clientseitig erkennbare Gruppenuhr. Die Klassifikationszahlen sind
klein, modellabhängig und kein Informationsmaß oder Sicherheitsbeweis.
Insbesondere ist der RT-Logistiker nicht garantiert der stärkste
Beobachter; seine geringere Trefferzahl als T2 darf nicht als
Entwarnung gelesen werden.

Der Mechanismus ist auch ohne Klassifikator sichtbar: Bei der
Zurückstellregel wurden im getrennten C0-Trace **6/8** Fälle mit
vorgewärmter Sendeposition 4 schon bei `A+1.050 ms` vollständig
freigegeben, aber **0/24** mit Position 1–3. In den älteren 64
Positiven lagen die 17 frühen vollständigen Gruppen ausschließlich
auf Position 3 oder 4. Die Freigabe **als Gruppe** verbirgt also die
Einzelreihenfolge, ihr gewählter Tick verrät hier weiterhin etwas über
die Cacheposition. Das ist eine explorative Assoziation in lokalen
C0-Daten; mehrere Regeln und Beobachter wurden betrachtet.

## Was sich begrenzen lässt

Für eine vollständige Viererfreigabe bei einem festen Termin `D` ist
notwendig und hinreichend, dass `max(C_i) <= D`. Bei unverändertem
Backend betragen die individuell unvermeidbaren Wartezeiten an
diesem Termin `D-C_i`. In den beiden älteren Serien waren **17/72**
Gruppen bis 1.050 ms, **58/72** bis 1.100 ms, **70/72** bis 1.150 ms
und **72/72** bis 1.160 ms bereit; die größte beobachtete
Fertigstellungsdistanz betrug 1.154,10 ms. Die getrennte C0-Sitzung
hatte **36/36** bis 1.150 ms bereit. Das ist eine scharfe
**empirische Deckungs-/Wartekurve für diese Spuren und feste Slots**,
keine populationsweite Grenze.

Allgemein folgt aus `R_i >= C_i`: Falls irgendein `C_i > D`, kann
eine Regel nicht gleichzeitig bis `D` die **vollständige echte**
Antwort ausgeben und alle vier Antworten gemeinsam halten. Sie muss
später ausgeben, eine unvollständige/ersetzte Antwort liefern oder eine
Verfügbarkeitsgrenze verletzen. Die Auswahl zwischen diesen Ereignissen
kann wieder sichtbar sein. Diese einfache Machbarkeitsaussage ist
**keine neue allgemeine Privacy-Untergrenze**; für eine solche wären
eine Verteilung oder Schranke der Completion-Zeiten, Angreiferwissen,
zulässige Fehler-/Dummyantworten und ein formales Leakage-Maß nötig.

## Literatur und Abgrenzung

Heute gezielt im Original nachgeprüft: [Pacer, USENIX Security 2022](https://www.usenix.org/system/files/sec22-mehta.pdf),
§§2.2–4, fordert geheimnisunabhängige sichtbare Sendepläne und
behandelt Abweichungen vom Solltermin. [Accumulate-and-Serve, 2013](https://arxiv.org/pdf/1302.6123),
§§V–VI, zeigt den allgemeinen Pufferungs-/Verzögerungskonflikt in
geteilten Schedulern. [One-Sided Bounded Noise, CCS 2025](https://people.csail.mit.edu/devadas/pubs/one_sided_noise.pdf),
§§1–2 und 5, untersucht positive begrenzte Verzögerung mit formalen
Privacy-Maßen. Die [Threshold-Pool-Mix-Arbeit von 2014](https://www.sciencedirect.com/science/article/pii/S1389128614001522)
optimiert laut Verlagstext bereits Anonymität und Verzögerung;
der relevante Volltext war hier nicht zugänglich. Deshalb wird aus
diesem Pilot **kein allgemeiner Neuheitsanspruch** für Batch-Timing,
periodische Freigabe oder Verzögerungsoptimierung abgeleitet.
Der spezifische offene Anschluss an die [eigene ICCAI-2026-Arbeit](../references/iccai2026-completion-order.pdf)
ist die vollständige clientseitige Antwortfolge unter unbekannter
LLM-Completion-Zeit und expliziten Verfügbarkeitskosten.

## Reproduktion und nächster Entscheidungstest

Code: `src/causal_release_pilot.py`. Quellen: die unveränderten
`trials-24.jsonl`/`proxy.jsonl` unter
`results/decision-validation-20261102/slot-fallback/{holdout,confirm}/`
und `trials.jsonl`/`proxy.jsonl` unter
`results/release-boundary-20261102/c0/`. Neue abgeleitete Zeilen
liegen in `results/causal-release-20261102/replay-rows.jsonl`, alle
Kennzahlen und Konfidenzintervalle in `replay.json` desselben Ordners.
Erneute Ausführung mit einem **neuen** Ausgabestamm:

```bash
/home/rock/projects/porto/.venv-py313-repair/bin/python \
  src/causal_release_pilot.py \
  results/causal-release-20261102/recheck.json
```

**Empfehlung für den nächsten, getrennt zu beschließenden Schritt:**
Zuerst ein explizites Latenz-/Verfügbarkeitsbudget und ein vollständiges
Client-Trace-Leakage-Maß festlegen. Dann eine wirklich neue,
vorgeplante C0-Fallfolge für den kalibrierten festen Slot und höchstens
eine begründete alternative Regel live messen. C1 und größere
Completion-Tails müssen die Geltungsgrenze prüfen. Ohne solche
Bestätigung bleibt 1.160 ms eine lokale Offline-Hypothese.
