# C2 Robustheit unter fester Hintergrundlast

Stand: 05.11.2026. **Ergebnis B und unabhängig davon D:** Der gepaarte
Cachezustandseffekt bleibt unter dem festen C-Lastprofil erkennbar.
Die alten Klassifikationsgrenzen versagen jedoch: T1 und T2 nennen
sämtliche Fälle „kalt“, BA jeweils 50 %. Gleichzeitig bleiben die
unveränderten Scores mit AUC 1,00 vollständig rangtrennend in dieser
Stichprobe. Die Forschungsphase für C1/C2 ist abgeschlossen.

## Aufbau und öffentliche Lastplanung

Qwen2.5-7B-Instruct, derselbe lokale Snapshot, vLLM 0.17.1 und RTX 3090;
native C2-Konfiguration mit Tokenbudget 256 und Prefillschwelle 64.
Kein BOS und kein neuer Scheduler. Jeder der 64 Fälle erhält ein frisches
Backend. A/B behalten die Salts des vorherigen verborgenen-Versatz-Tests;
C hat einen dritten festen Salt. Prompttexte bleiben unverändert.

24 randomisierte Warm/Kalt-Paare verteilen sich mit sechs Paaren je
Versatz auf 0/150/300/450 ms. Innerhalb eines Paars gelten derselbe
B-Sendeplan und A-Versatz. Hinzu kommen acht Abwesenheits- und acht
andere-kalte-Arbeit-Kontrollen, je zwei pro Versatz. Paarblöcke und
Kontrollen sind vorab gemischt. A bereitet wie bisher ein Dokument
mit einer Ein-Token-Anfrage vor; nach 250 ms Pause startet die Gruppe.
Warm/Kalt verwendet denselben A-Zielprompt und 16 Ausgabetokens. B
sendet vier eigene 16-Token-Anfragen bei 0/10/20/30 ms über den bisherigen
direkten Proxy, der Cachefelder aus den Clientantworten entfernt.

Das einzige C-Profil besteht aus einer kalten 548-Token-Anfrage für
Dokument B mit exakt 256 Ausgabetokens und Temperatur 0. Der C-Thread wird
100 ms vor der A/B-Gruppenfreigabe gestartet; es gibt keine Nachfüllung,
Anpassung oder Abbruchentscheidung anhand von As Zustand. C wird auch
nach Abschluss von B vollständig zu Ende verarbeitet. SSE-Zeitpunkte
und abschließende Usagewerte belegen reale Inferenz und gemessenen
Fortschritt während offener B-Anfragen. Sie messen weder exakte
GPU-Kernelüberlappung noch identische tatsächliche Auslastung in beiden
Cachezuständen. Auf tatsächlich gleiche C-Laufzeiten wird nicht
nachträglich selektiert.

## Eingefrorene Beobachter und getrennte Forschungsfragen

T1/T2 verwenden exakt das alte C2-Rezept: StandardScaler und logistische
Regression mit C=1. T1 sieht den ersten vollständigen B-Empfang relativ
zum ersten B-Versand, T2 die vier Empfangszeiten in der bekannten
Sendereihenfolge. Eine Beobachtung ist eine Vier-Probe-Kohorte, nicht
vier unabhängige Angriffe. A-/C-Zeitpunkte oder Backenddaten gehen in
keinen Beobachter ein. Scores bleiben auf „warm“ orientiert; eine
Vorhersage verwendet unverändert Score>0.

Die früheren C2-Skripte speicherten keine numerischen Modellkoeffizienten.
Vor diesem Test wurden die Modelle deshalb deterministisch ausschließlich
aus denselben 16 alten Entwicklungsfällen und demselben Rezept
rekonstruiert und als Koeffizienten samt Skalierung eingefroren. Sie
reproduzieren auf den alten verborgenen-Versatz-Daten T1 = 14/16,
T2 = 16/16 und sämtliche Kontrollklassifikationen; beide festen Scores
ergeben dort AUC 1. Es gibt keinen historischen Koeffizientencheckpoint
für einen zusätzlichen Bytevergleich. Keine neue Lastmessung wurde zum
Anpassen von Modellen oder Schwellen verwendet.

**RQ1:** Primär ist die erste vollständige B-Antwortzeit kalt minus warm
innerhalb jedes der 24 Paare. Ausgewertet werden Vorzeichen, Verteilung,
Median, einseitiger exakter Vorzeichentest in der vorab gewählten
Richtung und 5000 Paarbootstraps für Median-/Mittelwertintervalle.
Der Bootstrap zieht innerhalb der vier Versatzstrata je sechs ganze
Paare. Exakte Null-Differenzen werden beim Vorzeichentest als Bindungen
ausgewiesen und nicht als Erfolge gezählt.

**RQ2:** Die alten festen Vorhersagen und Scores liefern Accuracy,
Balanced Accuracy und ROC-AUC mit denselben geschichteten
Paarbootstrapblöcken. Das vorab festgelegte Erkennbarkeitskriterium
verlangt bei mindestens einem der zwei bestehenden Beobachter sowohl
BA- als auch AUC-Untergrenze über 0,5. Nominale Intervalle sind keine
allgemeine Sicherheits- oder Produktionsgarantie. Positive Paareffekte,
Score-Ranginformation und kalibrierte Einzelkohortenentscheidungen werden
nicht gleichgesetzt. Die 16 Kontrollen gehören in keinen Accuracy-Nenner.

## Vorabfestlegung und technische Revision

Aktive Messfassung:
`results/tenant-background-20261105-02/protocol.json`, vor Datenerhebung
lokal festgeschrieben in **64086bd3ea75e793655849382b07d2b53a3f0f2c**.
Protokoll-SHA-256:
`f7b546006bd611585c0b7ece5c35359881ad1b222d64ed70e8e1cfb39797e892`.
Fallfolge, Beobachter, Salts, Prompts und Quellcodesnapshots sind erfasst.
Beobachter-SHA-256: `f34ea1644f0d782a358587c2a80437935bbb2d0940deb7bc9b36ca4349a6f9a1`.

Es gibt eine ausdrückliche Abweichung vom ursprünglich gewünschten
einzigen Freeze: Die erste Fassung, Commit `b39ac44`, scheiterte wegen
eines zu langen temporären Unix-Socketpfads bereits vor Backendbereitschaft.
Alle sieben Startversuche sind unter `results/tenant-background-20261105-01/`
erhalten: kein Backend bereit, kein Modellladebeginn, keine Vorbereitung
oder A/B/C-Versuchsanfrage, kein `trial.json`. Die Korrektur verkürzt nur
den temporären Pfad; Fallplan, C-Profil, Statistikregeln und numerische
Beobachter sind unverändert. Erst die erneut vor Datenerhebung
festgeschriebene zweite Fassung erfasst Messdaten. Die Fehlstarts werden
nicht als erfolgreiche Fälle ausgegeben; keine erhobene Kohorte wurde
wiederholt oder anhand ihres Ergebnisses ersetzt.

## Ergebnisse und Manuskriptentscheidung

### Tatsächliche Last und Integrität

Alle **64 geplanten Messfälle** wurden genau einmal vollständig
ausgeführt: 64 Vorbereitungen, 56 A-Zielantworten, 256 B-Antworten und
64 vollständig beendete C-Streams. Keine Messfehler, Timeouts,
unvollständigen Antworten oder Ersatzfälle. Mit den sieben verworfenen
Startversuchen vor Datenerhebung gab es insgesamt 71 Backendstartversuche.

A meldet in allen 24 warmen Hauptfällen **544 Cachetokens**, in allen
24 kalten und acht anderen-kalten Fällen null. Alle **256 B-Anfragen**
und alle C-Anfragen sind ohne Cachetreffer. Die nicht entfernten
Backend-Diagnosen im Proxylog wurden geprüft: Der festgehaltene
vLLM-Quellcode emittiert `cached_tokens` bei aktivierter Detailoption
nur für positive Treffer. Ein fehlendes Feld allein in den bereinigten
B-Clientantworten wäre hierfür kein Beleg.

C verarbeitet jeweils tatsächlich 548 Prompt- und 256 Ausgabetokens.
Gemessener C-Versand relativ zum ersten B-Versand: −100,51 bis −100,04 ms.
Die erste C-Textausgabe trifft 271,80–372,55 ms nach B-Start ein,
der C-Abschluss nach 5840,86–6217,84 ms. C überlappt B in allen 64 Fällen
für 1074,98–1370,48 ms. Jeweils **22 C-Streamingereignisse vor Bs erster
Vollantwort** und 25–30 während der gesamten offenen B-Gruppe belegen
Fortschritt im relevanten Fenster. Auch alle 56 A-Zielintervalle
überlappen C. Das ist kein Nachweis identischer GPU-Belegung oder
reiner GPU-Kernelzeit.

Die Analyse meldet **null Integritätsfehler**. Alle eingefrorenen Quellen,
Beobachter, Prompts, installierten Backenddateien und 956 vorherigen
Ergebnisdateien sind unverändert. Ein zusätzlicher SHA-256-Manifest bindet
alle 448 neuen Fallartefakte einschließlich Proxy- und Serverlogs.
Backend und Proxy sind beendet; kein Push.

### RQ1 Der gepaarte Cachezustandseffekt bleibt

| Erste vollständige B-Antwort, kalt minus warm | Ergebnis |
| --- | ---: |
| Positive / negative / gebundene Paare | **24 / 0 / 0** |
| Median | **100,73 ms** |
| Geschichtetes 95-%-Paarbootstrapintervall des Medians | **87,14–107,26 ms** |
| Mittelwert; entsprechendes 95-%-Intervall | 98,61 ms; 85,59–111,16 ms |
| Kleinste / größte Paardifferenz | 22,38 / 161,48 ms |
| Einseitiger exakter Vorzeichentest | **p = 5,96 × 10⁻⁸** |

Das vorab festgelegte RQ1-Kriterium ist erfüllt. Die randomisierte
Warm/Kalt-Behandlung verändert Bs beobachtete Antwortzeiten unter
demselben öffentlichen C-Lastplan in der erwarteten Richtung. Gleiche
tatsächliche GPU-Auslastung wird nicht vorausgesetzt. Ein positiver
Paareffekt beweist keinen Erfolg einer einzelnen festen Entscheidung.

### RQ2 Kalibrierung verloren bei erhaltener Ranginformation

| Serie | T1 Accuracy / BA | T1 AUC | T2 Accuracy / BA | T2 AUC |
| --- | ---: | ---: | ---: | ---: |
| Bisher unbelastet, 16 Hauptfälle | 87,50 % (14/16) | 1,000 | 100 % (16/16) | 1,000 |
| **Feste C-Last, 48 Hauptfälle** | **50,00 % (24/48)** | **1,000** | **50,00 % (24/48)** | **1,000** |

Beide Klassifikatoren sagen in allen 48 Hauptfällen „kalt“: je 24 kalte
richtig und 24 warme falsch. Die alten Entscheidungsgrenzen übertragen
sich nicht. Trotzdem ordnen beide unveränderten Scores alle warmen
Hauptfälle vor allen kalten ein. **AUC 1,00 bei BA 0,50 ist kein
Widerspruch:** Die Ranginformation bleibt, während die Grenze Score=0
für die neuen absoluten Zeiten unpassend liegt. Eine neue Grenze wurde
weder gesucht noch ausgewertet.

Die vorab definierten Paarbootstrapintervalle sind bei beiden
Beobachtern BA **[0,50; 0,50]** und AUC **[1,00; 1,00]**. Sie
degenerieren bei konstanten Entscheidungen beziehungsweise perfekter
empirischer Rangtrennung und garantieren keine entsprechenden Werte
für neue Fälle. Das RQ2-Kriterium belastbarer **fester Klassifikation**
ist nicht erfüllt; ein Verschwinden der Seitenkanalinformation wäre
angesichts der AUC ausdrücklich falsch.

Die alten Wilsonintervalle der Accuracy betragen T1 64,0–96,5 % und
T2 80,6–100 %. Die alte T2-AUC wurde hier lediglich aus dem unverändert
rekonstruierten Score auf den alten Daten berechnet. Unterschiedliche
Stichprobengrößen und Messsitzungen erlauben keinen neu randomisierten
kausalen Last-an/Last-aus-Vergleich. Die kausale RQ1-Auswertung erfolgt
innerhalb der neuen Warm/Kalt-Paare.

### Kontrollen und Spezifität

| Kontrolle unter C-Last | Erste B-Antwort, Median | T1 „kalt“ | T2 „kalt“ |
| --- | ---: | ---: | ---: |
| Keine A-Zielanfrage | 1027,31 ms | 8/8 | 8/8 |
| Andere kalte A-Arbeit | 1143,21 ms | 8/8 | 8/8 |

Die neuen Hauptmediane liegen bei 1044,90 ms für warmes und 1138,32 ms
für kaltes A. Die andere kalte Arbeit sieht ähnlich wie das kalte Ziel
aus; dies ist deskriptiv und kein Äquivalenztest. Zudem genügt unter
C-Last die Situation ohne A-Zielanfrage für die alte „kalt“-Entscheidung.
Ergebnis D muss daher unabhängig von B berichtet werden: Weder
Dokument-A-Zugriff noch As Anwesenheit ist daraus eindeutig identifizierbar.
Im alten unbelasteten Test wurden alle vier Abwesenheitskontrollen
„warm“ und alle vier anderen kalten Kontrollen „kalt“ genannt.

### Zulässiger C2-Claim und Abschluss

**C2 darf beanspruchen:** Unter einem festen, tatsächlich überlappenden
zusätzlichen Inferenzlastprofil beeinflusst As privater Cachezustand
weiterhin Bs eigene vollständige Antwortzeiten trotz getrennter Salts
und null B-Hits. Der Paareffekt und die Score-Rangtrennung bleiben
beobachtbar, während die bisherigen festen Einzelkohortenentscheidungen
ihre Kalibrierung verlieren. Die Inferenz bleibt konditional auf bekannte
A-Zielarbeit und ist nicht dokumentenspezifisch.

Geeigneter englischer Ergebnissatz:

> Under one fixed competing inference workload, all 24 cold-minus-warm
> pairs remained positive (median 100.73 ms; paired 95% interval
> 87.14–107.26 ms). Both previously specified observers retained AUC 1.00
> but classified every case as cold, reducing balanced accuracy to 50%.
> This separates persistent cache-dependent timing information from
> transfer of a calibrated decision rule. Absent-target and unrelated-work
> controls prevent document-specific or presence-inference claims.

Kein produktionsweiter Robustheitsnachweis, keine Gleichheit realisierter
GPU-Auslastung und keine Aussage gegen beliebige andere Angreifer.
Die Daten gelten für dieses Modell, diese GPU, Loopback und genau
dieses eine C-Profil. Vorzeichentest und Bootstrap ersetzen keine
Prüfung anderer Populationen oder zeitlicher Abhängigkeit.

**Die Forschung für C1/C2 ist beendet.** C1 wurde ausschließlich anhand
vorhandener Proxy-Traces ergänzt (`paper/c1-proxy-mechanism-20261105.json`),
ohne weiteren GPU-Test. Nächster Schritt ist Schreiben und Satz des
fünfseitigen englischen ICCAI-Papers mit C1/C2 als Hauptbeiträgen.

## Reproduktionspfade

Ergebnisbasis: `results/tenant-background-20261105-02/`.

- `protocol.json`, `commit.json`, `observers.json`, `salts.json`,
  `prompts.json`, `source/`: festgeschriebener Plan und alte Beobachter.
- `case-00` bis `case-63`: je `start.json`, `status.json`, `trial.json`,
  `proxy.jsonl` sowie Client-, Proxy- und Serverlog. C-Streamingzeitpunkte
  und tatsächliche Anfragezeiten stehen in `trial.json`.
- `analysis.json`: eingefrorene RQ1-/RQ2-Auswertung und Kontrollvorhersagen.
- `paired-effects.csv`, `case-observations-and-load.csv`: Paardifferenzen,
  B-Zeiten, feste Scores und tatsächliche Lastzeiten.
- `verification.json`, `load-verification.json`, `raw-manifest.json`:
  Integrität, zusätzliche Lastnachweise und Hashes aller Fallartefakte.

Messclient: `src/tenant_background_case.py`, Supervisor:
`src/tenant_background_run.py`, Analyse:
`src/tenant_background_analysis.py`. Maßgeblich ist der Code-Snapshot des
aktiven Commits. Offline-Reproduktion mit einer Kopie des Ergebnisordners
ohne bestehende `analysis.json`/`verification.json`; `analyze` trainiert
nichts und verweigert das Überschreiben dieser Dateien. Alte Daten:
`results/tenant-offset-20261103/`; ausschließlich alte Trainingsquelle:
`results/tenant-scheduler-20261103/dev/trials.jsonl`.
