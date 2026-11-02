# Release-Boundary-Angreifer: begrenzter Entscheidungstest

Stand: 02.11.2026. Ausschließlich lokales Qwen2.5-7B-Instruct,
vLLM 0.17.1, RTX 3090 und der unveränderte Python-Freigabeproxy.
Die neue Studie prüft eine **Erkenntnis über die Freigabegrenze**,
keine Promptrekonstruktion oder allgemeine Sicherheitsgarantie.

## Entscheidung

**Als eigenständigen Angriffsbeitrag derzeit nicht verfolgen.** Eine
feste, interpretierbare Clientregel erkennt unter C0 und 24
Ausgabetokens die grobe Cacheposition 1/2 gegenüber 3/4 auf einer
neuen Fallfolge in **31/32** Fällen. Die genaue Vierklassenposition
erkennt das neue Grenzmodell nur in **13/32** Fällen; RT erreicht
16/32, T2 13/32. Die binär trainierte T2-Basis liegt mit 29/32
nahe an der Grenzregel. Unter C1 und bei ausgeschaltetem Cache
liefert die Grenzregel je **8/16**, also kein Positionssignal.
Der neue Wert ist deshalb vor allem eine **erklärbare, prospektiv
bestätigte Gültigkeitsgrenze** des konkreten 1.050-ms-Slots unter C0.
Das Paper sollte den Schutz-/Kosten- und Fallback-Befund untersuchen,
ohne diesen Beobachter als neue allgemeine Angriffsklasse auszugeben.

## Originalarbeiten und Abgrenzung

RDNA **L2**: die genannten Originalabschnitte, Resultate und Grenzen
wurden am 02.11.2026 gezielt online geprüft. Dies ist keine
erschöpfende systematische Literatursuche.

| Originalarbeit | Bereits beschrieben | Hier untersuchte Grenze |
| --- | --- | --- |
| [PROMPTPEEK, NDSS 2025](https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf), §IV-A, S. 4–6 | LPM-Warteschlange, Dummies, Rangantworten; ein Ausgabetoken. | Kein Freigabeproxy, kein Fallback vollständiger Antworten. |
| [OptiLeak v1](https://arxiv.org/html/2602.20595v1), §§3.1, 4.2, 6 | Positionsabstand zwischen Antworten als Cachefeedback unter SGLang/LPM. | Dessen „gap“ zählt Rangplätze, nicht Millisekunden zwischen vollständig empfangenen Antworten. Ein Positionsmerkmal allein ist keine Neuheit. |
| [Carlini/Nasr 2024](https://arxiv.org/html/2410.17175), §§III–IV, VII | Aktive Timing-Probes; konstante Ausgaberate mit Leernachrichten bei fehlenden Tokens und explizite Latenz-/Bandbreitenkosten. | Kein BOS-Blockschluss und keine hier getestete späte Einzelfreigabe; feste Ausgabe als Prinzip ist bekannt. |
| [Pacer, USENIX Security 2022](https://www.usenix.org/system/files/sec22-mehta.pdf), §§2.2–4 | Geheimnisunabhängiger Sendeplan; auch tatsächliche Abweichungen vom Plan dürfen keine Geheimnisse tragen. §4 beschreibt Grenzen empirischer Verzögerungsmaskierung. | Unser `late_fallback` ist ein konkretes Beispiel für eine solche Abweichung, nicht die Entdeckung des Prinzips. Pacer ist kein direkt getesteter Schutz für vollständige LLM-HTTP-Antworten. |
| [Accumulate-and-Serve, 2013](https://arxiv.org/pdf/1302.6123), §V–VI | Sammeln und gemeinsames Bedienen reduziert Timingauflösung bei Verzögerungskosten. | Kein Cache-/LLM-/Slot-Fallback-Versuch; seine Garantien gelten nicht für unseren Proxy. |
| [SafeKV v2](https://arxiv.org/html/2508.08438v2), §§4.1–4.2, 7.2 | Selektive Cachefreigabe und „Safeguard“-Fallback gegen fälschlich geteilte KV-Blöcke, gemessen mit TTFT. | „Fallback“ meint Cache-Isolation, nicht späte HTTP-Antwortfreigabe. |
| [CacheSolidarity v1](https://arxiv.org/html/2603.10726v1) / [PrefixWall v2](https://arxiv.org/html/2603.10726v2), §§2.4, 4–5 | Dieselbe arXiv-Arbeit unter geändertem Titel; selektive Prefix-Isolation, benannte Ausnahmen und ein aktivierbarer Schutz nach Signalstärke. | Kein Angriff auf BOS oder einen Antwort-Slot. Ihre Schutzgrenzen warnen gegen pauschale Transferclaims. |

**Neuheitsurteil:** Die Literatur beschreibt Timing, Rangabstände,
Ausgabetakte und die Gefahr geheimnisabhängiger Abweichungen bereits.
In den geprüften Stellen fand sich keine konkrete Messung der
Clientlücke an einem `late_fallback` vollständiger LLM-Antworten nach
einem BOS-/Slot-Proxy. Unsere lokale Messung ist eine empirische
Konkretisierung, kein Beweis, dass ein solcher Angriff allgemein neu ist.

## Angreifer und eingefrorenes Protokoll

Die Regel verwendet ausschließlich eigene Sendezeiten, die IDs und
vollständigen Empfangszeiten der vier Antworten. Man sortiert die
Empfangszeiten und berechnet drei aufeinanderfolgende Abstände.
**Maximaler Abstand >10 ms → Cacheposition 1/2; sonst 3/4.** Die
10-ms-Grenze stammt aus der früheren 24-Token-Kalibrierung und wurde
vor den neuen Läufen in `results/release-boundary-20261102/protocol.json`
festgehalten. Das zusätzliche Vierklassenmodell verwendet nur die
logarithmierten drei Abstände und die Position der größten Lücke,
regulierte logistische Regression `C=1`, trainiert auf 16 alten
Kalibrierfällen. R1, T1, T2 und RT wurden nach denselben
Clientbeobachtungen wie zuvor verglichen. Das Grenzmerkmal ist eine
Funktion der vier Clientzeiten; es kann informationstheoretisch
**nicht mehr Information als T2** enthalten. Es kann allenfalls als
induktive Regel bei Sitzungsdrift robuster sein.

Der öffentliche Stellknopf war ausschließlich `max_tokens=min_tokens`:
alle vier Probes hatten zunächst 16, dann 24 Ausgabetokens. Das
erzeugt unter C0 eine messbare Änderung der Fallbackhäufigkeit,
ohne eine Probe gezielt länger zu machen. Der Angreifer braucht
keine internen Zeiten, keine Cache-Zähler und kein Proxy-Flag.
Proxyprotokolle dienen nur der nachträglichen Integritätsprüfung.
Die Vorwärmung wird vom **Versuchsaufbau als Stellvertreter für einen
fremden Cacheeintrag** ausgeführt. Der Beobachter bekommt weder den
gewählten Kandidaten noch die Vorwärmantwort als Eingabe. Es gab
keinen realen fremden Nutzer; ein Angreifer, der die Vorwärmung selbst
ausführte, würde das Label schon kennen. Die Schlussfolgerung ist
daher eine lokale Seitenkanal-Machbarkeit unter gemeinsam nutzbarer
Salt-/Cache-Domäne, keine Demonstration eines Fremdnutzerangriffs.

## Daten und Ergebnisse

Alte 24-Token-Entwicklungsserie: 16 positive Fälle. Zwei frühere
32er-Tests verwendeten dieselbe deterministische Fallfolge und sind
daher nur begrenzt unabhängig. Die neue C0-Serie nutzt eine **andere,
vorab zufällig erzeugte Fallfolge**, frische Salts und einen neuen
Backend-/Proxy-Start; acht positive Fälle je Position plus vier
unvorgewärmte Kontrollen. C1 hat vier positive Fälle je Position
plus vier unvorgewärmte Kontrollen. Die Cache-aus-Serie hat je vier
markierte Positionen, aber **keine tatsächlichen Cachetreffer**.
Damit wurden 48 neue positive Vierer-Durchläufe und 16 markierte
Cache-aus-Kontrollen gefahren; die Obergrenze von 64 positiven
Entscheidungsfällen wurde eingehalten. Alle drei Fallfolgen haben
verschiedene Seeds; die neuen Folgen stimmen nicht mit dem alten
24-Token-Testplan überein.

| Test nach Training auf 16 alten C0-Fällen | Binäre Grenzregel | Binär trainiertes T2 | Grenzmodell, vier Klassen | R1 / T1 / T2 / RT, vier Klassen |
| --- | ---: | ---: | ---: | --- |
| Alter 24-Token-Holdout, 32 positive | 28/32 | 24/32 | 14/32 | 8 / 8 / 14 / 14 |
| Alte 24-Token-Bestätigung, 32 positive | 27/32 | 27/32 | 15/32 | 14 / 10 / 20 / 13 |
| **Neue C0-Bestätigung, 32 positive** | **31/32** | **29/32** | **13/32** | **11 / 8 / 13 / 16** |
| Neue C1-Übertragung, 16 positive | **8/16** | 8/16 | 4/16 | 6 / 2 / 2 / 4 |
| Cache aus, 16 markierte Positionen | **8/16** | 11/16 | 5/16 | 4 / 4 / 5 / 4 |

Binäres Zufallsniveau ist 50 %, Vierklassen-Zufallsniveau 25 %.
Für die neue C0-Grenzregel: Balanced Accuracy 0,969, Wilson-95-%-
Intervall **0,843–0,995**; ein Fehler, ein später Cachetreffer
fälschlich als frühe Position. Das neue Vierklassenmodell erreicht
13/32 (Wilson 0,255–0,577), mit **0/8** richtigen Position-1-
Vorhersagen. Die exakten Konfusionsmatrizen stehen in
`results/release-boundary-20261102/final-analysis.json`. Die Differenz
31/32 zu 29/32 bei binär trainiertem T2 ist auf 32 Fällen **kein
belastbarer Überlegenheitsnachweis**. Beide benutzen dieselben
Clientzeiten; hier zählt die Interpretierbarkeit der Regel.

Die Integritätsprüfung verband alle **288 neuen Clientantworten** mit
ihren Proxyzeilen: HTTP 200, 548 Prompt- und 24 Ausgabetokens,
korrekte Zeitfolge, keine Cache-Diagnosefelder beim Client.
Die Proxykontrolle meldete 32/32 Cachetreffer in C0, 16/16 in C1
und 0/16 bei ausgeschaltetem Cache. Tatsächliche Fallback-Gruppen:
**30/36** C0, **4/20** C1 (alle vier unvorgewärmt), **16/16** Cache aus.
Die >10-ms-Regel erkannte 21/30, 4/4 beziehungsweise 16/16
Fallbackgruppen ohne falschen Fallbackalarm. Sie **erkennt nicht jeden
Fallback**. Vor allem sind alle vier unvorgewärmten C0-Kontrollen
und sämtliche Cache-aus-Fälle ebenfalls lückenhaft: Eine sichtbare
Lücke beweist weder einen Cachetreffer noch dessen genaue Position.
Die 31/32-Aussage setzt voraus, dass unter den vier Kandidaten genau
einer vorbereitet ist.

## Antworten auf die Forschungsfragen

1. **Clientseitig erkennbar?** Eine große Lücke zeigt in diesem Proxy
   häufig eine späte Einzelfreigabe, aber nicht vollständig. Die
   Grobposition wird unter C0/24 Tokens prospektiv erkannt.
2. **Öffentlich gezielt untersuchbar?** Ja, hier durch gleiche
   Ausgabelänge für alle vier Anfragen. 16 Tokens zeigten im alten
   Slotlauf keine Fallbacks, 24 Tokens im neuen C0-Lauf 30/36 Gruppen
   mit Fallback. Eine adaptive Suche über viele Längen wurde nicht
   durchgeführt.
3. **Mehr Information/robuster?** Keine zusätzliche Information über
   T2 hinaus. Gegenüber R1 und T1 ist die binäre Grenze nützlich;
   gegenüber binär trainiertem T2 kein gesicherter Vorteil. Bei der
   exakten Vierklassenposition ist sie sogar schwächer als RT im
   neuen C0-Test.
4. **C0 oder C1?** Der Positionsbefund ist bisher nur C0. C1 hatte
   positive Cachetreffer, aber keinen positiven Fallback und 8/16
   binär; Cache aus ebenfalls 8/16. Das ist ein Bedingungsbefund,
   kein Beweis allgemeiner Sicherheit unter C1.
5. **Neu gegenüber Originalarbeiten?** Die konkrete Kombination aus
   vollständiger LLM-Antwort, festem Slot, späten Einzelfreigaben und
   Clientlücke wurde in den geprüften Stellen nicht berichtet.
   Die allgemeine Timing-/Fallback-Logik ist bekannt.
6. **Paper-Entscheidung?** Ein **stärkerer Schutzgrenzen-Befund**,
   kein eigenständiger neuer Angriff. Die Paperfrage sollte lauten,
   unter welchen Serving- und Antwortzeitbedingungen eine
   Antwortfreigaberegel Restinformation preisgibt und was eine
   wirksame Spätantwortregel an individueller Wartezeit kostet.

## Reproduktion und nächste Entscheidung

`src/release_boundary_attack.py` berechnet ausschließlich aus den
gespeicherten Clientdaten die Angreifermerkmale und validiert die
Proxyprotokolle getrennt. Aufruf mit der vorhandenen Python-3.13-
Projektumgebung:

```bash
/home/rock/projects/porto/.venv-py313-repair/bin/python \
  src/release_boundary_attack.py \
  results/release-boundary-20261102/recheck.json
```

Der neue Seed-Parameter in `src/bos_pilot.py` ist optional; frühere
Aufrufe behalten ihre alten Defaults. Die Freigaberegel in
`src/order_release_proxy.py` blieb unverändert. Die Rohdaten und
Logs liegen ausschließlich in `results/release-boundary-20261102/`.
Ein erster Start scheiterte vor jeglicher Messung an einem zu langen
lokalen Socket-Pfad; `c0/server.log` dokumentiert den Fehler,
`c0/server-restart.log` den erfolgreichen Lauf.

Der kleinste sinnvolle nächste Test ist **keine weitere
Accuracy-Suche**. Für einen eigenständigen Schutzbeitrag müsste eine
alternative Spätantwortregel vorab definiert und an denselben
24-Token-Bedingungen bezüglich Leakage, individueller Wartezeit
und Verfügbarkeit geprüft werden. Dafür wäre eine eigene
Versuchsentscheidung nötig; dieser Auftrag hat die Regel bewusst
nicht verändert.
