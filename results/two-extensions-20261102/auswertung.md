# Zwei weitere Wege zum Reihenfolgesignal

Stand: 02.11.2026. Die beiden Prüfungen wurden **nach gezielter Lektüre von
Security-Originalarbeiten** ausgewählt. Sie sind kleine Robustheits- und
Grenztests des bereits beobachteten lokalen Kanals, keine BOS-Messung.

## Ausgangspunkt aus der Literatur

[PROMPTPEEK, §IV-A](https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf)
erzwingt bei Kandidaten und Dummies je ein Ausgabetoken und nutzt eine
gefüllte Warteschlange unter LPM. Die Ein-Token-Bedingung hält die
GPU-Belastung klein. [EarlyBird v3, §2.2 und §4](https://arxiv.org/html/2409.20002v3)
wertet dagegen TTFT aus; ein frühes Token ist nicht dasselbe wie die
Reihenfolge **vollständiger** Antworten. Darum prüft Weg 1 bewusst längere
Ausgaben statt die Ein-Token-Annahme zu übernehmen.

[Contention-Induced Reliability Collapse v1, §IV und §V sowie §XIV–XVI](https://arxiv.org/html/2609.06853)
zeigt, dass gleichzeitig laufende Anfragen die Verlässlichkeit von
Cache-*Timing* ändern können, und fordert gemessene Überlappung statt
einer bloß geplanten Hintergrundlast. Darum prüft Weg 2 denselben
Rangbeobachter während einer tatsächlich überlappenden Zusatzanfrage.
Die dortigen Timing-Ergebnisse werden nicht als Vorhersage für unseren
Rangkanal behandelt. [OptiLeak v1, §4.2](https://arxiv.org/html/2602.20595v1)
macht deutlich, dass Positionsfeedback selbst bereits ein bekannter
Angriffsbaustein ist.

## Gemeinsamer Aufbau

Qwen2.5-7B-Instruct, vLLM 0.17.1, RTX 3090, `127.0.0.1:8765`, FCFS,
`max-model-len=2048`, `gpu-memory-utilization=0.8`, `cpu-offload-gb=0`,
Eager-Modus, Tokenbudget 256, `long_prefill_token_threshold=64`.
Vier gleich lange Probes A–D mit je 548 Prompt-Tokens wurden mit rund
10 ms Abstand gesendet. Je Bedingung gab es 16 balancierte Durchläufe:
jedes Label war an jeder Sendeposition einmal vorgewärmt. Vier weitere
Durchläufe hatten keine Vorwärmung. Beide Bedingungen wurden innerhalb
jedes Serverstarts in zufälliger Folge gemischt. Danach lief dieselbe
Fallfolge erneut mit **Prefix-Cache aus**; die Salts waren frisch.

Weg 1: Alle vier Probes forderten **16 Ausgabetokens** an; `min_tokens=16`
erzwang in der verwendeten vLLM-API tatsächlich 16 Tokens. Die Vorwärmung
blieb bei einem Token. Weg 2: Alle Probes blieben bei einem Ausgabetoken,
während eine zusätzliche Anfrage mit 64 erzwungenen Ausgabetokens bereits
lief. Sie hatte einen **separaten Salt**, so dass sie keinen Probe-Prefix
vorwärmte. Ihre gemessene Laufzeit überdeckte bei **20/20** Durchläufen
alle vier Probe-Sendezeitpunkte und mindestens die erste Probe-Antwort.

In allen 80 Durchläufen stimmten geplante und tatsächliche Sendereihenfolge
überein; Sendeabstände 9,76–10,34 ms. Alle Probe-HTTP-Antworten hatten
Status 200. Bei Cache an meldete ausschließlich die vorgewärmte Probe
544 gecachte Tokens, bei Cache aus keine. Das Diagnosefeld diente nur
zur Kontrolle, nicht als Rangsicht des Beobachters.

## Beobachtete vollständige Antwortreihenfolge

| Weg | Cache an: spätere vorgewärmte Probe zuerst | Cache aus: spätere markierte Probe zuerst | Cache an: Vorsprung bei Sendeposition 4 |
| --- | ---: | ---: | ---: |
| 1: 16-Tokens-Antworten | **12/12**; insgesamt vorgewärmte Probe Rang 1 in 16/16 | **0/12** | **101,34–105,43 ms** (4/4 Rang 1) |
| 2: eine überlappende Zusatzanfrage | **12/12**; insgesamt vorgewärmte Probe Rang 1 in 16/16 | **2/12**, beide bei Sendeposition 2 | **173,77–176,19 ms** (4/4 Rang 1) |

Über alle vorgewärmten Fälle lag der Empfangsvorsprung gegenüber der
frühesten kalten Probe bei Weg 1 zwischen 101,34 und 206,78 ms
(Median 126,82 ms), bei Weg 2 zwischen 173,77 und 535,55 ms
(Median 501,71 ms). Diese globalen Mediane hängen stark von der
Sendeposition ab und sollten **nicht** als direkter Leistungsvergleich der
beiden Wege benutzt werden. Der Positions-4-Vergleich ist enger: der
frühere ruhige Ein-Token-Pilot hatte dort 297,68–310,07 ms Vorsprung;
16 Ausgabetokens und die zusätzliche Anfrage verringerten ihn in diesen
kleinen Serien, ließen ihn aber klar positiv.

Bei Cache aus waren die Antworten **nicht immer exakt in Sendefolge**:
Weg 1 hatte zwei Vertauschungen unter den 16 markierten Durchläufen,
Weg 2 vier; in den Kontrollen ohne Vorwärmung war die exakte Folge
3/4 beziehungsweise 1/4. Unter Hintergrundarbeit lagen die ersten
beiden kalten Antworten teils nur Bruchteile einer Millisekunde
auseinander. Die aussagekräftige, deutlich getrennte Kontrolle ist
die als vierte gesendete Probe: bei Cache aus in beiden Wegen 4/4 auf
Rang 4, bei Cache an 4/4 auf Rang 1.

## Bedeutung und Grenzen

Der Basiskanal überlebt in diesem lokalen Aufbau zwei relevante
Abweichungen vom ursprünglichen Ein-Token-/Ruhezustand. Weg 1 ist für
eine Freigabeschicht besonders wichtig: BOS sieht vollständig fertige
Antworten, und deren Reihenfolge bleibt hier auch bei längerer Ausgabe
cacheabhängig. Weg 2 zeigt, dass eine einzelne überlappende Anfrage den
Effekt nicht automatisch verdeckt. Er beweist keine Robustheit gegen
realistische Mehrnutzerlast; die zitierte Contention-Arbeit behandelt
einen anderen Beobachter und warnt gerade vor nichtlinearer Lastwirkung.

Weiterhin nur ein Modell, ein Rechner, synthetische Probes, eine gezielt
kleine Prefill-Schwelle und lokale HTTP-Zeiten. Die GPU bedient auch den
Desktop. Die Cache-aus-Serien wurden nach den Cache-an-Serien gefahren,
also nicht zeitlich vollständig interleaved. Der Salt ist innerhalb
eines Probe-Durchlaufs geteilt; tenantgetrennte Salts würden diesen
Reuse-Weg unterbinden. Kein fremder Nutzer, keine Promptrekonstruktion,
kein BOS-Schutz und kein Neuheitsnachweis. Der interne Scheduler wurde
auch hier nicht instrumentiert.

**Entscheidung:** Für den nächsten kleinen BOS-Piloten ist die Variante
mit vollständigen 16-Token-Antworten geeignet. Die Störlast-Variante
bleibt eine anschließende Robustheitskontrolle; aus 16 positiven Fällen
folgt noch keine allgemeine Lasttoleranz.

## Dateien

- `trials-cache-on.jsonl`, `trials-cache-off.jsonl`: alle 80 Rohdurchläufe
  einschließlich Sende-/Empfangszeiten von Probes und Hintergrundanfrage.
- `server-cache-on.log`, `server-cache-off.log`: genaue vLLM-Startparameter
  und Serverantworten; beide Server wurden nach dem jeweiligen Lauf beendet.
- `client-cache-on.log`, `client-cache-off.log`: Fallfolge und Fehlerausgabe.
- `../../src/two_extensions_pilot.py`: der neue Messclient;
  `../../src/cache_order_pilot.py`: gemeinsame HTTP-Anfragefunktion.
