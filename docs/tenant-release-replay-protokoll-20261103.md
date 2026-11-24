# Offlineprüfung öffentlicher Antworttermine

Stand: 03.11.2026. Exploratives Protokoll vor Ausführung der neuen
Nachrechnung; die zugrunde liegenden Daten wurden schon früher ausgewertet.
Es gibt keinen neuen unberührten Holdout und keine GPU-Messung.

**Hypothese:** Eine starke einfache Release-only-Baseline könnte den bisher
beobachteten B-only-Kanal auf diesen Spuren bereits bei moderaten Kosten
abdecken. Ein Vorteil eines neuen Schedulers darf nicht vorausgesetzt werden.

**Daten:** Die vier alten getrennte-Salts-Serien direkt/BOS × frische/feste
Salts mit ihren bisherigen Entwicklungs- und Prüfteilen. Der 24-Fall-Test
mit verborgenem A-Start nutzt ausschließlich die alte frische-Salts-
Direktentwicklung zur Terminkalibrierung, ohne Zugriff auf seine Prüfzeiten.
Kontrollen bleiben bei der Kosten- und Deckungsrechnung enthalten.

**Öffentlicher Vertrag:** vier B-Anfragen in bekanntem Sendeplan; Referenz
ist die erste B-Proxyankunft, bei individuellen Fristen die jeweilige eigene
Proxyankunft. Weder Cachelabel noch Testcompletion wählen einen Termin.
Die B-Sendereihenfolge wird als öffentliche Batchmetadaten vorausgesetzt;
ein späterer realer Dienst muss sie authentifizieren oder anhand öffentlicher
Sequenznummern bilden. Das Replay ordnet gemäß gespeichertem Sendeplan zu.

**Termine:** Je altem Entwicklungsstart werden die maximalen
Backend-Eingangszeiten über beide Geheimnisse und Kontrollen nach oben
auf 10 ms gerundet. Verglichen werden (1) ein gemeinsamer Termin mit
festen 2-ms-Abständen in öffentlicher Sendereihenfolge, (2) dieselbe Frist
nach jeder eigenen Ankunft und (3) vier feste Termine je öffentlichem
Senderang ab erster Ankunft, monotonisiert mit mindestens 2 ms Abstand.
Die individuelle Frist verwendet das Maximum der individuellen
Backend-Eingangszeit minus eigener Proxyankunft. Kein Parametersweep.

**Spätregel:** `max(Termin, tatsächlicher Backend-Eingang)` gibt eine späte
Antwort sofort frei. Diese Regel ist ausdrücklich unsicher. Gemeldet
werden späte Antworten und Gruppen nach Zustand, nicht nur Accuracy.
Die aus Prüfdaten gemessenen minimal deckenden Termine werden ausschließlich
als Diagnostik ausgegeben, niemals als erfolgreiche kalibrierte Policy.

**Kosten:** Individuelle Wartezeit nach vollständigem Backend-Eingang,
modellierte B-Endzeit minus jeweiligem Clientversand, Mittel/Median/P95/Max.
A bleibt für den engen festen B-only-Beobachter unverzögert (Zusatzkosten
null); separat wird eine symmetrische A-Freigabe berechnet. Dort ist As
Clientempfang mangels Proxyinstrumentierung nur ein konservativer Ersatz
für Bereitschaft, keine gemessene A-Proxywartezeit. Kein P99- oder
Durchsatzclaim aus wenigen, rückkopplungsfreien Traces.

**Beobachter:** Neu trainierte logistische Regression, RBF-SVM und kleiner
Random Forest mit festgelegten Parametern im Programm. Merkmale: alle vier
B-Clientempfangszeiten, eigene Sendezeitabstände, Ränge und erste/letzte
Empfangszeit. Training nur auf alter Entwicklung; binäre Balanced Accuracy
und AUC auf bisherigen Prüfserien. Keine Auswahl anhand des besten Testwerts.
Die neuen Modelle sind explorative Diagnostik, keine finale Angreiferfestlegung.

**Grenzen:** Bereitzeiten werden festgehalten, GPU-Ausführung nicht
umgeplant. Reale Timer, Ausgabe, Netzlaufzeit und Rückkopplung zukünftiger
Requests fehlen. Die gemessene Differenz zwischen erster Clientsendung
und Proxyankunft bleibt erhalten und kann selbst kleine Zeitinformationen
tragen. Ein ideal getakteter Replay ist kein vollständiger Live-Clienttrace.
Das Fixieren der nachfolgenden Traces verhindert auch keine Leakage über
adaptives Nachsenden, Queueing oder spätere Fenster.

**Entscheidung:** Nur wenn der Vergleich eine relevante Kosten- oder
Sicherheitslücke zeigt und die Literatur eine konkrete neue Eigenschaft
offenlässt, wird ein einzelner Engine-Kandidat spezifiziert. Kein
Implementierungs- oder Liveauftrag folgt automatisch aus dieser Nachrechnung.

Programm: `src/tenant_release_feasibility.py`; neuer Ergebnisordner:
`results/tenant-release-feasibility-20261103/`. Alte Dateien bleiben unverändert.
