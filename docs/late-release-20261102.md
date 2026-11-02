# Später fester Freigabeslot: lokaler Schutz- und Kostentest

Stand: 02.11.2026. Lokales Qwen2.5-7B-Instruct, vLLM 0.17.1,
RTX 3090, C0 (`max_num_batched_tokens=256`,
`long_prefill_token_threshold=64`), vier 548-Token-Probes mit je
24 Ausgabetokens. Die Vorwärmung simuliert einen fremden Cacheeintrag;
es gab keinen realen Fremdnutzer. Alle Ergebnisse und Logs liegen
unter `results/late-release-20261102/`.

## Entscheidung

**Ein einheitlicher späterer Slot beseitigte in diesem lokalen
24-Token-Bereich den beobachteten Fallback, verursachte aber hohe
individuelle Wartezeit.** Ein bei der ersten Proxy-Ankunft
verankerter Slot von 1.200 ms gab im Entwicklungs- und neuen
Backend-Holdout **56/56 Gruppen vollständig zu viert** frei;
0 Antworten wurden einzeln verspätet freigegeben. Der stärkste
der hier geprüften Vierklassen-Clientbeobachter traf im Holdout
**10/32** vorbereitete Positionen (Zufallserwartung 8/32). Das ist
**kein Sicherheitsbeweis** und kein Beleg für alle Lasten oder
Antwortlängen. Der Live-Holdout maß pro Antwort median **182,70 ms**
Proxy-Wartezeit (P95 351,98 ms, Maximum 367,32 ms). Die gepaarte,
idealisierte Nachrechnung auf 108 bisherigen 24-Token-Traces
ergab einen Median von **150 ms zusätzlicher individueller Wartezeit**
gegenüber dem 1.050-ms-Slot.

Die wissenschaftlich relevante Aussage ist eine **lokale
Schutz-Kosten-Grenze**: Die einfache `late_fallback`-Regel gab in
der zuletzt neu randomisierten 1.050-ms-C0-Serie 30/36 Gruppen
teilweise einzeln frei und ermöglichte eine clientseitige
Früh-/Spätpositionsregel mit 31/32 Treffern. Ein für alle Gruppen
gleicher späterer Zeitpunkt entfernte diesen Ausfallbereich in
der getesteten Antwortzeitspanne. Der Slot wurde aus früheren
Traces gewählt; er ist kein allgemeines optimales oder hartes
Latenzbudget.

## Vorab festgelegte Regel und Literatur

Vor dem ersten neuen Live-Lauf wurden `slot1200`, 24 Tokens,
16 positive Entwicklungsfälle und 32 positive Holdoutfälle mit
getrennten Seeds und Backend-Neustart sowie R1/T1/T2/RT in
`results/late-release-20261102/protocol.json` festgehalten.
Bei `slot1200` bleibt **jede** vollständige Antwort bis 1.200 ms
nach erster Proxy-Ankunft zurückgehalten; dann wird die verfügbare
Gruppe gemischt und wie bisher mit 2-ms-Abstand seriell versendet.
Der vorhandene `late_fallback` für Antworten **nach** diesem Slot
blieb absichtlich erhalten. `slot1050` und die übrigen alten
Regeln wurden nicht verändert.

Die Wahl von 1.200 ms stammt ausschließlich aus den 108 vorher
vorliegenden 24-Token-Gruppen: Die späteste vierte Backend-Antwort
lag dort 1.154,10 ms nach der ersten Proxy-Ankunft, also 45,90 ms
vor dem neuen Slot. 1.050 ms erreichten nur **23/108** Gruppen
vollständig, 1.200 ms in der idealisierten Nachrechnung **108/108**.
Die neuen Sitzungen prüfen diese Entscheidung außerhalb der
Auswahltraces.

Eine naheliegende andere Spätregel wäre, bei 1.050 ms die ganze
Teilgruppe bis zur vierten Antwort zurückzuhalten. Sie verhindert
einzelne Fallbacks, macht den ersten sichtbaren Empfang aber
erneut vom letzten Backend-Eingang abhängig und kehrt damit zum
bereits gemessenen BOS-Blockschlusskanal zurück. Sie wurde hier
aus diesem mechanistischen Grund nicht live als weiterer Kandidat
getestet.

Der Grundsatz ist aus [Pacer, §§2.2–4](https://www.usenix.org/system/files/sec22-mehta.pdf)
bekannt: Auch tatsächliche Abweichungen von einem Sendeplan dürfen
keine geheimen Verarbeitungszeiten zeigen. [Carlini/Nasr, §VII](https://arxiv.org/html/2410.17175)
untersucht einen festen Ausgabetakt für Token und seine
Latenz-/Bandbreitenkosten; [Accumulate-and-Serve, §§V–VI](https://arxiv.org/pdf/1302.6123)
analysiert Pufferungs- und Verzögerungskosten. **Feste spätere
Ausgabe ist nicht neu.** Unser Beitrag ist die gemessene lokale
Grenze einer vollständigen LLM-HTTP-Antwortgruppe mit explizitem
Fallback, clientseitigem Beobachter und individueller Wartezeit.
Diese drei Originalabschnitte wurden am 02.11.2026 nochmals gezielt
geprüft (RDNA L2); die breitere Quellenkarte steht in `docs/quellen.md`.

## Live-Messungen und Angreifer

Die Entwicklungsserie hatte 16 positive Fälle (vier je Position)
und vier unvorgewärmte Kontrollen. Die Holdoutserie hatte 32 positive
Fälle (acht je Position) und vier Kontrollen, eine neue zufällig
erzeugte Fallfolge, frische Salts und einen neuen Backend- und
Proxy-Start. Insgesamt wurden **56 neue Vierer-Durchläufe** und
224 vollständige Clientantworten geprüft. Alle Antworten: HTTP 200,
548 Prompt-Tokens, 24 Ausgabetokens, gültige Zeitfolge und kein
Cache-Diagnosefeld im Client. Genau die markierten positiven
Probes zeigten proxyintern 544 Cache-Tokens. Der Angreifer nutzte
diese internen Felder **nicht**.

| 1.200-ms-Regel | Entwicklung | Holdout |
| --- | ---: | ---: |
| Vollständige Vierergruppen | 20/20 | **36/36** |
| Späte Einzelfreigaben | 0/80 Antworten | **0/144 Antworten** |
| Letzte Backend-Antwort relativ zur ersten Proxy-Ankunft, Maximum | 1.120,14 ms | **1.124,00 ms** |
| Clientlücke >10 ms unter positiven Fällen | – | **0/32** |
| R1, richtige Cacheposition | – | **7/32** |
| T1 / T2 / RT, auf 16 Entwicklungsfällen trainiert | – | **10 / 10 / 10 von 32** |

Vierklassen-Zufallserwartung: 8/32. Für 10/32 beträgt das
Wilson-95-%-Intervall 0,180–0,486; der einseitige Binomialwert
gegen 25 % ist 0,263 unter näherungsweise unabhängigen Fällen.
Die Konfusionsmatrizen stehen in `analysis.json`. Bei nur einem
Rechner und 32 Prüffällen kann eine stärkere adaptive Clientregel
nicht ausgeschlossen werden. Insbesondere bedeutet „kein
detektierter Angriff“ keine bewiesene Informationsfreiheit.

## Individuelle Kosten und fairer Vergleich

Proxy-Wartezeit = Freigabebeginn minus vollständigem Backend-
HTTP-Eingang; Client-End-to-End = vollständiger Clientempfang minus
Clientversand. Die folgende Live-Tabelle stammt aus zwei
verschiedenen Backend-Sitzungen und ist **nicht gepaart**:

| 24 Tokens, C0 | Antworten | Proxy-Wartezeit Median / P95 / Max, ms | Client-End-to-End Median / P95 / Max, ms | Vollständige Gruppen |
| --- | ---: | ---: | ---: | ---: |
| Bisheriger 1.050-ms-Slot, letzte neue C0-Serie | 144 | 19,51 / 185,13 / 197,76 | 1.047,63 / 1.087,16 / 1.105,12 | 6/36 |
| Neuer 1.200-ms-Slot, Holdout | 144 | **182,70 / 351,98 / 367,32** | **1.189,54 / 1.207,75 / 1.207,93** | **36/36** |

Die zuletzt genannte 1.050-ms-Serie enthält 32 Positive und vier
Kontrollen; ihre sechs vollständigen Gruppen sind aus den Rohdaten
erneut gezählt. Die separate, **gepaarte Offline-Nachrechnung**
verwendet dagegen dieselben 108 alten Backend-Eingangsfolgen
(432 individuelle Antworten) für beide Slots. Ihre idealisierten
Medianwartezeiten betragen **15,73 ms** bei 1.050 ms und
**165,73 ms** bei 1.200 ms; der Median der **individuellen gepaarten
Differenzen** beträgt **150,00 ms**. Für die 96 vorbereiteten
Antworten beträgt derselbe gepaarte Differenzmedian 150,00 ms.
Die Nachrechnung lässt Python-Timerstreuung, serielle Ausgabe und
eine mögliche Rückkopplung auf das Backend aus. Ihre 150 ms sind
keine zusätzliche Live-Durchsatz- oder Latenzgarantie.

## Grenzen und nächster wissenschaftlicher Schritt

1. **Verspätung jenseits 1.200 ms:** Der alte `late_fallback` bleibt
   aktiv. Bei längeren Antworten oder anderer Last kann derselbe
   Kanal wieder auftreten. Eine harte individuelle Wartegrenze ist
   nicht bewiesen.
2. **Bedrohungsmodell:** Die Vorwärmung simuliert einen verborgenen
   Cachezustand auf demselben Rechner. Keine Fremdnutzer-, Netz-
   oder Mehrmodellmessung; gemeinsame Salt-/Cache-Domäne bleibt
   Voraussetzung.
3. **Kosten:** Der spätere Slot beseitigt das lokale Fallbackproblem
   durch Warten für **alle** Gruppen. Das ist ein bekannter
   Mechanismus und kein Entwurf einer allgemein neuen Abwehr.
4. **Paper-Entscheidung:** Der Befund stärkt die Richtung
   *Schutz-Kosten-Grenze nach BOS*, nicht einen selbständigen
   Release-Boundary-Angreifer. Für einen echten neuen Schutzbeitrag
   fehlt eine Spätantwortpolitik, die auch bei Überschreiten des
   öffentlichen Slots ihre Leakage- und Verfügbarkeitswirkung
   nachvollziehbar begrenzt.

Reproduktion mit der vorhandenen Python-3.13-Umgebung:

```bash
/home/rock/projects/porto/.venv-py313-repair/bin/python \
  src/late_release_analysis.py \
  results/late-release-20261102/recheck.json
```

`src/order_release_proxy.py` erhielt nur den zusätzlichen Modus
`slot1200`; die bisherigen Modi bleiben in ihrer Funktionsweise
unverändert. Das Auswerteprogramm verbindet jede Clientantwort mit
der Proxyzeile, berechnet die Clientbeobachter und die gepaarten
idealen Wartekosten aus den vorhandenen Traces.
