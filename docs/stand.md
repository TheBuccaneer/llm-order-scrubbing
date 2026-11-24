# Projektstand

Stand: 05.11.2026

## Aktuelle Etappe

**C2-Lasttest abgeschlossen: Ergebnis B und unabhängig D. Forschung für C1/C2 beendet.**
Alle 24 Warm/Kalt-Paardifferenzen sind positiv: erste vollständige
B-Antwort kalt minus warm median 100,73 ms, geschichtetes 95-%-
Paarbootstrapintervall 87,14–107,26 ms, exakter Vorzeichentest
p=5,96×10⁻⁸. Der Effekt bleibt unter dem einen festen C-Lastprofil.
Beide alten Klassifikatoren nennen jedoch alle 48 Hauptfälle „kalt“:
BA jeweils 50 %, zugleich AUC jeweils 1,00 mit unveränderten Scores.
Das ist verlorene Kalibrierung bei erhaltener Ranginformation, kein
Verschwinden des Seitenkanals. Beide Beobachter nennen auch alle acht
Abwesenheits- und acht andere-kalte-Kontrollen „kalt“; keine eindeutige
Dokument- oder Anwesenheitsinferenz.

64/64 Messfälle vollständig, 256 B-Antworten ohne Hits; A warm544/kalt0.
C verarbeitet jeweils 548 Prompt- und 256 Ausgabetokens. In allen 64
Fällen C-Fortschritt bereits vor der ersten B-Vollantwort; keine
Behauptung gleicher tatsächlicher GPU-Auslastung. Keine Messfehler,
Timeouts oder Ersatzfälle. Alle 956 vorherigen Ergebnisdateien und
eingefrorenen Quellen/Beobachter unverändert; Backend/Proxy beendet.

Bericht: `docs/tenant-hintergrundlast-20261105.md`.
Daten: `results/tenant-background-20261105-02/`, aktiver Vorabcommit
`64086bd3ea75e793655849382b07d2b53a3f0f2c`. Der erste Freeze `b39ac44`
scheiterte bei sieben Backendstarts vor Modellladen und jeglicher
A/B/C-Messung am zu langen IPC-Pfad. Alle Fehlstarts bleiben unter
`...-01` erhalten; zwei Protokollfassungen ausdrücklich dokumentiert.
Nur temporärer Pfad korrigiert, gleiche 64 Fälle, Last und Modellbytes;
keine erhobene Kohorte wiederholt. Kein Push.

C1 ausschließlich offline ergänzt: alle 72 alten vollständigen BOS-Blöcke
geben erst nach dem letzten Backendempfang am Proxy frei; Abstand zum
ersten Clientempfang median 0,542 ms, kein weiterer C1-GPU-Test.
Artefakt: `paper/c1-proxy-mechanism-20261105.json`.

**Nächster verbindlicher Schritt:** fünfseitiges englisches ICCAI-Paper
mit C1/C2 als Hauptbeiträgen schreiben und im offiziellen Format setzen.
Aktuelle Planung: `paper/short-paper-plan-20261105.md` (fünf zweispaltige
Seiten einschließlich Referenzen). Keine neue Explorationsphase,
Lastprofile, Angreifer oder Forschungstests. C3 bleibt als vorhandenes
Implementierungs-/Kostenresultat erhalten, kein dritter Hauptbeitrag.

### Vorheriger Abschluss: C3-Positivkontrolle

**Abschließende C3-Positivkontrolle bestanden; experimentelle Arbeit beendet.**
Die neue Policy `direct` verwendet den unveränderten C3-Piloten mit
512/2048 und nativen privaten Cachetreffern, ohne Schutz oder Verzögerung.
Zwölf neue Trainings- und 24 Prüfpaare, Plan vor GPU-Start gespeichert,
Modelle und Skalierung vor der Prüfserie eingefroren. T1 und T2 treffen
beide 48/48 Prüfkohorten, BA=AUC=1; gemeinsamer Paar-Labeltausch-p=0,000200.
Erste B-Latenz kalt minus warm im Mittel 113,39 ms, nominales
95-%-Paarbootstrapintervall 103,96–123,03 ms; alle 24 Differenzen positiv.

72/72 Kohorten, 360 vollständige Antworten, keine Fehler oder fehlenden
Antworten. A tatsächlich warm544/kalt0, alle 288 B-Antworten ohne Hits.
Direct hat keine Join-Deadline, daher kein definierter Overrunendpunkt.
Alle Quellen/Snapshots, Prompts und 900 alte Ergebnisdateien unverändert;
GPU-Engine beendet, kein Push. Vergleich und methodische Unterschiede:
`docs/protected-prefill-prototyp-20261103.md`, neuer Datensatz
`results/protected-prefill-direct-20261104-01/`.

**C3-Entscheidung:** ungeschütztes Signal für die eingefrorenen Rezepte
belegt; Protected Prefill bleibt Implementierungs-/Normalisierungs- und
Kostenfallstudie mit beobachterbezogener Einordnung. Alte Schutzintervalle
bleiben breit, alte Policies wurden nicht gleichzeitig neu gemessen;
keine Timing-Sicherheitsgarantie aus der Positivkontrolle ableiten.

**Nächster verbindlicher Schritt:** englisches Paper schreiben und im
offiziellen ICCAI-Format auf bis zu zehn einspaltige Seiten inklusive
Referenzen setzen. Keine weitere Forschungsmessung oder Schutzentwicklung.

### Vorherige Etappe: Manuskriptstruktur

**Manuskriptphase: weitere Protected-Prefill-Entwicklung gestoppt.**
Die ausgearbeitete Struktur steht in
`paper/manuskriptstruktur-20261103.md`: drei empirische Contributions mit
Evidenz, engster Vorarbeit und Geltungsgrenzen, ein Budget für acht
einspaltige ACM-Seiten inklusive Literatur, zwei Tabellen und drei aus
vorhandenen Daten erzeugte Abbildungen unter `paper/assets-20261103/`.

Paperlinie: (1) vollständige Clientzeiten können nach BOS informativ
bleiben; (2) getrennte Cache-Salts verhindern den konditionalen
Konkurrenz-Zeitkanal im geprüften Szenario nicht; (3) die normalisierte
Protected-Prefill-Konstruktion spart im konfigurationsgleichen warmen
Vergleich Ausführungsintervall, erhöht aber individuelle Antwortlatenz.
Der logische Beweis ist unterstützend, keine Timing-Sicherheitsgarantie.
Keine allgemeine neue Angriffsmethode oder überlegene Verteidigung behauptet.

Die Abbildungen verwenden nur vorhandene Analysen und Rohdaten; keine
neuen Messungen, Beobachterfits oder Unsicherheitsschätzungen. Ihre
Eingänge sind mit SHA-256 im Manifest gebunden, die PNGs visuell geprüft.
Die textliche T1-Fehlerbeschreibung im Zeitfensterbericht wurde anhand der
vorhandenen Konfusionsmatrix korrigiert: zwei warme Fälle als kalt,
nicht umgekehrt. Messdateien bleiben unverändert.

**Nächster Schritt:** englisches Manuskript schreiben und Satzumfang
prüfen, ohne weitere Forschungsexperimente zur Voraussetzung zu machen.

### Vorheriger Stand: formaler Vertrag

**Quellcodegebundene logische Nichtinterferenz hergeleitet.** Kompakter
Bericht: `docs/protected-prefill-nichtinterferenz-20261103.md`.
Der Satz betrifft B-Antwortzuordnung und logische gemeinsame
Decodeentscheidungen erfolgreicher, fehlerfreier geschlossener Kohorten
im expliziten funktionalen Backendmodell. Er setzt Gleichheit am Join
nicht voraus: isolierte B-Ausführung, Snapshot/Clear/Scatter, frische
KV-Manager, feste Kapazitäten und Workerinstallation stellen die benötigte
B-Projektion her. As private Nutzdaten müssen für diesen Satz nicht gleich
sein. Kontrollierte Cacheherkunft und gleiche Rechenform liefern im Modell
zusätzlich die stärkere aktive KV-Normalform.

**Keine reale Timing-/HTTP-Reihenfolge- oder Fehler-Nichtinterferenz
bewiesen.** Warm kann die Frist einhalten, kalt bei gleicher Zusatzlast
abbrechen; Erfolg gegen 500 ist sichtbar. Ein explizites Gegenbeispiel
und die fehlende cacheunabhängige Laufzeit-/Admissioninvariante sind
dokumentiert. Ein einheitlicher Fehlertext oder späterer Fehlertermin
repariert diesen Unterschied nicht. Produktive adaptive Zusatzanfragen
während Decode sind nicht implementiert; nur ordnungsgemäße Wiederholung
nach Reset mit logischen Beobachtungen fällt unter die Induktion.

CPU-Prüfer `src/protected_prefill_contract_checks.py` und Ergebnis
`results/protected-prefill-contract-20261103/checks.json`: echte KV-Manager
und echter Kopierkörper auf CPU, getrennte A-Payloads/Quelladressen,
gleiche kanonische B-Werte aller 28 Schichten, gelöschte Restbereiche;
echte Stop-/Deadlineguards geprüft. Unterstützende Instanzen, keine
Maschinenverifikation der GPU-Bibliotheken. Keine Produktionskorrektur,
kein neuer Scheduler und keine GPU-Serie; alte Rohdaten unverändert.

Vier engste Originaltexte gezielt nachgeprüft: Time Protection, IFS,
Predictive Mitigation und SafeKV. Möglicher Beitrag ist der konkrete
hinreichende vLLM-Wiedereintrittsvertrag. Weder notwendige/minimale
Kanonisierung noch neue allgemeine Timingabwehr nachgewiesen; globale
Neuheitsentscheidung bleibt offen. SIDE weiterhin L1.

### Abgeschlossene CUDA-Hardwareentscheidung

**CUDA-Hardwareentscheidung abgeschlossen: kein Zweirunner-Scheduler.**
Der vorab fixierte Minimalpilot unter
`results/protected-prefill-cuda-20261103-01/` verwendet die echten
Eager-Forwardformen A512/A36 und B2048/B144 bei einmal vorhandenen
Qwen-Gewichten, geklonten Eingaben/Attention-Metadaten und zwei Streams.
Kein zweiter Scheduler, keine Graph- oder Parametersuche.

Zwölf kalte Paare: seriell Mittel 618,15 ms, parallel 571,66 ms;
Gewinn 46,49 ms, einseitige 95-%-Untergrenze 40,10 ms. Sechs warme Paare:
490,98/480,84 ms, Gewinn 10,14 ms. Gefordert waren mindestens 66 ms
plus vorab gewählte 20 ms Reserve. Maximaler kalter Parallellauf 589,28 ms
passt zudem nicht unter das 589,43-ms-Joinlimit zuzüglich Integration,
Normalisierung und Reserve. **Hardwaregate nicht bestanden; keine
Implementierung der Zwei-Runner-Konstruktion begonnen.**

Alle 36 Replays liefern bitgleiche aktive KV-Daten aller 28 Schichten
und Frontier-Logits, warm/kalt sowie seriell/parallel. Gemessen ist reale
Dauer inklusive Eager-Host-Enqueue, Synchronisierung und Konkurrenz;
vollständiger Scheduler/CPU-Sampler/KV-Normalisierung sind noch nicht
enthalten. Diese zusätzlichen Kosten würden den Befund nicht verbessern.
Die funktionierende ursprüngliche Normalisierung und der frühere private
Rechenvorteil bleiben erhalten. Keine weitere Architektur oder Messserie
begonnen; alte Rohdaten/Enginequellen unverändert, GPU-Engine beendet.
Tabelle, Messgrenzen und Reproduktion im bestehenden Prototypbericht.

### Vorherige Offline-Konstruktionsprüfung

**Kritischer Pfad analysiert, keine neue Implementierung oder GPU-Messung.**
Die 72 vorhandenen geschützten Gate-Traces sind offline zerlegt unter
`results/protected-prefill-critical-path-20261103/`. Mit unveränderten
seriellen Operationskosten bleiben selbst nach optimistischem Streichen
aller Leerlauf-/Steuerungslücken 929,74 ms ab Epoch bzw. ungefähr 926,57 ms
eigener B-Latenz. Das reicht nicht gegen Ignore-Hits warm 910,87 ms.
Dies ist ein Trace-Replay im vorhandenen Kostenmodell, keine allgemeine
Hardwareuntergrenze. Ein früherer 512-Token-Join verschiebt 180 gemeinsame
Suffix-Tokens auf denselben Antwortpfad; kein belegter 110-ms-Gewinn.

**Konkrete Bauhypothese:** A und B in zwei getrennten Prefill-Runnern auf
getrennten CUDA-Streams innerhalb eines geschlossenen geschützten Fensters
starten; unveränderte Modellgewichte teilen, anschließend beide drainen,
kanonisch normalisieren und vollständige Workerzustände zusammenführen.
Öffentlicher Join müsste bei höchstens 589,43 ms liegen. Dafür sind nach
alten Operationskosten 31–66 ms effektive Überlappung nötig, zuzüglich
Reserve und neuer Orchestrierungskosten. Der existierende einzelne Runner
ist wegen `execute_model_state`, veränderlichem Inputbatch und globalem
Forwardkontext dafür ungeeignet; separater Runnerzustand und kontrolliertes
Host-Enqueue sind der benannte Implementierungsweg.

Die alten Traces enthalten keine gleichzeitigen Kernel-/Belegungsdaten.
Die Abhängigkeitsstruktur erlaubt das Ziel, beweist aber die nötige
Hardwareüberlappung nicht. **Kein positiver Hardware-Machbarkeitsbefund;
entsprechend dem Auftrag noch nicht programmiert.**

Öffentliche Zweikohorten-Pipeline ebenfalls konkret gerechnet: zwei
geschützte Phasen bis 1400 ms, anschließend gemeinsames Zehner-Decode.
Für110 ms weniger Engine-Ausführungszeit je Kohorte müsste dieses
≤ 423,77 ms dauern (nicht gemessen). Dann etwa 1824/1124 ms individuelle
Latenz bei nur 912 ms mittlerem Serviceabstand. Das ist eine Kosten-/
Durchsatzalternative, kein belegter Latenzgewinn. Engine-Wallspannen sind
dabei keine isolierten CUDA-Kernelzeiten. Vollständiger Ablauf, Quoten,
vLLM-Eingriffspunkte und Annahmen im bestehenden Prototypbericht.

### Abgeschlossenes Contribution-Gate vor Konstruktionsprüfung

**Das konfigurationskontrollierte Contribution-Gate ist abgeschlossen,
insgesamt nicht bestanden.** Alle drei Verfahren nutzen jetzt dieselben
512-Token-Chunks, 2048-Token-Budgets und dieselbe Cachevorbereitung;
auch die gemeinsamen Decode-Einstellungen stimmen überein.
`results/protected-prefill-gate-20261103-01/` enthält den vorab fixierten
Plan und Quellcode, 216 neue Kohorten/1080 Antworten, trainierte Modelle
vor Testbeginn sowie Auswertung und Prüfnachweise. Je Verfahren zwölf
Trainingspaare und 24 getrennte Prüfpaare, keine Nachjustierung.

Auf den Prüfdaten warm: Protected Prefill A/B median 1024,69/1021,61 ms;
Ignore-Hits 912,94/910,87 ms, Release-only 784,63/1240,07 ms.
**Der frühere Latenzvorteil gegenüber Ignore-Hits bestätigt sich unter
gleicher Konfiguration nicht.** Warmer CUDA-Vorteil bleibt: 814,52 statt
922,82 ms, gepaarte mittlere Einsparung 107,99 ms, simultane einseitige
95-%-Bootstrap-Untergrenze 102,67 ms. Keine Energiemessung; kalt kein
CUDA-Vorteil gegenüber Ignore-Hits.

Beide neuen Zeitbeobachter bleiben trainiert eingefroren: geschützte
Test-BA 54,17/58,33 %, AUC 0,530/0,528. Gemeinsamer Permutationswert
p=0,595: kein signifikanter Kanal durch diese Beobachter. Die gemeinsame
Unsicherheitsobergrenze von BA/AUC liegt aber bei 0,215 statt unter dem
vorab verlangten Abstand 0,15 von Zufall. **Schutzgate unentschieden bzw.
nicht bestanden, keine Behauptung bewiesener Vertraulichkeit.**

Unveränderter Normalisierer erneut all-layer-bytegleich im Funktionspaar;
dieselben fünf Tokenfolgen in allen 72 geschützten Kohorten. 0/72 Overruns,
minimale Joinreserve 8,75 ms. Konfiguration, Normalisierung, beobachtete
Verfügbarkeit und warmer Rechenvorteil bestanden; gleichzeitiger Nachweis
von Beobachtungsarmut und Kostenvorteil bleibt offen. Konstruktion behalten,
keine neue Methode oder Parametersuche begonnen. Vollständiger Befund:
`docs/protected-prefill-prototyp-20261103.md`. 74 alte Rohdateien unverändert,
alle GPU-Engines beendet, kein Commit/Push.

### Abgenommene Zwischenoptimierung vor Konfigurationskontrolle

Die bestehende Konstruktion ist **strukturell beschleunigt**: öffentlich
feste 512-Token-Prefillblöcke reduzieren kaltes A und B von jeweils neun
auf zwei Modellaufrufe. Letztes B-Prefill und Normalisierung teilen ein
geschütztes Schlussfenster. Der öffentliche Join sinkt von **940 auf
700 ms**. Kein früherer Join nach Cachetreffern, keine bereite Teilmenge.
Der ausführbare Modus heißt `protected_block512` (`--block-prefill`).

Der neue GPU-Funktionstest `results/protected-prefill-block512-20261103-kv03/`
belegt erneut identische aktive KV-Daten aller 28 Schichten, kanonische
Metadaten und fünf gleiche Tokenfolgen warm/kalt bei 512 privaten Hits.
Der anschließende kleine Kostenvergleich unter
`results/protected-prefill-block512-20261103-pilot01/` umfasst 16 Kohorten,
80 Antworten und die drei festgelegten Vergleichsverfahren. B warm
median 1020,31 ms statt 1260,48 beim alten Schutz und 1240,07 bei
Release-only; A 1023,70 statt 766,40 bei Release-only. CUDA-Intervalle
inklusive Kopieren warm 814,98 statt 1203,14 ms bei Ignore-Hits.
Kein Vorteil für beide Mandanten gegenüber Release-only behauptet.

Die erste getrennte B-Frist von 650 ms scheiterte zweimal; die Reparatur
fasst B und Normalisierung innerhalb des unveränderten öffentlichen
J=700 zusammen. Pläne und Fehler bleiben erhalten, keine Nachjustierung
im anschließenden Kostenvergleich. Kleinste beobachtete Joinreserve
10,81 ms; Warm/Kalt-Zeitdifferenz von B weiterhin 3,70 ms. Keine allgemeine
Laufzeitschranke, Zeitvertraulichkeit oder Methodenneuheit bewiesen.
Vollständiger Befund und Reproduktion im bestehenden Prototypbericht.
Der HTTP-Adapter ist weiterhin auf dem bisherigen 940-ms-Stand.

### Abgenommener Ausgangsprototyp

Der **Protected-Prefill-/Shared-Decode-Prototyp ist implementiert und auf
der RTX 3090 ausgeführt**. Einstieg und vollständiger technischer Befund:
`docs/protected-prefill-prototyp-20261103.md`. Dateien:
`src/protected_prefill_scheduler.py`, `src/tenant_kv_partition.py`,
`src/protected_prefill_pilot.py` und der lokale HTTP-Server
`src/protected_prefill_server.py`. Keine installierten vLLM-Dateien geändert.

Konstruiert sind echte Tenant-KV-Pools (128/256 Blöcke), geschützte
Schedulerfenster, Parken bei 548 verarbeiteten Prompttokens plus einem
Ausgabetoken, echte kanonische GPU-KV-Kopie mit vollständigem
Metadatenneuaufbau, CUDA-Drain und Worker-Blocktabellenersetzung vor
gemeinsamem Decode. Die numerische Rechenform wurde repariert:
geschütztes A nutzt 512 statt 544 Cachetokens, damit warm und kalt
denselben letzten 36-Token-Chunk berechnen. Der GPU-Funktionstest
`results/protected-prefill-20261103-aligned-kv01/` weist identische
SHA-256 über aktive KV-Daten aller 28 Schichten sowie identische
Tokenausgaben aller fünf Requests nach. Kaltes A: 0 Treffer, warmes
A: 512; B jeweils 0. Echte KV-Manager-/Quotenchecks stehen ausführbar in
`src/protected_prefill_checks.py`.

Der korrigierte kleine Kostenpilot
`results/protected-prefill-20261103-pilot04/` enthält 16 Kohorten/80
Vollantworten; zwei Warm/Kalt-Paare pro Policy, keine neuen trainierten
Angreifer. Feste öffentliche Fenster aus früherem Smoke-Test, J=940 ms.
Warme geschützte Modellarbeit: 2303 statt 2815 Tokens bei Ignore-Hits;
CUDA-Inferenz plus Kopieren etwa 949 statt 1211 ms. B-Latenz warm median
1264,71 ms gegenüber Release-only 1240,08 ms; A 1268,02 gegenüber
773,93 ms. **Keine Latenzdominanz oder formale Vertraulichkeit behauptet.**
Metadaten-/Queue-/Frontier-/Workerprüfungen melden keine Fehler.

Der echte HTTP-Test unter `results/protected-prefill-20261103-http02/`
lieferte warm/kalt je fünf vollständige Antworten, gleiche Texte und
keine Cachezähler/fremden Datensätze an B. Getrennte lokale Rollen,
feste Intakekohorte und kontrollierte Cacheherkunft sind Teil des
Prototypvertrags. Die aktiven Bytes und logischen Zustände sind geprüft;
physische Mikrocache-/Takt-/Temperatur- und Host-Zeitunabhängigkeit ist
nicht allgemein bewiesen. Die dokumentierten früheren Auditurteile unten
gelten für den damaligen Stand vor dieser Implementierung.

### Vorheriger Stand vor der Implementierung

Die **Neuheitsprüfung ist noch nicht bis zu einer wissenschaftlich
abgegrenzten Methodenkandidatin abgeschlossen**. Die frühere Einordnung
des Entwurfs als bereits begründbare Kandidatin wurde korrigiert.
Der neue Forschungsauftrag zur Security-Systems-Erweiterung hat bislang
einen technischen Entwurf mit nicht belegter Methodenneuheit geliefert;
Entscheidung und Schutzvertrag stehen in
`docs/cache-state-oblivious-kandidatin-20261103.md`,
die Originaltextabgrenzung in `docs/security-novelty-matrix-20261103.md`.
Öffentliche Fenster, TDMA, selektiver Privacy-Schutz und Ausgabetimer sind
bekannt; neuheitsfähig wäre erst ein konkret begründeter und günstigerer
normalisierter Übergang von geschütztem Prefill zu gemeinsamem Decode.
Die zusätzliche enge Vorarbeit IFS (CCS 2021) ist berücksichtigt.
**SIDE ist nur L1:** Verlags-/Repositorysuche lieferte keinen Volltext,
auch der Nutzer hat keinen. Eine abschließende Abgrenzung bleibt offen.

Das Offline-Replay `src/tenant_release_feasibility.py` liest 240 alte
Gruppen / 960 B-Antworten ohne Rohdatenänderung. Protokoll:
`docs/tenant-release-replay-protokoll-20261103.md`; Ergebnisse, Eingabehashes,
Rechenkontrollen und Literaturfassungen:
`results/tenant-release-feasibility-20261103/`.
Alle Termine stammen nur aus alter Entwicklung. Auf dem Test mit
verborgenem A-Start deckt eine individuelle öffentliche 1240-ms-Frist
96/96 Antworten, kostet B median 222,58 ms Zusatzwartezeit und verzögert
A im festen B-only-Szenario nicht. Vier frühere öffentliche Termine
senken Bs Median auf 132,11 ms, erzeugen jedoch vier Spätantworten in
drei Fällen. Das belegt Kosten/Transfergrenzen, **keinen** Vorteil einer
neuen Enginepolicy und keine formale Vertraulichkeit. Die neu trainierten
Beobachter, Frontend-Zeitreste und kleinen Stichproben sind dokumentiert.

**Entscheidende Lücke:** Die vorgeschlagene Normalisierung ist nur
vorausgesetzt, nicht konstruiert; der bedingte Sicherheitsbeweis löst
sie nicht. Es fehlt ein gegenüber bekannten Bausteinen eigenständiger
Mechanismus oder eine neue scharfe Grenze. Eine zusätzliche einfache
Baseline ist gezielte Prefix-Neuberechnung; der installierte interne
`skip_reading_prefix_cache`-Pfad wurde lesend geprüft. Deren Leistungs-
und Sicherheitswerte sind ungemessen. Der Neuheitsauftrag bleibt offen,
unabhängig von der zusätzlichen SIDE-Volltextlücke.
Keine Verteidigungsimplementierung, kein neuer GPU-Lauf,
kein Commit und kein Push in dieser Etappe. Der alte empirische Bestand
bleibt erhalten. Die folgenden Abschnitte halten frühere Etappen fest.

Der **Audit-Entscheidungstest mit verborgener A-Startzeit** ist in
`docs/tenant-zeitfenster-20261103.md` dokumentiert; Rohdaten
unter `results/tenant-offset-20261103/`. Mit festen, getrennten
Benutzersalts und exakt gleichen A-Zielprompts über 24
frische Backend-Starts wurde As Zeitpunkt zwischen 0 und
450 ms vorab randomisiert und B verborgen. Der alte
T1-Angreifer traf 14/16 Warm/Kalt-Fälle, T2 16/16;
alle 8 gepaarten T1-Unterschiede hatten die festgelegte
Richtung. Bs Probes hatten weiterhin keine Cachetreffer.
Kontrollen ohne A-Zielanfrage sahen wie „warm“, andere
kalte A-Arbeit wie „kalt“ aus: Der Angriff erkennt daher
den Cachezustand **bei bekannter Zielanfrage**, nicht
selbstständig einen beliebigen fremden Dokumentzugriff.
Die Audit-Lücken Zeitlage und Prompt-Fallcode sind für
diesen engen Test adressiert; Anwendungswissen, Last und
Schutzkosten bleiben offen. Alle Prozesse beendet. Die
folgenden Abschnitte halten frühere Etappen fest.

Der lokale **Zwei-Benutzer-Pilot mit getrennten Cache-Salts** steht in
`docs/getrennte-salts-scheduler-20261103.md`; alle neuen Rohdaten
unter `results/tenant-scheduler-20261103/`. A hatte bei derselben
Zielanfrage 544 gecachte Tokens oder keinen Treffer; B hatte mit
eigenem Salt durchgehend **keinen** Cachetreffer. Dennoch trennten
Bs vollständige Antwortzeiten warm/kalt in der unabhängigen
Prüfung unter direkter Freigabe und BOS jeweils 32/32 Fälle,
auch bei einem festen Salt je Benutzer und Serverstart. Alle
16 gepaarten Prüfvergleiche pro Bedingung hatten die zuvor
festgelegte Richtung. BOS mischte die Ränge, behielt den
Zeitkanal und verursachte median etwa 47 ms individuelle
Proxy-Wartezeit (p95 etwa 193 ms). Das ist ein synchronisierter
Qwen/C0-/Loopback-Befund, keine Behauptung allgemeiner
Angreifbarkeit oder einer neuen Verteidigung. Die nächste
Forschungsentscheidung ist ein vorab budgetierter Vergleich
einer tenantbewussten Zulassungs-/Freigaberegel mit direkter
Freigabe, BOS und festem Slot; kein automatischer Ausbau.
Alle Messprozesse sind beendet. Die folgenden Abschnitte
halten frühere Etappen fest.

Die **Llama-3.1-8B-Instruct-Referenzvalidierung** ist abgeschlossen;
Bericht und Geltungsgrenzen stehen in
`docs/llama-referenzvalidierung-20261103.md`, Rohdaten unter
`results/llama-reference-20261103/`. Der lokale Cache-/Completion-
Kanal trat auch beim zweiten Modell auf. In der unabhängigen
BOS-Prüfung erreichte T2 21/32 (C0) und 14/32 (C1); die binäre
Blockschluss-AUC betrug 0,911/0,953. Bei synthetischen Dokumenten
verkürzte ein gemeinsamer öffentlicher Präfix den gepaarten
Client-Blockschluss median um 321,5/231,0 ms. Die eingefrorene
T2-Kalibrierung übertrug sich auf P1 schlecht; das ist kein
Schutzbeweis. Entscheidung: Llama als zweite Modellkontrolle in
das eng begrenzte empirische ICCAI-2027-Paper aufnehmen, ohne
eine allgemeine C1-Sicherheits- oder Neuheitsbehauptung. Alle
neuen Server und Proxies wurden beendet. Die folgenden Abschnitte
halten die vorherigen Etappen fest.

Der abschließende **Präfixstruktur-×-BOS-Pilot** vom 03.11. steht in
`docs/prefix-struktur-bos-20261103.md`. P0 beginnt mit vier
unterschiedlichen Dokumenten; P1 verschiebt 304 identische,
öffentliche Tokens an den Anfang. Über C0 → C1 → C1 → C0
liefen 128 positive und 16 Kontrollgruppen, alle 576 Antworten
vollständig. Unter P1 nutzten die drei nicht gezielt vorgewärmten
Kandidaten jeweils 304 Tokens statt 0; die erste BOS-Clientantwort
kam gepaart median 310 ms (C0) beziehungsweise 230 ms (C1)
früher. Ein zuvor auf P0 trainierter T2-Beobachter fiel unter P1
auf 8/32, aber P1-spezifische Kreuzstart-Kalibrierung erreichte
22/32 (C0) und 14/32 (C1). Der binäre Blockschlusskanal blieb
sichtbar (AUC 0,875/0,818). Entscheidung: als wichtige Ablation
im empirischen Paper verwenden, **nicht** als neuen Schutz-
oder Angriffsbeitrag. Weitere Exploration beenden und den
Manuskriptentwurf strukturieren. Alle neuen Prozesse beendet.

Der gegenbalancierte **Dokumentenanalyse-Pilot** vom 03.11. steht in
`docs/dokument-workload-20261103.md`. Vier synthetische technische
Dokumente ersetzen die alten künstlichen Prompts bei gleicher
548-Token-Länge. Über C0 → C1 → C1 → C0 und je 32 positive
BOS-Gruppen traf der zuvor trainierte T2-Beobachter unter C0
21/32, unter C1 13/32. Die vorab festgelegte Entscheidungshilfe
wurde erfüllt; ein gepaarter Unterschied ist bei dieser Größe
statistisch unsicher (exakter McNemar-p-Wert 0,134). Der binäre
Blockschluss bleibt unter C1 klar sichtbar (AUC 0,932). Alle 92
Gruppen/368 Antworten waren vollständig, Cachetreffer und volle
BOS-Blöcke wurden geprüft. Die vier Backend-Starts sind beendet.
Empfehlung: den engen Manuskriptentwurf beginnen und die
Schedulerwirkung nicht als allgemeine Informationsreduktion
formulieren.

Der **Scheduler-/BOS-Entscheidungstest** vom 03.11. steht in
`docs/scheduler-bos-entscheidung-20261103.md`. Auf gepaarter neuer
Fallfolge mit je 32 positiven BOS-Gruppen traf der vollständige
Clientzeit-Beobachter T2 unter C0 21/32 und unter C1 11/32.
C1 behielt einen binären Blockschluss-Rangkanal (AUC 0,813),
obwohl die vorher fixierte absolute 780-ms-Regel in einer getrennten
ersten C1-Sitzung scheiterte. Vier kurze instrumentierte Gruppen
zeigen, wie die unterschiedlichen Prefill-Schritte und gemeinsame
Decode-Schritte zu den Abschlussmustern passen. Ein fester Slot
glättete sie im **idealisierten Replay** gegen zusätzliche
individuelle Wartezeit; keine neue Freigaberegel wurde gebaut.
Empfehlung: ein eng begrenztes empirisches Nachfolgepaper zu
Information nach BOS, Schedulerabhängigkeit und Schutzkosten
entwerfen; noch keine allgemeine Sicherheits- oder Neuheitsgarantie.
Alle neuen Backend- und Proxyprozesse sind beendet.

Die prospektive C1-Direktprüfung vom 03.11. ist in
`docs/c1-cocompletion-20261103.md` dokumentiert. Die zuvor fixierte
Paarabstandsregel bestimmte in einer frischen, balancierten Serie mit
neuem Backend-Start die Cacheposition 32/32 Mal (95-%-Wilson-Intervall
89,3–100 %); R1 erreichte 11/32, T2 und RT je 31/32. Vier
unvorgewärmte Kontrollen zeigten keinen engen Antwortabstand.
Der Befund ist ein lokaler Mechanismuskandidat unter C1-Direktfreigabe,
kein Beleg für BOS-Leakage, allgemeine Übertragbarkeit oder höhere
Genauigkeit als T2. Alle 36 Gruppen und 144 Antworten sind vollständig;
Backend und Proxy sind beendet.

3 – Technische Optionen und Paper-Richtung bewertet. Der lokale BOS-
Mechanismus, seine Konfigurationsabhängigkeit, stärkere Clientbeobachter
und der Fallback eines festen Freigabeslots wurden in begrenzten,
getrennten Messsitzungen geprüft. Entscheidung und alle Grenzen stehen
in `docs/entscheidungsvalidierung-20261102.md`.
Der anschließende Release-Boundary-Test ist in
`docs/release-boundary-20261102.md` dokumentiert: neue Fallfolge,
32 C0-Positive (binäre Früh-/Spätposition 31/32), 16 C1-Positive
(8/16) und 16 markierte Cache-aus-Kontrollen (8/16). Die
Vierklassenregel verbessert T2/RT nicht. Empfehlung: als
Schutzgrenzen-Befund weiterführen, nicht als eigenständigen
Angriffsclaim.
Der nachfolgende Test einer **einheitlich späteren Freigabe nach
1.200 ms** steht in `docs/late-release-20261102.md`: 56/56
Vierergruppen einschließlich Kontrollen vollständig, 0 späte
Einzelfreigaben, im neuen 32er-Holdout höchstens 10/32 für die
geprüften Clientbeobachter. Die gepaarte Nachrechnung auf 108
alten 24-Token-Traces ergibt median 150 ms zusätzliche
individuelle Wartezeit. Das gilt nur, solange alle Antworten
vor dem neuen Slot bereit sind; der bisherige Fallback bleibt
danach bestehen.
Der anschließende **kausale Offline-Pilot** in
`docs/causal-release-pilot-20261102.md` verglich auf 108 vorhandenen
24-Token-Gruppen BOS, feste Slots und zwei periodische Gruppenregeln.
Beide periodischen Regeln verhindern im idealen Replay Einzel-Fallbacks,
geben über den gewählten Freigabetick aber erneut Completion-Information
preis. Ein explorativ auf 1.160 ms kalibrierter fester Slot deckte alle
108 Spuren ab und spart modelliert 40 ms je Antwort gegenüber 1.200 ms.
Das ist weder live bestätigt noch ein neuer Schutzalgorithmus. Die
abgeleiteten Rohzeilen stehen unter `results/causal-release-20261102/`.
Der folgende **Zufallsslot-Pilot** in
`docs/randomized-release-pilot-20261102.md` prüfte drei einfache
zustandsunabhängige 50:50-Mischungen auf denselben 108 Gruppen. Jeder
feste Mitteltermin hatte in den Entwicklungsdaten geringere oder
gleiche mittlere Wartezeit und geringeres oder gleiches Fallback-Risiko;
die breite Mischung zeigte zusätzlich ein clientseitiges Zeitsignal.
Keine der Mischungen begründet derzeit einen Methodenbeitrag. Keine
neue GPU-Messung oder Änderung der produktiven Regel.

## Bisher umgesetzt
- Privates GitHub-Repository erstellt.
- Lokale Git-Verbindung eingerichtet.
- Projektverzeichnisse angelegt.
- .gitignore, AGENTS.md und README.md erstellt.
- Repository am Messrechner unter `/home/rock/projects/llm-order-scrubbing`
  vorgefunden; `main`, Ausgangscommit `7690f03`, Arbeitsbaum vor Beginn sauber.
- Arbeitsauftrag, AGENTS.md, README.md, diesen Stand und docs/quellen.md gelesen.
- Hardware und vorhandene Laufzeitumgebungen lesend erfasst (siehe unten).
- Auf „Dann bitte gleich sichten“: lokale Projekt-/Dokumentablagen sowie den
  dokumentierten ordleak-Commit über die GitHub-Verbindung lesend gesichtet.
- Auf „weiter“: vorhandene Python-3.13-Umgebung auf Importierbarkeit und
  CUDA-Geräteerkennung geprüft; technische Quellen und relevante Abschnitte
  von PROMPTPEEK, OptiLeak und SafeKV gezielt aktuell nachgelesen.
- Auf das nächste „weiter“: lokalen Qwen-Snapshot mit vLLM gestartet, genau
  eine Anfrage mit einem Ausgabetoken beantwortet und Server beendet.
- Auf „vllt nochmal probieren?“: denselben Server erneut gestartet und mit
  einer kurzen Chat-Anfrage eine sichtbare vollständige Antwort geprüft.
- Auf „einfach mal weitermachen“: drei kontrollierte Anfragen zur
  Prefix-Cache-Wiederverwendung und Salt-Trennung ausgeführt; Rohantworten
  und Serverlog im Repository abgelegt.
- Auf „gezielte Machbarkeit“: 108 balancierte Zweier-Durchläufe mit zwei
  Tokenbudgets einschließlich einer Wiederholung durchgeführt und ausgewertet.
- Auf „weiter explorativ“: 188 zusätzliche Zweier-/Vierer-Durchläufe mit
  expliziter Prefill-Schwelle und passender Cache-aus-Kontrolle durchgeführt;
  Rangabstände und Rohdaten in `results/full-order-20261102/auswertung.md`.
- Auf „zwei weitere Möglichkeiten“ und „erst Security-Paper prüfen“:
  PROMPTPEEK, EarlyBird, OptiLeak und die Contention-Arbeit an den
  entscheidenden Originalstellen nachgelesen; danach zwei kleine
  Cache-an-/Cache-aus-Prüfungen mit 16 Ausgabetokens beziehungsweise
  überlappender Zusatzanfrage ausgeführt (80 Durchläufe).
- Auf „nächster Schritt, bis belastbarer Befund“: lokale Python-
  Freigabeschicht gebaut, direkte Antwort, BOS W=4, zwei Ziel-Deadlines
  und festen Freigabezeitpunkt in balancierten Vierergruppen verglichen;
  Client-, Proxy- und Backend-Eingangszeiten getrennt protokolliert.
  Nach Neustart und mit entferntem Cache-Diagnosefeld bestätigt:
  volle Rangmischung verdeckt die Information in der ersten
  Clientantwortzeit nicht. Details in
  `results/bos-sanitized-20261102/auswertung.md`.
- Auf den Daybreak-Blue-Auftrag: bisherige BOS-Daten unabhängig
  nachgerechnet; C1/C2-Konfigurationen, anderen Promptsatz und
  Slot-Fallback in insgesamt 308 neuen Vierer-Durchläufen geprüft;
  fünf Clientbeobachter und gepaarte Offline-Schutzkosten verglichen.
  Der starke Rangkanal ist unter C0 reproduzierbar und nicht an den
  ersten Prompttext gebunden, aber unter C1/C2 stark reduziert.
  Der Slot schützt das einfache T1-Merkmal bei vollständigen Gruppen;
  bei 24 Tokens trat in zwei getrennten Tests häufig Fallback auf,
  und ein vor der Bestätigung fixierter T2-Beobachter traf 20/32.
  Die beiden 24-Token-Testserien nutzten dieselbe deterministische
  Fallfolge, aber neue Salts und getrennte Serverstarts; diese
  Einschränkung ist im Bericht ausgewiesen.
  Die eigene ICCAI-2026-PDF wurde danach vollständig gegen die neue
  Forschungsfrage gelesen und als `references/iccai2026-completion-order.pdf`
  zur Nachprüfung im Repository gesichert. Sie prüfte Ränge ohne
  Clientzeiten und berichtete Gesamtlaufzeit statt individueller
  Antwortwartezeiten.
  Vollständiger Bericht: `docs/entscheidungsvalidierung-20261102.md`.
- Ausschließlicher Schreibort für Ergebnisse: dieses Repository.

## Inventar des Messrechners (02.11.2026)

| Komponente | Tatsächlich vorgefunden |
| --- | --- |
| CPU | AMD Ryzen Threadripper 3970X, 32 physische Kerne, 64 Threads, 1 NUMA-Knoten |
| RAM | 125 GiB nutzbarer Gesamtspeicher (rund 128 GB), bei Aufnahme 118 GiB verfügbar; Swap 511 MiB |
| GPU | NVIDIA GeForce RTX 3090, 24.576 MiB VRAM; bei Aufnahme 821 MiB belegt, Anzeige aktiv |
| Betriebssystem | Ubuntu 26.04.1 LTS, x86_64; Kernel 7.0.0-42-generic |
| NVIDIA | Treiber 580.178.04; `nvidia-smi` erfolgreich, angezeigte CUDA-Unterstützung 13.0 |
| CUDA-Toolkit | `/usr/bin/nvcc`, Release 12.4, V12.4.131; Paket nvidia-cuda-toolkit 12.4.131~12.4.1-8 |
| System-Python | `/usr/bin/python3`, 3.14.4; pip 25.1.1, NumPy 2.3.5; keine aktive virtuelle Umgebung |
| Weitere Werkzeuge | uv 0.12.1; rustc, cargo, conda, docker, ollama, vllm, sglang, llama-server und llama-cli nicht im aktuellen PATH gefunden |

Erfasst mit `lscpu`, `free -h`, `/etc/os-release`, `uname -r`,
`nvidia-smi`, `nvcc --version`, Versionsabfragen und Python-Paketmetadaten.
Die CUDA-Angabe von `nvidia-smi` ist kein Nachweis eines installierten
CUDA-13-Toolkits. Ein CUDA-Rechenlauf oder Engine-Start wurde nicht ausgeführt.
Die GPU dient gleichzeitig dem Desktop; die obige Belegung ist eine Momentaufnahme.

### Vorhandene Python-/LLM-Umgebungen

- Im System-Python fehlen die abgefragten Pakete torch, transformers, vllm,
  sglang, sgl-kernel, llama-cpp-python, triton, cuda-python, flash-attn,
  accelerate und huggingface-hub.
- In `/home/rock/projects/porto/.venv` und
  `/home/rock/projects/porto/.venv-py313-repair` liegen Paketmetadaten für
  vLLM 0.17.1, PyTorch 2.10.0, Transformers 4.57.6, Triton 3.6.0 und
  huggingface-hub 0.36.2 (jeweils site-packages für Python 3.13).
  Das belegt vorhandene Installationsartefakte, noch keine funktionsfähige Engine.
  Versionsabfragen ergeben: `.venv/bin/python` startet inzwischen Python 3.14.4
  trotz Konfiguration für 3.13.7; damit ist die alte Umgebung nicht ohne Weiteres
  als nutzbar anzusehen. `.venv-py313-repair/bin/python` meldet Python 3.13.7
  und ist der passendere Kandidat für eine spätere gezielte Funktionsprüfung.
- Weitere virtuelle Umgebungen in DOS, DOS2, energy, objective-placement-map
  und einem DOS-Unterprojekt enthalten keine der dort abgefragten LLM-Pakete.
  Ihre Konfigurationen verweisen teilweise auf Python 3.12 bzw. 3.13;
  Konfigurationsangaben sind kein aktueller Funktionstest.
- Im vorhandenen Hugging-Face-Cache liegen Verzeichnisse für
  `Qwen/Qwen2.5-7B-Instruct` und `meta-llama/Llama-3.1-8B-Instruct`.
  Bei der anschließenden Artefaktsichtung wurden alle im Index genannten
  Gewichtsdateien vorgefunden; Ladefähigkeit und Dateiinhalte bleiben ungeprüft.
- Das Nachbarprojekt `/home/rock/projects/vllm-offload-profiles` ist vorhanden.
  Befunde zur anschließenden inhaltlichen Sichtung stehen unten.

Die Inventarsuche blieb auf `/home/rock/projects` und naheliegende Laufzeit-/Cachepfade
beschränkt. Es gab keine Installation, Änderung fremder Projekte, Modellladung
oder Messkampagne. Rust ist außerhalb der geprüften Pfade nicht ausgeschlossen.

## Artefaktsichtung (02.11.2026)

### ICCAI 2026 / ordleak

- In `/home/rock/projects`, `/home/rock/Documents` und `/home/rock/Downloads`
  kein ordleak-Checkout bzw. passend benanntes Archiv gefunden. Die gezielte
  Textsuche in Code und Dokumentation ergab außerhalb dieses Projekts nur
  einen historischen BOS-Verweis in `porto/.../results_notes_paper1.md`.
  Keine Aussage über andere Datenträger oder ungeprüfte Archive.
- Über GitHub tatsächlich gelesen: ordleak am festgehaltenen Commit
  `2dad2ecb3116f4826f234d0da550dd83bfdfb474`; kein lokaler Klon angelegt.
  `src/victim.py` enthält `BOSScrubber`, `src/client_rank_only.py` den
  Reihenfolgeclient; `scripts/run_dataset.py` und `scripts/analyze.py`
  liefern Datenerfassung, ODS/GAP_VAR/first_half_ods und einfache Auswertung.
- BOS puffert W abgeschlossene IDs, mischt einen vollen Block und leert am
  Durchlaufende den Rest. W=0 ist ohne Schutz, W=1 ohne Umordnung.
  **W begrenzt eine Anzahl, keine individuelle Wartezeit.** Ein Zeitlimit oder
  Deadline-Flush fehlt. Der PRNG wird pro `RUN` neu mit dem angegebenen Seed
  initialisiert; sein Zustand läuft nur innerhalb dieses Durchlaufs weiter.
- Der vollständig gelieferte Git-Baum enthält 150 CSV-Dateien einschließlich
  Stage-1/2/3-, KDF- und Overhead-Daten, aber keine `.done.log`-Rohreihenfolgen.
  Eine Stage-3-CSV und eine Overhead-CSV wurden stichprobenartig gelesen:
  Kennzahlen, Labels, W und Seed sind erhalten, vollständige Permutationen und
  individuelle Zeitstempel fehlen. Der alte Client erfasst ausdrücklich keine
  Zeitstempel. Das Overhead-Skript misst die Gesamtlaufzeit vieler Durchläufe,
  nicht die individuelle BOS-Zusatzwartezeit. `.gitignore` schließt Logs aus.
- Wiederverwendbar sind der kleine Python-BOS-Kern, die Reihenfolgebehandlung
  und Kennzahlfunktionen. LLM-Anbindung, Zeitbudget und individuelle
  Fertigstellungs-/Freigabe-/Empfangszeiten sind damit noch nicht implementiert.
  Alte AUC-/Schwellwertauswertung ist keine Validierung eines neuen Beobachters.

### Lokale LLM-Artefakte

- `/home/rock/projects/vllm-offload-profiles`, Commit
  `547be9005dd6483d21e15e32416ffab96d1a2e63`, enthält kuratierte Start-/Clientskripte,
  Rohdaten, Konfigurationsevidenz und Auswertung für Offload, Profilvariation,
  GPU-Hintergrundlast und KV-/VRAM-Druck. Das ist ein anderes Experiment als BOS.
- In `data/raw/baseline/{llama,qwen}` liegen jeweils 180 JSON-Dateien.
  Je eine Datei wurde gelesen: je 20 Anfragen mit `start_times`, `ttfts`,
  `itls`, Ausgabelängen und Fehlern. Die Arrays werden laut lokalem vLLM-Code
  in Anfragefolge gespeichert, nicht in Abschlussfolge. Aus
  `start_times[i] + ttfts[i] + sum(itls[i])` lässt sich die Reihenfolge letzter
  Token ableiten; das ist kein direkt protokollierter HTTP-Abschluss oder
  BOS-Freigabezeitpunkt. Bisher keine neue Auswertung durchgeführt.
- `/home/rock/projects/porto`, Commit `72b9272c59ca0738ffe7fb012b9a33169b3b941f`,
  enthält zusätzliche HTTP-Streaming-Clients und historische Serverlogs.
  `paper1_workspace/step3_policy_gating/victim_worker.py` erfasst pro Anfrage
  ID, `start_time`, `e2el_ms`, TTFT und Tokenabstände. Eine vorhandene
  `.../policy_runs_offload0_20260416_092616/naive_threshold/offload0_naive_threshold_run4_victim.json`
  bestätigt 399 individuelle Datensätze; daraus sind Empfangsabschlusszeiten
  innerhalb dieses Workers ableitbar. Kein BOS-Versuch.
- Ein Qwen-Serverlog vom 27.07. belegt vLLM 0.17.1, bfloat16,
  Prefix-Caching, asynchrones Scheduling und erfolgreiche API-Antworten.
  Lokaler vLLM-Code nennt FCFS als Standard und außerdem Priorität;
  ein LPM-Scheduler oder ein ausnutzbarer Reihenfolgekanal ist damit nicht belegt.
  Die frühere Messumgebung war laut Artefaktdokumentation Kubuntu 25.10,
  Kernel 6.17 und ein älterer NVIDIA-Treiber: historischer Erfolg ersetzt keinen
  aktuellen Starttest nach dem Systemwechsel.
- Modellcache geprüft: Qwen-Snapshot `a09a35458c702b33eeacc393d103063234e8bc28`
  und Llama-Snapshot `0e9e39f249a16976918f6564b8830bc894c89659` enthalten jeweils
  alle vier im Index genannten Gewichtsdateien sowie Konfiguration und Tokenizer.
  Nur Existenz/Dateigröße geprüft, keine Inhaltsprüfung oder Modellladung.
- Die alten Skripte schreiben in ihre eigenen Arbeitsverzeichnisse und starten
  teils ganze Matrizen. Sie wurden ausschließlich gelesen, nicht ausgeführt.

**Entscheidungsrelevanter Befund:** Vorhandene vLLM-/Python-Komponenten können
den Neuaufbau voraussichtlich verkleinern. Vollständige alte BOS-Reihenfolgen
sind in den gesichteten Beständen nicht verfügbar; individuelle Schutzkosten
müssen neu erfasst werden. Eine funktionsfähige LLM-BOS-Freigabeschicht wurde
nicht vorgefunden. Es wurde nichts aus fremden Projekten kopiert oder verändert.

## Wissenschaftlicher Stand
- Nachfolgeprojekt zur ICCAI-2026-Arbeit.
- Forschungsfrage und vorläufiger Versuchsplan dokumentiert.
- Ein lokaler, konfigurationsabhängiger Rang-Basiskanal mit Cache-aus-
  Kontrolle ist nachgewiesen. Ein BOS-Pilot zeigt einen konkreten
  Rang-/Zeit-/Kostenkonflikt; Übertragbarkeit und Novelty sind noch offen.

## Machbarkeit und Entscheidungsvorlage (02.11.2026)

**Gezielte Funktionsprüfung:** Mit
`/home/rock/projects/porto/.venv-py313-repair/bin/python -B` lassen sich
PyTorch **2.10.0+cu128** und vLLM **0.17.1** importieren. Python ist **3.13.7**,
PyTorch meldet seine CUDA-Version **12.8**, `torch.cuda.is_available()` ist
`True` und das Gerät wird als RTX 3090 erkannt. Die Python-Prüfung lief ohne
Bytecode-Schreibzugriffe und mit Offline-Modus für Hugging Face. Kein
Modell-/Serverstart, kein GPU-Rechentest und keine Installation. Der erfolgreiche
vLLM-Paketimport allein belegt noch nicht die vollständige
Server-Abhängigkeitskette. Der nachfolgende Starttest prüfte diese separat.

**Einzelner Server-/Modellstart (02.11.2026):** Der vorhandene
Qwen2.5-7B-Instruct-Snapshot ließ sich mit vLLM 0.17.1 unter Python 3.13.7
auf der RTX 3090 laden. Für diesen Machbarkeitstest: lokaler OpenAI-Server
auf `127.0.0.1:8765`, `max-model-len=2048`, `gpu-memory-utilization=0.80`,
`cpu-offload-gb=0`, Eager-Modus, Offline-Modus. Die einzige
`/v1/completions`-Anfrage erhielt HTTP 200 und `completion_tokens=1`;
das eine ausgegebene Token war ein Zeilenumbruch. Die 0,167 s HTTP-Gesamtzeit
ist eine Einzelbeobachtung, keine Latenzmessung. Anschließend wurde der
Server beendet; Port und GPU-Speicherbelegung kehrten auf den Ausgangszustand
zurück. Keine Installation, kein Kanal- oder BOS-Test.

Der erste Startversuch scheiterte vor der Modellladung, weil der unter
`results/qwen-single-20261102/tmp` vorgesehene IPC-Socket-Pfad die
107-Zeichen-Grenze überschritt. Mit `results/tmp` innerhalb des Repositorys
gelang derselbe Start. Belege:
`results/qwen-single-20261102/server.log` (Fehler),
`server-second.log` (erfolgreicher Start und Shutdown), `response.json` und
`response.headers`. Laufzeit-Caches liegen ebenfalls nur unter
`results/qwen-single-20261102/cache`; die vorhandene Modellablage und
Python-Umgebung wurden lediglich gelesen. Dieser Start mit verkürzter
Kontextlänge und Eager-Modus bestätigt noch keine spätere Pilotkonfiguration.

**Wiederholung auf Wunsch (02.11.2026):** Mit derselben lokalen Konfiguration
und einer einzigen Anfrage an `/v1/chat/completions` antwortete Qwen auf
„Antworte mit genau einem Wort: TEST“ mit `TEST` (HTTP 200,
`finish_reason=stop`, zwei Ausgabetokens bei höchstens acht erlaubten).
Die HTTP-Gesamtzeit von 0,201 s ist wiederum nur eine Einzelbeobachtung.
Der Server wurde anschließend beendet. Belege:
`results/qwen-single-20261102/server-third.log`,
`response-repeat.json` und `response-repeat.headers`. Die Wiederholung
bestätigt eine sichtbare Chat-Antwort, keinen Cache-/Reihenfolgekanal.

**Cache-Kontrolle (02.11.2026):** Derselbe Qwen/vLLM-Server lief mit
aktiviertem Prefix-Caching und `--enable-prompt-tokens-details`. Drei
nicht gestreamte Anfragen hatten denselben Prompt mit 258 Tokens und je
höchstens ein Ausgabetoken; zuerst Salt A, dann erneut Salt A, zuletzt Salt B.
Alle drei erhielten HTTP 200. Die zweite Antwort meldete
`cached_tokens=256`; die erste und dritte meldeten kein positives
`cached_tokens`-Feld. Der lokale vLLM-Code setzt das Feld nur bei einem
positiven Wert. Damit sind Wiederverwendung bei gleichem Salt und Trennung
bei verschiedenem Salt in diesem Einzeltest sichtbar. Die beobachteten
HTTP-Gesamtzeiten (0,170 / 0,074 / 0,114 s) sind nicht für einen
Leistungs- oder Kanalbefund belastbar. Anfragen, Antworten und Log liegen
unter `results/cache-control-20261102`; der Server wurde beendet.
Dieser Test erfasst weder konkurrierende Anfragen noch Antwortreihenfolgen.

**Gezielter Machbarkeitspilot (02.11.2026):** 108 Durchläufe mit jeweils zwei
konkurrierenden Probes; 72 davon mit A oder B vorgewärmt, 36 ohne Vorwärmung
als Kontrolle. A/B hatten je 548 Prompt-Tokens, maximal ein Ausgabetoken,
neuen Salt pro Durchlauf und rund 10 ms tatsächlichen Sendeabstand. Die
Vorwärmung führte in allen 72 passenden Probes zu 544 gemeldeten
Cache-Tokens. Unter dem ursprünglichen Tokenbudget 2048 gewann stets die
zuerst gesendete Probe; bei Budget 256 kamen spätere Cache-Treffer in
8/12 und bei der Wiederholung in 5/12 Fällen zuerst, aber mit höchstens
0,093 ms Empfangsabstand. Das ist kein robuster Rangbefund. Dagegen war die
Clientzeit der zuerst gesendeten Probe bei Vorwärmung in allen beobachteten
Fällen unter 77 ms, ohne deren Vorwärmung über 137 ms. Eine nachträglich
gewählte 100-ms-Grenze trennt die binären A/B-Zustände innerhalb dieser
Messdaten, ohne unabhängige Validierung. `cached_tokens` diente nur als
Kontrolle und wurde nicht als Rang-/Timing-Beobachtung verwendet.
Versuchsaufbau, Tabellen, Grenzen, Rohdaten und Logs:
`results/order-feasibility-20261102/auswertung.md`; Client:
`src/cache_order_pilot.py`. Die beiden Server wurden nach den Serien beendet.

**Explorativer Rangpilot mit Prefill-Grenze (02.11.2026):** Bei Qwen/vLLM
0.17.1, FCFS, Tokenbudget 256 und ausdrücklich gesetzter
`long_prefill_token_threshold=128` gewann der 10 ms später gesendete,
vorgewärmte Treffer in zwei unabhängigen Fallfolgen **24/24** Zweier-Durchläufe
mit 51,00–88,66 ms Empfangsvorsprung. Mit Prefix-Caching aus gewann er
**0/12** Mal. Bei Schwelle 64 und vier Probes stand die vorgewärmte Probe
in **32/32** Durchläufen auf Empfangsrang 1, selbst bei Sendeposition 4
(**8/8**, Vorsprung 297,68–310,07 ms vor der ersten kalten Antwort).
Mit Cache aus entsprach ihr Rang in **32/32** der Sendeposition. Weitere
Kontrollen ohne Vorwärmung zeigten keine systematische Bevorzugung der
markierten Probe; unter vier kalten Probes trat allerdings je einmal eine
Vertauschung auf. Alle vorgewärmten Probes meldeten 544 gecachte von 548
Prompt-Tokens, kalte keine. Diagnosefeld `cached_tokens` war nicht Teil der
Rangentscheidung. Der Mechanismus ist mit Chunked Prefill konsistent, aber
intern nicht instrumentiert; der Effekt gilt nur für diese gezielte lokale
Konfiguration. Vollständiger Versuchsbericht, Rohdaten und Logs:
`results/full-order-20261102/auswertung.md` und
`results/prefill-threshold-20261102/`. Beide Server sind beendet.

**Zwei literaturgeleitete Anschlüsse (02.11.2026):** PROMPTPEEK nutzt
ein Token pro Anfrage; die Contention-Arbeit zeigt, dass konkurrierende
Arbeit Cache-Timing erheblich verändern kann. Deshalb wurden bei derselben
gezielten vLLM-Konfiguration einmal **16-Tokens-Antworten** und einmal
**eine tatsächlich überlappende 64-Token-Zusatzanfrage** getestet,
jeweils gegen Cache aus. In beiden Cache-an-Bedingungen gewann die später
gesendete vorgewärmte Probe **12/12** Mal; bei Cache aus **0/12**
beziehungsweise **2/12**, letztere nur an Sendeposition 2 und mit
nahezu gleichen kalten Antwortzeiten. Als vierte gesendet lag der Treffer
bei Cache an in **4/4** Fällen vorn, bei Cache aus in **4/4** Fällen
auf Rang 4. Der Vorsprung bei Sendeposition 4 betrug 101,34–105,43 ms
für 16 Tokens und 173,77–176,19 ms unter Zusatzlast. Die
Zusatzanfrage überdeckte in **20/20** zugehörigen Durchläufen die
Probe-Sendezeitpunkte und erste Antwort. Volle Rohdaten, Kontrolle und
Grenzen: `results/two-extensions-20261102/auswertung.md`. Das ist ein
lokaler Robustheitsbefund, keine allgemeine Last- oder BOS-Aussage.

**Durchgängiger Schutz-/Kostenpilot (02.11.2026):** Vier vollständige
16-Token-Antworten durch eine lokale Python-Freigabeschicht geleitet.
Die Hauptserie umfasste 272 balancierte Durchläufe / 1.088 Probes:
direkt war der Cache-Treffer 64/64 Mal auf Rang 1; BOS W=4 nur
19/64; mit 100-ms-Ziel 64/64, weil die vorgewärmte Antwort 64/64
Mal allein freigegeben wurde; mit 250-ms-Ziel 18/64 in vollen
Viererblöcken. Eine vorgezogene Timer-Auslösung hielt die
**gemessene** Zusatzwartezeit bei 100 ms unter dem Ziel (Maximum
95,03 ms), ist aber kein harter Echtzeitbeweis. Die frühe Antwort
wartete beim vollen W=4 median 193,79 ms zusätzlich.

Der wichtige **Restkanal**: Das Mischen verändert die Rangfolge,
nicht den Zeitpunkt, zu dem die letzte Backend-Antwort den Block
freigabefähig macht. Eine nur aus dem ersten Clientempfang nach
dem ersten Versand gebildete, vor dem Test fixierte Vierfachregel
erkannte nach Neustart des Modellservers 53/64 W=4- und 56/64
250-ms-Zustände; die zuerst empfangene ID traf 21/64 und 15/64.
Ein fester Freigabezeitpunkt 1.050 ms nach erstem Anfrageeingang
glättete dieses eine Zeitsignal im lokalen Pilot, erhöhte aber die
mediane individuelle Wartezeit der frühen Antwort auf 362,50 ms.
Im abschließenden 204-Durchlauf-Vergleich wurde das direkt
clientseitig sichtbare `cached_tokens`-Feld entfernt; die
Zeitregel traf weiterhin 41/64 bzw. 43/64 bei BOS und 250 ms,
eine einfache Slot-Zeitregel nur 12/64. Alle 816 Clientantworten
waren ohne Cache-Diagnosefeld; intern protokollierte Treffer,
API-IDs und Zeiten stimmten. Bericht, Grafik, Rohdaten und Grenzen:
`results/bos-sanitized-20261102/auswertung.md`.

**Quellenbefund und Grenze:** PROMPTPEEK (§IV-A, S. 5–6; §VIII, S. 13)
untersucht LPM und gezielt aufgebaute Warteschlangen. OptiLeak v1 (§4.2/§5.1)
nutzt ebenfalls LPM/Positionsfeedback und SGLang. Der dortige Mechanismus ist
kein Nachweis für die lokale vLLM-FCFS-Konfiguration. vLLM 0.17.1 dokumentiert
Prefix-Wiederverwendung voller Blöcke und optionale Cache-Salts; APC spart
Prefill, nicht Decode. Die historischen Aussagen über andere Scheduler aus
PROMPTPEEK dürfen deshalb nicht pauschal auf heutiges vLLM übertragen werden.
SafeKV v2 (§6) schützt an der Cache-Wiederverwendung und untersucht TTFT;
es ist eine Vergleichsbasis, kein Beleg für BOS-Restinformation.
Dies war eine begrenzte, entscheidungsorientierte Quellenprüfung, kein neuer
umfassender Literatur-/Novelty-Audit; Fundstellen und Lesestände in docs/quellen.md.

| Option | Aussagekraft / vorhandene Basis | Aufwand bis zum ersten Befund |
| --- | --- | --- |
| A: vLLM + Python-Client/Freigabe | Lokal umgesetzt; konfigurationsabhängiger Basiskanal und erste Schutz-/Kostenmessung vorhanden | Geringster Zusatzaufwand für gezielte Übertragbarkeitsprüfung |
| B: vLLM + Rust-Freigabe | Gleiche Forschungsfrage; präzisere Freigabe wäre zu messen, kein automatischer Vorteil | Höher: Rust nicht gefunden, zusätzliche Schnittstelle; derzeit kein belegter Bedarf |
| C: andere Engine | Keine zusätzliche funktionsfähige lokale Engine gefunden; SGLang dokumentiert LPM und wäre näher an PROMPTPEEK | Erst Einrichtung/Kompatibilitätsprüfung erforderlich; kein vorhandener schnellerer Weg belegt |

**Aktualisierte Empfehlung:** A mit dem vorhandenen Qwen2.5-7B-Instruct-
Snapshot und der kleinen Python-Freigabeschicht weiterführen. Der
konfigurationsabhängige Basiskanal ist bei 16 Ausgabetokens sichtbar,
und der erste Schutzversuch liefert einen konkreten Restzeitkanal.
Rust oder Engine-Wechsel erst bei einem konkreten Hindernis neu
bewerten. SGLangs aktuelle Dokumentation führt LPM als wählbar,
inzwischen FCFS als Standard; LPM nicht stillschweigend voraussetzen.

**Vorläufiger Erkenntniskandidat, noch kein Neuheitsclaim:** Ein
voller BOS-Block mischt bei vollständigen LLM-Antworten die Ränge,
verrät aber über seinen Fertigstellungszeitpunkt weiter den
kontrollierten Cachezustand. Eine kurze Deadline zerstört die
Blockmischung; eine vom Anfrageeingang verankerte Ausgabe glättet
das beobachtete Zeitsignal zu höheren individuellen Kosten.
Cache-Leakage, Blockmischung und zeitgebundene Ausgabe als solche
sind bereits bekannt.

**Versuchsentscheidung nach dem Rangpilot:** Gleiche tokenisierte Promptlänge,
ein Ausgabetoken, frischer gemeinsamer Salt je Durchlauf und getrennte
Cache-an-/Cache-aus-Serien haben den Basiskanal nachvollziehbar gemacht.
Die Vorbelegung und ihre gemeldeten 544 Cache-Tokens wurden nur als
Kontrolle ausgewertet. Im Schutzversuch blieben Antwort-ID,
vollständige Empfangsreihenfolge und individuelle Zeiten getrennte Felder.
Das API-Diagnosefeld `cached_tokens` wurde im letzten Vergleich
clientseitig entfernt. Der Proxyversuch zeigt die lokale Verringerung
des Rangkanals und die Wartezeiten; ein Deadline-Flush ist eine
ausdrückliche Mechanismusänderung. Er beweist keine allgemeine Sicherheit.

## Offen
- Starker Vierklassenkanal und BOS-Restzeitbefund sind weiterhin nur
  für die gezielte C0-Konfiguration auf einem Rechner belegt. C1 ist
  wesentlich schwächer; C2 zeigte keinen entsprechenden Rangkanal.
- Realistische Mehrnutzerlast, andere Netze und Modelle sind ungeprüft.
  Gemeinsame Salt-Domäne bleibt eine ausdrückliche Voraussetzung.
- Der Slot-Fallback ist nun gemessen, aber eine alternative sichere
  Spätantwortregel und harte Wartezeitgrenzen sind ungeprüft.
- Frühere T1-Zahlen sind reproduzierbar, doch die Prospektivität
  ihrer ursprünglichen Regelauswahl ist aus den Artefakten nicht
  sicher nachweisbar. Die neue Fallback-Bestätigungsserie wurde
  nach Auswahl von T2 getrennt gefahren.

## Nächster Schritt
Die empirische BOS-/Fallback-Richtung mit einem expliziten
Latenz-/Verfügbarkeitsbudget und vollständiger Client-Trace-Auswertung
prospektiv stärken. Dafür einen kleinen, frisch randomisierten Live-Test
eines vorab fixierten Slots nach neuem Backend-Start planen; C1 und
längere Completion-Tails als Geltungsgrenzen behandeln. Auf den
bereits explorierten Spuren keine weitere Slot-/Münzoptimierung.
