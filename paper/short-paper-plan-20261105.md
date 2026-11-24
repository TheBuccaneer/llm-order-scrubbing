# ICCAI 2027 Short Paper mit C1 und C2

Stand: 05.11.2026. Diese Planung ersetzt für das nächste Manuskript die
frühere Drei-Contribution-Struktur. Ziel sind **fünf zweispaltige Seiten
einschließlich Referenzen** mit C1 und C2 als Hauptbeiträgen. Die
ICCAI-Seite nennt regulär 4–5 zweispaltige oder 8–10 einspaltige Seiten;
„Short Paper“ ist hier unsere Umfangsbezeichnung, keine Behauptung einer
gesonderten veröffentlichten Einreichungskategorie.
[Offizielle Umfangsangabe](https://www.iccai.net/registration.html),
[Einreichung und Vorlage](https://www.iccai.net/submission.html),
geprüft am 05.11.2026.

**Arbeitstitel:** *Client Timing Leakage in LLM Serving Beyond Rank
Scrubbing and Cache Namespaces*.

## Zwei Hauptbeiträge

**C1 — Beobachtungsgrenze der Rangmischung.** Eingefrorene Beobachter
zeigen im Qwen-Dokumenttransfer nach BOS unter S64 7/32 richtige
Rangklassifikationen und 21/32 richtige Zeitklassifikationen; S0 9/32
gegen 13/32. Die separate Llama-Synthetikprüfung ergänzt die Evidenz,
ohne als identischer Workload gepoolt zu werden. Kein universeller
Rangschutz und kein gesicherter kausaler Konfigurationseffekt behauptet.
Die engste Vorarbeit bleibt die eigene BOS-Arbeit, ergänzt um bekannte
LLM-Rang-/Timingangriffe und Ausgabeformung.

Die vorhandenen Qwen-Proxytraces liefern eine konkrete Erklärung: In
allen 72 vollständigen BOS-Viererblöcken beginnt die Proxyfreigabe nach
Empfang der letzten vollständigen Backendantwort. Dazwischen liegen
median 0,264 ms; der erste vollständige Clientempfang folgt median
0,542 ms nach dem letzten Backendempfang am Proxy. Dies belegt eine
mit dem Ablauf konsistente Blockschließzeit, keine Messung des exakten
GPU-Abschlusses und keine isolierte Schedulerkausalität.
Offline-Beleg: `paper/c1-proxy-mechanism-20261105.json`, mit Hashes aller
acht alten Eingabedateien. Kein neuer C1-GPU-Test oder Beobachter.

**C2 — Konditionale Inferenz trotz getrennter Cache-Namensräume.** Der
bestehende versteckte-Versatz-Test zeigt T1 14/16 und T2 16/16 bei
unveränderten A/B-Salts und null B-Hits. Die zusätzliche feste
C-Lastprüfung trennt ausdrücklich den gepaarten Cachezustandseffekt
von der Übertragbarkeit der alten Einzelkohortenklassifikatoren.
Abwesenheits- und andere-kalte-Arbeit-Kontrollen begrenzen die
Dokument-/Anwesenheitsspezifität. Namespace-Isolation und bekannte
Leistungsinterferenz werden zitiert; kein Brechen fremder Cachekeys
oder erste allgemeine Seitenkanalklasse beansprucht.

**Abschließendes Lastergebnis B und unabhängig D:** Alle 24 gepaarten
Kalt-minus-Warm-Differenzen sind positiv; Median 100,73 ms, geschichtetes
95-%-Paarbootstrapintervall 87,14–107,26 ms, exakter Vorzeichentest
p=5,96×10⁻⁸. Beide festen Beobachter erreichen unter C-Last nur 50 % BA,
weil sie alle 48 Hauptfälle „kalt“ nennen; zugleich behalten ihre
unveränderten Scores AUC 1,00. Das ist **erhaltene Ranginformation bei
verlorener Kalibrierung**, kein Verschwinden des Kanals. Ohne Last waren
T1 = 14/16 und T2 = 16/16 bei jeweils AUC 1.

Alle acht Abwesenheits- und acht andere-kalte-Kontrollen werden von
beiden Beobachtern ebenfalls „kalt“ genannt. C2 identifiziert damit
weder Ziel-Dokument noch Anwesenheit eindeutig. 64/64 Fälle sind
vollständig; sämtliche 256 B-Anfragen ohne Hits. Tatsächlicher
C-Fortschritt vor der ersten B-Vollantwort ist in allen 64 Fällen
belegt, ohne gleiche tatsächliche GPU-Auslastung zu behaupten.

Auswertung: `results/tenant-background-20261105-02/analysis.json`;
Claim, Kontrollen, Unsicherheit und Rohdatenpfade:
`docs/tenant-hintergrundlast-20261105.md`. Der aktive Freeze wurde vor
Datenerhebung in `64086bd` lokal committed. Die IPC-Pfadkorrektur vor
jeglicher Inferenzmessung ist einschließlich aller sieben verworfenen
Starts und der ersten Protokollfassung ausdrücklich dokumentiert.

## Seiten und sichtbare Evidenz

| Teil | Seitenbudget | Inhalt |
| --- | ---: | --- |
| Titel, Abstract, 1 Introduction | 0,65 | Konkretes Problem, zwei Contributions; Unterschied zur reinen Rangbeobachtung von ICCAI 2026 |
| 2 Related Work and Observation Model | 0,60 | BOS, PROMPTPEEK/OptiLeak, Cache-Namensräume, bekannte LLM-Interferenz; Angreiferwissen und B-only-Features |
| 3 Method | 0,65 | Qwen/vLLM/GPU, vollständige HTTP-Empfänge, vier Kandidaten versus binäres A-Cachebit, Splits, S64/S0 und feste Salts |
| 4 Rank Scrubbing and Block Closure | 0,85 | C1-Zahlen und Intervalle; Abbildung 1; 72 alte Proxyblöcke als Ablaufbeleg |
| 5 Cross-Tenant Timing and Background Load | 1,15 | C2 unbelastet/belastet; RQ1 und RQ2 getrennt; Abbildung 2 und Ergebnistabelle; Kontrollen im Haupttext |
| 6 Limitations and Conclusion | 0,40 | Bekannte A-Anfrage, lokale Verbindung, eine Hardware, fixe C-Last statt realem Verkehr, Grenzen der Klassifikatorübertragung |
| References | 0,70 | Etwa 12–14 tatsächlich genutzte Quellen |
| **Summe** | **5,00** | Zwei Abbildungen und eine kompakte Ergebnistabelle |

Abbildung 1 verwendet die bereits vorhandenen Rang-/Zeitwerte mit
Vierklassen-Zufallslinie 25 %. Die zwei Modellpanels bleiben klar
getrennt. Bei Platzmangel wird die Llama-Stützung im Text verdichtet,
statt zusätzliche Versuche oder eine neue Forschungsfrage einzuführen.

Abbildung 2 zeigt die vorhandenen acht unbelasteten C2-Paardifferenzen
und die 24 neuen unter dem einen C-Profil. Die Gruppen bleiben
unterschiedliche Messserien; keine neu randomisierte gepaarte
Last-an/Last-aus-Kausalinferenz behaupten. Innerhalb des neuen Lastprofils
ist der randomisierte A-Warm/Kalt-Paarvergleich der primäre Endpunkt.

Die Ergebnistabelle führt pro Lastbedingung T1/T2-BA und AUC mit
geeigneten Unsicherheitsangaben auf. Ein positives RQ1-Ergebnis und
schlechte feste Schwellenklassifikation gehören ausdrücklich zusammen
in die Darstellung. A-/C-Zeitpunkte prüfen die Versuchsgültigkeit und
werden nicht zu neuen Angreifermerkmalen. C-Streamingfortschritt während
offener B-Anfragen ist keine Behauptung identischer tatsächlicher
GPU-Auslastung oder paralleler GPU-Kernel.

## Behandlung von Protected Prefill und Abschluss

Der bisherige C3-Prototyp, seine Kosten, die Direct-Positivkontrolle und
der begrenzte logische Vertrag bleiben als vorhandene Forschungsergebnisse
erhalten. Sie werden in diesem fünfseitigen Paper **nicht als dritter
Hauptbeitrag** ausgeführt. Falls fachlich erforderlich, erhält die
Diskussion einen kurzen Verweis auf die ergänzenden Artefakte; weder
Timing-Sicherheitsgarantie noch überlegene Schutzmethode behaupten.

Mit dem abgeschlossenen einen C2-Lastversuch endet die Forschung für C1 und C2
unabhängig vom Vorzeichen des Befunds. Der nächste Arbeitsschritt ist
das englische Manuskript und seine Satzprüfung im offiziellen Format.
Kein neuer GPU-Test, Lastprofil, Angreifer, Scheduler oder Parametersweep
wird zur Voraussetzung des Schreibens gemacht.
