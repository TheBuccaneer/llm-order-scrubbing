# Geschützter Prefill mit normalisiertem Übergang zu gemeinsamem Decode

Stand: 03.11.2026. Ergebnis der Literaturabgrenzung und des Offline-
Machbarkeitstests. Ausgangscommit: `f0d7b68`; alte Rohdaten unverändert.

**Nachtrag nach konstruktivem Folgeauftrag:** Die unten noch als fehlend
bezeichnete Zustandsnormalisierung wurde anschließend tatsächlich
implementiert und auf der GPU geprüft. Aktueller ausführbarer Stand,
Bytegleichheitsprüfung, HTTP-Schnittstelle und Kosten stehen in
[Protected Prefill Prototyp](protected-prefill-prototyp-20261103.md).
Das folgende Neuheitsurteil dokumentiert den Stand **vor** dieser
Implementierung; die neue technische Leistung wird nicht vorab als
wissenschaftlich neu oder kostenoptimal ausgegeben.

**Korrigierte Forschungsentscheidung nach Neuheitsnachprüfung:** Der
vorliegende Text ist ein technischer Entwurf mit **nicht belegter
Methodenneuheit**, keine bereits wissenschaftlich abgegrenzte
Contribution-Kandidatin. Er kombiniert bekannte Isolation, öffentliche
Grenzen, Zustandsnormalisierung und anschließendes Batching. Seine zentrale
Normalisierung ist als Anforderung benannt, aber noch nicht konstruiert.
Der bedingte Beweis unten setzt genau diese ungelöste Anforderung voraus.
Auch unabhängig vom fehlenden SIDE-Volltext rechtfertigt das noch keinen
C2-Claim. Die Offlinebefunde bleiben gültig; ein neuer Schutzmechanismus
oder dessen Kostenüberlegenheit folgt daraus nicht.

## Neuheitsurteil und geprüfte Erweiterungen

Die Originalstellen grenzen die Bausteine ab: Accumulate-and-Serve §V
liefert Pufferung und getrennte Bedienung, IFS §§3–4 selektiven Schutz
einschließlich ungenutzter privater Slots, Time Protection §§3.2/4.3
deterministische Zustandsübergänge und Pacer §§3–4 den Schutz des
tatsächlichen Ausgabepfads. Sarathi-Serve §§4.1–4.2 liefert phasenbewusstes
Batching. Keine dieser Quellen ist ein identischer LLM-Gesamtalgorithmus;
daraus folgt aber noch keine neue wissenschaftliche Eigenschaft unserer
Kombination.

Die nächste substanzielle Erweiterung wurde präzisiert: ein **konstruktiv
hergeleiteter hinreichender Übergangszustand**, der weniger Isolation als
volle Tenant-Trennung erfordert. Dafür müsste gezeigt werden, welche
konkreten Variablen normalisiert werden, welche bestehen bleiben dürfen
und warum ihr Einfluss unter allen erlaubten Probes begrenzt ist. Die
bisherige Aufzählung „Queues, KV, Fortschritt, Konten“ erfüllt das nicht.
Ein lediglich vorausgesetzter äquivalenter Zustand ist die zu lösende
Aufgabe, keine Lösung. Der generische Coupling-Schluss und `q_0+q_1` sind
ebenfalls kein neuer Grenzbeitrag.

Zwei naheliegende Ausweichvarianten tragen derzeit nicht: Treffer durch
Dummyarbeit auf Kaltarbeit aufzufüllen ist als Constant-work-Prinzip
bekannt; trefferbedingt freie Kapazität fremden Probes zu geben kann
gerade deren Servicefortschritt verraten. Eine Freigabefrist darüber
liefert zunächst wieder eine bekannte Paddingkonstruktion. Keine dieser
Varianten wird ohne neue konkrete Eigenschaft umbenannt und implementiert.

**Zusätzliche notwendige Baseline:** die privaten Prefixhits geschützter
Requests gezielt ignorieren und den Prompt neu berechnen. Die installierte
vLLM-0.17.1-Engine besitzt dafür den internen Pfad
`request.skip_reading_prefix_cache`; `KVCacheManager.get_computed_blocks()`
gibt dann leere Treffer und null wiederverwendete Tokens zurück
(`vllm/v1/core/kv_cache_manager.py`, Zeilen 164–181).
Das ist ein vorhandener Enginepfad, kein neuer Algorithmus und noch keine
geprüfte öffentliche HTTP-Option. Der Eingriff entfernt im logischen
Modell die cacheabhängig ausgelassene Prefillarbeit; vollständige
End-to-End-Vertraulichkeit trotz anderer Restzustände ist damit nicht
bewiesen. Kosten und Schutz wurden hier nicht live gemessen. Ein späterer
Methodenvergleich muss auch diese einfache Alternative berücksichtigen.

**Stand des Auftrags:** Die Literaturprüfung hat bekannte Bausteine und
ungerechtfertigte Claims eingegrenzt. Sie hat bislang weder eine
belastbar eigenständige neue Methode noch eine neue scharfe Grenze
geliefert. Die frühere Bezeichnung als „begründbare Methoden-Kandidatin“
war deshalb zu weitgehend. Eine Wiederholung des Offline-Replays löst
diese Neuheitslücke nicht. Die folgenden Abschnitte dokumentieren den
Entwurf und die weiterhin verwertbaren Berechnungen.

## 1 Schutzvertrag

Das Geheimnis `S ∈ {kalt,warm}` bezeichnet, ob As **identische bekannte
Zielanfrage** unmittelbar vor ihrer Ausführung einen privaten Präfixtreffer
hat. In den vorliegenden Hauptfällen sind dies 0 gegenüber 544 gecachte
Tokens. Anwesenheit, Anfrageidentität und das begrenzte Aktivitätsfenster
werden nicht verborgen. Die andere kalte Anfrage und Abwesenheit sind
Kontrollen, keine zusätzlichen Klassen des zu schützenden Geheimnisses.

Öffentlich `P` sind Modell/Version, Prompt- und Ausgabelängenklasse,
Anfragekontingente, Tenantidentitäten, externe Einreichungsereignisse,
zugesicherte Epochentermine und B-eigene Anfragen. As tatsächlicher Start
innerhalb des Fensters ist B unbekannt; er wird zwischen den beiden
Geheimnissen gleich gekoppelt. Nicht öffentlich sind Trefferlänge,
Restarbeit, Fertigstellungsereignisse und daraus abgeleitete Belegungen.
Ein Zeitstempel **nach** gemeinsamem geheimnisabhängigem Queueing wird
nicht durch Benennung zum öffentlichen, unabhängigen Ereignis.

B sieht seine eigenen Sende- und vollständigen Empfangszeiten, IDs,
Reihenfolgen, Status, Antwortlängen und Antwortinhalte. Die bisherigen
Angreifer nutzen deren Zeit-/Ranganteil; vollständige Body-Gleichheit wurde
in diesen Tenant-Dateien nicht geprüft. Cachezähler, A-Zeiten und interne
Schedulerlogs bleiben Diagnosematerial. B darf sein authentifiziertes
öffentliches Kontingent ausschöpfen, einschließlich wiederholter Probes;
eine Sicherheitsbehauptung nur für einen eingefrorenen Klassifikator
genügt nicht. Sybil-Tenants und Last jenseits des Kontingents benötigen
einen separaten Vertrag.

Angestrebte Eigenschaft für jede zugelassene B-Strategie `b`:

\[
\operatorname{TV}\bigl(\mathcal L(O_B\mid S=0,P,b),
\mathcal L(O_B\mid S=1,P,b)\bigr)\leq\varepsilon.
\]

Für gleiche Klassenprioren ist die optimale Balanced Accuracy dann
höchstens `(1+ε)/2`. Die Accuracy eines getesteten Angreifers liefert
keine obere Schranke für ε. Wiederholungen müssen im gesamten Transcript
enthalten sein; ein Einzelfallvertrag schützt nicht automatisch eine
unbegrenzte Zahl weiterer Abfragen.

Die Lücke zur Latenzisolation lässt sich ohne neue Angriffsannahme
präzisieren: Für dieselbe isolierte B-Referenzzeit `d` erfüllen die
deterministischen Zeiten `d+δ/3` bei kalt und `d+2δ/3` bei warm beide
die Obergrenze `d+δ` für jedes `δ>0`. Trotzdem sind ihre Zeitverteilungen
disjunkt: TV ist 1, optimale BA ist 1. Auch beliebig kleine positive
Latenztoleranz impliziert somit keine kleine Leakage. Dies ist ein
Gegenbeispiel zur behaupteten Implikation, **kein** Angriffsnachweis gegen
die FairInference-Implementierung und kein neuer allgemeiner Lehrsatz.

Der Verteidiger darf intern Cachehits nutzen, **wenn deren Einfluss auf
beobachtbare Entscheidungen eingeschlossen bleibt**. Admission, fremde
Ausführungsgelegenheiten, öffentliches Kostenkonto und Rückfallpolitik
dürfen den Treffer nicht indirekt verraten. Zu den Kosten gehören As und
Bs End-to-End-Latenz, Admission-/Enginewartezeit, Pufferzeit, ungenutzte
GPU-Zeit, Speicherreservierung und Fehler/Spätfälle. Geringe lokale
Accuracy ist eine Messung; die obige Aussage verlangt zusätzliche
Modellannahmen und einen Beweis.

## 2 Was die starke einfache Baseline bereits kann

Programm und vor Ausführung gespeicherter Plan:
`src/tenant_release_feasibility.py` und
`tenant-release-replay-protokoll-20261103.md`.
Die Auswertung liest insgesamt **240 alte Gruppen / 960 B-Antworten**:
vier Bedingungen mit je 18 Entwicklungs- und 36 Prüffällen sowie
24 Fälle mit verborgenem A-Start. Die Daten waren schon früher bekannt;
„Prüfung“ bezeichnet die alte Aufteilung, keinen neuen prospektiven Test.

Für erste Proxyankunft `a`, eigene Ankunft `a_i` und vollständigen
Backend-HTTP-Eingang `c_i` werden drei bekannte Regeln verglichen:

| Regel | Vorab aus alter Entwicklung festgelegter Solltermin |
| --- | --- |
| Gemeinsamer Termin | `a + D + 2(i−1) ms`, öffentliche Sendereihenfolge |
| Individuelle gleiche Frist | `a_i + D_ind` |
| Vier öffentliche Einzeltermine | `a + d_i`, abhängig nur vom Senderang |

Kalibrierung nimmt Maxima über **alle** Entwicklungszustände und
Kontrollen, rundet auf 10 ms auf und friert die Termine ein. Der letzte
Test verwendet allein die alte frische-Salts-Direktentwicklung:
`D=1270 ms`, `D_ind=1240 ms`, `d=(1080,1100,1130,1270) ms`.
Die reale Client-zu-Proxy-Vorlaufzeit bleibt im Replay erhalten;
Egress und Netz sind idealisiert. Bei Überschreitung gilt explizit der
unsichere Sofortfallback `r_i=max(Solltermin,c_i)`.

| Alte Prüfserie und Policy | Späte Gruppen / Antworten | B-Zusatzwartezeit Median / P95 | Modellierte B-E2E Median |
| --- | ---: | ---: | ---: |
| Frische Salts, direkt, gemeinsamer Termin | 0/36 / 0/144 | 302,57 / 377,35 ms | 1258,51 ms |
| Frische Salts, direkt, individuelle Frist | 0/36 / 0/144 | 294,36 / 347,35 ms | 1240,53 ms |
| Frische Salts, direkt, vier Termine | 0/36 / 0/144 | 164,03 / 315,71 ms | 1100,53 ms |
| Feste Salts, direkt, individuelle Frist aus eigener Entwicklung: 1220 ms | 0/36 / 0/144 | 268,47 / 327,78 ms | 1220,54 ms |
| Verborgener A-Start, gemeinsamer Termin | 0/24 / 0/96 | 249,82 / 341,52 ms | 1258,70 ms |
| **Verborgener A-Start, individuelle Frist** | **0/24 / 0/96** | **222,58 / 311,52 ms** | **1240,74 ms** |
| Verborgener A-Start, vier Termine | 3/24 / 4/96 | 132,11 / 280,36 ms | 1102,14 ms |

Alle Kosten enthalten Kontrollen. Die vier Termine haben Spätfälle in
**2/8 kalten Hauptfällen** mit drei Antworten und **1/4 anderen kalten
Kontrollen** mit einer Antwort; warm und abwesend jeweils null. Die
niedrigere Wartezeit darf deshalb nicht als gleichwertiger Schutz gelten.
Für die individuelle Frist im Offset-Test beträgt die mediane B-Wartezeit
warm **282,29 ms**, kalt **159,74 ms**; ihr Mittel über alle Antworten
ist **218,82 ms**. Von den anderen Serien hat frische-Salts-BOS bei
Kalibrierung auf seiner eigenen Entwicklung ebenfalls Spätfälle: ein
Prüffall, bei der Vierterminregel zwei Antworten. Ein Entwicklungsmaximum
ist keine Lastgarantie.

Die diagnostisch nötigen Deckungsschwellen der 24 Offset-Spuren sind
1255,127 ms nach erster Proxyankunft beziehungsweise 1225,197 ms nach
eigener Ankunft. Diese Zahlen verwenden Prüfcompletions und sind
**keine zulässige nachträgliche Policywahl**. Die beobachtete
Viertermin-Hülle ist `(1091,388; 1103,321; 1124,761; 1255,127) ms`.

**Faire A-Kosten:** Für den festen B-only-Anfrageplan bleibt A
unverzögert, Zusatzwartezeit null. A ist kein obligatorisches Mitglied
eines B-Freigabeblocks. Eine symmetrische Frist ist eine andere Policy;
die JSON-Datei weist sie separat anhand von As Clientempfang als
Bereitschaftsersatz aus. Ein A-Clientempfang ist keine intern gemessene
Backend-Fertigstellung. Der künftige Scheduler muss As zusätzliche
Admission-/Enginewartezeit vollständig anrechnen.

Neu trainierte Logistik-, RBF- und Random-Forest-Beobachter verwenden
vier B-Empfänge, eigene Sendeabstände und Ränge. Auf den 16 Offset-
Hauptfällen erzielen alle drei im unveränderten Trace BA/AUC 1,0;
unter modellierter individueller Frist liegen die BA bei 0,3125–0,375
und AUC bei 0,2578–0,3125. Unterhälftige Werte werden **nicht** als
negative Leakage interpretiert oder nach Testlabels umgedreht. Die
paarweisen Bootstrapintervalle stehen in `verification.json`.

Eine wichtige Gegenkontrolle: Bei der alten frische-Salts-Direktprüfung
erreicht der RBF-Beobachter selbst nach vollständig gedeckter Gruppen-
oder Vierterminfreigabe BA 0,65625 und AUC 0,69531. Die idealen Zeiten
enthalten noch Client-zu-Proxy-Vorlauf und eigene Sendestreuung; der
skalierte Beobachter kann diese kleinen Unterschiede verwenden. Damit
ist **auch null Spätantworten kein Beweis für einen vollständigen
Clientschutz**. Aus acht Fällen pro Zustand lässt sich ohnehin keine
kleine maximale Fehlerrate ableiten: Selbst unter einer hier nicht
belegten IID-Annahme erlaubt 0/8 ein einseitiges 95-%-Oberlimit von
31,2 % für die Spätrate.

**Antwort auf Phase A:** Es gibt beobachtete Kosten und eine
Transfergrenze engerer Freigabepläne. Es gibt **keinen Nachweis**, dass
die starke einfache individuelle Frist unzureichend oder durch unseren
Scheduler dominiert ist. Sie kostet im Offset-Replay median 222,58 ms,
verzögert A nicht und deckt alle vorliegenden Antworten. Diese Baseline
ist die Hürde. Die ältere, deutlich kleinere BOS-Wartezeit bietet hier
keinen vergleichbaren Cachezustandsschutz.

Durchsatz, echte GPU-Auslastung, neue Backend-Completions und Kosten
voller Isolation sind aus diesen Traces nicht rekonstruierbar.
Antwortfreigabe beeinflusst in einem echten Dienst künftiges Nachsenden,
Queueing, Ressourcen und eventuell die nächste Epochengrenze. Es folgt
keine Produktions- oder Sicherheitsgarantie aus diesem Replay.

## 3 Der verbleibende Schutz und Kostenkonflikt

Die [Novelty-Matrix](security-novelty-matrix-20261103.md) schließt die
einfachen Neuheitsbehauptungen aus. Gesucht wird präziser:

> Wie kurz kann die Zeit sein, in der cacheabhängige private Ausführung
> von fremdem Service getrennt werden muss, wenn nach diesem Zeitraum
> wieder gemeinsame Decode-Batches zulässig sein sollen und beide
> Mandanten ein begrenztes Latenzbudget behalten müssen?

Eine feste Release-only-Frist verändert die konkurrierende GPU-Arbeit
nicht. Vollständiges öffentliches Tenant-TDMA unterbindet außerdem
mögliche gemeinsame Decodeeffizienz. Ein bloßes Prefill-Gate kann
jedoch früheres Decode, Batchgröße, Warteschlangen oder Speicherzustand
weitergeben. Der mögliche neue Gegenstand ist deshalb die **hinreichende
und kostengünstig realisierbare Zustandsnormalisierung vor dem Teilen**.
Dass gleiche Zustände gleich weiterlaufen, ist kein neuer Satz.

## 4 Technischer Entwurf ohne belegte Methodenneuheit

Die erste Konstruktion bedient eine begrenzte öffentliche Kohorte auf
einer GPU. Sie schützt nur deren anfänglichen Cachezustand. Öffentliche
Längenklassen und Kontingente begrenzen Prompt- und Decodebedarf;
Prefix-Salts bleiben getrennt. Bis zum Ende der Kohorte kommt keine
neue Prefill-Arbeit in deren gemeinsames Decode. Ein allgemeiner
Continuous-Batching-Dienst ist damit noch nicht konstruiert.

Für den ersten Vertrag gelten eine bekannte A-Zielanfrage und höchstens
vier B-Requests, jeweils höchstens 16 Ausgabetokens; die vorhandenen
548-/554-Token-Prompts sind getrennte öffentliche Längenklassen. Ein
öffentliches Intake-Fenster W muss die zugelassene 450-ms-Startvariation
aufnehmen. Mit Tenantbudgets `p_t` und festen Drain-/Normalisierungsreserven
`g_t` ist `J=e+W+Σ(p_t+g_t)` vorab festgelegt. Bei gemeinsamer
Decodeobergrenze `D_max` gilt als symbolisches Verfügbarkeitsbudget
`L_r ≤ J+D_max−a_r`, wobei `a_r` das externe Intakeereignis ist.
Die dafür nötigen Phasenobergrenzen sind noch nicht gemessen oder
bewiesen; heutige E2E-Traces dürfen sie nicht ersetzen. Erfolgreiche
Antworten müssen vollständig und echt sein; Dummy-/Teilantworten zählen
nicht als erfolgreiche Fertigstellung. Fehler und Overruns werden
vollständig berichtet und nicht aus der Kostenstatistik entfernt.

```text
COLLECT(e):
    Kohorte am öffentlichen Intake-Ende schließen.
    Nach öffentlicher Tenant-ID/Sequenznummer und Kontingent auswählen.
    Worst-case-KV-Kapazität reservieren; Kostenkonten öffentlich belasten.
    Tenant-Fenster [u_t, v_t) und Join-Zeit J öffentlich festlegen.

PREFILL(t) in [u_t, v_t):
    Nur t darf GPU-Arbeit der geschützten Kohorte ausführen.
    Privaten Prefixcache nutzen; bis zur kanonischen Grenze vorgehen:
        voller Prompt verarbeitet, genau ein erstes Ausgabetoken erzeugt.
    Dann Request parken. Kein vorgezogenes fremdes Decode,
    kein Verleihen trefferbedingt freier Restzeit an fremde Requests.
    Andere Tenant-Fenster beginnen unverändert an ihrer Sollzeit.

JOIN bei der öffentlichen Zeit J, einschließlich fester Drain-Reserve:
    Kanonische Queue-/KV-/Fortschrittsdeskriptoren herstellen.
    Erst nach erfülltem Zustandsvertrag in gemeinsamen Decodepool übergeben.

SHARED_DECODE:
    Gemeinsame Decode-Batches der Kohorte ausführen.
    Keine Abhängigkeit mehr von alten Hit-/Miss-Kostenkonten zulassen.
    Fertige Vollantworten regulär freigeben, soweit der Zustandsvertrag gilt.

OVERRUN:
    Verletzung des Schutzvertrags protokollieren und als solche auswerten.
    Kein cacheabhängiges Weiterreichen bereiter Teilkohorten als sicher ausgeben.
```

`OVERRUN` ist **keine fertige sichere Fehlerbehandlung**. Exakte
Nichtinterferenz setzt voraus, dass öffentlich zugelassene Arbeit die
Fenster sicher einhält. Empirisch profilierte Kaltmaxima beweisen das
nicht. Bei probabilistischen Budgets zählt jede Überschreitung zum
expliziten Leakage-/Verfügbarkeitsrisiko. Ein globaler Fehler genau dann,
wenn etwas spät ist, kann ebenfalls das Geheimnis verraten.

## 5 Was am Übergang wirklich gleich sein muss

Für die beiden Welten dürfen gleich lange Prompts allein nicht als
gleichwertiger Enginezustand gelten. Erforderlich sind mindestens:

- Gleiche aktive Requests, Promptfortschritte und Decode-Tokenindizes;
  gleiche Verteilung der ersten Tokens und der späteren Samplingzustände.
  Cache-Reuse und Neuberechnung können andere numerische Ausführungspfade
  nutzen; Token-/KV-Gleichwertigkeit ist eine zu prüfende Voraussetzung.
- Gleiche B-relevante KV-Kapazität, freie/allokierte Blöcke, Appendkosten
  und Preemptionmöglichkeiten. Namensraumsalts allein partitionieren weder
  Kapazität noch Allocator-/Evictionmetadaten. Nicht mehr erreichbare
  A-Cachehistorie darf nur bestehen bleiben, wenn sie B nicht beeinflusst.
- Gleiche Quoten, Prioritäten, Queueordnung und virtuelle Servicekonten.
  Einsparung durch warmen Prefill darf kein später nutzbares fremdbeobachtbares
  Guthaben hinterlassen. Reservierung berücksichtigt volle öffentliche Längen.
- Kein ausstehender A-Kernel, Async-Step, Transfer oder Callback über eine
  Fenstergrenze; die Übergangsdauer selbst ist öffentlich begrenzt.
- S-unabhängige Restwirkung von CPU-/GPU-Zustand, Takt/Temperatur,
  Speicherhierarchie, Frontend und Egress. Für einen rein logischen
  Schedulerbeweis ist dies eine explizite Abstraktion, keine bewiesene
  Eigenschaft der RTX 3090. Ein End-to-End-Claim erfordert ihre Validierung.

Gleiche Dekodierverteilungen erlauben nach J auch variierende Batchgrößen
oder Early-EOS, **wenn** diese in beiden S-Welten gleich gekoppelt sind.
Bei geheimem Promptinhalt oder geheimer Ausgabelänge entfällt diese
Begründung. Dann müsste das spätere Decode zusätzlich geschützt werden.
Unser enges Cachezustandsziel darf nicht stillschweigend erweitert werden.

## 6 Begrenzte formale Aussage

Unter gemeinsam gekoppelten öffentlichen Eingaben/Zufallsquellen sei
(i) Bs Transcript bis J gleich, (ii) der B-relevante Zustand bei J in
beiden Welten äquivalent und (iii) jede folgende Engine-/Ausgabetransition
erhalte diese Äquivalenz. Dann stimmen die B-Transcripte vollständig
überein: Bis J folgt dies aus (i), nach J induktiv aus (ii) und (iii).
Bei adaptivem B erzeugt dasselbe bisherige Transcript dieselbe nächste
B-Aktion; die Induktion bleibt unter öffentlichen Kontingenten erhalten.

Wenn ein solches Coupling außerhalb von Overrun-/Normalisierungsfehlern
funktioniert und deren Wahrscheinlichkeiten in Welt s durch `q_s`
beschränkt sind, folgt aus Coupling-Ungleichung und Vereinigungsabschätzung

\[
\operatorname{TV}(O_B^0,O_B^1)\leq q_0+q_1.
\]

Weitere nicht abgedeckte Kopplungsfehler müssen zusätzlich eingerechnet
werden. Das ist eine **bekannte generische Beweistechnik**, keine neue
LLM-Untergrenze. Die wissenschaftliche Arbeit wäre, die Voraussetzungen
mit einem kleinen realen Zustandsvertrag zu erfüllen und Kosten zu sparen.
Null beobachtete Overruns liefert hier keine kleine populationsweite
Schranke auf `q_s`.

## 7 Sicherheitsprüfung und technische Eingriffstiefe

| Prüfpunkt | Konsequenz für den Kandidaten |
| --- | --- |
| Treffer verändern Admission oder Folgekohorte | Intake und Quoten dürfen nur öffentliche deklarierte Arbeit zählen; kein hitabhängiges Nachrücken. |
| Warmer Prefill beginnt früher zu decodieren | An der ersten Tokenfrontier parken; kein Fremdbatch vor J. |
| Freiwerdende GPU-Zeit verrät Treffer | Reservierte Zeit nicht vor J fremd verleihen; allfällige Energieersparnis ist kein Durchsatzgewinn. |
| Spätantwort, später Fensterbeginn oder -schluss | Öffentliche Grenzen wirklich einhalten; Overruns als Fehler/Risiko zählen. Warten bis „alle bereit“ ist kein öffentlicher Join. |
| B sendet zusätzliche Probes | Sämtliche Requests desselben authentifizierten Tenants durch dieselbe Gate-/Quotenregel führen; kein direkter Backend-Bypass. |
| Weiterwirkende Cache-/Allocatorhistorie | KV-Kapazität und Metadaten kontrollieren; bloße Tokenbudgetänderung reicht nicht. |

Der installierte vLLM-0.17.1-Code wurde gelesen: `schedule()` bei
Zeile 317 ff. beschreibt ausdrücklich eine einheitliche Tokenplanung,
keine separat kontrollierten Prefill-/Decodephasen. Bei Zeile 600 ff.
ändert `get_computed_blocks()` den berechneten Fortschritt und damit
das verbleibende Tokenbudget. Laufende Requests werden im nächsten
Schritt weiterbedient. Die vorhandenen HTTP-Clients können dies nach
Admission nicht selektiv stoppen.

[`SchedulerConfig.scheduler_cls`](https://docs.vllm.ai/en/v0.17.1/api/vllm/config/scheduler/)
erlaubt eine eigene Schedulerklasse; die Schnittstelle ist ausdrücklich
nicht stabil. Notwendig wären Tokenauswahl für laufende **und** wartende
Requests, Parken an der Tokenfrontier, Tenantmetadaten, Reservierungen
und ein realer Kernel-Drain an Grenzen. Ein Schedulerhook allein beweist
keine Speicher-/Hardwareisolation. Die Bestandsinstrumentierung kann
später die tatsächlichen Token-/Batchentscheidungen prüfen.
Eine zeitversetzte HTTP-Zulassung wäre daher **kein Prototyp dieser Methode**.
Die installierte Engine wurde heute nicht verändert.

## 8 Möglicher Beitrag und Entscheidung vor Implementierung

Der Kandidat unterscheidet sich von reinem Release durch eine Änderung
der Ausführung **vor** B-Fertigstellung. Gegenüber dauerhafter Tenant-
Trennung teilt er Decode nach einem begründeten Ende der Geheimniswirkung.
Gegenüber Deadline-Fairness verlangt er Verteilungsunabhängigkeit.
Gegenüber selektiven Cacheverfahren behandelt er fremde Konkurrenz ohne
fremde Cachehits. Die Matrix zeigt zugleich: Keine dieser allgemeinen
Gegenüberstellungen allein belegt Neuheit.

Ein Kostenpotenzial besteht nur, falls die zusätzliche Isolation und
Normalisierung kleiner ausfallen als die dadurch ersparte Releasewartezeit
und/oder verlorene Decode-Batchingeffizienz. Für eine Kohorte sei
`P` die öffentliche Prefillreservierung inklusive Übergänge, `D_mix` die
gemeinsame Decodezeit und `D_t` die Decodezeit voller Tenant-Trennung.
`D_mix < Σ D_t` schafft lediglich mögliches Kohortenpotenzial;
**individuelle** Latenzen enthalten Tenantreihenfolge und Warten bis J.
Warmes A kann durch die Barriere erheblich verlieren. Die vorhandenen
Completions enthalten keine separaten Phasenmessungen, aus denen sich
dieser Vergleich zuverlässig berechnen ließe.

Die 450-ms-Unsicherheit ist für diese Kohortenkonstruktion selbst teuer:
Wird die Kohorte erst nach `W=450 ms` geschlossen, bleiben gegenüber
der individuellen 1240-ms-Baseline für die erste B-Anfrage nur ungefähr
**790 ms für reservierten Prefill, Übergänge und gemeinsames Decode**.
Im idealen festen Kohortenablauf wäre `P+D_mix < 790 ms` die Bedingung,
um deren ersten 1240-ms-Termin zu unterbieten. Das ist ein konkreter
Machbarkeitsfilter, kein gemessener Wert. Bei größeren Intake-/Drain-
Reserven schrumpft dieses Budget weiter. Scheitert der Filter oder
steigen As Kosten unverhältnismäßig, rechtfertigt die Phasenidee allein
keine Implementierung als vermeintliche Privacy-Cost-Verbesserung.

Die nächste substanzielle Prüfentscheidung ist deshalb eng:

1. Den minimalen B-relevanten Übergangszustand gegen vorhandene Engine-
   Instrumentierung konkretisieren. Scheitert bereits die logische
   Zustandsäquivalenz, keine vermeintlich sichere Prefill-Abwehr bauen.
2. SIDE im Original abgleichen, sobald zugänglich. Bis dahin bleibt der
   spezifische Abgrenzungsclaim provisorisch; kein weiteres Nachfragen
   beim Nutzer, der keinen Volltext hat.
3. Erst bei tragfähigem Vertrag genau diesen Engineeingriff prototypisieren;
   derselbe kleine Qwen-Versuch vergleicht direkt, BOS, starke individuelle
   öffentliche Freigabe und faire volle zeitliche Trennung. Keine erfundenen
   FairInference-Zahlen, keine neue Angriffskampagne oder Parametersuche.

Der Pilot müsste vorab denselben Privacy-/Overrunvertrag für alle
Policies, unberührte Testdaten und starke neu trainierte Angreifer
festlegen. Als Vorteil zählt ein belastbarer Kostenpunkt bei gleichem
Schutz für **A und B**, oder weniger Isolation bei gleichem vollständigem
Transcriptschutz. Nur ein schönerer Median für B reicht nicht.
Unabhängige Bestätigung und Llama folgen erst nach positivem Qwen-Pilot.

**C1:** präziser Vertrag und kontrollierter vorhandener Befund;
allgemeine Interferenz ist bekannt. **C2:** bisher nur eine Anforderung
an Normalisierung und Ende der Isolation; die eigenständige Konstruktion
fehlt. **C3:** offene Kostenhypothese gegenüber starken einfachen Baselines,
noch unbelegt.
Eine neue allgemeine Unmöglichkeitsgrenze wurde heute nicht gefunden.
Der empirische BOS-/Tenant-Bestand bleibt erhalten, falls C2/C3 scheitern.

## Reproduktion

Die Nachrechnung wurde mit der vorhandenen Pythonumgebung ausgeführt:

```bash
/home/rock/projects/porto/.venv-py313-repair/bin/python \
  src/tenant_release_feasibility.py \
  results/tenant-release-feasibility-NEUER-LAUF
```

Ausgabeordner müssen neu sein. `analysis.json` enthält Terminauswahl,
alle Bedingungen, Kosten, neu trainierte Angreifer und Eingabehashes.
`verification.json` enthält zusätzliche Rechenkontrollen und Unsicherheit;
`literature-sources.json` die geprüften Downloadfassungen. Kein Push,
kein Commit und kein neuer Serverstart in dieser Etappe.
