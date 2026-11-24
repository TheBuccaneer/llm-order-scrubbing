# Literaturabgrenzung für konditionale Cachevertraulichkeit

**Nachtrag nach Implementierung und formaler Untersuchung:** Der
hinreichende logische Wiedereintrittsvertrag ist nun quellcodegebunden
hergeleitet; [Bericht](protected-prefill-nichtinterferenz-20261103.md).
Er gilt für erfolgreiche geschlossene Kohorten im definierten Backendmodell,
nicht für echte Clientzeiten, HTTP-Reihenfolgen oder cacheabhängige Fehler.
Damit ist die frühere Konstruktionslücke teilweise geschlossen, eine neue
allgemeine Timing-Schutzmethode aber nicht bewiesen. Die nachfolgenden
Entwurfsurteile dokumentieren den Stand vor dieser Implementierung;
die Quellenabgrenzung bleibt relevant. Vier engste Originalabschnitte
wurden für den Bericht erneut gezielt geprüft; SIDE bleibt L1.

Stand: 03.11.2026. Recherchegrenze ist **03.11.**, nicht der noch zukünftige
Rest des Novembers. Gezielt geprüfte Originalstellen, keine erschöpfende
systematische Literaturübersicht. **L2** bedeutet heute gelesene, unten
benannte Volltextabschnitte; **L1** nur Abstract. Alte Lesestände in
`quellen.md` bleiben erhalten. Downloads und SHA256 stehen in
`../results/tenant-release-feasibility-20261103/literature-sources.json`.

**Korrigiertes Neuheitsurteil:** Öffentliche Zeitfenster, selektiver Schutz,
feste Ausgabe und Privacy-Delay-Optimierung sind bekannte Bausteine. Der
Entwurf hat noch keinen davon abgegrenzten eigenen Mechanismus geliefert.
Ein **sicherer Wiedereintritt in gemeinsames Decode** ist bislang eine
offene Konstruktionsaufgabe: Die benötigte Zustandsäquivalenz wird
vorausgesetzt, nicht hergestellt. Das genügt auch ohne SIDE nicht als
Methodenbeitrag. Gegenüber SIDE bleibt zusätzlich eine Volltextlücke;
der Nutzer hat keinen Volltext verfügbar.

## Schutzmodell und tatsächliche Garantien

| ID und Originalfassung, heute gelesene Stellen | Geschütztes Geheimnis | Angreiferbeobachtung | Geschützte Ressourcen | Tatsächlich behauptete Eigenschaft |
| --- | --- | --- | --- | --- |
| P: [Pacer, Security 2022](https://www.usenix.org/system/files/sec22-mehta.pdf), L2 §§2.2–4, 6 | Anwendungsgeheimnisse, die Verkehrsform beeinflussen | Paketgrößen und Zeiten, auch indirekte Konkurrenzbeobachtung | Tunnel, Sendeausführung, Transport-/Kontrollpfad | Geheimnisunabhängige Verkehrsform unter den Designannahmen; interne Interferenz darf den Shaper nicht verschieben. |
| A: [Kadloor et al., 1302.6123v1](https://arxiv.org/pdf/1302.6123v1), L2 §§III–VI, Th. 5.1/5.2 | Zeitliche Jobdichte eines anderen Benutzers | Eigene Jobankünfte, Größen und Bedienzeiten | Ein geteilter Server, Pufferung und Bedienreihenfolge | Untere Schranke des Schätzfehlers bei Accumulate-and-Serve; p-TDMA lernt Raten über lange Anpassungsintervalle. Keine LLM-Garantie. |
| I: [Gong et al., 1306.3484v1](https://arxiv.org/pdf/1306.3484v1), L2 §§II, III-E, IV, Th. 3.6/4.2/4.3 | Benutzerankunftsdichte | Eigene Ankunfts-/Abgangsfolge aktiver Probes | Diskreter Zwei-Benutzer-Scheduler | Shannon-Äquivokation, FCFS-Leakage und mit Sammelintervall steigende Privatsphäre. Dies präzisiert hier die unspezifische Auftragsbezeichnung „Privacy in Shared Schedulers“; kein separater Volltext dieses exakten Titels identifiziert. |
| W: [Deterministische work-conserving Scheduler, 1403.1276v3](https://arxiv.org/pdf/1403.1276v3), L2 §§II, IV-E, Th. 4.7 | Jobankünfte | Eigene Bedienzeiten unter aktiven Probes | Deterministischer, arbeitskonservativer Einzelserver | Modellabhängige universelle Leakage-Untergrenze. Kein Satz über jedes LLM-Batching oder über ausschließliches Cachezustandsgeheimnis. |
| F: [FairInference, 2609.18112v1](https://arxiv.org/html/2609.18112v1), L2 §§2–5.7, Alg. 2/3, §§6–7.1 | Kein Vertraulichkeitsgeheimnis; schützt Tokenlatenzen wohlerzogener Clients | Leistungsmetriken TTFT/TBT/TTLT | Prefill-/Decode-Zulassung und KV-Reservierungen | Token spätestens bei isolierter Referenzzeit plus δ, unter Last-, Headroom- und Modellannahmen. Weder Gleichheit der Zeitverteilungen noch Nichtinterferenz. |
| K: [KVGov, 2608.09225v1](https://arxiv.org/html/2608.09225v1), L2 §§2.3, 4.1–4.3, 5, 7 | Fremde gecachte Präfixinhalte | Eigene Cacheprobe-TTFT/Fingerprints | Hash-/Salt-Namensräume; zusätzlich Auditbudget | Disjunkte Cachekeys verhindern fremde Treffer. Aussagen über fehlende Fingerprints beziehen sich auf dieses Cacheorakel; ORIGAMI plant Audits, nicht GPU-Ausführung. |
| X: [CacheSolidarity v1](https://arxiv.org/pdf/2603.10726v1), L2 Überblick und Design; [PrefixWall v2](https://arxiv.org/html/2603.10726v2), L2 §§2.4, 3–5 | Einträge privater Präfixe | Kandidatenprobes und TTFT | Selektive Freigabe/Isolation von Präfixknoten | Bedingte All-Miss-Eigenschaft für die spezifizierte Probesequenz bei aktivem Schutz; Aktivator und erster richtiger Guess begrenzen die Aussage. Zwei Versionen derselben Arbeit. |
| S: [SafeKV, 2508.08438v2](https://arxiv.org/html/2508.08438v2), L2 §§3–4, 6–7 | Sensitive KV-Blöcke und deren Wiederverwendung | API-Probes, TTFT, wiederholte Sessions | Klassifikation, private/geteilte Bäume, RDR-Safeguard | Default-private und kontrollierte Promotion; Restexposition an Klassifikationsfehler gebunden. §6 grenzt andere koresidente Systemangriffe ausdrücklich aus. |
| O: [One-Sided Bounded Noise, CCS 2025](https://people.csail.mit.edu/devadas/pubs/one_sided_noise.pdf), L2 §§1.2, 2, 3–5, insb. Th. 4 und §5.2 | Allgemeine sensitive Eingabe; Anwendung AES-Key | Perturbierter Funktionswert, etwa Zahl von Cachemisses | Einseitige Ausgabetransformation, keine LLM-Engine | Optimierung unter DP, Maximal Leakage und PAC Privacy; teils Komposition. Kosten sind u.a. zweites Moment beziehungsweise definierte Kostenmatrix. |
| N: [NetShaper, finale Security-2024-Fassung](https://www.usenix.org/system/files/usenixsecurity24-sabzi.pdf), L2 §§2.3, 3–4.3, 5 | Inhalt eines Anwendungsdatenstroms | Form des öffentlichen Tunnelverkehrs | Middlebox-Shaper, Warteschlangen und Netzpfad | DP bei definierter Stromnachbarschaft, Sensitivitäts-/Fensterannahmen und isolierter Shaper-Ausführung. §2.3 schließt Leakage über koresidente Anwendungen ausdrücklich aus. |
| D: [SIDE, TMC Early Access, 31.08.2026](https://doi.org/10.1109/TMC.2026.3729753), **L1** | Exit-Tiefe eines Multi-exit-DNN, daraus ableitbare Ergebnisse/Membership | Im Abstract beobachtete Latenz | Im Abstract gemeinsame Ressourcenallokation, Routing, Submodelldeployment | Abstract behauptet konfigurierbare ASR-Schranke für ein modelliertes Angriffsszenario. Voraussetzungen, Algorithmus und Beweis **nicht geprüft**. |
| R: [Sarathi-Serve, 2403.02310v3](https://arxiv.org/pdf/2403.02310v3), L2 §§3.2, 4.1–4.3, 5.4 | Kein Vertraulichkeitsgeheimnis | TTFT/TBT und Servingkapazität | Tokenbudget, Chunked Prefill, gemischte Batches | SLO-orientierte Begrenzung von Prefill-/Decode-Stalls; keine Geheimnisunabhängigkeit eines Batchzeitplans. |
| Q: [Packet scheduling with optional client privacy, CCS 2021](https://www.cis.upenn.edu/~sga001/papers/ifs-ccs21.pdf), L2 §§3–5, 7–8 | Ankunftsfolge privater Clients | Eigene Paketankunft und Übertragung; Angreifer kontrolliert andere Clients | IFS: Priorität für indifferente Clients, private Zufallsslots einschließlich Leerlauf | Statistische Ununterscheidbarkeit privater Ankunftsfolgen im Slotmodell. Selektive Privatsphäre und bessere Effizienz als allseitiges TDMA sind bereits untersucht. |
| B: [Predictive Mitigation, CCS 2011](https://www.cs.cornell.edu/andru/papers/ccs11.pdf), L2 §§2–5, 6; [2010-Vorläufer](https://www.cs.cornell.edu/andru/papers/ccs10.pdf), L1/Einordnung | Interne Geheimnisse einer Blackbox | Echte externe Ausgabeevents; Dummies dürfen erkennbar sein | Ausgabeplan und öffentliches Vorhersagemodell | Begrenzte Timing-Leakage auch bei Fehlvorhersagen, unter den jeweiligen Scheduler-/Penalty-Annahmen. Öffentliche Requesttypen und mehrclientfähige Planung sind bekannt. |
| T: [Time Protection, EuroSys 2019](https://yuval.yarom.org/pdfs/GeYCH19.pdf), L2 §§3.2, 4.3, 5.1 | Aktivitäten einer Sicherheitsdomäne | Ausführungsgeschwindigkeit anderer Domänen | Partitionierung, Flushes, Kernelmetadaten, Interrupts | Zeitisolation verlangt auch normalisierte Übergangsdauer und kontrollierten Ressourcenzustand; bloßer Kontextwechsel genügt nicht. Hardwareannahmen bleiben wesentlich. |

## Experimente und Abgrenzung des Entwurfs

Hier bezeichnet **J** die in `cache-state-oblivious-kandidatin-20261103.md`
spezifizierte Prefill-Barriere mit normalisiertem Decode-Wiedereintritt.
„Offen“ ist eine überprüfbare Anschlussfrage, keine bestätigte Neuheit.

| ID | Was tatsächlich evaluiert wird | Fehlende Eigenschaft für unser Ziel | Ist J eigenständig? |
| --- | --- | --- | --- |
| P | Reale Cloud-Tunnel, Angriffsclassifier, Bandbreite/Clientlatenz/Throughput | Cacheabhängige GPU-Arbeit vor B-eigenen vollständigen Antworten wird nicht umgeplant | Nur ein nachgewiesener kürzerer Isolationshorizont mit günstigerem A/B-Kostenprofil ginge über Anwendung des bekannten Ausgabeprinzips hinaus. |
| A/I | Mathematische Modelle, Privacy-/Delay-Analyse und numerische Vergleiche | Prefill verbraucht ein Geheimnis, danach kann logisch gleiches Decode folgen | Nur die LLM-spezifische Zustands- und Kostencharakterisierung; periodische Tenant-Batches allein sind redundant. |
| W | Formale Untergrenzen und konkrete Scheduleranalysen | Hier bleibt Ankunft öffentlich und nur Cachezustand variiert | Kein neuer allgemeiner Work-conservation-Unmöglichkeitssatz beanspruchbar. |
| F | SGLang-Prototyp, Prefix-Matching-/Outputlängen-Workloads und Macrobenchmarks | B-only-Verteilungsunabhängigkeit für warm/kalt | J erzwingt einen öffentlichen Übergang und normalisierten Zustand statt allein Deadlineeinhaltung. Kostenüberlegenheit gegenüber FairInference ist ungemessen. |
| K | Angriff/Abwehr weitgehend Simulation, reale TTFT-Kanalmessungen; Boundary-Reuse extrapoliert | Kein Schutz vor fremder cacheabhängiger Konkurrenz ohne eigene Cachehits | Komplementär zum Salt; neue Namespacekonstruktion wäre redundant. |
| X | Cache-Reuse-/Latenzexperimente, Modelle/Lasten, Aktivator | Kein Gleichheitsvertrag für B-Zeiten bei privat warmem/kaltem A unter getrennten Namensräumen | Möglicher anderer Mechanismus; selektive Isolation selbst ist bekannt. |
| S | API-Probing, Detektor/Safeguard und Multitenant-Performance | Keine allgemeine Absicherung koresidenter Ausführungsinterferenz | Anderes Schutzobjekt; ein weiterer Sensitivitätsclassifier wäre keine ausreichende Erweiterung. |
| O | Optimierte Störmechanismen; AES-/Kommunikationsanwendungen | Keine Ausführungsplanung, die die ursprüngliche Completion-Verteilung verändert | J muss Nutzen aus verändertem Backendverlauf zeigen. Eine weitere Delay-Verteilung wäre hier kein eigenständiger Grundgedanke. |
| N | Video-/Webanwendungen, Privacy-/Bandwidth-/Latency-Kurven | Koresidenter B-only-Kanal ist außerhalb des Modells | Komplementär; DP-Label oder Tunnelpadding allein deckt den Konflikt nicht ab. |
| D | Laut Abstract reales Testbed, ASR und Effizienz | **Mangels Volltext nicht entscheidbar** | Allgemeiner Claim „ressourcenbewusste Timingabwehr mit weniger Kosten“ vorweggenommen. Engere Abgrenzung von J bleibt ungeklärt; keine freigegebene Novelty-Aussage. |
| R | Mehrere Modelle/Hardware, Servingkapazität, Chunkingkosten | Gleiches Tokenbudget kann dennoch von privaten Cachehits beeinflusste Batches enthalten | Phasenbewusstes Batching allein redundant; ein bewiesener Übergangsvertrag wäre die zu prüfende Erweiterung. |
| Q | Reale Switch-Angriffe/Prototyp und vollständiger IFS im PIFO-Simulator, Latenz/Throughput | Variable GPU-Kernels und sich auflösende Cachezustandsabhängigkeit passen nicht direkt zum Einheits-Slotmodell | Stärkste zusätzliche Privacy-Scheduler-Vorarbeit. Selektiver Schutz und freigegebene Restkapazität allein redundant; J braucht zusätzlich eine konkrete LLM-Zustandskonvergenz. |
| B | Mehrclient-Webanwendungen, Latenz/Throughput und Leakage-Grenzen | Optimiert externe Freigabe, nicht den LLM-Prefill-/Decode-Zustandsübergang | Eine lediglich öffentlich parametrisierte HTTP-Frist wäre keine Neuerung. |
| T | seL4 auf Arm/x86, Cachekanäle, Schutzkosten | Kein spezifischer Nachweis, wann private Prefill-Geschichte vor gemeinsamem LLM-Decode verbraucht ist | Normalisierung plus Padding ist bekannt; neuer Beitrag müsste in überprüfbarer minimaler Normalisierung und daraus messbarem Kostenvorteil liegen. |

## Gezielt nachgeprüfte jüngere Scheduler

- [P-PAS v1, 15.08.2026](https://arxiv.org/html/2608.15171v1), **L2 §3, Alg. 1, §§4–5**: passt Prefillbudget anhand laufender/wartender Prefills und Decodes an; untersucht wechselnde Last und Modelle/GPUs. Gerade diese internen Zähler können vom Cachegeheimnis abhängen. Keine Ununterscheidbarkeitsgarantie; ein dynamisches Tokenbudget wäre kein neuer Beitrag.
- [Cascade v1, 06.08.2026](https://arxiv.org/html/2608.06557v1), **L2 §§IV-A–IV-C und V-A**: koppelt SLO-Budget, KV-Hitprofil, Prefixrestoration und Scheduling. Sicherheitsunabhängigkeit wird nicht formuliert. Cachebewusste gemeinsame Budgetoptimierung ist bereits Vorarbeit, darf nicht umbenannt werden.
- [EdgePace v1, 27.10.2026](https://arxiv.org/html/2610.37307v1), **L2 §§3.1–3.3 und 4.1**: sichere Unterbrechungsstellen in Prefill/Decode und Scheduling anhand Speicherdruck, Fristen und Freshness. „Sicher“ meint konsistente Unterbrechung/Deadlineziel, nicht Cachegeheimnis-Nichtinterferenz.
- [KV-Cloak, NDSS 2026](https://www.ndss-symposium.org/wp-content/uploads/2026-f258-paper.pdf), **L1/Einleitung**: Tensorzugriff und Matrixobfuskation, kein im gelesenen Teil ausgewiesener GPU-Timing-Scheduler. Nur zur Eingrenzung, kein tragender Ausschlussclaim.

Gesucht wurden bis zum Stichtag Kombinationen aus LLM, cache state,
oblivious scheduling, noninterference, timing isolation, prefill/decode,
side-channel defense sowie die konkreten Titel. Sekundärtreffer dienten
nur zum Auffinden der Primärtexte. Ein fehlender Suchtreffer beweist
keine Nichtexistenz. SIDE bleibt nach Verlags-, DOI-, OpenAlex- und
Autorensuche ohne zugänglichen Originalvolltext.

## Verbleibende Behauptung und Stopkriterien

**Noch nicht konstruktiv eingelöster Zielclaim:** Für identische Anfragen mit unterschiedlicher privater
Präfixvorwärmung genügt unter expliziten Engineannahmen ein endlicher,
öffentlich terminierter Schutz der Prefill-Geschichte, wenn der spätere
Schedulerzustand einschließlich KV-Ressourcen von dieser Geschichte
entkoppelt wird; danach kann gemeinsam und arbeitskonservativ decodiert
werden. Der zu belegende Nutzen ist ein besserer A/B-Kostenpunkt gegenüber
individueller fester Freigabe und fair konfigurierter voller Tenant-Trennung.

Nicht neu sind der allgemeine Nichtinterferenz-Schluss aus gleichen
Zuständen, feste Fenster, Padding oder die Fristuntergrenze `R ≥ C`.
Neuheitsfähig wäre erst die konkrete nachgewiesene LLM-Konstruktion mit
einer hinreichenden, tatsächlich realisierbaren Normalisierung und einem
Kostenvorteil. Diese Konstruktion fehlt bisher. C2/C3 sind damit
**offene Forschungsziele**, keine bereits abgegrenzten neuen Methoden-
oder Grenzkandidaten. Zusätzlich zur individuellen Freigabe und vollen
Isolation ist gezielte Prefix-Neuberechnung als einfache mechanistische
Baseline erforderlich; ein entsprechender interner vLLM-Pfad ist vorhanden.
