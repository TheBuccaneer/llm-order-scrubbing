# Logische Nichtinterferenz bei Protected Prefill

Wissenschaftlicher Kurzbericht · 03.11.2026 · vLLM 0.17.1, synchroner v1-Pfad.

**Ergebnis.** Der implementierte Übergang stellt einen hinreichenden
B-relevanten Zustand für cacheunabhängige **logische Fortsetzung** her.
Die benötigte Äquivalenz wird unten aus der isolierten B-Berechnung,
der physischen Kopie, dem Managerneuaufbau und der anschließenden
Workerinstallation hergeleitet. Gleichheit sämtlicher A-Daten ist dafür
nicht notwendig. Der Satz gilt für den erfolgreichen, fehlerfreien
Kohortenpfad im definierten Modell. Er ist **keine** Nichtinterferenzgarantie
für tatsächliche HTTP-Zeitpunkte, Empfangsreihenfolgen oder Fehlerauftreten.
Ein Overrun-Gegenbeispiel widerlegt die entsprechende unbedingte Aussage.

## 1 System und Beobachtungen

Untersucht wird ausschließlich der vorhandene einzelne Scheduler mit
`Pilot.normalize`, `gpu_canonical_copy` und `TenantKVPartition`; der
verworfene Zweistream-Pfad gehört nicht zum Modell. Der lokale HTTP-Dienst
nutzt die ursprüngliche 64-Token-Rechenform; der direkte Enginepilot
zusätzlich die 512-Token-Rechenform. Der Beweis umfasst beide bei jeweils
festen, vergleichsgleichen Einstellungen.

Ein öffentlicher beziehungsweise vergleichsfixierter Kontext U enthält
die fünf Requestidentitäten und ihre Reihenfolge, die Prompts mit je 548
Tokens, Samplingparameter, Modellgewichte und Backend, Termine und Quoten.
Genau ein A- und vier B-Requests sind zugelassen. Sampling ist greedy;
`min_tokens=max_tokens=16`, kein Streaming, keine Stopregel,
Async-/Spec-/Transferpipeline, LoRA, Multimodalität oder externe
Abbruchoperation. Der Kontext ist derselbe in beiden Ausführungen; allein
As privater Cache variiert. Dies ist keine Aussage über variierende
A-Promptgeheimnisse. Bs Manager beginnt nach dem verpflichtenden Reset
leer; A darf die kontrollierte private Vorbereitung verwenden.

Der konkrete Zustand lässt sich schreiben als

$$S=(R,Q,K,G,W,D,T,E,H,\mu).$$

R sind Requestdaten und Fortschritt, Q die Queues, K der physische
KV-Speicher, G die Manager, W Worker- und Samplingzustände, D die
anfragebezogene Ausgabeaufbereitung, T Termine/Phasen, E Fehler.
H enthält nur intern ausgelesene Historie/Statistik; μ bezeichnet
Hardware-, Betriebssystem- und Netzwerkzustände.

**B-Beobachtung im Satz** ist die nach Request indizierte Zuordnung der
erfolgreichen B-Antworten, einschließlich Tokens/Text, Finishgrund und
öffentlichen Tokenzählern, sowie der logische B-Schedulingverlauf des
Enginekerns nach Join. Private Prefillschritte sind unsichtbare τ-Schritte;
ihre Anzahl wird nicht beobachtet. Der öffentliche Join trägt den Marker J,
keinen gemessenen Zeitpunkt. Tatsächliche Sendereihenfolge konkurrierender
HTTP-Threads und reale Ankunfts-/Antwortzeiten werden nicht durch diese
Beobachtung abstrahiert und gleichzeitig als geschützt ausgegeben: Sie
liegen ausdrücklich außerhalb des bewiesenen Beobachters.

### Für B relevante Zustandsprojektion

| Bestandteil | Für die Fortsetzung erforderlicher Vertrag |
| --- | --- |
| Gemeinsame Steuerung | Geschlossene Requestmenge, feste Queue-/Batchordnung, Phase, fixe Parameter und Tokenbudgets; keine Arbeit aus der geschützten Phase, höchstens derselbe neu vorbereitete Decode-Aufruf. |
| Fortschritt aller fünf Requests | Berechnete Positionen und Tokenanzahl, aktiv/beendet und maximale Fortsetzung, keine Spec-Tokens, Platzhalter oder Preemptions. As privater Terminalgrund ist ausgenommen. |
| B-Inhalte | Prompts, bisherige Ausgabetokens, gültige B-KV-Werte, Detokenizer-/Ausgabezustand und Samplingparameter. |
| B-Ressourcen | Eigene Blocktabellen, feste Adressen/Kapazitäten, Referenzen, Cacheindex und freie Listen. |
| A-Ressourcenhülle | Ausreichend bereits reservierte Kapazität für die gesamte feste Fortsetzung; A darf keinen Allokationsfehler mit globaler Preemption auslösen. |
| Worker | B-Tokenhistorie und aktive Zeilen, rekonstruierte Blocktabellen, gemeinsame Batchgeometrie; leere ausstehende Ausführung und greedy Sampling. |
| Termine und Fehler | Öffentliche J-/Fensterparameter; Erfolg versus Fehler darf nicht stillschweigend aus dem Beobachtungsmodell verschwinden. |

As private Token-/KV-Werte, eigene spätere Hashwerte und der historische
Trefferzähler sind keine B-Eingaben des hier begrenzten Decoders. Ihre
Gleichheit wird nicht verlangt. Der Code stellt teilweise stärkere
Gleichheit her, insbesondere auch kanonische A-Adressen. Eine global
kleinstmögliche Projektion wird nicht behauptet; die Tabelle beschreibt
die für den untersuchten Daten-/Kontrollfluss geschlossene Projektion.

An den entsprechend phasengleichen Übergangspunkten definieren wir

$$S\approx_B S'\iff C(S)=C(S')\land V_B(S)=V_B(S')\land
G_B(S)=G_B(S')\land W_B(S)=W_B(S')\land
\operatorname{Reserve}_A(S)\land\operatorname{Reserve}_A(S').$$

C ist die gemeinsame Steuerung einschließlich aller Fortschrittshüllen,
V_B enthält gültige B-Inhalte und Ausgabezustände, G_B die B-Ressourcen.
C enthält auch den logischen Fehlerstatus, der auf dem Satzpfad OK ist.
W_B bezeichnet die für den nächsten Forward installierten B-Zeilen und
Samplingdaten. Reserve_A bedeutet für aktive A-Requests genügend korrekt
referenzierte private Kapazität ohne Eingriff in B; nach deren Entfernung
ist die Bedingung leer. Am Join ist kein Aufruf ausstehend; beim
Forward-Eintritt ist derselbe neu zugeteilte Aufruf zulässig. Diese
Phasen werden nicht vermischt. Gleichheit von μ, H oder As Nutzdaten
gehört nicht zur Relation.

## 2 Semantik und Vertrauensbasis

Betrachtet wird Qwen2.5-7B-Instruct mit 28 Lagen, ungequantisierten
BF16-Werten, einem FullAttention-KV-Group, FlashAttention, einem GPU,
TP/PP=1 und Eager-v1-Ausführung. Die Modellkonfiguration des verwendeten
Snapshots und der Pilottreiber legen diesen Pfad fest.

Das logische Modell behandelt Tensoroperationen als funktionale,
speichersichere Operationen. Bei identischer Geometrie ist die B-Ausgabe
eine deterministische Funktion der eigenen Token-/KV-Daten und der
festen Gewichte. Aufmerksamkeit liest nur die KV-Blöcke der jeweiligen
Anfrage. Der GPU-Speicherzugriff ist innerhalb eines Modellschritts
ordnungsgemäß synchronisiert; Timing und Ressourcenbelegung sind kein
Ergebnis dieser Funktion.

Das ist ein ausdrücklich vertrauter Operatorvertrag, keine vorausgesetzte
Wiedereintrittsäquivalenz: Qwen2s Embedding, Norm, Projektionen und MLP
arbeiten tokenweise; Attention erhält anfragebezogene Blocktabellen und
Sequenzgrenzen. Greedy Sampling verwendet zeilenweises `argmax` und kehrt
im All-Greedy-Zweig ohne Zufallsziehung zurück. Der konkrete Pfad deaktiviert
gemeinsame Prefixoptimierung durch `get_num_common_prefix_blocks() == [0]`.
Dies begründet den logischen Vertrag, ersetzt aber keinen Beweis der
CUDA-/cuBLAS-/FlashAttention-Implementierungen oder ihrer Bitdeterministik
auf beliebiger Hardware. Die Modellgewichte werden nicht geändert.

Falls eine verborgene Kernel-/Workspaceauswahl trotz gleicher Geometrie
Bs **Ergebniswerte** verändert, ist dieser Operatorvertrag verletzt;
solcher Zustand darf nicht lediglich als Zeitjitter ausgeklammert werden.
Quantisierung und zufälliges Sampling gehören nicht zum betrachteten
Pfad. Bibliotheksinterne funktionale Zustände werden hier weder vollständig
modelliert noch durch die Normalisierung gelöscht. Der Satz ist deshalb
ein Beweis im genannten logischen Modell, keine vollständige Verifikation
des ausführbaren GPU-Stacks. Gemessene Bitgleichheit schließt diese
Verifikationslücke nicht allgemein.

Der Satz bezieht sich auf den **tatsächlich verdrahteten Aufrufpfad**:
`configure_cohort(..., normalizer=pilot.normalize)`. Ein beliebiges callable
als Normalisierer und ein allein gesetztes Diagnoseflag sind kein
Nachweis einer Kopie. Der authentifizierte HTTP-Adapter beziehungsweise
der vertrauenswürdige Pilottreiber bindet Tenantnamen und öffentliche
Samplingparameter; die Schedulerklasse allein ist keine Authentifizierung.

`num_cached_tokens` von A bleibt ausdrücklich 0 beziehungsweise 512;
auch private Traces und Zähler dürfen verschieden bleiben. Im betrachteten
Erfolgspfad steuern sie weder Bs Fortsetzung noch einen adaptiven
Ressourcenregler. Der native Rekonstruktionspfad, der Trefferhistorie bei
fehlgeschlagenem KV-Transfer liest, ist durch deaktivierte Connectoren
ausgeschlossen. A-Ausgabestatistik und Adminlogs sind keine B-Antworten.

## 3 Invarianten und ihre Hersteller

Die folgenden Verweise bezeichnen den geprüften Quellstand; SHA-256 und
CPU-Prüfergebnis stehen in
`results/protected-prefill-contract-20261103/checks.json`.

| Invariante | Konkrete Operation |
| --- | --- |
| I1 Geschlossene, beschränkte Kohorte | `configure_cohort` und `schedule` prüfen 1A/4B, eindeutige IDs, feste Ausgabe, Budget und verbotene Ausführungspfade; zusätzliche Core-Requests führen zum Vertragsfehler. [Scheduler](../src/protected_prefill_scheduler.py#L50) |
| I2 A kann B nicht allokieren/evicten | Zwei echte KV-Manager und disjunkte Bereiche A1–128/B129–384; Routing vor `allocate_slots`, getrennte Hash-/Freilisten. [KV](../src/tenant_kv_partition.py#L26) |
| I3 Geschützter Fortschritt ist vollständig drainbar | Beide Queues werden pro Tenant gefiltert; Parken bei 548 berechneten Prompttokens und genau einem Output; `_inflight_ids` wird erst nach Modelloutput geleert. [Scheduler](../src/protected_prefill_scheduler.py#L138) |
| I4 Keine frühe B-Vollantwort | M=16 statt1; `Pilot.drain` liefert nur fertige Requests; HTTP erlaubt kein Streaming. Cachezähler/Backendtraces fehlen in `deliver`. [Treiber](../src/protected_prefill_pilot.py#L150), [HTTP](../src/protected_prefill_server.py#L167) |
| I5 Kanonische Kapazität/Adressen | `plan_canonical` verlangt vollständige Frontier und aktiven Requestsatz; je 36 Blöcke an öffentlichen Positionen. [Plan](../src/tenant_kv_partition.py#L203) |
| I6 Daten bleiben erhalten, Historie wird gelöscht | Alle Quellen aller Schichten zuerst sichern, dann 384 Tenantblöcke nullen, auf kanonische Ziele kopieren, ungültige Endpositionen nullen; Device-Drain davor/danach. [Kopie](../src/protected_prefill_pilot.py#L33) |
| I7 Manager hängen nicht von alten Freilisten ab | Frische Manager; kanonische Blöcke in fester Reihenfolge referenzieren, Tabellen installieren und berechnete Prefixblöcke indizieren. `new_block_ids.clear()` verhindert späteres Löschen gültiger Kopien. [Commit](../src/tenant_kv_partition.py#L251) |
| I8 Keine geheimnisabhängige Join-Auswahl | Frontier aller fünf erforderlich, Running sortiert, Waiting/In-flight leer, vorherige Schritt-IDs geleert, öffentliche J-Grenze; nie nur bereite Teilmenge. [Join](../src/protected_prefill_scheduler.py#L189) |
| I9 Worker erhält die neuen Tabellen tatsächlich | Erster gemeinsamer Output markiert alle fünf als resumed und enthält Volltabellen. v1-Worker entfernt die alten Batchzeilen, ersetzt `block_ids` und fügt sie in der gemeinsamen Reihenfolge neu hinzu. [Transport](../src/protected_prefill_scheduler.py#L312) |

**Wichtige Präzisierung zu I9:** Beim Scheduler-Join sind die alten
Workertabellen noch nicht umgeschrieben. Der Übergang besteht aus
Normalisierung **und Installation vor dem ersten gemeinsamen Forward**.
`GPUModelRunner._update_states` läuft vor diesem Forward. Die vorhandene
synchron erzeugte B-Tokenhistorie bleibt erhalten; `all_token_ids` allein
würde sie im synchronen v1-Pfad nicht neu installieren. Die Begründung
ihres Inhalts ist deshalb Lemma 1, nicht ein ungeprüftes Transportflag.

## 4 Beweis der logischen Fortsetzungseigenschaft

**Lemma 1, B vor der Normalisierung.** A verändert wegen I2 nur seinen
eigenen KV-Manager und seine physische Partition. Nach dem Reset sind
Bs Manager in beiden Ausführungen gleich. I3 gibt B danach dieselben
Requests in derselben Reihenfolge; As unterschiedliche Anzahl privater
Schritte ist verborgen. Im realen Szenario sind Bs feste Prefillformen
4 × 512 und 4 × 36, beziehungsweise die feste 64-Token-Rezeptur. Alle vier
B-Requests beginnen kalt, haben dieselbe Länge und erhalten bei Budget 4c
jeweils denselben nächsten Chunk min(c, Restlänge); 140 Blöcke passen in
Bs Quote 256. Im Worker wird das nicht eingeplante A vor dem B-Forward
aus dem aktiven Inputbatch entfernt. Vier neue B-Zeilen belegen die
kleinsten freien Indizes; danach hängt ihre Form nur vom eigenen
Fortschritt ab. Alte A-Zeilendaten sind keine B-Eingaben. Induktion
über diese Schritte und die Decoderlagen: Embedding/Norm/Projektion
berechnen gleiche B-Werte, die Attention liest nur bereits gleiche
eigene KV-Werte beziehungsweise gerade geschriebene neue Werte. Alte
unbenutzte Speicherzellen werden nicht als gültiger Prefix gelesen.
Also sind Bs vollständige logische KV-Folgen, erste Ausgabetokens und
Ausgabezustände gleich. As numerische Ergebnisse müssen nicht gleich sein.
I4 verhindert auf dem normalen Prefillpfad B-Vollantworten. Öffentliche
Validierungs-/Slotzurückweisungen hängen nur von Bs Eingaben und der
öffentlichen Intakephase ab. Vertragsfehler behandelt Abschnitt5 separat.

**Lemma 2, konkrete Normalisierung.** Setze c=ceil((548+16)/16)=36 und

$$\pi_U(r,k)=s_{t(r)}+36\,\operatorname{rang}_{t(r)}(r)+k,$$

mit s_A=1 und s_B=129. Für B sind das die Bereiche 129–164, 165–200,
201–236 und 237–272. Die alten Quellen heißen α(r,k); sie dürfen zwischen
Ausführungen verschieden sein. Nach vollständiger, nicht spekulativer
Prefillzuteilung hat jeder Request35 gültigkeitsrelevante Quellblöcke.
I6 implementiert für jede Schicht λ und jede gültige Tokenposition j:

$$K'_{\lambda,\pi_U(r,\lfloor j/16\rfloor),j\bmod16}
=K_{\lambda,\alpha(r,\lfloor j/16\rfloor),j\bmod16},\quad 0\le j<548.$$

Das folgt direkt aus Snapshot vor jeglichem Clear/Scatter und der
entsprechenden Indexkopie. Überlappung von Quelle und Ziel zerstört
dadurch keine noch benötigten Daten. Nicht gültige Positionen der
Tenantpartitionen sind danach null: insbesondere 12 Restpositionen des
letzten belegten Blocks und der 36. reservierte Block. Die Kopie setzt
keine gleichen A-Werte voraus. Für B liefert Lemma 1 gleiche rechte Seiten;
π_U liefert gleiche linke Adressen. Also ist der kanonische B-Speicher gleich.
Block0 und unzugeteilte Backingblöcke außerhalb 1–384 werden nicht als
gelöschter gesamter GPU-Speicher ausgegeben und sind keine gültigen B-KV-Ziele.

I7 verwirft beide alten Allokatoren. Jeder reservierte Zielblock wird genau
einmal referenziert; A hat 92, B 112 freie Blöcke. Die aktive B-Tabellierung,
Cacheindizierung und Reihenfolge verbleibender freier Blöcke sind damit
Funktionen von U und der gleichen B-Historie, nicht von α oder As Cache.
I8 liefert die gleiche Steuerungshülle. I9 installiert vor dem Forward
gleiche B-Zeilen, Eingabetokens, Fortschrittswerte, Tabellen und greedy
Samplingdaten. Aus diesen konkreten Operationen folgt S≈_B S′ am ersten
gemeinsamen Forward; diese Äquivalenz war keine Eingangshypothese.

**Lemma 3, Erhaltung über Decode.** Nach k abgeschlossenen gemeinsamen
Schritten, 0≤k<15, gilt für alle aktiven Requests: berechnet 548+k,
Outputs 1+k, logische Gesamtlänge 549+k. Es besteht genau ein noch
zu berechnendes Token.
Das native Schedulerbudget reicht für fünf; Reihenfolge und Geometrie
sind gleich. Für jeden Request ist bis zum Ende genügend Kapazität bereits
reserviert: ceil(564/16)=36. Deshalb kann auch A keine globale Preemption
durch einen lokalen Zuteilungsfehler auslösen. Das ist wesentlich: Der
native Scheduler könnte bei Allokationsfehlern sonst B als Opfer auswählen.

Beim nächsten Workeraufruf wird der Eingabefortschritt 548+k installiert;
der Scheduler hat die Zuteilung bereits um eins vorgemerkt. Worker und
Scheduler müssen daher nicht jederzeit dieselbe Zählerzahl besitzen,
sondern diese feste Phasenbeziehung. Unter dem Operatorvertrag ist Bs
nächster KV-Wert und greedy Token allein durch gleiche B-Daten und die
gleiche Geometrie bestimmt. B-Textaufbereitung bleibt gleich. A-Daten
können unterschiedlich bleiben; A hat dieselbe Fortschritts-/Kapazitätshülle.
`check_stop` beendet wegen min=max=16 keinen Request vor 16 Outputs,
unabhängig vom Tokenwert. Mit Schritt 15 sind alle fertig und werden
entfernt. As privater Finishgrund kann sich dabei unterscheiden, etwa
EOS statt Längenende am letzten Token; beide führen zur selben Entfernung.
Bs Finishgrund ist wegen gleicher Tokens gleich. Damit bleibt
die B-Projektion induktiv erhalten; Bs Antworten und logische
Schedulingentscheidungen sind gleich. Private A-Cachehashes, die während
Decode entstehen, wirken nur im A-Pool und werden für keine neue Anfrage
dieser geschlossenen Kohorte verwendet.

**Satz.** Für zwei erfolgreiche, fehlerfreie Ausführungen des definierten
Pfads mit demselben U und verschiedenem A-Cache stimmen B-Antwortzuordnung
und gemeinsamer logischer Decodeverlauf überein. Der Beweis ist die
Komposition von Lemma 1–3, nicht lediglich der allgemeine Schluss
„gleicher Zustand impliziert gleiche Zukunft“. Der Satz setzt den
funktionalen Backendvertrag voraus. Er beweist weder universelle
GPU-Bitdeterministik noch cacheunabhängiges Erreichen der Erfolgsdomäne.

Formal sei R_ok(U) die Menge der unter dem Operatorvertrag vollständig
erfolgreichen, fehlerfreien Ausführungen dieses Programmpfads bei U:

$$\forall\rho_0,\rho_1\in R_{\mathrm{ok}}(U):\quad
\operatorname{Obs}^{\mathrm{log}}_B(\rho_0)
=\operatorname{Obs}^{\mathrm{log}}_B(\rho_1).$$

R_ok ist eine Einschränkung des Satzes, **kein vom Programm gelieferter
Beweis**, dass beide Cachezustände derselben cacheunabhängig zugelassenen
Erfolgsmenge angehören. Insbesondere ist dies kein fehlerbereinigter
Beweis über die Gesamtheit realer Clientbeobachtungen.

**Verstärkung für die kontrollierte Cacheherkunft.** Die tatsächlichen
Treiber setzen zurück und erzeugen genau eine alleinstehende Vorbereitung
mit derselben Chunkrezeptur wie kaltes A. Ein gültiger warmer 512-Prefix
ist deshalb das Ergebnis genau derjenigen ersten 512 Positionen, die
kaltes A neu berechnet: einmal 512 oder achtmal 64. Der rohe 544-Treffer
wird vor Zuteilung auf 512 gekürzt; beide Zustände berechnen danach 36
Tokens mit derselben Geometrie. Induktion über identische Prefixoperatoren
und das Endstück ergibt im logischen Backendmodell auch gleiche aktive
A-KV-Werte und ersten Token. Zusammen mit Lemma 2 entsteht dann die
stärkere vollständige aktive KV-Normalform. Dies setzt gültige Cachewerte
aus eben dieser kontrollierten Herkunft voraus, nicht beliebige injizierte
Cachebytes. Die Schedulerklasse prüft die Herkunft nicht selbst; sie
folgt aus dem Reset-/Vorbereitungsprotokoll und dem konkreten Treibercode.
Die früher gemessenen 28-Schicht-Hashes sind empirische Instanzen dieser
Verstärkung, kein Ersatz für deren Modell- und Herkunftsbedingungen.

**Adaptive Fortsetzung.** Innerhalb der laufenden Kohorte sind zusätzliche
produktive B-Anfragen nicht zugelassen; der Core weist Extra-IDs zurück,
HTTP bindet die vier festen Slots. Daher gibt es hier keinen Satz für
beliebige aktive Probes. Für wiederholte ordnungsgemäße Kohorten mit
verpflichtendem Reset, öffentlicher Aufnahmeplanung und erfolgreicher
Ausführung gilt Induktion über Runden: gleiche bisherige logische
B-Beobachtung führt bei derselben B-Strategie zu gleichen nächsten
zugelassenen Eingaben; Reset und Lemma 1–3 liefern wieder Gleichheit.
Dies gilt nicht für eine Strategie, die reale Antwortzeiten, Fehler-
oder Serververfügbarkeit zur Auswahl der nächsten Probes nutzt.

## 5 Gegenbeispiele und notwendige Grenzen

**Overrun.** Öffentliche A-Frist 200 ms, privates warmes Prefill 22 ms,
kaltes 141 ms. Derselbe zusätzliche Host-/Ausführungsstillstand von 70 ms
führt warm nicht, kalt aber zur Überschreitung. Der reale Deadlineguard
wirft dann `ProtectedPrefillError`; HTTP setzt die wartenden Antworten auf
500 und beendet die Engine. Warm können 200-Antworten entstehen. Erfolg
gegen Fehler verrät auch ohne genaue Zeitmessung etwas. Der feste Join
repariert das nicht. Die Erfolgsdomäne ist **keine implementiert bewiesene
cacheunabhängige Zulassungsmenge**; Ausblenden fehlgeschlagener Läufe
begründet keine unbedingte Nichtinterferenz.

**Unkontrollierte Übergangsdaten.** Die Kopie konserviert gültige B-Werte,
sie berechnet keine korrekten Werte neu. Sind diese verschieden, bleiben
sie verschieden. Lemma 1 und der Backendvertrag sind deshalb notwendig.
Ebenso würde bloßes Ändern der Schedulerblocktabellen ohne I9 den Worker
mit alten Adressen gegen bereits umkopierten Speicher rechnen lassen.

**Zeit und Versandordnung.** Nach erfolgreichem Sleep kann J um Hostjitter
überschritten werden; nach J wirken GPU-Takt, Temperatur, Cache- und
Allocatorzustände weiter. `ThreadPoolExecutor` und HTTP-Threads ordnen
reale Sendungen nicht durch den kanonischen Core-Schedule. Der Satz
garantiert deshalb auch keine zeitlose Empfangsreihenfolge im Netzwerk.
Erweiterungen um Streaming, Abbruch, EOS-Frühende, neue Requests, gemeinsame
Eviction oder adaptive Zusatzlast benötigen einen neuen Vertrag.

**Konstruktive Reparaturgrenze.** Öffentlich verspätete Fehlerausgabe oder
einheitlicher Fehlertext lösen Erfolg versus Fehler nicht. Für einen
fehlerberücksichtigenden Gesamtsatz wäre mindestens ein cacheunabhängiger
Admission-/Laufzeitsicherheitsvertrag erforderlich, der allen zugelassenen
Cachewelten Erfolg garantiert, oder eine separat begründete Offenlegung
des Fehlerereignisses. Konkret müsste eine öffentliche Admissionprüfung
für jede freigegebene Eingabeklasse U zertifizierte Schranken
W_A(U)≤Fenster_A, W_B(U)≤Fenster_B und eine passende Schranke für
Normalisierung samt gemeinsamem Abschluss prüfen; die Suprema müssen
alle zugelassenen Cachezustände und Störungen umfassen. Gemessene Maxima
sind kein solches Zertifikat; bei unbeschränkten Hoststörungen existieren
diese endlichen Schranken nicht. Eine solche Zeit-/Fehlerinvariante ist derzeit
nicht implementiert oder bewiesen. Der zulässige minimale Schritt ist,
den nachgewiesenen Satz auf die logische erfolgreiche Fortsetzung zu
begrenzen; ein kleiner Timerpatch kann die stärkere Eigenschaft nicht
ehrlich herstellen. Im untersuchten Erfolgsprogramm wurde keine dafür
notwendige Quellcodekorrektur vorgenommen.

**Nachprüfbarkeit.** `src/protected_prefill_contract_checks.py` verwendet
echte KV-Manager und den echten Tensor-Kopierkörper auf CPU-Tensoren;
nur CUDA-Geräte-/Eventplumbing wird ersetzt. Unterschiedliche A-Werte
und Quelladressen ergeben gleiche kanonische B-Werte, unterschiedliche
A-Werte bleiben erhalten; ungenutzte Tenantbereiche werden genullt.
Ein veränderter B-Quellwert bleibt nach der Kopie verändert. Echte Stop-
und Deadlineguards bezeugen festen Outputumfang beziehungsweise das
Fehlergegenbeispiel. Dies sind unterstützende CPU-Instanzen, keine
Maschinenverifikation des Induktionsbeweises oder der GPU-Bibliotheken.

Reproduktion aus dem Repository mit neuem Ergebnisordner:

```bash
/home/rock/projects/porto/.venv-py313-repair/bin/python \
  src/protected_prefill_contract_checks.py results/protected-prefill-contract-NEU
```

## 6 Neuheitsabgrenzung und mögliche Contribution

Die vorhandene [Novelty-Matrix](security-novelty-matrix-20261103.md) bleibt
Ausgangspunkt. Vier engste Originaltexte wurden gezielt in den folgenden
Abschnitten nachgeprüft; keine erneute breite Suchkampagne:

- **Time Protection**, EuroSys 2019, §3.2 und §4.3: Partitionierung,
  deterministischer Restzustand und Padding auf sichere Übergangsdauer
  sind bereits Prinzipien des Designs. Unser Vertrag ist eine konkrete
  Anwendung auf KV-/Worker-Wiedereintritt und beansprucht deren allgemeine
  Idee nicht neu. [Original](https://yuval.yarom.org/pdfs/GeYCH19.pdf)
- **IFS**, CCS 2021, §§3.1–3.3 und 4.1–4.2: optionale Privacy mit eigener
  Ununterscheidbarkeitsdefinition und adaptiven Zeitprobes ist bereits
  untersucht. Das dortige Slotmodell ist bezüglich Zeitbeobachtung stärker
  als unser erfolgreicher logischer Vertrag; bloße selektive Isolation
  wäre keine neue Contribution. [Original](https://www.cis.upenn.edu/~sga001/papers/ifs-ccs21.pdf)
- **Predictive Mitigation**, CCS 2011, §2.2, §3 und §4: Planung anhand
  öffentlicher Eingaben sowie Leakage durch Fehlvorhersagen sind bekannt.
  Ein öffentlicher HTTP-Release oder das Ignorieren von Overruns wäre
  keine neue Absicherung. [Original](https://www.cs.cornell.edu/andru/papers/ccs11.pdf)
- **SafeKV v2**, §§4.3 und 6: tenantbezogene Sichtbarkeit/Reuseentscheidungen
  adressieren das Cross-Tenant-Hit-Orakel. Unser untersuchtes Objekt ist
  das Wiederaufnehmen gemeinsamer Ausführung nach privater Cachearbeit;
  die gelesenen Abschnitte liefern dafür keinen KV-/Worker-Vertrag.
  Dies ist eine konkrete Abgrenzung, kein Ausschluss jeder Überschneidung.
  [Original](https://arxiv.org/html/2508.08438v2)

Lesestatus dieser Nachprüfung: L2 der benannten Originalabschnitte.
SIDE bleibt mangels Volltext L1; keine abschließende globale Neuheits-
oder Publikationsentscheidung wird daraus abgeleitet.

**Möglicher Paper-Beitrag:** Ein implementierter und quellcodegebunden
hergeleiteter hinreichender Zustandsvertrag für die Wiederaufnahme
gemeinsamen LLM-Decodings nach privater Prefill-Wiederverwendung:
Fortschritts-/Kapazitätshüllen, kanonische B-KV-Belegung, frische
Allocatorzustände und verpflichtende Workerinstallation reichen im
definierten logischen Modell zur B-Fortsetzungsnichtinterferenz.
Der Vertrag benötigt keine Gleichheit sämtlicher privater A-Inhalte
und benennt Erfolg-/Fehlergrenze ausdrücklich.

Das ist ein konkreter möglicher Implementierungs-/Verifikationsbeitrag,
noch keine gesicherte neue Timing-Schutzmethode. Der faire Kostenpilot
belegt warmen Rechenvorteil, aber keinen Latenzvorteil gegenüber Ignore-Hits;
echte Zeitvertraulichkeit ist weiterhin offen. Auch macht der B-logische
Satz nicht jede Kopie notwendig: Bei getrenntem B-Pool, ausreichender
A-Kapazität und gleichen Formen könnte derselbe schwache Beobachter
bereits ohne vollständige Kanonisierung unabhängig sein. Nachgewiesen
ist ein hinreichender Vertrag mit expliziter Ressourcennormalform,
keine minimale oder notwendige Schutzkonstruktion. Die Kombination
bekannter Bausteine und der allgemeine Induktionsschluss allein tragen
keinen Neuheitsclaim. Keine neue GPU-Serie und keine Änderung alter Rohdaten.
