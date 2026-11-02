# Gezielter Cache-/Reihenfolgepilot, 02.11.2026

## Frage und Aufbau

Kann ein Client aus der Reihenfolge oder der Zeit zweier vollständiger
LLM-Antworten erkennen, welcher von zwei bekannten Prefixen zuvor berechnet
wurde? Dies ist ein lokaler Machbarkeitstest **ohne BOS** und keine
Prompt-Rekonstruktion.

- Messrechner: RTX 3090, Qwen2.5-7B-Instruct, vLLM 0.17.1,
  Python 3.13.7. Lokaler HTTP-Server auf `127.0.0.1:8765`, ein GPU-Worker,
  CPU-Offload 0, `max-model-len=2048`, Eager-Modus, Prefix-Caching an.
- A und B unterscheiden sich im ersten Token; beide Prompts sind genau
  548 Tokens lang. Jede Antwort darf höchstens ein Token enthalten.
- Pro Durchlauf ein neuer Cache-Salt. Bei 24 von 36 Durchläufen wird A oder B
  vorgewärmt: sechs Durchläufe je Kombination aus vorgewärmtem Prefix und
  zuerst gesendetem Prefix. Weitere zwölf Durchläufe ohne Vorwärmung sind
  Kontrollen. Die Fallreihenfolge ist fest randomisiert.
- Pro Durchlauf werden A und B in zwei Threads gesendet, mit beabsichtigtem
  Abstand von 10 ms. Tatsächliche Sende- und Empfangszeitpunkte stammen aus
  derselben monotonen Client-Uhr. Empfang heißt: vollständige HTTP-Antwort
  gelesen. Die tatsächliche Ankunftszeit im Server wurde nicht gemessen.
- Drei Serien: Tokenbudget pro Scheduler-Schritt 2048 (36 Durchläufe), dann
  256 (36 Durchläufe), anschließend eine unabhängige Reihenfolge mit 256
  (36 Durchläufe). Beim Budget 256 kann ein kalter Prefill über mehrere
  Schritte verteilt werden. Sonst blieben die Serveroptionen gleich.
- `cached_tokens` wurde nur als **Mechanismuskontrolle** erfasst. Ein
  Rang-/Timing-Beobachter erhält dieses direkte API-Feld in der Auswertung
  nicht. Das Feld wird in dieser vLLM-Version nur bei positivem Wert gesetzt.
  Ein Dienst, der dieses Feld an Clients ausgibt, bietet damit einen
  zusätzlichen direkten Beobachtungskanal.

Der Client steht in `src/cache_order_pilot.py`. Er schreibt pro Durchlauf
Vorwärmung, Cache-Kontrolle, Anfrage-IDs sowie Sende- und Empfangszeiten
in die drei `trials*.jsonl`-Dateien. Die zugehörigen Server- und Clientlogs
liegen daneben. Der Client wurde mit zwei Seeds ausgeführt; jede Datei wurde
neu angelegt und keine Rohdatei überschrieben.

## Beobachtungen

Alle 108 Durchläufe und alle dazugehörigen HTTP-Anfragen waren erfolgreich.
Alle Probes hatten 548 Prompt-Tokens. Bei jedem der 72 vorgewärmten
Durchläufe meldete die passende Probe 544 gecachte Tokens; die andere
meldete kein positives Cache-Feld. Die tatsächliche Sendereihenfolge entsprach
in allen Durchläufen der geplanten; medianer Abstand: 10,075 / 10,178 /
10,092 ms in den drei Serien.

| Serie | Vorwärmung zuerst gesendet: gewinnt | Vorwärmung 10 ms später gesendet: gewinnt | Ohne Vorwärmung: zuerst gesendete Probe gewinnt |
| --- | ---: | ---: | ---: |
| Budget 2048 | 12/12 | 0/12 | 12/12 |
| Budget 256, erste Serie | 12/12 | 8/12 | 12/12 |
| Budget 256, Wiederholung | 12/12 | 5/12 | 12/12 |

Bei Budget 256 klingt 13/24 spätere Cache-Treffer zuerst nach einem
Rangsignal. Die beiden Antworten dieser 24 Fälle lagen jedoch ausnahmslos
höchstens **0,093 ms** auseinander; Vorzeichen und Gewinner wechselten
zwischen den Serien. Im Normalbudget 2048 kam der spätere Cache-Treffer
stets etwa 19–23 ms nach der zuerst gesendeten kalten Probe. Ein belastbarer
Rangkanal ist damit **nicht** belegt. Die nahezu gleichzeitigen HTTP-Antworten
bei Budget 256 sind besonders anfällig für lokale Dispatch- und
Empfangsschwankungen.

Die **Clientzeiten** trennen die zwei vorgewärmten Zustände in diesem Aufbau
deutlich. Die Tabelle zeigt die Zeit vom Senden bis zum Empfang der
**zuerst gesendeten** Probe:

| Serie | Erste Probe vorgewärmt, Median (Bereich) | Zweite Probe vorgewärmt, Median (Bereich) | Keine vorgewärmt, Median (Bereich) |
| --- | ---: | ---: | ---: |
| Budget 2048 | 28,4 ms (27,4–76,4) | 139,2 ms (137,8–146,6) | 138,8 ms (137,5–143,2) |
| Budget 256, beide Serien | 28,7 ms (26,7–75,4) | 165,3 ms (161,8–170,2) | 210,8 ms (207,8–217,7) |

Bei der **binären** Frage „A oder B vorgewärmt?“ und bekannter
Sendereihenfolge trennt eine nach Sichtung der Daten gewählte
100-ms-Schwelle alle 72 vorgewärmten Durchläufe: Lag die zuerst gesendete
Probe darunter, war sie vorgewärmt; andernfalls die zweite. Das ist eine
Beschreibung der vorliegenden Daten, **keine** vorab festgelegte oder
extern validierte Klassifikationsleistung. Der Kontrollzustand „keine
Vorwärmung“ gehört nicht zu dieser binären Regel.

## Bewertung und Grenzen

Ein Cache-Timing-Signal ist auf diesem Rechner und unter diesen
Versuchsbedingungen klar sichtbar. Der Reihenfolgekanal, den BOS schützen
soll, ist bei zwei Probes unter dem normalen vLLM-Tokenbudget nicht sichtbar.
Das kleinere Budget erzeugt fast gleichzeitige Antworten, aber keinen
robusten Rangabstand. Ein einzelner Modell-/Hardware-/Prompt-Aufbau und
lokale HTTP-Zeiten erlauben keine Aussage über andere Dienste oder Netze.
Die GPU diente gleichzeitig dem Desktop; Lastschwankungen wurden nicht
systematisch kontrolliert. Es gab keine BOS-Freigabeschicht und damit keine
Messung individueller Zusatzwartezeit.

Für den nächsten Entscheidungstest ist eine **gezielte Warteschlangenbedingung**
mit mehreren Probes sinnvoll, bevor BOS implementiert wird. Dabei müssten
Sendeabstände, Empfangsabstände und Cache-Treffer weiter getrennt bleiben.
Wenn auch dort nur Timing, aber kein stabiler Rang entsteht, muss die
Forschungsfrage für vLLM-FCFS entsprechend eingegrenzt oder eine Engine mit
geeignetem Scheduling gesondert bewertet werden.

## Geprüfte technische Grundlage

Die [vLLM-0.17.1-Scheduler-Dokumentation](https://docs.vllm.ai/en/v0.17.1/api/vllm/config/scheduler/)
nennt FCFS als Standard und beschreibt das Tokenbudget. Die
[vLLM-Optimierungsdokumentation](https://docs.vllm.ai/en/v0.17.1/configuration/optimization/)
erklärt Chunked Prefill bei begrenztem Budget. [PROMPTPEEK, §II-B und
§IV-A](https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf)
verwendet LPM und eine gezielt gefüllte Warteschlange; dessen Rangbefund
wird nicht auf diese lokale FCFS-Konfiguration übertragen.
