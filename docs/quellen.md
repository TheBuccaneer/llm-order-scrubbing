# Literatur und Quellen

Stand: 03.11.2026

## Zwei-Benutzer-Scheduler-Pilot vom 03.11.2026

Gezielte aktuelle Originaltextprüfung für den neuen
getrennte-Salts-Claim. Dies ist **kein** vollständiger
systematischer Neuheitsnachweis; frühere Quellen bleiben erhalten.

| Originaltext und Lesestatus | Bedeutung für den Pilot |
| --- | --- |
| [vLLM 0.17.1, Automatic Prefix Caching](https://docs.vllm.ai/en/v0.17.1/design/prefix_caching/), „Note 1“ und „Cache Isolation for Security“, heute L2 | Salt im ersten Block trennt direkte KV-Wiederverwendung. Der Pilot misst zusätzlich, ob der gemeinsame Scheduler den fremden Cachezustand indirekt sichtbar macht. |
| [KVGov v1](https://arxiv.org/html/2608.09225), §§4.1–4.3 und Evaluation, heute L2 | Per-Principal-Salt verhindert das dortige direkte Cache-Fingerprint-Orakel. Dessen ORIGAMI ist ein **Audit**-Scheduler, keine gemessene Antwortfreigabe-Isolation. Der hiesige indirekte B-only-Kanal ist eine andere Angriffsfläche; keine pauschale Widerlegung von KVGov. |
| [FairInference v1](https://arxiv.org/html/2609.18112), §§2.1–2.2, 5 und 7.1.1, heute L2 | Mehrbenutzer-Interferenz durch Scheduler und unterschiedliche Präfixtreffer sowie Latenzisolation sind bereits erforscht. Vertraulichkeitsinferenz aus vollständigen Antworten bei getrennten Salts ist hier die engere zu prüfende Frage; Interferenz allein ist nicht neu. |
| [Pacer, USENIX Security 2022](https://www.usenix.org/system/files/sec22-mehta.pdf), §3.2 und §4, heute L2 | Geheimnisunabhängiger tatsächlicher Sendeplan einschließlich Abweichungen ist bekannt. Ein neuer öffentlicher Slot wäre ohne bessere Kosten-/Leckagewerte keine eigenständige Methode. |
| [Abu Bakar, „Contention-Induced Reliability Collapse“, v1](https://arxiv.org/html/2609.06853), §§IV und XV, heute L2 | Konkurrenzstruktur und Überlappung beeinflussen Cache-Timing-Zuverlässigkeit. Der vorliegende ruhige, synchronisierte Pilot ist eine günstige Bedingung und nicht auf Mehrnutzerlast extrapolierbar. |

## Llama-Referenzvalidierung vom 03.11.2026

Gezielte aktuelle technische Nachprüfung (RDNA L2 für die
genannten Dokumentationsabschnitte), kein neuer vollständiger
Novelty-Audit. Die im weiteren Dokument aufgeführten
Originalarbeiten bilden weiterhin die wissenschaftliche
Abgrenzung des BOS-Claims.

- [Meta, Llama-3.1-8B-Instruct-Modellkarte](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct), Modellidentität und vLLM-/Chat-Anwendungsbeispiel: offizieller Primärtext. Die tatsächliche lokale Ladefähigkeit und Tokenisierung wurden eigenständig geprüft.
- [vLLM 0.17.1, Automatic Prefix Caching](https://docs.vllm.ai/en/v0.17.1/design/prefix_caching/), Einleitung, „Note 1“ und „Cache Isolation for Security“: nur volle KV-Blöcke werden wiederverwendet; der erste Block trägt den optionalen Salt. Die gemessenen 304/544-Token-Treffer sind lokale Beobachtungen, nicht aus der Dokumentation abgeleitet.
- [vLLM 0.17.1, Scheduler-Konfiguration](https://docs.vllm.ai/en/v0.17.1/api/vllm/config/scheduler/), `max_num_batched_tokens` und `long_prefill_token_threshold`: C0/C1 sind bewusste lokale Konfigurationsvarianten. Ein modellübergreifend gleicher Schedulerablauf wird daraus nicht behauptet.

## Ausgangsbasis

Die vollständige bisherige Quellenkarte befindet sich
im Abschnitt "Startkarte der bisherigen Quellen" in AGENTS.md.

Sie umfasst:
- Eigene ICCAI-2026-Arbeit und ordleak
- Aktuelle LLM-Side-Channel-Arbeiten
- Grundlagen zu Timing-Kanälen und Schutzverfahren
- Technische Dokumentation der vorgesehenen Engines

## Prüfstatus

Die bisherigen Lesestände sind in AGENTS.md dokumentiert.
Am 31.10.2026 erfolgte noch keine neue Volltextprüfung.

Ab Etappe 3 wird die Quellenkarte hier fortgeführt.
Für wissenschaftliche Aussagen dokumentieren wir
Version, relevante Fundstellen und RDNA-Lesestatus.

## Artefaktprüfung vom 02.11.2026 (Etappe 2)

Keine neue Literatur- oder Novelty-Prüfung; die bisherige Quellenkarte bleibt
unverändert. Neu geprüft wurden technische Primärartefakte:

- [ordleak, festgehaltener Commit](https://github.com/TheBuccaneer/ordleak/tree/2dad2ecb3116f4826f234d0da550dd83bfdfb474):
  vollständiger Git-Baum; `src/victim.py` (BOSScrubber und dessen Initialisierung
  pro RUN), `src/client_rank_only.py` (Reihenfolge ohne Zeiten),
  `scripts/run_dataset.py`, `scripts/analyze.py`, `scripts/overhead_sweep_pure.sh`
  und `.gitignore` gelesen; je eine Stage-3- und Overhead-CSV stichprobenartig
  gelesen. Online nachgeprüft, nicht lokal installiert oder ausgeführt.
- `/home/rock/projects/vllm-offload-profiles`, Commit
  `547be9005dd6483d21e15e32416ffab96d1a2e63`: README, Umgebungsbeschreibung,
  Baseline-Qwen-Start-/Clientskripte und je eine Baseline-JSON beider Modelle.
  Relevant für vorhandene Infrastruktur und tatsächlich erhaltene Zeitfelder.
- `/home/rock/projects/porto`, Commit `72b9272c59ca0738ffe7fb012b9a33169b3b941f`:
  Serverstarts, `step3_policy_gating/victim_worker.py` und eine zugehörige JSON;
  historischer Erfolgsbeleg in
  `server_logs_qwen/server_qwen_offload0_20260727_162821.log`.
- Lokale vLLM-0.17.1-Installation unter `porto/.venv-py313-repair`:
  `vllm/config/cache.py`, `vllm/config/scheduler.py` sowie
  `vllm/benchmarks/serve.py` (Anfragezuordnung der Ergebnisarrays,
  gespeicherte Zeitfelder und Timeline-Berechnung) gezielt gelesen.
  Keine aktuelle Funktionsprüfung und keine Aussage zur Engine-Auswahl.

Die konkreten Befunde und Grenzen stehen ohne weitere Ergebnisdatei in
`docs/stand.md`.

## Gezielte Nachprüfung vom 02.11.2026 (Etappe 3)

Begrenzte Online-Suche zu LLM-Antwortreihenfolge, Cache und Scheduling sowie
Nachlesen der folgenden entscheidungsrelevanten Primärquellen. Keine Aussage
über Vollständigkeit oder Neuheit des Gesamtprojekts. Frühere Lesestände der
übrigen Quellenkarte bleiben unverändert; heute jeweils RDNA **L2**:

| Quelle / Fassung | Heute gelesene Fundstelle und Bedeutung |
| --- | --- |
| [PROMPTPEEK, NDSS-2025-PDF](https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf) | §III-B, §IV-A (S. 4–6), §VIII/andere Scheduling-Policies (S. 13): API-Beobachter, LPM und Warteschlangenbedingungen; kein allgemeiner Nachweis für modernes vLLM-FCFS |
| [OptiLeak v1](https://arxiv.org/html/2602.20595v1) | §3.1, §4.2, Beginn §5.1: Positionsfeedback, LPM und SGLang; stärkerer Beobachter als ein einzelner ODS-Wert bereits bekannt |
| [SafeKV v2](https://arxiv.org/html/2508.08438v2) | §5–6: Schutz an der Wiederverwendung, TTFT als untersuchte Oberfläche und Grenzen; keine Aussage über BOS |
| [vLLM 0.17.1: APC-Nutzung](https://docs.vllm.ai/en/v0.17.1/features/automatic_prefix_caching/) | Introduction und Limits: Einsparung im Prefill, nicht Decode; begründet kurze Ausgaben im Kanaltest |
| [vLLM 0.17.1: APC-Design](https://docs.vllm.ai/en/v0.17.1/design/prefix_caching/) | Volle Blöcke, Blockhashes, Cache Isolation for Security: `cache_salt` trennt Wiederverwendung; keine garantierte Rangwirkung |
| [SGLang: Serverargumente](https://docs.sglang.io/docs/advanced_features/server_arguments) | Memory and scheduling, `--schedule-policy`: FCFS als aktueller Standard, LPM als Option; laufende Dokumentation, keine lokale Installation geprüft |

Zusätzlich lokal gelesen: vLLM-0.17.1-Protokolle in
`porto/.venv-py313-repair/.../vllm/entrypoints/openai/` für
`cache_salt` und `prompt_tokens_details.cached_tokens`. Letzteres ist gegebenenfalls
direkt clientseitig sichtbare Cache-Evidenz und muss vom Rang-/Timing-Beobachter
ausdrücklich unterschieden werden. Importprüfung: Python 3.13.7,
torch 2.10.0+cu128, vllm 0.17.1; CUDA-Geräteerkennung erfolgreich.

## Gezielte Nachprüfung für den lokalen Pilot (02.11.2026)

Keine neue breite Literatur- oder Neuheitsrecherche. Für die konkrete
Machbarkeitsfrage wurden folgende Primärstellen erneut beziehungsweise
zusätzlich gelesen (RDNA L2):

- [PROMPTPEEK, NDSS-2025-PDF](https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf),
  §II-B und §IV-A, S. 3 und 5–6: LPM priorisiert Cache-Treffer; die
  Angriffsmessung nutzt eine bewusst gefüllte Warteschlange. Das begründet
  keine entsprechende Rangwirkung im lokalen FCFS-Server.
- [vLLM 0.17.1, Scheduler-Konfiguration](https://docs.vllm.ai/en/v0.17.1/api/vllm/config/scheduler/),
  `policy` und `max_num_batched_tokens`: FCFS als Standard, Tokenbudget
  je Schritt. Lokal mit der installierten Konfiguration und dem Startlog
  abgeglichen.
- [vLLM 0.17.1, Optimization and Tuning](https://docs.vllm.ai/en/v0.17.1/configuration/optimization/),
  Abschnitt „Chunked Prefill“: bei zu kleinem Budget wird ein Prefill
  auf mehrere Scheduler-Schritte verteilt. Das motiviert genau die eine
  zusätzliche Budget-256-Bedingung im Pilot.

Ergebnis und Grenzen der Messung stehen in
`results/order-feasibility-20261102/auswertung.md`. Aus dieser begrenzten
Prüfung folgt kein allgemeiner Neuheits- oder Sicherheitsclaim.

## Originaltext-Nachprüfung zum deutlichen Rangkanal (02.11.2026)

Gezielte Online-Recherche und Lektüre benannter Originalabschnitte, kein
separater Deep-Research-Lauf und keine erschöpfende Novelty-Prüfung.
Die Etappenentscheidung lautet: Lokaler Basiskanal vorhanden; als Nächstes
Schutzwirkung und individuelle Zusatzwartezeit messen. Heute RDNA L2:

| Primärquelle / Fassung | Geprüfte Stelle und Abgrenzung |
| --- | --- |
| [PROMPTPEEK, NDSS 2025](https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf) | §II-B und §IV-A, insb. Kandidaten-/Dummy-Versand: LPM-Warteschlangenpriorisierung erzeugt dort ein Reihenfolgesignal. Unser lokaler FCFS-/Chunked-Prefill-Aufbau ist anders; Rang-Leakage selbst ist nicht neu. |
| [OptiLeak v1, Februar 2026](https://arxiv.org/html/2602.20595v1) | §3.1, §4.2, §5.1 und §6: Ordnung/Position als Feedback für optimierte Promptrekonstruktion. Ein stärkerer Beobachter als ein einzelner ODS-Wert ist bereits Vorarbeit; unser Pilot zeigt keine Rekonstruktion. |
| [Contention-Induced Reliability Collapse, September 2026](https://arxiv.org/html/2609.06853) | §XIV-D und §XV–XVI: Last und Überlappung können Kanalzuverlässigkeit verändern; empfiehlt Angaben zu Scheduler, Prompt-/Ausgabelänge, Cachezustand und runweisen Verteilungen. Hier noch keine Lastvariation. |
| [KVGov v1, August 2026](https://arxiv.org/html/2608.09225v1) | §4.1–4.2, §5.7 und §7: Namespace-Isolation als Gegenmaßnahme; reales Qwen/vLLM-TTFT-Experiment, während weitere Schutzbehauptungen auf Simulation bzw. Extrapolation beruhen. Geteilte Salts im lokalen Pilot sind ausdrücklich eine Bedingung, keine Eigenschaft aller Dienste. |
| [SafeKV v2](https://arxiv.org/html/2508.08438v2) | §6–7.2: Cache-Sharing/Isolation und TTFT als andere Schutzfläche. Kein dort belegter Vergleich vollständiger Antwortfreigaben unter individueller Deadline. |
| [Cache Me, Catch You, NDSS 2026](https://www.ndss-symposium.org/wp-content/uploads/2026-f2812-paper.pdf) | Abstract, Einleitung und §VIII: Cache-Kollisionen und -Vergiftung mit Fokus auf Integrität; die vorgeschlagene Randomisierung betrifft Cache-Hashing, keine Freigabe vollständiger Antworten. Thematisch relevante Cache-Sicherheitsarbeit, aber kein direkter BOS-Vergleich. |
| [vLLM 0.17.1, Scheduler-Konfiguration](https://docs.vllm.ai/en/v0.17.1/api/vllm/config/scheduler/) | `policy`, `max_num_batched_tokens`, `long_prefill_token_threshold`, `max_num_partial_prefills`: FCFS ist Standard, Schwelle und Tokenbudget sind explizite Einstellungen. Wichtig zur Reproduzierbarkeit; keine allgemeine vLLM-Default-Aussage. |
| [vLLM 0.17.1, Optimierung](https://docs.vllm.ai/en/v0.17.1/configuration/optimization/) | „Chunked Prefill“: lange Prefills können in mehrere Schritte zerlegt werden. Dies stützt die Hypothese zum lokalen Effekt, ersetzt keinen internen Scheduler-Trace. |

Der installierte Quellcode in
`/home/rock/projects/porto/.venv-py313-repair/lib/python3.13/site-packages/vllm/v1/core/sched/scheduler.py`
wurde nur gelesen, insbesondere die Tokenbegrenzung durch
`long_prefill_token_threshold` für laufende und wartende Anfragen.
Versuch und Auswertung stehen in
`results/full-order-20261102/auswertung.md`. Die aufgelisteten Fundstellen
reichen für die lokale Pilotentscheidung, nicht für einen abschließenden
Beitragstitel oder Neuheitsanspruch.

## Nachprüfung vor zwei Anschlussversuchen (02.11.2026)

Auf Nutzerwunsch wurden **vor** den weiteren Messungen online die
Originalvolltexte erneut gezielt geprüft. Ein gesondertes Deep-Research-
Werkzeug stand nicht zur Verfügung. RDNA-Status für diese heutige Lektüre
jeweils **L2** (benannte Originalabschnitte, teils Ergebnisse und Grenzen):

| Security-Arbeit | Geprüfte Stelle | Konsequenz für den lokalen Test |
| --- | --- | --- |
| [PROMPTPEEK, NDSS 2025](https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf) | §IV-A, S. 5–6: Dummies/Kandidaten in gefüllter Warteschlange, genau ein Ausgabetoken. §VIII, S. 13: damalige Einordnung anderer Scheduler. | Weg 1 verlässt die Ein-Token-Annahme bewusst; LPM-Warteschlangenbefund wird nicht auf vLLM-FCFS übertragen. Die damalige FCFS-Einordnung ist für aktuelle vLLM-Versionen nicht maßgeblich. |
| [EarlyBird v3](https://arxiv.org/html/2409.20002v3) | §2.2 und §4: TTFT als Beobachtung; die end-to-end Probe fordert ein Ausgabetoken an. | Vollständige Antwortreihenfolge bei 16 Tokens ist eine andere Oberfläche als TTFT. |
| [OptiLeak v1](https://arxiv.org/html/2602.20595v1) | §4.2 und §6: Positionsfeedback unter SGLang/LPM, mögliche Anpassung eines Validators an andere Engines. | Positionsfeedback ist Vorarbeit; ein lokales vLLM-Signal allein ist kein eigenständiger Neuheitsclaim. |
| [Contention-Induced Reliability Collapse v1](https://arxiv.org/html/2609.06853) | §IV-B/C, §V, §IX, §XIV-D und §XV–XVI: vLLM-Timingprobe mit einem Token; Last mindert Zuverlässigkeit, gemessene Überlappung und runweise Verteilungen sind entscheidend; keine universelle Schwelle. | Weg 2 misst die tatsächlich überlappende Zusatzanfrage und vollständige Ränge. Die dortige Timing-Verschlechterung wird nicht auf Ränge hochgerechnet. |
| [SafeKV v2](https://arxiv.org/html/2508.08438v2) | §7.2: Schutzbewertung auf TTFT-basierte Unterscheidbarkeit; Cache-Freigabe als eigene Schutzfläche. | Kein direkter Vergleich zu blockweiser Freigabe vollständig fertiger Antworten; gemeinsam gesalzener Cache bleibt eine Bedingung des Piloten. |

Die Entscheidung lautete nach dieser Lektüre: ein Pilot mit **16
Ausgabetokens** und ein separater Pilot mit **überlappender
Hintergrundanfrage**, jeweils mit Cache-aus-Kontrolle. Ergebnisse in
`results/two-extensions-20261102/auswertung.md`. Beide Piloten
untersuchen Robustheit des lokalen Basiskanals, nicht Angriffserfolg oder
Schutzwirkung. Weitere Literaturprüfung ist vor einem Paper-Claim nötig.

## Quellenabgleich zum BOS-Schutz-/Kostenpilot (02.11.2026)

Vor dem durchgängigen Versuch wurden die folgenden Primärtexte gezielt
online nachgelesen (heute jeweils RDNA L2, keine abschließende
Novelty-Prüfung):

| Originaltext | Gelesene Fundstelle | Grenze für unseren Claim |
| --- | --- | --- |
| [PROMPTPEEK, NDSS 2025](https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf) | §IV-A: Antwortreihenfolge bei gefüllter LPM-Warteschlange und Ein-Token-Probes. | Reihenfolge-Leakage ist bekannt; unser Schutzpilot verwendet vollständige 16-Token-Antworten und vLLM-FCFS mit begrenztem Prefill. |
| [OptiLeak v1](https://arxiv.org/html/2602.20595v1) | §4.2 und §6: Positionsfeedback und Austauschbarkeit des Validators. | Ein stärkerer Rangbeobachter ist Vorarbeit, nicht unsere Erfindung. |
| [Mitigating Timing Side Channel in Shared Schedulers](https://arxiv.org/pdf/1302.6123) | §V-A/B, S. 5–7: Accumulate-and-Serve, längere Sammelintervalle gegen höhere Verzögerung. | Pufferung und Privatsphäre-/Wartezeitkonflikt sind allgemeine Vorarbeit; die dortigen formalen Garantien gelten nicht für den hiesigen LLM-Proxy. |
| [Pacer, USENIX Security 2022](https://www.usenix.org/system/files/sec22-mehta.pdf) | §3.1/§3.2 und §4, insb. S. 4–8: Ausgabe nach einem geheimnisunabhängigen Zeitplan, Verankerung an öffentlichen Anfrageereignissen und Umgang mit Verzögerungen. | Feste Ausgabezeit und Traffic Shaping sind bekannt; der Slot-Pilot ist nur ein Vergleich an vollständigen LLM-Antworten, keine Pacer-Sicherheitsgarantie. |
| [Contention-Induced Reliability Collapse v1](https://arxiv.org/html/2609.06853) | §XIV-D und §XV–XVI: Konfiguration, Länge, Überlappung und Rohverteilungen transparent berichten; keine universellen Lastschwellen. | Die heutigen BOS-Ergebnisse gelten nicht automatisch unter Mehrnutzerlast. |

Der lokale `ordleak`-Code wurde bereits am dokumentierten Commit geprüft:
`BOSScrubber` mischt W fertiggestellte Antworten und besitzt keine
individuelle Deadline. Der neue Proxy übernimmt diese Blockregel
inhaltlich und untersucht zwei **explizit neue Varianten**:
Deadline-Flush und festen Freigabezeitpunkt. Ein nachträglicher
Rangwechsel in einer CSV wäre keine gleichwertige Messung; hier wurden
Backend-Eingang, Proxyfreigabe und Clientempfang tatsächlich erfasst.
Die Ergebnisse und Grenzen stehen in
`results/bos-sanitized-20261102/auswertung.md`.

## Quellenprüfung für die wissenschaftliche Entscheidung (02.11.2026)

Heute nochmals gezielt online geprüft; Lesestatus **L2** bedeutet
benannte relevante Volltextabschnitte einschließlich der für den
Claim wichtigen Grenzen, keine vollständige systematische
Literaturübersicht. Einzelheiten und die experimentelle Entscheidung
stehen in `docs/entscheidungsvalidierung-20261102.md`.

| Primärquelle | Heute geprüfte Stelle | Bedeutung / Grenze |
| --- | --- | --- |
| [Eigene ICCAI-2026-Arbeit](../references/iccai2026-completion-order.pdf), [DOI](https://doi.org/10.1145/3821244.3821268) | **L3**: vom Autor bereitgestellter Volltext, §§2–6 einschließlich ODS-Methode, BOS-Sweep, Kosten und Grenzen gelesen. | Der Angreifer verwendet ausdrücklich nur Ränge und keine Zeiten. BOS bei CPU/MEM W=4: ODS-AUC 0,750; W=16: 0,449. Die Angabe ±0,1 % betrifft Gesamtlaufzeit unter Angriffslast, keine individuellen Antwortwartezeiten. AI-Serving ist in §5 ein Ausblick, keine Messung. Der [ordleak-Commit](https://github.com/TheBuccaneer/ordleak/tree/2dad2ecb3116f4826f234d0da550dd83bfdfb474) ergänzt die Implementierung. |
| [PROMPTPEEK, NDSS 2025](https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf) | **L2**, §III–IV-A, insbesondere Kandidaten-/Dummy-Versand und LPM-Warteschlange; Ergebnisabschnitte. | Cacheabhängige Antwortreihenfolge und Promptrekonstruktion sind bekannt; kein direkter Beleg für vLLM-FCFS mit Chunked Prefill. |
| [OptiLeak v1](https://arxiv.org/html/2602.20595v1) | **L2**, §3.1, §4.2, §6. | Positionsfeedback und stärkere Kandidatenauswahl sind Vorarbeit; ein R2-Beobachter ist kein Neuheitsclaim. |
| [Mitigating Timing Side Channel in Shared Schedulers](https://arxiv.org/pdf/1302.6123) | **L2**, §V–VI: Accumulate-and-Serve, Verzögerungs-/Privatsphäre-Grenze. | Pufferung ist nicht neu; die dortigen Garantien gelten nicht automatisch für fertiggestellte LLM-HTTP-Antworten. |
| [Pacer, USENIX Security 2022](https://www.usenix.org/system/files/sec22-mehta.pdf) | **L2**, §2.2, §3–4 und Behandlung realer Sendeabweichungen. | Geheimnisunabhängige Freigabe muss auch bei Abweichungen gelten. Der hier getestete `late_fallback` verletzt genau die benötigte Unabhängigkeit; dies ist eine Anwendung des bekannten Prinzips, keine neue allgemeine Theorie. |
| [NetShaper, USENIX Security 2024, Vorab-PDF](https://www.usenix.org/system/files/sec24summer-prepub-168-sabzi.pdf) | **L2**, §3–5, insbesondere Zeitintervall und Latenz-/Bandbreitenkosten. | Formaler Traffic-Shaping-/Kostenansatz für Netzverkehr; unser lokaler Proxy hat keine entsprechende Privatsphäre-Garantie. |
| [SafeKV v2](https://arxiv.org/html/2508.08438v2) | **L2**, §2, §6–7: Cache-Sharing und TTFT-Unterscheidbarkeit, Grenzen. | Schutz an der Wiederverwendung ist eine andere Oberfläche als die Freigabe vollständiger Antworten; gemeinsame Salts bleiben im lokalen Versuch notwendig. |
| [vLLM 0.17.1 SchedulerConfig](https://docs.vllm.ai/en/v0.17.1/api/vllm/config/scheduler/) und [Optimization](https://docs.vllm.ai/en/v0.17.1/configuration/optimization/) | **L2**, `enable_chunked_prefill`, `long_prefill_token_threshold`, `max_num_batched_tokens`; Abschnitt „Chunked Prefill“. | C1/C2 wurden anhand ihrer echten Serverlogs und des lokal installierten Schedulercodes, nicht anhand vermuteter Defaults, eingeordnet. |

Die vorläufige Paper-Richtung baut auf bekannten Prinzipien auf:
vollständige LLM-Antworten, lokales Blockschluss-Signal, individuelle
Wartezeiten und beobachteter Slot-Fallback. Der Volltextabgleich mit
der eigenen Arbeit ist nun abgeschlossen: Die neue Fragestellung
erweitert deren bewusst rangbeschränktes Modell. Ein allgemeiner
Neuheitsclaim benötigt weitere Prüfung der Übertragbarkeit und
verwandter LLM-Schutzarbeiten.

## Release-Boundary-Nachprüfung (02.11.2026)

Gezielte aktuelle Online-Lektüre der für den neuen Claim relevanten
Originalabschnitte, jeweils **RDNA L2**; keine vollständige
systematische Neuheitsrecherche. Einzelheiten und die konkrete
Abgrenzung stehen in `docs/release-boundary-20261102.md`.

| Fassung und Fundstelle | Aussage für die Entscheidung |
| --- | --- |
| [PROMPTPEEK, NDSS 2025](https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf), §IV-A, S. 4–6 | LPM-gestützte Antwortreihenfolge mit Ein-Token-Probes und Dummies. Kein Test eines Freigabe-Fallbacks vollständiger Antworten. |
| [OptiLeak v1](https://arxiv.org/html/2602.20595v1), §§3.1, 4.2, 6 | Ein Rangpositionsabstand dient bereits als Cachefeedback. „Gap“ hier ist Rangabstand; der neue Versuch misst einen Zeitabstand, aber ein Gap-Merkmal allein ist nicht neu. |
| [Carlini/Nasr 2024](https://arxiv.org/html/2410.17175), §§III–IV, VII | Aktive Timing-Probes und fester Ausgabetakt mit Leernachrichten bei nicht bereiten Tokens; Schutz-/Kostenprinzipien sind bekannt. |
| [Pacer, USENIX Security 2022](https://www.usenix.org/system/files/sec22-mehta.pdf), §§2.2–4 | Tatsächliche Abweichungen von einem geheimnisunabhängigen Sendeplan dürfen selbst keinen geheimen Laufzeitverlauf zeigen. Unser lokaler Fallback illustriert diesen bekannten Punkt. |
| [Accumulate-and-Serve, 2013](https://arxiv.org/pdf/1302.6123), §§V–VI | Sammelintervalle und formale Verzögerungs-/Privatsphäre-Grenze; nicht direkt auf den LLM-Proxy übertragbar. |
| [SafeKV v2](https://arxiv.org/html/2508.08438v2), §§4.1–4.2, 7.2 | Der dortige Safeguard-Fallback isoliert verdächtige Cacheblöcke; keine späte Einzelfreigabe von HTTP-Antworten. |
| [CacheSolidarity v1](https://arxiv.org/html/2603.10726v1) und [PrefixWall v2](https://arxiv.org/html/2603.10726v2), §§2.4, 4–5 | Versionswechsel desselben arXiv-Eintrags; selektive Cacheisolation und benannte Schutzgrenzen, keine BOS-/Slot-Evaluation. |

## Später einheitlicher Antwortslot (02.11.2026)

Vor der lokalen 1.200-ms-Messung nochmals gezielt geprüft,
jeweils **RDNA L2**; die übrige Quellenkarte bleibt unverändert:

| Originalstelle | Relevanz für die neue Regel |
| --- | --- |
| [Pacer, USENIX Security 2022](https://www.usenix.org/system/files/sec22-mehta.pdf), §§2.2–4 | Ein geheimer Verarbeitungsschritt darf den tatsächlichen Sendeplan nicht verschieben. Ein späterer öffentlicher Slot ist eine bekannte Art der Entkopplung, aber keine Garantie bei dessen Überschreiten. |
| [Carlini/Nasr 2024](https://arxiv.org/html/2410.17175), §VII | Feste Token-Ausgaberate mit Leernachrichten bei nicht bereiten Tokens und gemessene Latenz-/Bandbreitenkosten; hier werden stattdessen vollständige HTTP-Antworten in Gruppen freigegeben. |
| [Accumulate-and-Serve, 2013](https://arxiv.org/pdf/1302.6123), §§V–VI | Allgemeine Pufferungs-/Verzögerungsgrenze; formale Resultate gelten nicht für unseren LLM-Proxy. |

Die konkrete Live-/Replay-Entscheidung und die individuellen
Kosten stehen in `docs/late-release-20261102.md`.

## Kausaler Gruppenfreigabe-Pilot (02.11.2026)

Vor dem Offline-Replay gezielt online nachgeprüft; die bisherige
Quellenkarte bleibt bestehen. Der kleine Pilot und seine Daten stehen
in `docs/causal-release-pilot-20261102.md`.

| Originaltext / Lesestatus heute | Für den Claim relevante Stelle |
| --- | --- |
| [Pacer, USENIX Security 2022](https://www.usenix.org/system/files/sec22-mehta.pdf), **L2** | §§2.2–4: Auch Abweichungen des tatsächlichen vom geplanten Sendezeitpunkt dürfen keine Geheimnisse offenlegen. Der hier beobachtete completion-abhängige Gruppen-Tick verletzt die angestrebte Unabhängigkeit des sichtbaren Zeitplans. |
| [Mitigating Timing Side Channel in Shared Schedulers, 2013](https://arxiv.org/pdf/1302.6123), **L2** | §§V–VI: Accumulate-and-Serve puffert und bündelt Arbeit; Privatsphäre und Verzögerung sind gekoppelt. Eine periodische Gruppenregel als solche ist daher kein neuer Grundgedanke. |
| [One-Sided Bounded Noise, CCS 2025](https://people.csail.mit.edu/devadas/pubs/one_sided_noise.pdf), **L2** | §§1–2 und 5: Nur positive, begrenzte Zusatzverzögerung wird bereits mit DP, Maximal Leakage und PAC-Privacy untersucht. Ein allgemeiner Delay-Optimierungsclaim wäre unhaltbar. Die dortigen Garantien gelten nicht automatisch für Completion-gebundene Vierer-LLM-Antworten. |
| [Optimizing the Design Parameters of Threshold Pool Mixes for Anonymity and Delay, 2014](https://www.sciencedirect.com/science/article/pii/S1389128614001522), **L1/Teilauszug** | Verlagstext beschreibt Mehrzieloptimierung von Anonymität und Verzögerung. Direktzugriff auf den Volltext lieferte 403; ein abschließender Novelty-Vergleich ist damit nicht möglich. |
| [Eigene ICCAI-2026-Arbeit](../references/iccai2026-completion-order.pdf), **vorher L3** | Rangbasierter ODS/BOS-Ausgangspunkt; der jetzige Pilot untersucht zusätzlich die vollständige Client-Zeitfolge und individuelle Proxy-Wartezeit. Heute keine erneute Volltextlektüre. |

Die heutige Recherche war gezielt und begrenzt, kein vollständiger
systematischer Literaturreview. Die Offline-Ergebnisse beweisen keine
formale Schutzgarantie.

## Zufallsslot-Pilot (02.11.2026)

Vor dem Anschluss-Pilot erneut gezielt online abgeglichen. Der
Versuchsbefund steht in `docs/randomized-release-pilot-20261102.md`.

| Quelle / Lesestatus | Konsequenz für die Münzregel |
| --- | --- |
| [One-Sided Bounded Noise, CCS 2025](https://people.csail.mit.edu/devadas/pubs/one_sided_noise.pdf), **L2 aus vorheriger Volltextprüfung, heute Abstract/Verlagsseite bestätigt** | Positive begrenzte Zufallsverzögerung und ihre Privacy-/Kostenoptimierung sind bekannt. Unser `q(D)` ist keine Neuerfindung; der spezifische Unterschied ist der Completion-/Fallback-Zwang mehrerer echter Antworten. Der heutige PDF-Direktzugriff lief in einen Timeout. |
| [Pacer, USENIX Security 2022](https://www.usenix.org/system/files/sec22-mehta.pdf), **L2 heute**, §§2.2–4 | Der echte sichtbare Sendeplan und seine Abweichungen müssen vom Geheimnis entkoppelt werden. Ein unabhängig gezogener Termin genügt nicht, wenn sein Fallback wieder geheimnisabhängig ist. |
| [Mitigating Timing Side Channel in Shared Schedulers, 2013](https://arxiv.org/pdf/1302.6123), **L2 heute**, §V-A/B und §VI | Allgemeine periodische Pufferung und deren Delay-/Privacy-Konflikt sind Vorarbeit; formale Resultate gelten nicht automatisch für LLM-HTTP-Antworten. |
| [Threshold Pool Mixes, Computer Networks 2014](https://www.sciencedirect.com/science/article/pii/S1389128614001522), **L1/Teilauszug heute** | Verlagstext beschreibt bereits Mehrzieloptimierung von Anonymität und Wartezeit. Originalvolltext ließ sich weiterhin nicht verlässlich öffnen (403), daher keine abschließende Novelty-Aussage. |
| [Eigene ICCAI-2026-Arbeit](../references/iccai2026-completion-order.pdf), **zuvor L3, heute nicht erneut gelesen** | BOS/ODS-Rangmodell ist der Ausgangspunkt; die hier geprüfte gemeinsame Completion- und Fallback-Frage ist ein enger Anschluss, aber die getestete Münzregel liefert keinen belegten Methodenbeitrag. |

## C1-Abschlussstruktur (03.11.2026)

Gezielte Nachprüfung für den prospektiven C1-Test; die engsten Stellen
wurden am 02./03.11. gelesen (**L2**), die übrige Quellenkarte nicht
neu geprüft. Keine systematische Vollständigkeitsbehauptung und kein
besonderer „Deep-Research“-Lauf. Versuch und Abgrenzung stehen in
`docs/c1-cocompletion-20261103.md`.

| Originaltext / Fundstelle | Grenze für den möglichen Claim |
| --- | --- |
| [PROMPTPEEK, NDSS 2025](https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf), §IV-A und §VIII | Ein-Token-Reihenfolge unter LPM ist Vorarbeit; dessen damalige FCFS-Einordnung gilt nicht automatisch für vLLM 0.17.1. |
| [OptiLeak v1](https://arxiv.org/html/2602.20595v1), §4.2 und §6 | FCFS-Timing/TTFT als Validator wird ausdrücklich vorgeschlagen. Allgemeine Timing-Positionsinferenz ist daher kein Neuheitsclaim. |
| [PrefixWall v2](https://arxiv.org/html/2603.10726v2), §§2.2–2.4, 5 | TTFT-basierte Cachetreffer und Lastgrenzen sind untersucht; vier relative 16-Token-Vollantwortzeiten sind dort nicht der gewählte Beobachter. |
| [Contention-Induced Reliability Collapse](https://arxiv.org/html/2609.06853), §§IV-B, XIV–XV | Nicht gestreamte Endzeiten sind bereits untersucht, aber mit einem Ausgabetoken. Konkurrenzlast kann Timing-Kanäle verändern; unser Leerlaufbefund ist nicht auf Last übertragbar. |
| [Eigene ICCAI-2026-Arbeit](../references/iccai2026-completion-order.pdf), zuvor L3 | Die frühere BOS-/ODS-Auswertung war rangbezogen. Der neue C1-Test fragt nach relativen Abschlusszeiten, prüft aber noch kein BOS. |

## Scheduler-/BOS-Forschungsentscheidung (03.11.2026)

Für den Bericht `docs/scheduler-bos-entscheidung-20261103.md`
wurden die folgenden Primärstellen gezielt online nachgeprüft
(RDNA **L2**, nicht systematisch vollständig). Die Quellen der
vorangegangenen Abschnitte bleiben erhalten.

| Quelle / Fundstelle | Konsequenz für den Claim |
| --- | --- |
| [PROMPTPEEK, NDSS 2025](https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf), §IV-A, §VIII | LPM-/Ein-Token-Reihenfolge ist Vorarbeit; damalige FCFS-Einordnung nicht auf aktuelles vLLM übertragen. |
| [OptiLeak v1](https://arxiv.org/html/2602.20595v1), §4.2 und §6 | FCFS-Timing als Validator wird ausdrücklich genannt. Timing-Inferenz als solche ist nicht neu. |
| [Pacer, USENIX Security 2022](https://www.usenix.org/system/files/sec22-mehta.pdf), §3.2 | Geheimnisunabhängige Sendepläne einschließlich sichtbarer Abweichungen sind bekannt; Slot kein neuer allgemeiner Algorithmus. |
| [SafeKV v2](https://arxiv.org/html/2508.08438v2), §7.2 | TTFT-Kanal und selektive Cachefreigabe; andere Schutzfläche als BOS-Vollantworten. |
| [PrefixWall v2](https://arxiv.org/html/2603.10726v2), §§2.2, 5.2 | TTFT-basierte Angreiferprüfung und Lastgrenzen; keine identische BOS-Clienttrace-Evaluation. Vorabfassung, kein gesicherter Konferenzstatus. |
| [Contention-Induced Reliability Collapse](https://arxiv.org/html/2609.06853), §§IV-B, XIV–XV | Nicht gestreamte Endzeiten sind bereits für Ein-Token-Probes untersucht; eine Behauptung, vollständige Clientzeitmessung sei generell neu, wäre falsch. |
| [Sarathi-Serve](https://arxiv.org/html/2403.02310), §§4.1–4.2 | Chunked Prefill und Batching sind bekannte Schedulingmechanismen; deren Wirkung auf die hier geprüfte BOS-Restinformation bleibt unsere enge Frage. Keine Gleichsetzung mit vLLM 0.17.1. |
| [vLLM 0.17.1 Scheduler](https://docs.vllm.ai/en/v0.17.1/api/vllm/config/scheduler/) und lokal installierter `vllm/v1/core/sched/scheduler.py`, `schedule()` | Tokenbudget und Prefill-Schwelle sind explizit konfigurierbar; lokale Scheduler-Schritte wurden zusätzlich instrumentiert. |
| [One-Sided Bounded Noise, CCS 2025](https://people.csail.mit.edu/devadas/pubs/one_sided_noise.pdf), früher L2 | Positive Verzögerung als allgemeine Schutz-/Kostenidee bereits bekannt; am 03.11. nicht neu im Volltext gelesen. |
| [Eigene ICCAI-2026-Arbeit](../references/iccai2026-completion-order.pdf), früher L3 | Rangbasierter Ausgangspunkt; am 03.11. nicht erneut vollständig gelesen. |

Die [offizielle ICCAI-2027-Startseite](https://www.iccai.net/)
nennt aktuell den **10.12.2026** als reguläre Einreichungsfrist.
Die [Sondersitzungsseite](https://www.iccai.net/special.html)
nennt den **10.11.2026** für Beiträge zu Sondersitzungen.

## Nachprüfung 03.11.2026 für den Dokumenten-Pilot

- [PROMPTPEEK, NDSS 2025](https://www.ndss-symposium.org/wp-content/uploads/2025-1772-paper.pdf), §II-B und §IV-A: Originaltext heute gezielt geprüft (L2). LPM-Reihenfolge und Ein-Token-Kandidaten sind bekannte Angriffsbausteine; kein identischer Test der vollständigen BOS-Clientzeitfolge.
- [OptiLeak v1](https://arxiv.org/html/2602.20595v1), §6: Originaltext heute gezielt geprüft (L2). FCFS-/Timing-/TTFT-Adaptionen werden ausdrücklich diskutiert; der Dokumenten-Pilot beansprucht Timing nicht als neues Primitive.
- [vLLM 0.17.1 Prefix Caching](https://docs.vllm.ai/en/v0.17.1/design/prefix_caching/), Abschnitt „Cache Isolation for Security“: Originaldokumentation heute geprüft (L2). Cache-Salt im ersten Block isoliert Wiederverwendung; die gemeinsame Salt-Domäne ist explizite Bedingung des lokalen Piloten.

## Nachprüfung 03.11.2026 für die Präfixstruktur-Ablation

- [NVIDIA, „Structuring Applications to Secure the KV Cache“, 2025](https://developer.nvidia.com/blog/structuring-applications-to-secure-the-kv-cache/), Abschnitte „How application prompts are assembled“ und „Prompt structure matters“: heute L2. Öffentliche Promptanordnung, gemeinsame Präfixe und Sicherheitseinfluss sind bereits beschrieben; keine Neuheit für die allgemeine Strukturidee beanspruchen.
- [Gu et al., „Auditing Prompt Caching in Language Model APIs“, ICML 2025, arXiv v2](https://arxiv.org/pdf/2502.07776), §§2.1, 4.3 und Fig. 5: heute L2 am Originalvolltext. Präfixlänge und Präfixfraktion beeinflussen bekannte Cache-Timing-Audits; vollständige Antworten nach BOS und C0/C1-Prefill-Regime sind nicht ihr Testgegenstand. Die bei ihnen untersuchte Promptstruktur begrenzt unseren Novelty-Claim deutlich.
- [vLLM 0.17.1 Prefix Caching](https://docs.vllm.ai/en/v0.17.1/design/prefix_caching/), Hash-/Salt-Abschnitte: heute L2. Volle gemeinsame Blöcke und gleiche Salt-Domäne sind die technische Voraussetzung; die tatsächlichen 304/544-Token-Treffer wurden zusätzlich lokal gemessen.
