# Zufällige Freigabeslots: begrenzter konstruktiver Offline-Pilot

Stand: 02.11.2026. Dieser Anschluss an den kausalen Gruppenpilot
prüft eine **vom Cachezustand unabhängige Münzentscheidung** zwischen
zwei festen Slots. Die bereits implementierte Slot-/Einzelfallback-Regel
bleibt unverändert. Grundlage sind dieselben 108 lokalen C0-Gruppen
mit vier vollständigen Qwen-Antworten zu je 24 Ausgabetokens; keine
neuen GPU-Messungen.

## Entscheidung

**Keine der drei vorab klein gehaltenen 50:50-Mischungen liefert auf
den Entwicklungsdaten einen plausiblen Schutz-Kosten-Vorteil gegenüber
dem jeweiligen festen Mitteltermin.** In jeder Paarung hat der feste
Termin auf diesen Spuren höchstens dieselbe mittlere individuelle
Wartezeit und höchstens dasselbe Gruppen-Fallback-Risiko. Die breiteste
Mischung zeigt zusätzlich ein deutliches clientseitiges Zeitsignal.
Für die zwei engeren Mischungen ist eine Verbesserung der gesamten
Client-Trace-Unterscheidbarkeit nicht belegt. Gemäß der Abbruchregel
erfolgten weder nachträgliche Gewichtsoptimierung noch GPU-Läufe.

Das Ergebnis verwirft **diese kleine Policy-Familie auf diesen Daten**.
Es beweist nicht, dass jede randomisierte kausale Freigabe generell
schlechter wäre. Ein Methodenbeitrag für ICCAI 2027 ist daraus
derzeit nicht begründet.

## Modell und Vergleich

`A` ist die erste öffentliche Proxy-Ankunft, `C_i` der vollständige
Backend-Eingang und `R_i` die Freigabe der Antwort `i`. Beim Beginn
einer Gruppe wird unabhängig von den vier Cachepositionen ein Termin
`D` aus `q` gezogen. Beim Timer `A+D` werden alle bis dahin fertigen
Antworten gemischt ausgegeben; spätere Antworten folgen einzeln nach
ihrem Eingang. Damit gilt stets `R_i >= C_i`. Die Entscheidung sieht
weder geheime Labels noch zukünftige Completions. Im Offline-Replay
werden beide möglichen Münzausgänge pro Gruppe berechnet und mit
Gewicht 0,5 **exakt gemittelt**; es werden keine künstlich als unabhängig
behandelten Zusatzgruppen erzeugt.

Die drei Paare waren `q={1.050,1.160}`, `q={1.100,1.160}` und
`q={1.150,1.160}` ms. Vergleichspartner ist jeweils der feste
Mitteltermin **1.105, 1.130 oder 1.155 ms**; zusätzlich stehen die
vorhandenen festen 1.160 und 1.200 ms in den Rohkennzahlen. Die Wahl
ist **explorativ**: Alle 108 Spuren und der 1.160-ms-Pilot waren schon
vor dieser Analyse bekannt. Die zwei alten Sitzungen verwenden zudem
dieselbe randomisierte Fallfolge mit anderen Salts und sind keine 64
unabhängig randomisierten Fallfolgen. Für den Permutationstest werden
ihre Fälle deshalb paarweise umgelabelt. Die 32 positiven Fälle einer
getrennten C0-Sitzung dienen als Kreuzsitzungsprüfung, **nicht als
unberührter prospektiver Holdout**. Kosten und Risiko enthalten auch
die je vier unvorgewärmten Kontrollen pro Sitzung.

Der Clientbeobachter kennt nur seine eigenen vier IDs, Sendezeiten,
Empfangszeiten und deren Reihenfolge. Backend-Zeiten und das interne
Fallback-Flag gehen **nicht** in seine Merkmale ein. Der Replay setzt
eine geheimnisunabhängige Permutation und 2 ms serielle Ausgabe an;
Timer-Jitter, Netzverzögerung und Backend-Rückkopplung fehlen. Alle
Leakage-Zahlen sind daher **modellierte**, keine live gemessenen Werte.

## Ergebnis auf 72 alten Gruppen

`Wait` ist der Mittelwert der individuellen Proxy-Zusatzwartezeit
nach dem Backend-Eingang. `Fallback` ist die erwartete Zahl von
Gruppen mit wenigstens einer verspäteten Antwort; halbe Gruppen sind
bei der Münze ein Erwartungswert. `MMD²` ist ein vorab fest skaliertes
Kernelmaß auf **allen vier clientseitigen Zeiten und ID-Rängen**,
gemittelt über die sechs Cachepositionspaare. Der Permutationswert
berücksichtigt die paarweise wiederholte Fallfolge und 999
Umlabelungen; er ist kein Privacy-Garantiewert.

| Regel | Wait | Fallback | MMD² | Permutations-p |
| --- | ---: | ---: | ---: | ---: |
| Fest 1.105 ms | 95,63 ms | 11/72 | 0,0198 | 0,623 |
| Münze 1.050/1.160 ms | 100,41 ms | 27,5/72 | 0,1151 | 0,002 |
| Fest 1.130 ms | 119,55 ms | 6/72 | 0,0222 | 0,394 |
| Münze 1.100/1.160 ms | 120,16 ms | 7/72 | 0,0698 | 0,550 |
| Fest 1.155 ms | 144,29 ms | 0/72 | 0,0222 | 0,394 |
| Münze 1.150/1.160 ms | 144,30 ms | 1/72 | 0,0261 | 0,394 |

Die größere rohe MMD²-Zahl einer Münze darf nicht allein als stärkerer
Angriff interpretiert werden: unabhängige Terminzufälle erhöhen auch
die Nullstreuung des Kernelmaßes. Der Permutationstest findet nur für
die breite Mischung ein Signal. Dieses repliziert in der bereits
bekannten getrennten C0-Sitzung: MMD² **0,2033**, `p=0,001`, gegenüber
**0,0198** und `p=0,997` beim festen 1.105-ms-Termin. Dort kostet die
breite Mischung durchschnittlich **99,10 statt 93,87 ms** und hat
**15 statt 5 erwartete Fallback-Gruppen von 36**. Die anderen beiden
Mischungen liefern auch dort keinen belastbaren Vorteil. Die kleinen
T2-/RT-Logistikbeobachter sind in `analysis.json` enthalten; ihre
Trefferzahlen allein entscheiden diese Frage nicht.

Ein direkt sichtbares Einzelereignis bestätigt die Mechanik: Bei der
breiten Mischung ist `E = (größte Lücke zwischen Clientempfängen >
10 ms)`. Seine modellierte Rate auf den positiven Entwicklungsfällen
beträgt nach warmer Sendeposition 1–4 **0,500 / 0,406 / 0,125 /
0,063**, in der getrennten C0-Sitzung **0,500 / 0,500 / 0,063 /
0,000**. Für zwei Zustände ist die Differenz der Ereignisraten eine
Untergrenze der Total-Variation-Distanz ihrer **modellierten**
Client-Trace-Verteilungen: maximal **0,438** bzw. **0,500** für diese
empirischen Verteilungen. Das interne Fallback-Flag selbst ist nicht
stets eindeutig aus den Clientdaten erkennbar; dafür wird **keine**
TV-Untergrenze behauptet. Die Ereigniswahl und Ergebnisse sind
explorativ, nicht unabhängig bestätigt.

## Warum die Münze hier nicht hilft

Die Wartekosten eines Slots sind pro Antwort
`w_i(D)=max(0,A+D-C_i)`. Diese Funktion ist konvex in `D`.
Deshalb gilt für jede zustandsunabhängige Slotverteilung mit
Mittelwert `d`: `E_q[w_i(D)] >= w_i(d)`. Eine Münze kann also bei
**gleichem mittleren Termin** die mittlere Wartezeit nicht senken.
Für das Fallback-Risiko folgt eine entsprechende allgemeine
Ungleichung **nicht** ohne Annahmen an die Completion-Verteilung;
auf diesen Spuren ist es bei allen drei festen Mittelterminen jedoch
ebenfalls geringer oder gleich. Die Münze bringt hier einen früheren
Tail in den sichtbaren Ausgabepfad, während der spätere Münzausgang
Wartezeit kostet.

Bei empirisch null Fallback muss jede Slotwahl mit positiver
Wahrscheinlichkeit hinter dem größten beobachteten `max(C_i)-A`
liegen. Innerhalb dieses idealisierten Modells liefert ein bereits
vollständig gedeckter, fester Slot keine Completion-abhängige
Gruppenzeit mehr; zusätzliche zustandsunabhängige Terminvarianz kann
diese Komponente nicht weiter entfernen. Das ist eine **eingeschränkte
Machbarkeitsaussage für die aufgezeichneten Traces**, keine formale
Privacy-Untergrenze für unbekannte Lasten oder andere
Client-/Netzbeobachtungen.

## Literatur und nächster Schritt

[One-Sided Bounded Noise, CCS 2025](https://people.csail.mit.edu/devadas/pubs/one_sided_noise.pdf)
optimiert positive begrenzte Störungen bereits unter formalen
Privacy-Maßen; eine Münze über Antwortslots ist als Randomisierung
nicht neu. [Pacer, USENIX Security 2022](https://www.usenix.org/system/files/sec22-mehta.pdf)
fordert, dass sichtbare Sendepläne und Abweichungen keine geheimen
Laufzeitdetails abbilden. [Accumulate-and-Serve, 2013](https://arxiv.org/pdf/1302.6123)
belegt den allgemeinen Pufferungs-/Verzögerungskonflikt. Die
[Threshold-Pool-Mix-Arbeit von 2014](https://www.sciencedirect.com/science/article/pii/S1389128614001522)
optimiert laut zugänglichem Verlagstext bereits Anonymität und Delay;
ein verlässlicher Volltextzugriff fehlte auch diesmal. Gegenüber der
[eigenen ICCAI-2026-Arbeit](../references/iccai2026-completion-order.pdf)
bleibt die gemeinsame Verfügbarkeit vollständiger LLM-Antworten eine
konkrete Anschlussfrage. **Diese einfache Münzregel ist kein
eigenständiger Methodenbeitrag.**

Eine weitere Slot-/Münzsuche auf denselben Spuren wäre angesichts der
explorativen Nutzung und geringen unabhängigen Fallzahl wenig wert.
Für die Paper-Entscheidung ist nun eher die **empirische BOS-/Fallback-
Studie** mit prospektivem Test unter definiertem Latenz- und
Verfügbarkeitsbudget zu stärken. Eine neue Methode sollte erst mit
einem wirklich anderen Umgang mit verspäteten Antworten begründet
werden. Der kleinste unabhängige Test wäre eine frisch randomisierte
Fallfolge mit neuem Backend-Start, vorab fixiertem Slot und
vollständiger Client-Trace-Auswertung; C1 oder längere Completion-Tails
markieren die Geltungsgrenze.

Reproduktion: `src/randomized_release_pilot.py` liest die drei
unveränderten 24-Token-Sitzungen des vorherigen Piloten.
`results/randomized-release-20261102/analysis-components.jsonl`
enthält pro Gruppe und Slot die abgeleiteten Einzelresultate;
`analysis.json` enthält Protokoll, Kosten, Risiken, Angriffszahlen
und Permutationstests. Neuer Ausgabestamm für eine Wiederholung:

```bash
/home/rock/projects/porto/.venv-py313-repair/bin/python \
  src/randomized_release_pilot.py \
  results/randomized-release-20261102/recheck.json
```
