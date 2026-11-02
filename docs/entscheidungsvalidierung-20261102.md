# Wissenschaftliche Entscheidungsvalidierung – ICCAI 2027

Stand: 02.11.2026. Lokales Qwen2.5-7B-Instruct / vLLM 0.17.1 / RTX 3090.
Zweck dieses Berichts ist die Entscheidung über eine **Forschungsfrage**,
nicht die Bestätigung früherer positiver Zahlen. Alle neuen Messungen
nutzen dasselbe Modell und dieselbe GPU; es gab keine Installation, keinen
fremden Nutzer und keine Promptrekonstruktion. Neue Messdaten wurden nur
unter `results/decision-validation-20261102/` geschrieben. Bestehende
Rohdaten blieben unverändert.

## Entscheidung in einem Absatz

**Primär verfolgen: „Residual Leakage after Order Scrubbing“, mit der
Gültigkeitsgrenze fester Freigabeslots als zentralem zweiten Befund.**
Der Mechanismus ist in den lokalen Daten klar: BOS W=4 mischt die IDs,
gibt aber beim Eingang der letzten vollständigen Backend-Antwort frei.
Diese Blockschlusszeit trägt in der gezielt eingestellten C0-Konfiguration
ein sichtbares Clientzeitsignal. Ein fester Slot glättet das bisherige
Einzelzeitmerkmal nur, solange alle Antworten rechtzeitig eintreffen.
Bei 24 statt 16 Ausgabetokens erzeugt die **unveränderte** Fallback-Regel
erneut beobachtbare, positionsabhängige Antwortmuster; ein auf 16
Kalibrierfällen trainierter Vierklassenbeobachter mit vier Clientzeiten
traf in einer späteren, getrennten Bestätigungsserie **20/32** Fälle.
Gleichzeitig ist der starke ursprüngliche Rangkanal **konfigurationsabhängig**:
Ohne die besondere Prefill-Schwelle ist er deutlich schwächer oder fehlt
in den hier getesteten Bedingungen. Der Paper-Claim muss auf diesen
Gültigkeitsbereich begrenzt bleiben. Der nun geprüfte Volltext der
eigenen ICCAI-2026-Arbeit behandelt nur Rangfolgen, ODS und die
Gesamtlaufzeit; individuelle Antwortwartezeiten und Clientzeiten
fehlen dort. Die lokale Erweiterung ist damit gegenüber der eigenen
Vorarbeit abgrenzbar, aber noch kein allgemeiner Neuheitsnachweis
gegenüber der gesamten LLM- und Traffic-Shaping-Literatur.

## 1. Validierung der bisherigen Ergebnisse

Eine eigenständige Nachrechnung verbindet Client- und Proxy-Zeilen über
die API-ID. Für die vier bisherigen Kernserien wurden **2.720 Antworten**
erneut geprüft: 1.088 Hauptserie, 544 BOS-Holdout, 272 Slot-Folgeserie
und 816 bereinigter Lauf. Kein fehlender oder doppelter Request, kein
Proxyfehler, keine ungültige Zeitfolge, kein Cache-Kontrollfehler.
Die positiven Fälle sind pro Regel gleichmäßig auf vier vorbereitete
Sendepositionen verteilt (je 16). Die gemeldeten 544 Cache-Tokens liegen
nur bei der vorgesehenen Probe; alle 816 Clientantworten im bereinigten
Lauf enthalten **kein** `cached_tokens`-Diagnosefeld. Das Feld war in
früheren Läufen offen, ging aber nicht in die berichteten Rang- oder
Zeitregeln ein. Der aktuelle Proxy entfernt es vor der Clientantwort.

Die aufgezeichneten Shuffle-Seeds rekonstruieren die tatsächlichen
Permutationen der vollen und partiellen Blöcke; der Code zieht jeden Seed
über `secrets.randbits(64)` unabhängig von Label und Cachezähler.
Aus endlichen Stichproben folgt keine mathematisch bewiesene
Unabhängigkeit; die Implementierung und die Rekonstruktion liefern
aber keinen Hinweis auf eine labelabhängige Auswahl der Permutation.
Die erneute Auswertung stimmt bytegleich mit der zuvor geschriebenen
unabhängigen Rekonstruktion überein. Insbesondere bestätigt sie:

| Bisherige Regel | Positive Fälle | Vorbereitete Antwort auf Rang 1 | Reproduzierte Clientzeit-Regel |
| --- | ---: | ---: | ---: |
| Direkt, Hauptserie | 64 | **64/64** | – |
| BOS W=4, Hauptserie | 64 | **19/64** | Training der Zeitmediane |
| 100-ms-Ziel, Hauptserie | 64 | **64/64**, jeweils vorbereitete Antwort allein freigegeben | – |
| 250-ms-Ziel, Hauptserie | 64 | **18/64**, volle Viererblöcke | – |
| BOS W=4, getrennter Backend-Neustart | 64 | **21/64** | **53/64** aus Hauptserien-Medianen |
| 250-ms-Ziel, derselbe Neustart | 64 | **15/64** | **56/64** aus denselben Medianen |
| BOS W=4, bereinigter Lauf | 64 | **14/64** | **41/64** mit derselben Regel |
| 250-ms-Ziel, bereinigter Lauf | 64 | **16/64** | **43/64** mit derselben Regel |

Die Entwicklungs- und Prüffälle verwenden verschiedene Salts und
Durchläufe. Der erste BOS-Holdout lief nach einem Neustart von Backend
und Proxy; der bereinigte Lauf ist ein weiterer Client-/Proxy-Datensatz,
teilte aber den Backend-Server mit der vorherigen Holdout-/Slot-Phase.
Es sind daher **keine** unabhängigen Hardware- oder Modellpopulationen.
Zudem erzeugt `src/bos_pilot.py` seine Fallfolge allein aus der
Wiederholungszahl (`20261106 + repeats`). Die beiden neuen
24-Token-Slot-Tests mit jeweils `repeats=2` haben daher dieselbe
Reihenfolge der Positionen und Kontrollen; neue Salts und getrennte
Backend-/Proxy-Neustarts machen die Cachezustände verschieden, aber
die Reihenfolge ist **nicht unabhängig randomisiert**. Dasselbe gilt
für die beiden C1-BOS-Serien mit `repeats=1`. Ein unbekannter
zeitlicher Verlauf könnte die Varianz oder Klassifikation beeinflussen.
Der Code berechnet die Zeitmediane ausschließlich aus der Hauptserie
und benutzt für die Tests keine internen Zeiten. Die vorhandenen
Dateizeitstempel belegen jedoch **keine sichere Prospektivität der Wahl
von Merkmal und Regel vor dem ersten Holdout**: Die aktuelle Fassung des
Auswerteskripts wurde später verändert. 53/64 und 41/64 sind deshalb
ehrlich als reproduzierte, zwischen Sitzungen geprüfte Analysen zu
lesen, nicht als formal vorregistrierter Angriff.

## 2. Kausaler Mechanismus: Was der Blockschluss erklärt

Im aktuellen Proxy löst ein voller BOS-Block die Freigabe aus, sobald
die **vierte vollständige HTTP-Antwort** vom Backend am Proxy eingegangen
ist. Der interne Modell-Fertigstellungszeitpunkt wurde nicht
instrumentiert. Alle hier verwendeten Client-, Proxy-Eingangs- und
Freigabezeitpunkte stammen von derselben monotonen Rechneruhr; es
werden keine Zeitdifferenzen zwischen verschiedenen Uhren gebildet.

Bei vollständigem W=4/250-ms-BOS betrug die Zeit vom letzten
Backend-Eingang bis zum ersten vollständigen Clientempfang in den
Haupt-, Holdout- und bereinigten Serien median **0,55–0,60 ms**;
die größte beobachtete Differenz unter den positiven Fällen blieb
unter **0,92 ms**. Die erste Proxy-Freigabe folgte dem letzten
Backend-Eingang median nach etwa 0,26–0,29 ms. Bei W=4 in der
Hauptserie lagen die Mediane der ersten Clientantwort nach
vorbereiteter Sendeposition 1–4 bei **914,79 / 903,03 / 884,45 /
860,87 ms**; die Mediane des letzten Backend-Eingangs zeigten
dasselbe Muster. Diese nahezu direkte Zeitkette erklärt das
gemessene Clientmerkmal mechanistisch **für diesen Proxy**.

Die Variation **vor** dem Blockschluss kann weiterhin durch
vLLM-Scheduling, Cache-Wiederverwendung und GPU-Last geprägt sein;
ohne internen Scheduler-Trace lässt sich deren jeweiliger Anteil
nicht exakt trennen. Tatsächliche Client-zu-Proxy-Ankunftslags lagen
typisch um 0,6 ms und erklären allein nicht den Abstand der
Positionsmediane. Vier Antworten enthielten jeweils exakt 16
Ausgabetokens; die Antwortlänge in Bytes wurde nicht getrennt
protokolliert. Proxy-Verarbeitung und serielle Freigabe mit geplantem
2-ms-Abstand verschieben vor allem spätere Clientantworten, während
das benutzte Merkmal die **erste** vollständige Antwort ist.
Transport- und Betriebssystemeffekte bleiben mögliche Quellen
kleinerer Streuung; die absolute Laufzeit driftete zwischen Sitzungen.
Der Blockschluss ist somit eine **belastbare mechanistische Erklärung
der Freigabezeit**, aber kein vollständig isolierter kausaler Nachweis
für die internen Schedulerentscheidungen. Ein zusätzliches
experimentelles Instrumentieren der Backend-Fertigstellung wäre dafür
der fehlende Kontrollschritt.

## 3. Übertragbarkeit: Konfiguration und Promptinhalt

Die Serverlogs bestätigen in vLLM 0.17.1 jeweils aktiviertes Chunked
Prefill. Die dokumentierte Schwelle `long_prefill_token_threshold=0`
setzt in diesen Starts keine zusätzliche 64-Token-Kappung pro
Prefill-Schritt; das Tokenbudget gilt weiterhin. Damit sind C0, C1
und C2 tatsächlich unterschiedliche Einstellungen, keine vermuteten
Defaults. Alle neuen Probes forderten genau 16 Ausgabetokens an.

| Konfiguration und Prompt | Positive Fälle | Vorbereitete Antwort Rang 1 | Später gesendeter Treffer Rang 1 | Einordnung |
| --- | ---: | ---: | ---: | --- |
| C0: Budget 256, Schwelle 64, bisheriger Prompt; direkte Hauptserie | 64 | **64/64** | **48/48** | Starker lokaler Rangkanal |
| C1: Budget 256, Schwelle 0, ursprünglicher Prompt; zwei getrennte Serverstarts | 64 | **26/64** | **10/48**; ausschließlich Sendeposition 2 | Deutlich schwächer; Positionen 3 und 4 nie zuerst |
| C2: Budget 2048, Schwelle 0; ein Serverstart | 32 | **8/32** | **0/24** | In dieser Serie entspricht der erste Rang der Sendeposition |
| C0 mit neuem Promptsatz; zwei getrennte Serverstarts | 64 | **64/64** | **48/48** | Nicht auf den ursprünglichen Prompttext beschränkt |

Die neue Promptgruppe hat andere Inhalte; der tatsächlich geladene
Qwen-Tokenizer ergab **548 Tokens für A, B, C und D**. Sie wurde vor
der Messung als `configs/prompt-set-v2.json` fixiert; SHA-256 des
Promptsatzes steht in jeder Rohzeile. Bei C0 meldete jede vorbereitete
Probe 544 Cache-Tokens. Vier Cache-aus-Kontrollen mit dem neuen Satz
ordneten die markierte Antwort viermal ihrem Sendeplatz zu. C1 und C2
haben ebenfalls je vier Cache-aus-Kontrollen ohne positiven Cachetreffer.
Das sind Mechanismuskontrollen, keine präzise Schätzung seltener
Fehlordnungen.

Ein nur aus der ersten Clientantwortzeit trainierter Vierklassenbeobachter
traf in C1 nach getrenntem Neustart **14/32**. Das signalisiert vor allem
den zuerst gesendeten Treffer; die drei späteren Positionen trennen
sich kaum. Ein zusätzlicher C1-BOS-Test nutzte zwei getrennte,
balancierte 16er-Serien mit vollen Viererblöcken: der auf der ersten
Serie trainierte Zeitbeobachter traf im zweiten Lauf **6/16**, die
erste Antwort-ID **5/16** (Zufallserwartung 4/16). **Ein starker
vierklassiger BOS-Restkanal unter C1 ist damit nicht belegt.**
C2 wurde nach 32 positiven Fällen ohne erkennbaren Rangkanal nicht
weiter verlängert; eine C2-BOS-Aussage folgt daraus nicht.

Die klare Klassifikation lautet: **reproduzierbar unter C0 und mit
anderen Promptinhalten, aber wesentlich konfigurationsabhängig**.
Die Ergebnisse widerlegen keine anderen Cache-Timing-Kanäle unter
C1/C2; sie begrenzen den hier untersuchten Vierer-Rangkanal.

## 4. Stärkere Angreifer und Generalisierung

R1 nutzt die erste Antwort-ID; R2 die vollständige ID-Permutation;
T1 die erste Clientzeit; T2 alle vier vollständigen Clientzeiten;
RT beides. Die gelernten Beobachter sind standardisierte logistische
Regressionen mit festem `C=1`, ohne Hyperparametersuche. Features
sind nach **bekannter Sendeposition** geordnet, Labels die vier
möglichen vorbereiteten Positionen. Die Eingaben enthalten keine
Proxy-/Backend-Zeit, keinen Cachezähler und keinen Promptinhalt.
Es wird **auf ganzen Durchläufen und nach Messsitzung getrennt**;
frische Salts verhindern eine gemeinsame Cachezustandsrealisierung
auf beiden Seiten. Vier Klassen sind in jeder genannten positiven
Serie gleich häufig; Accuracy und Balanced Accuracy sind daher gleich.

| Training → Test, Regel | R1 | R2 | T1 gelernt | T2 gelernt | RT gelernt | T1 aus früheren BOS-Medianen |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BOS-Hauptserie → Neustart, W=4, n=64 | 21 | 14 | 53 | **54** | 49 | 53 |
| BOS-Hauptserie → bereinigt, W=4, n=64 | 14 | 15 | 35 | **37** | 35 | **41** |
| BOS-Hauptserie → Neustart, 250 ms, n=64 | 15 | 11 | 53 | **54** | 44 | 56 |
| BOS-Hauptserie → bereinigt, 250 ms, n=64 | 16 | 25 | 31 | 30 | **37** | **43** |
| Frühe Slot-Pilotfälle → bereinigter 16-Token-Slot, n=64 | 14 | 9 | 20 | 14 | 9 | – |
| Slot-Folgeserie mit 64 Fällen → bereinigter Slot, n=64 | 14 | 14 | 19 | 17 | 15 | – |

Alle Zahlen sind richtige Vorhersagen von 64; Zufallserwartung **16/64**.
Vollständige Konfusionsmatrizen, Balanced Accuracy und Wilson-Intervalle
stehen in `results/decision-validation-20261102/observer-comparison.json`
und `slot-trained64-sanitized.json`. Beispiel: T2 bei W=4 nach
Neustart 54/64, Wilson 95 % **0,736–0,913**; nach dem bereinigten
Lauf 37/64, **0,456–0,691**. Die absolute Zeitregel leidet unter
Sitzungsdrift. Die höhere R2-Zahl 25/64 nur im bereinigten 250-ms-
Lauf wiederholt sich im anderen Test **nicht** (11/64); mehrere
explorative Vergleiche verbieten einen isolierten Signifikanzclaim.
Eine Accuracy unter 25 % beweist keine Informationsfreiheit.
Klassifikationsgenauigkeit wird nicht als gemessene gegenseitige
Information ausgegeben.

## 5. Fester Slot und sein tatsächlicher Fallback

Der Proxy wurde **nicht** umprogrammiert: `slot1050` verankert den
Timer am ersten Proxy-Anfrageeingang. Zum Slot bereits vollständig
eingegangene Antworten werden gemischt und mit geplantem 2-ms-Abstand
ausgegeben. Jede danach eingehende Antwort erhält einzeln
`late_fallback` und wird sofort freigegeben. Bei 16 Tokens waren in
der bereinigten Serie **68/68** Gruppen vollständig und kein Fallback
trat ein. Für den Grenztest wurden allein die Ausgaben **aller vier
Probes gleichermaßen** auf 24 Tokens verlängert; Prompt, Salt-Logik,
Sendeabstand, Server C0 und 1.050-ms-Slot blieben gleich.

Eine 20-Gruppen-Kalibrierung (16 positive, vier ohne Vorwärmung)
bestimmte diese Bedingung. Danach folgten zwei **separate Backend- und
Proxy-Neustarts** mit je 36 Gruppen (32 positive, vier Kontrollen),
ohne Änderung der Bedingung. Alle 24-Token-Antworten waren vollständig,
HTTP 200, Zeiten geordnet und das Cache-Diagnosefeld clientseitig
entfernt. Die positiven Fälle waren je 8-mal pro Position vertreten.

| Slot bei 24 Tokens | Kalibrierung | Holdout | Bestätigung |
| --- | ---: | ---: | ---: |
| Gruppen mit mindestens einem Fallback | 14/20 | **28/36** | **27/36** |
| Vollständige Viererblöcke | 6/20 | 8/36 | 9/36 |
| Einzeln spät freigegebene Antworten | 37/80 | 54/144 | 55/144 |
| R1 bei positiven Fällen | 10/16 | 8/32 | **14/32** |
| T2, auf den 16 Kalibrierfällen trainiert | – | 14/32 | **20/32** |

Die Anzahl proxyintern tatsächlich verspäteter Antworten hängt in
beiden getrennten Testserien deutlich von der vorbereiteten
Sendeposition ab. Im Bestätigungslauf hatten an Position 1 **8/8**
positive Gruppen Fallback, an Position 4 **3/8**. Eine balancierte
Permutation der Positionslabels ergab für die gesamte 4×4-Tabelle
der späten Antwortzahlen einen Monte-Carlo-Wert von **0,00038**
(100.000 Permutationen). Das ist eine mechanistische Assoziation
aus internen Logs, **kein** Angreiferfeature.

Der Client kann manche Fallbacks an einer großen Lücke zwischen
vollständigen Antworten erkennen. Die auf der Kalibrierung gesetzte
Regel „größter Empfangsabstand >10 ms“ erkannte im ersten Holdout
**20/28** Gruppen mit Fallback ohne Fehlalarm und im Bestätigungslauf
**23/27** ohne Fehlalarm. Sie erkennt Fallback **nicht** immer:
späte Antworten können während der seriellen Ausgabe der ersten
Teilgruppe eintreffen. Der stärkere T2-Beobachter nutzte deshalb alle
vier Clientzeiten und traf im vor der Bestätigungsserie festgelegten
Test **20/32** Positionen (Balanced Accuracy 0,625; Wilson 95 %
**0,453–0,771**; Zufallserwartung 8/32). R1 traf 14/32,
T1 nur 10/32. Die T2-Auswahl erfolgte **nach** Sichtung des ersten
Holdouts; allein die zweite Serie ist hierfür bestätigend. Die
Wilson-/Binomialwerte setzen unabhängige Durchläufe näherungsweise
voraus; wiederholte Messungen auf einem Server und die in beiden
Testserien identische Fallfolge begrenzen die statistische
Übertragbarkeit. Die T2-Bestätigung ist unabhängig im Sinne frischer
Salts, eines neuen Serverstarts und ungesehener Antwortdaten, jedoch
kein Test auf neuer Fallfolge.

**Schluss:** Der feste Slot glättet das einfache Merkmal T1 nur in
einem Bereich, in dem Antworten rechtzeitig fertig sind. Sein
Fallback kann erneut Ränge und mehrere Clientzeiten preisgeben.
Das ist ein beobachteter Ausfallbereich der **konkreten Regel**, keine
allgemeine Widerlegung jedes festen Zeitplans. Ein echter Schutz
müsste die Behandlung verspäteter Antworten ausdrücklich in sein
Bedrohungs- und Verfügbarkeitsmodell aufnehmen.

## 6. Individuelle Schutzkosten und fairer Vergleich

Alle Kosten unten sind pro **vollständiger Antwort** gemessen.
Proxy-Zusatzwartezeit = Freigabebeginn minus vollständiger
Backend-HTTP-Eingang; End-to-End = Clientempfang minus Clientversand.
Es gibt keine belastbare Durchsatzmessung und keine Interpretation
eines 99. Perzentils aus diesen kleinen Serien.

| Live-Regel / Serie | Antworten | Proxy-Wartezeit Median / P95 / Maximum, ms | Client-End-to-End Median / P95 / Maximum, ms | Vollständige Gruppen / Fallback |
| --- | ---: | ---: | ---: | ---: |
| Direkt, Hauptserie 16 Tokens | 272 | 0,027 / 0,053 / 0,076 | 840,616 / 905,440 / 950,377 | – |
| BOS W=4, Hauptserie 16 Tokens | 272 | 42,472 / 228,223 / 246,716 | 883,469 / 938,284 / 975,148 | 68/68 |
| Ziel 100 ms, Hauptserie 16 Tokens | 272 | 74,281 / 94,858 / 95,033 | 906,962 / 958,432 / 991,480 | 4/68 volle Gruppen; alle 64 vorbereiteten Antworten einzeln |
| Ziel 250 ms, Hauptserie 16 Tokens | 272 | 41,549 / 228,276 / 235,571 | 885,475 / 941,390 / 981,709 | 68/68 |
| Slot, bereinigte Serie 16 Tokens | 272 | 210,479 / 373,253 / 385,679 | 1039,570 / 1057,745 / 1058,229 | 68/68; 0 Fallback |
| Slot, Holdout 24 Tokens | 144 | 16,645 / 192,669 / 205,330 | 1044,448 / 1094,743 / 1123,363 | 8/36; 28 Gruppen mit Fallback |
| Slot, Bestätigung 24 Tokens | 144 | 17,728 / 191,770 / 203,021 | 1046,034 / 1091,804 / 1124,994 | 9/36; 27 Gruppen mit Fallback |

Die ersten vier Regeln wurden in **einer** Hauptserie verschachtelt;
der Slot stammt aus einer späteren Serie. Absolute End-to-End-Mediane
über diese Sitzungen dürfen nicht als gepaarter Overhead gelesen
werden. Innerhalb der bereinigten 16-Token-Serie wartete die
vorbereitete Antwort unter BOS W=4 median **190,62 ms**, unter
dem Slot **363,24 ms**; 172,62 ms sind die **Differenz zweier
Gruppenmediane**.

Für einen gepaarten Vergleich wurden alle fünf Regeln auf **dieselben
204 Backend-Eingangsfolgen** der bereinigten Serie idealisiert
angewendet (insgesamt 816 Antworten). Die Replay-Regeln bilden
Blockvollständigkeit und Timeout ab: Timer bei 100/250 ms wird im
aktuellen Code 10 ms vorgezogen; Slot bei 1.050 ms nach erster
Proxy-Ankunft; späte Slot-Antworten sofort einzeln. Gegen die
zugehörigen Live-Modi stimmte das Batchmuster **204/204** Mal,
im Hauptlauf **272/272** Mal; tatsächliche Freigaben lagen
median 2,4–3,8 ms nach der idealisierten Bereitstellung und
höchstens 7,6 ms danach. Das Replay lässt Python-Timerstreuung,
serielle HTTP-Ausgabe und eine mögliche Rückkopplung auf die
Backendverarbeitung weg. Seine Zahlen sind **modellierte
Bereitstellungswartezeiten**, keine zusätzlichen Live-Messungen.

| Ideales Replay auf denselben 204 16-Token-Traces | Median aller individuellen Wartezeiten | Median der vorbereiteten Antwort | Volle Gruppen | Späte Slot-Antworten |
| --- | ---: | ---: | ---: | ---: |
| Direkt | 0,00 ms | 0,00 ms | – | – |
| BOS W=4 | 40,39 ms | 188,33 ms | 204/204 | – |
| Ziel 100 ms | 70,35 ms | 90,00 ms | 12/204 | – |
| Ziel 250 ms | **40,39 ms** | **188,33 ms** | **204/204** | – |
| Fester Slot | 204,30 ms | 358,80 ms | 204/204 | 0 |

In **allen** 204 gepaarten Traces kamen die vier Backendantworten
innerhalb des vorgezogenen 240-ms-Fensters an. Die 250-ms-Regel ist
hier daher **identisch zu vollem BOS**, kein unabhängiger
Schutznachweis. Der Median der **individuell gepaarten** Differenzen
Slot minus BOS für die vorbereitete Antwort beträgt **161,22 ms**;
die Differenz der beiden vorbereiteten Gruppenmediane beträgt
**170,47 ms**. Diese Werte sind ausdrücklich verschieden. Auf den
24-Token-Fallback-Traces sank die idealisierte Slot-Wartezeit
der vorbereiteten Antwort auf median 181,37 ms, weil späte
Antworten sofort freigegeben wurden; das ist ein **Verlust des
Schutzes**, keine kostenlose Verbesserung. Beobachtete Maxima
begründen keine harte Verzögerungsgarantie eines Python-Timers.

### Schutz-Kosten-Grenze im tatsächlich geprüften Bereich

| Regel | Stärkster reproduzierter Clientbeobachter | Restinformation | Kosten / Grenze |
| --- | --- | --- | --- |
| Direkt | R1 | 64/64 Cachepositionen in C0-Hauptserie | Fast keine Proxy-Wartezeit |
| BOS W=4 | T2/T1 | Deutlich über Zufall in getrennten C0-Sitzungen | Früh fertiggestellte Antwort ~191–194 ms zusätzlich; keine Wartegrenze bei fehlenden Gruppenmitgliedern |
| Ziel 100 ms | R1 | 64/64; vorbereitete Antwort allein | Gemessen maximal 95,03 ms Zusatzwartezeit, keine harte Grenze |
| Ziel 250 ms | T1/T2 | Wie voller BOS, da alle getesteten Gruppen vor Timeout vollständig waren | Ähnliche Kosten wie BOS; keine unabhängige Schutzwirkung belegt |
| Fester Slot, 16 Tokens | Kein getesteter einfacher Beobachter stabil über Zufall | Nur das untersuchte Merkmal geglättet, keine Sicherheitsgarantie | Höhere Wartezeit, kein Fallback in diesem Bereich |
| Derselbe Slot, 24 Tokens | T2 in getrennter Bestätigung | 20/32 vorbereitete Positionen erkannt | 27/36 Gruppen mit Fallback; Kosten sinken durch vorzeitige Einzelfreigabe |

Die Tabelle ist **keine** globale Pareto-Grenze: nicht alle Regeln
haben dieselben Last- und Promptbedingungen als Live-Paar durchlaufen,
und stärkere adaptive Beobachter bleiben möglich. Unter dem lokalen
16-Token-Szenario ist die 250-ms-Variante gegenüber BOS nicht
unterscheidbar; die 100-ms-Variante senkt einen Teil der Wartezeit,
gibt aber den Rangschutz auf. Der Slot hat einen deutlich höheren
Preis, und sein Vorteil gilt nur innerhalb der beobachteten
Fertigstellungszeitspanne.

## 7. Literaturabgrenzung

| Primärtext, Lesestatus heute | Für den Claim geprüfter Kern | Grenze unserer Aussage |
| --- | --- | --- |
| Eigene [ICCAI-2026-Arbeit](../references/iccai2026-completion-order.pdf), **L3**, §§2–6; [DOI](https://doi.org/10.1145/3821244.3821268); [ordleak-Code](https://github.com/TheBuccaneer/ordleak/tree/2dad2ecb3116f4826f234d0da550dd83bfdfb474), **L2** | Rangfolgen allein, ODS-AUC, CPU-/Speicher-/KDF-Last unter enger Core-Koresidenz; BOS-Windows bis 16. CPU/MEM-AUC bei W=4 noch 0,750, bei W=16 0,449. Gesamtlaufzeit unter Angriffslast ±0,1 %, aber keine individuellen Antwortwartezeiten. §5 nennt AI-Serving nur als mögliche Anwendung. | Unsere LLM-/Cache-Experimente mit vollständigen Antworten, erlaubten Clientzeiten, Blockschluss-Zeitkette, individuellen Schutzkosten und Slot-Fallback sind nicht dort untersucht. BOS selbst und allgemeines Timing-Leakage bleiben Vorarbeit. |
| [PROMPTPEEK, NDSS 2025](https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf), **L2**, §III–IV und Ergebnisse | LPM-Warteschlange, Kandidaten/Dummies und Antwortreihenfolge als Cachekanal. | Reihenfolgeleakage und Promptrekonstruktion sind bekannt; unser FCFS-/Chunked-Prefill-Aufbau und Schutzpilot sind enger. |
| [OptiLeak v1](https://arxiv.org/html/2602.20595v1), **L2**, §3.1, §4.2, §6 | Stärkeres Positionsfeedback und optimierte Kandidaten, unter SGLang/LPM. | R2 als Idee ist keine neue Angreiferklasse. |
| [Mitigating Timing Side Channel in Shared Schedulers](https://arxiv.org/pdf/1302.6123), **L2**, §V–VI | Accumulate-and-Serve und allgemeiner Verzögerungs-/Privatsphäre-Konflikt. | Keine Übertragung der dortigen formalen Garantie auf diesen Proxy. |
| [Pacer, USENIX Security 2022](https://www.usenix.org/system/files/sec22-mehta.pdf), **L2**, §2–4 und §6 | Sichtbarer Zeitplan muss geheimnisunabhängig sein, einschließlich realer Abweichungen. | Feste Ausgabe und die Gefahr sekretabhängiger Fallbacks sind als Prinzip bekannt. |
| [NetShaper, USENIX Security 2024, Vorab-PDF](https://www.usenix.org/system/files/sec24summer-prepub-168-sabzi.pdf), **L2**, §3–5 | Formal konfigurierte Traffic-Shaping-/Latenzkosten für Netzverkehr. | Unsere Messung liefert weder DP noch eine allgemeine Schutzgarantie. |
| [SafeKV v2](https://arxiv.org/html/2508.08438v2), **L2**, §2, §6–7 | Cache-Freigabe/Isolation und TTFT-basierte Unterscheidbarkeit. | Andere Schutzfläche als das Mischen vollständiger Antworten. |

Die Quellen stützen **keine** Neuheit von Cachekanälen, BOS-Mischen,
Deadline-Pufferung oder festem Traffic Shaping an sich. Die mögliche
Erweiterung ist eine **LLM-spezifische, individuell gemessene
Kombination** aus (a) Freigabe beim vollständigen Blockschluss,
(b) residualem Vierklassen-Clientzeitkanal, (c) kollabierendem
100-ms-Block und (d) erneutem Leck beim tatsächlichen Slot-Fallback.
Gegenüber der eigenen Vorarbeit ist diese eng gefasste Erweiterung
belegt: Dort verwendet der Angreifer absichtlich keine Zeiten;
„vernachlässigbarer Overhead“ meint eine Gesamtlaufzeitmessung,
nicht die Verzögerung einer einzelnen Antwort. BOS war dort auch
kein universeller Rangschutz: Beim kleineren W=4 blieb die
CPU/MEM-ODS-AUC 0,750. Unsere neue Frage ist, **welche Clientzeiten
und individuellen Kosten nach der Freigabemischung übrig bleiben**.
Das ist ein möglicher zusätzlicher Erkenntnisbeitrag, dessen breitere
Neuheit und Relevanz außerhalb der lokalen C0-Bedingung noch geprüft
werden müssen.

## 8. Paper-Entscheidung und Rangfolge

### Rang 1: Residual Leakage after Order Scrubbing

1. **Problem:** Ein Dienst mischt vollständige Antwort-IDs und behauptet
   damit möglicherweise mehr Schutz, als der beobachtbare Zeitplan trägt.
2. **Zusätzliche Erkenntnis in einem Satz:** Bei vollständigen
   LLM-Antworten kann BOS die Ranginformation unterdrücken, während
   der vom Cachezustand beeinflusste Blockschluss als Clientzeit
   sichtbar bleibt; die zeitliche Entkopplung hat messbare Kosten
   und einen Fallback-Gültigkeitsbereich.
3. **Engste Vorarbeit:** Eigene ICCAI-2026-BOS-Arbeit; Pacer/Accumulate
   für die allgemeinen Zeitformungsprinzipien; PROMPTPEEK/OptiLeak
   für den LLM-Reihenfolgekanal.
4. **Stütze:** Vollständige Proxy-Zeitkette, 2.720 nachgerechnete
   Antworten, 53/64 und 41/64 clientseitige Zeitregeln, gepaarte
   Kosten, zusätzlicher Fallback-Befund nach Serverneustart;
   die eigene Vorarbeit schloss Zeiten ausdrücklich aus.
5. **Dagegen:** Starker Vierklassen-Basiskanal bisher nur C0;
   frühe Zeitregel nicht sicher prospektiv; reale Dienstlast fehlt.
6. **Noch nötig:** Mindestens ein weiterer realitätsnäherer
   Serving-/Netz- oder Lasttest mit neu randomisierter Fallfolge
   vor einer allgemeinen Sicherheitsbehauptung.
7. **Aufwand:** Mittel; die reproduzierbare lokale Infrastruktur
   steht, aber externe Generalisierung ist nicht billig.
8. **Kleinster Entscheidungstest:** C0 mit kontrollierter
   Mehrnutzerlast und vorab eingefrorenem T1/T2-Beobachter.

### Rang 2: The Limits of Fixed-Time Release

1. **Problem:** Ein fester Slot sieht sicher aus, bis Antworten
   den Slot verfehlen und der Dienst dennoch antworten muss.
2. **Zusätzliche Erkenntnis in einem Satz:** Schon eine für alle
   Probes gleiche Verlängerung von 16 auf 24 Ausgabetokens verschob
   diesen lokalen Slot von voller Gruppenfreigabe zu häufigem,
   positionsabhängigem Fallback und erneuter Clientklassifikation.
3. **Engste Vorarbeit:** Pacer und NetShaper zur Behandlung
   geheimnisabhängiger Zeitabweichungen; eigene BOS-Freigabeidee.
4. **Stütze:** 28/36 und 27/36 Fallback-Gruppen nach zwei Neustarts;
   T2 14/32 und bestätigte 20/32; Proxy-/Client-Abgleich.
5. **Dagegen:** Der Fallback ist eine einfache lokale
   Implementierungsentscheidung; die allgemeine Gefahr ist in
   Traffic-Shaping-Arbeiten bereits angelegt.
6. **Noch nötig:** Mindestens eine zweite, sinnvoll entworfene
   Fallback-Politik und stärkere Last-/Antwortlängenvariation,
   bevor daraus eine eigenständige Designarbeit wird.
7. **Aufwand:** Mittel bis hoch für einen separaten Paper-Claim.
8. **Kleinster Entscheidungstest:** Eine alternative späte
   Freigaberegel auf denselben Traces und ein kleiner Live-Abgleich.

### Rang 3: Scheduling-Dependent Leakage in LLM Services

1. **Problem:** Reihenfolgekanäle werden leicht von einer
   Scheduler-Konfiguration auf andere übertragen.
2. **Zusätzliche Erkenntnis in einem Satz:** Die explizite
   Prefill-Kappung erzeugte unter C0 einen starken Viererkanal,
   während C1 ihn stark abschwächte und C2 ihn im getesteten
   Viererdesign nicht zeigte, obwohl Cache-Hits weiter bestanden.
3. **Engste Vorarbeit:** PROMPTPEEK/OptiLeak zu LPM,
   vLLM-Scheduler-Dokumentation und bekannte Cache-Timing-Arbeiten.
4. **Stütze:** C0 64/64 direkt, C1 26/64 über zwei Starts,
   C2 8/32; C1-BOS 6/16 Zeitklassifikation im Holdout;
   neuer Promptsatz C0 64/64.
5. **Dagegen:** Nur drei gezielte Einstellungen, ein Modell
   und ein Rechner; die intern ausgeführten Scheduler-Schritte
   wurden nicht getraced.
6. **Noch nötig:** Instrumentierter Scheduler-Trace und wenige
   weitere modell-/lastbezogene Kontrollen für einen eigenen
   Systems-Beitrag.
7. **Aufwand:** Hoch für eine generalisierende Konfigurationsarbeit.
8. **Kleinster Entscheidungstest:** Instrumentierter Vergleich
   eines C0- und C1-Durchlaufs mit denselben vier Anfragen.

**Empfehlung:** Richtung 1 als Papergerüst beginnen; Richtung 2 ist
ein notwendiger Ergebnisteil, Richtung 3 begrenzt das Bedrohungsmodell
und verhindert Überverallgemeinerung. Der vorläufig verteidigbare
Beitragssatz lautet: *Für vollständige LLM-Antworten zeigt eine
kontrollierte vLLM-Studie, dass blockweise Rangmischung einen
cacheabhängigen Freigabezeitpunkt übrig lassen kann; ein an
Anfrageeingang gebundener Slot glättet dieses Merkmal nur innerhalb
seines rechtzeitigen Fertigstellungsbereichs und verursacht
messbare individuelle Wartezeit.* Dies ist **vorläufig** und
beansprucht keine formale Geheimhaltung.

## 9. Nur noch entscheidungsrelevante offene Punkte

- Prospektiv festgelegter Angreifer auf unabhängiger, weniger
  künstlicher Last-/Serving-Bedingung mit neuer Fallfolge. Die
  bisherigen C0-Werte sind lokal; C1/C2 begrenzen den Vierklassenkanal.
- Behandlung verspäteter Antworten durch eine alternative
  Freigaberegel, falls Richtung 2 zum eigenständigen Claim werden soll.
- Tatsächliche Antwortgröße in Bytes und interner
  Modell-Fertigstellungs-/Scheduler-Trace, falls der kausale
  Mechanismus über die Proxy-Zeitkette hinaus behauptet werden soll.

## Nachvollziehbarkeit und Messrahmen

Die neuen Programme sind `src/decision_validation.py`,
`src/config_transfer_pilot.py`, `src/observer_compare.py`,
`src/analyze_config_transfer.py`, `src/analyze_slot_fallback.py`,
`src/offline_gate_replay.py` und `src/summarize_live_costs.py`;
der vorhandene `src/bos_pilot.py` erhielt nur optionale
Tokenzahl und Kontrollzahl (alte Standardwerte 16 und 4).
Messreihen, Seeds und Serverlogs liegen in
`results/decision-validation-20261102/`; die ursprünglichen
BOS-Rohdaten verbleiben in ihren bisherigen Verzeichnissen.
Neue Vierer-Durchläufe: **144** zur Konfiguration einschließlich
des C1-BOS-Entscheidungstests, **72** zu neuen Promptinhalten und
**92** zum Slot-Fallback, zusammen **308/320** des erlaubten
Gesamtrahmens. Alle Resultate wurden in neuen Dateien angelegt.
Nur ein Modell, eine GPU und ein Betriebssystem wurden verwendet.
