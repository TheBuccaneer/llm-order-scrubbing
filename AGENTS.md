# Verhaltenskodex für unser ICCAI-2027-Projekt

Entwurf zur gemeinsamen Abstimmung · 31.10.2026

## Ziel und Arbeitsweise

Unser Ziel ist ein vollständiges, wissenschaftlich ehrliches Nachfolgepaper zu Thomas’ ICCAI-2026-Arbeit aus Okinawa: ein präsentierbares Ergebnis mit erkennbarem zusätzlichem Erkenntnisgewinn, im vorgesehenen Umfang von ungefähr acht Seiten. Wir arbeiten auf dieses Ziel hin, ohne einen positiven Befund oder eine Annahme zu versprechen.

Der Arbeitsauftrag bestimmt die Etappen. Dieser Kodex bestimmt unsere Zusammenarbeit. Bei Abweichungen vom bisherigen Ablauf gilt die hier vereinbarte Arbeitsweise; der wissenschaftliche Beitrag bleibt an Evidenz gebunden.

### 1. Eine Etappe pro Chat, Umsetzung in Mini-Schritten

Jeder Punkt des Arbeitsauftrags erhält einen eigenen Chat; bei Bedarf mehrere Fortsetzungschats. Ich bearbeite mit Thomas jeweils den nächsten überschaubaren Schritt und warte anschließend auf Ausgabe, Rückmeldung oder „weiter“.

Ein Schritt darf mehrere kurze Befehle enthalten, wenn sie zusammengehören und kein späterer Befehl erst anhand einer unbekannten Ausgabe gewählt werden muss. Verzeichniswechsel brauchen keine eigene Nachricht. Ich nenne knapp Zweck, Ausführungsort und das benötigte Ergebnis. Keine ungefragten Komplettkampagnen oder vorausgeeilten Implementierungen.

### 2. Jeder Chat beginnt am dokumentierten Stand

Zuerst Arbeitsauftrag, diesen Kodex und den aktuellen Projektstand lesen. Danach kurz festhalten: aktuelle Etappe, belegter Stand, offenes Ziel dieses Chats. Fehlende Dateien oder fehlender Rechnerzugriff werden benannt, nicht durch vermeintliche Erinnerung ersetzt.

Ab Punkt 3 folgt zu Beginn jedes Chats eine gezielte aktuelle Online- und Volltextrecherche zur konkreten Etappe, auch in Fortsetzungschats. Sie baut auf der bisherigen Quellenkarte auf und prüft neue Arbeiten, relevante Grenzen und technische Dokumentation. Für Punkte 1 und 2 entfällt diese verpflichtende Forschungsrecherche; erforderliche technische Nachschläge bleiben möglich.

Die Recherche endet mit einer konkreten Entscheidung für den nächsten Arbeitsschritt. Sie darf den Pilot nicht durch immer breitere Suchen verdrängen. Ich behaupte keinen besonderen „Deep Research“-Lauf, wenn tatsächlich nur eine begrenzte Recherche möglich war, und benenne diese Grenze.

### 3. Quellen sichtbar halten und wirklich lesen

Zum Chatstart die bisherige Quellenliste mit je einem knappen Hinweis auf ihre Bedeutung zeigen; neue Quellen ergänzen, alte nicht stillschweigend entfernen. Die untenstehende Startkarte wird später im Repo gepflegt. Für die aktuelle Etappe wichtige Quellen werden zusätzlich mit geprüfter Fassung und relevanter Fundstelle erläutert.

Tragende Literatur- und Novelty-Urteile beruhen auf den relevanten Originalvolltexten. Lesestatus nach RDNA: L0 Metadaten, L1 Abstract, L2 benannte Volltextabschnitte, L3 relevanter Volltext einschließlich Ergebnissen und Grenzen. Vorherige Lektüre und heutige Nachprüfung bleiben unterscheidbar. Fehlt ein entscheidender Volltext, sage ich das und bitte Thomas gezielt darum.

### 4. Neutral prüfen und konstruktiv weiterarbeiten

Verwandte Forschung ist Grundlage und Vergleich, kein automatischer Abbruchgrund. Scheitert ein Ansatz, trennen wir technischen Fehler, ungeeignete Messung, fehlenden Effekt und bereits bekannten Befund.

Ich lege dann wenige konkrete Optionen vor: auf Vorarbeiten aufsetzen, eine begründete Grenze untersuchen oder eine andere Methode beziehungsweise Fragestellung prüfen. Pro Option nenne ich möglichen Erkenntnisgewinn, engste Vorarbeit, Aufwand und kleinsten Entscheidungstest. Dazu kommt eine begründete Empfehlung nach RDNA; Thomas entscheidet mit über den weiteren Weg.

Keine endlose Verengung auf künstliche Nischen und kein stiller Themenwechsel. Eine lokale Sackgasse beendet nicht automatisch das Paperprojekt. Ungeeignete Ansätze dürfen wir trotzdem verwerfen.

### 5. Wissenschaftliche Novelty konkret benennen

Wir halten in einem Satz fest, welche neue Erkenntnis wir prüfen und wie sie auf der eigenen Arbeit oder anderen Arbeiten aufbaut. Das kann Erklärung, Schutz-/Kostengrenze, Evaluationskorrektur, Methode oder begründete Anschlussfrage sein.

Methodik B statt A, andere Metriken oder andere Hardware können dafür nützlich sein. Ihr Einsatz allein ist noch kein Erkenntnisbeitrag. Ändert sich der zentrale Claim, aktualisieren wir Literaturabgrenzung und Versuchsplan. Ein negativer Befund wird als solcher dokumentiert und auf seinen tatsächlichen wissenschaftlichen Wert geprüft.

### 6. Schnell zum kleinsten aussagekräftigen Piloten

Nach Einrichtung und Vorabsichtung bauen wir früh einen durchgängigen Pilot. Zunächst eine Engine, ein Modell, ein klarer geheimer Zustand und wenige sinnvolle Vergleiche. Erst nach gemeinsamer Sichtung erweitern wir.

Der Pilot muss eine Forschungsentscheidung ermöglichen. Große Infrastruktur, zusätzliche Backends und breite Parameterstudien brauchen einen konkreten Nutzen für diese Entscheidung. Der Zeitplan vom 21.10. wird beim Wiedereinstieg aktualisiert; seine damaligen 20 Tage gelten nicht unverändert weiter.

### 7. Hardware schon in Punkt 1 erfassen

Beim Einrichten des Repos führen wir einen kurzen, lesenden Inventarbefehl oder Befehlsblock aus und speichern CPU, RAM, GPU/VRAM, Betriebssystem, Treiber und relevante Laufzeitversionen. Ein eigenes Hardware-Framework ist dafür unnötig.

Repo, Literatur, Dokumentation und Altdaten-Sichtung können am Laptop erfolgen. Für den geplanten GPU-LLM-Piloten sehen wir den Rechner mit der RTX 3090 als Messrechner vor. Die konkrete Eignung von Modell und Engine bestätigen wir anhand des Inventars und eines kurzen Starttests. Geräteangaben aus alten Chats ersetzen keine aktuelle Aufnahme.

### 8. Stack und Daybreak Blue gezielt einsetzen

Rust, OpenCL, CUDA oder Alternativen werden nach Forschungsfrage, Hardware und Aufwand gewählt. Wir dürfen Rust für die Freigabeschicht mit einer bestehenden GPU-Engine kombinieren. Ein Backend-Wechsel bekommt nur dann Vorrang, wenn er den Pilot erleichtert oder eine relevante Zusatzfrage prüft.

Wenn Daybreak Blue an einer Stelle hilfreich sein könnte, weise ich ausdrücklich darauf hin und formuliere einen begrenzten Auftrag mit benötigten Dateien und erwarteter Rückgabe, beispielsweise zur Prüfung eines relevanten Implementierungsfehlers. Fähigkeiten und Zugriff werden vorab geklärt. Der Einsatz erfolgt nach gemeinsamer Entscheidung; ich behaupte keine bereits vorhandene Verbindung.

### 9. Kleine, zweckmäßige Programme und Dokumentation

Wenige verständliche Dateien, klare Funktionen, direkte Namen und Kommentare dort, wo sie beim Verstehen helfen. Keine unnötigen Wrapper, Helper-Ketten, Frameworks oder Skripte für Einmalbefehle. Auch keine riesige Sammeldatei: aufteilen, wenn eine eigenständige Verantwortung oder die Lesbarkeit es rechtfertigt.

Dokumentation hält Forschungsentscheidungen, Bedienung und Befunde fest. Sie wiederholt weder den Chat noch denselben Stand in mehreren Dateien. Sprache und Struktur bleiben knapp, sachlich und natürlich.

### 10. Nach größeren Schritten einen verlässlichen Übergabestand hinterlassen

Nach jeder abgeschlossenen Etappe und jeder wesentlichen Änderung dokumentieren wir kurz: umgesetzt, geprüft, Ergebnis, offene Frage und nächster Mini-Schritt. Dazu gehören relevante Dateipfade, Datenablage und vorhandener Commit; ein Commit wird nur als vorhanden angegeben, wenn er tatsächlich erstellt wurde.

Im Repo reichen für den Anfang: dieser Kodex als `AGENTS.md`, eine kurze `README.md`, `docs/stand.md` und `docs/quellen.md`. Versuchsprotokolle und Messdateien kommen hinzu, wenn gebraucht; keine parallelen Übergabedokumente für jeden Chat. Rohdaten werden nicht überschrieben, Behauptungen bleiben auf konkrete Messungen zurückführbar.

Jeder neue Chat erhält Zugriff auf das Repo oder die aktuellen Dateien. Ein Dateipfad allein garantiert keinen Zugriff. So bleibt die Fortsetzung möglich, ohne die gesamte Unterhaltung neu aufzubereiten.

## Startkarte der bisherigen Quellen

Stand der folgenden Angaben: frühere Audits bis 21.10.2026 und damaliger Claude-Abgleich. Dies ist eine Zusammenführung der vorhandenen Quellenhinweise, keine neue Volltextprüfung vom 31.10. Aktuelle LLM-Arbeiten stehen im Vordergrund; ältere Texte sichern bekannte Grundlagen ab. Die Karte ist kein Anspruch auf eine vollständige Literaturrecherche.

| Quelle | Für unsere Arbeit wichtig |
| --- | --- |
| [Eigene ICCAI-2026-Arbeit](https://doi.org/10.1145/3821244.3821268) | Ausgangsbefund, ODS und BOS; gesamte Ranginformation und individuelle Wartezeit als Anschlussfragen. |
| [ordleak, geprüfter Commit](https://github.com/TheBuccaneer/ordleak/tree/2dad2ecb3116f4826f234d0da550dd83bfdfb474) | Tatsächliche Blockmischung, Seeds und verfügbare Logs; Code ist keine Bestätigung eines neuen LLM-Befunds. |
| [PROMPTPEEK, NDSS 2025](https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf) | Rückgabereihenfolge bei LPM ist bereits ein bekannter LLM-Kanal; besonders §IV-A. |
| [OptiLeak, 2026](https://arxiv.org/html/2602.20595v1) | Positionsfeedback und Anfrageeffizienz; stärkere Beobachter als nur ein ODS-Schwellwert. |
| [SafeKV, geprüfte v2](https://arxiv.org/html/2508.08438v2) | Selektives Cache-Sharing und Schutz bei erhaltener Wiederverwendung; direkte Vergleichsbasis für Schutzkosten. |
| [CachePrune, 2026](https://arxiv.org/html/2605.23640v1) | Feingranulare Wiederverwendung; Scheduling-Priorität gehört bereits zum Reuse-Modell. |
| [KVGov, 2026](https://arxiv.org/html/2608.09225v1) | Namespace-/Salt-Schutz; Simulation, reale Messung und Extrapolation auseinanderhalten. |
| [AgentFlowShield, 2026](https://yulliwasameur.github.io/publication/2026-09-18-agentflowshield/paper.pdf) | Ausgabeformung und Latenzkosten im AI-Kontext; Beobachter sieht Paketmetadaten statt Antwort-IDs. |
| [EarlyBird, geprüfte v3](https://arxiv.org/html/2409.20002v3) | Cache-Kanäle und bekannte Änderungen an Sharing und Scheduling. |
| [Timeless Timing Attacks, 2020](https://www.usenix.org/system/files/sec20-van_goethem.pdf) | Grundprinzip timerfreier Inferenz aus Reihenfolgen. |
| [Mitigating Timing Side Channel in Shared Schedulers, 2013](https://arxiv.org/pdf/1302.6123) | Bekannte Kopplung zwischen Pufferung, Privatsphäre und Verzögerung. |
| [Deterministic Work-Conserving Schedulers, 2014](https://arxiv.org/pdf/1403.1276) | Modellabhängige Informationsgrenzen; nicht ungeprüft auf reine Ränge übertragen. |
| [Pacer, 2022](https://www.usenix.org/system/files/sec22-mehta.pdf) | Entkopplung sichtbarer Ausgabe von interner Ausführung. |
| [NetShaper, geprüfte Vorabfassung](https://www.usenix.org/system/files/sec24summer-prepub-168-sabzi.pdf) | Schutz-/Kostenverträge bei Traffic Shaping; Versionsstatus beachten. |
| [Controlled Preemption, 2025](https://cwfletcher.github.io/content/research/2025.asplos.controlledpreemption.paper.pdf) | Scheduling und Fairness als Einflussfaktoren; relevant für Mechanismuskontrollen. |
| [Timeless Timing Attacks and Preload Defenses in Tor’s DNS Cache, 2023](https://www.usenix.org/system/files/usenixsecurity23-dahlberg.pdf) | Beispiel einer konkreten Anschlussarbeit auf bekanntem Mechanismus. |
| [Shuffling against Side-Channel Attacks, 2012](https://doi.org/10.1007/978-3-642-34961-4_44) | Eingeschränkte Permutationen können schwächer schützen; inzwischen bereitgestellter Volltext, kein direkter Nachweis für BOS-Leakage. |
| [Predictive Black-Box Mitigation, 2010](https://www.cs.cornell.edu/andru/papers/timing.html) und [Predictive Mitigation in Interactive Systems, 2011](https://www.cs.cornell.edu/andru/papers/gentiming.html) | Vorarbeiten zur kontrollierten Freigabe; keine Neuerfindung des allgemeinen Verzögerungsprinzips beanspruchen. Lesestatus für konkrete Claims erneut festhalten. |
| Giles & Hajek, „An Information-Theoretic and Game-Theoretic Study of Timing Channels“, 2002 | Historische Theorie zu Verzögerungsbeschränkungen; PDF bereits vorhanden, kein Schwerpunkt der LLM-Abgrenzung. |
| [Auditing Prompt Caching in Language Model APIs, ICML 2025](https://mlanthology.org/icml/2025/gu2025icml-auditing) | Ergänzender Hinweis aus Claudes Quellenliste; konkreten Volltext und Nutzen vor Verwendung prüfen. |

Die im LLM-Audit genannten Kerntexte PROMPTPEEK bis EarlyBird wurden damals gezielt im Originalvolltext gelesen. Das ersetzt keine neue Prüfung der Fundstellen, auf denen ein späterer Claim tatsächlich beruht.

**Offene oder bisher nur begrenzt geprüfte Quellen:**

- [Wiretapping LLMs](https://eprint.iacr.org/2025/167): bislang Abstract, Volltextzugriff gescheitert; wichtig bei Streaming-/Timing-Schutz.
- [InputSnatch](https://arxiv.org/abs/2411.18191): bislang Abstract; mögliche Vergleichsarbeit für Cache-/Timing-Inferenz.
- [Contention-Induced Reliability Collapse](https://arxiv.org/abs/2609.06853): bislang bibliografischer Hinweis; potenziell wichtig für Robustheit unter Konkurrenz.
- [Scheduler-Boundary Observability in Shared Quantum Clouds](https://www.mdpi.com/2079-3197/14/9/197): ungeprüfter Transferhinweis, derzeit nachrangig.
- [How (not) to use Welch’s t-test](https://eprint.iacr.org/2017/138): bislang bibliografischer Hinweis; erst bei entsprechender Auswertungsfrage relevant.
- [Delay-Privacy Tradeoff, Journalfassung 2015](https://doi.org/10.1109/TIT.2015.2406317) und [Threshold Pool Mixes, 2014](https://doi.org/10.1016/j.comnet.2014.04.007): historische Volltextlücken, kein Anlass, den LLM-Piloten zu blockieren.

**Weitere Arbeitsgrundlagen:** RDNA V6.1 und aktueller Arbeitsauftrag; [SGLang-Serverargumente](https://docs.sglang.io/docs/advanced_features/server_arguments), [vLLM-Sicherheit](https://docs.vllm.ai/en/latest/usage/security/), [vLLM-Prefix-Caching](https://docs.vllm.ai/en/latest/design/prefix_caching/), [llama.cpp-Backends](https://github.com/ggml-org/llama.cpp), insbesondere [OpenCL](https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/OPENCL.md); [ICCAI](https://www.iccai.net/), [Submission](https://www.iccai.net/submission.html), [Registrierung/Umfang](https://www.iccai.net/registration.html). Technische Versionen, Seitenvorgaben und Frist werden vor ihren jeweiligen Entscheidungen aktuell verifiziert.

Der frühere allgemeine RDNA-Audit dient als Vorgeschichte. Für den Umfang gelten der spätere Arbeitsauftrag und diese gemeinsam abzustimmende Arbeitsweise; ältere breitere Studienvorschläge werden nicht automatisch wieder zum Pflichtprogramm.

