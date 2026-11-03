# Llama-3.1-8B-Instruct als zweites Referenzmodell

Stand: 03.11.2026. Lokale Validierung der bisherigen Qwen/vLLM-Befunde.
Nur der eigene Messrechner und die bestehende BOS-Implementierung
werden verwendet; alte Rohdaten bleiben unverändert.

## Phase A: Modellstart

Der lokale Snapshot `0e9e39f249a16976918f6564b8830bc894c89659`
enthält die vier im Safetensors-Index genannten Gewichtsshards
(291 Tensoren), Konfiguration und Tokenizer. Die vorhandene
Python-3.13.7-Umgebung lädt vLLM 0.17.1, PyTorch 2.10.0+cu128
und Transformers 4.57.6. CUDA erkennt die RTX 3090. Es wurde
nichts installiert.

Der Server startete lokal mit maximal 2.048 Modell-Tokens,
`gpu_memory_utilization=0.8`, Eager-Modus, Prefix-Caching,
Tokenbudget 256 und Prefill-Schwelle 64 (C0). Ein erster roher
`/v1/completions`-Test lieferte HTTP 200 und die vollständige
nicht gestreamte JSON-Antwort, endete aber wegen `max_tokens=16`
mit `finish_reason=length` und einem unpassenden Fortsetzungstext.
Der unmittelbar folgende Chat-Test lieferte HTTP 200,
`finish_reason=stop` und die Antwort „Ready“. Der rohe Test
ist deshalb nur ein Server-/API-Nachweis, der Chat-Test der
erfolgreiche Instruktionsmodell-Funktionstest. Beide Anfragen
und Antworten sowie das Serverlog stehen unter
`results/llama-reference-20261103/phase-a/`. Der Server wurde
danach beendet.

## Phase B: Tokenisierung, vor der Cacheprüfung

Der lokale Llama-Tokenizer fügt beim Completion-Endpunkt ein
BOS-Token hinzu. Der alte künstliche Qwen-Prompt hat unter Llama
für alle vier Kandidaten 549 Prompttokens statt 548. Die vier
Dokumenten-Prompts hätten 549, 547, 547 und 549 Tokens.
Für Llama wurde bei Dokument B und C vor der abschließenden
Frage nur „Reviewed.“ ergänzt. Damit haben alle vier Kandidaten
in P0 und P1 jeweils 549 Tokens inklusive BOS. P0 teilt
keinen vollständigen ersten 16-Token-Block; P1 teilt 305
Anfangstokens und damit 19 volle Blöcke (304 Tokens).

Prompts und Tokenbefund stehen unter
`data/llama-reference-20261103/`. Die Qwen-Prompts wurden
nicht geändert. Ein kleiner C0-Cachetest mit gleichem und
verschiedenem Salt ist in
`results/llama-reference-20261103/phase-b/protocol.json`
vor der Ausführung festgelegt.

### Cacheprüfung abgeschlossen

Die sieben vorab festgelegten direkten Anfragen erhielten HTTP 200
und je 549 Prompttokens. Bei wiederholtem P0- oder P1-Prompt mit
demselben Salt meldete vLLM jeweils **544 gecachte Tokens**.
P0-Dokument B mit demselben Salt hatte keinen Treffer;
P1-Dokument B nutzte **304 gemeinsame Tokens**. P1-Dokument A
mit einem neuen Salt hatte keinen Treffer. Die tatsächlichen
Cacheblöcke entsprechen damit der Tokenprüfung. Rohantworten,
Anfrageparameter und Zeitpunkte stehen in
`results/llama-reference-20261103/phase-b/cache-check.jsonl`;
das Serverlog liegt daneben. Der Server wurde beendet.

Die Cachemechanik rechtfertigt einen kleinen direkten C0/C1-Pilot.
Sein Protokoll steht in
`results/llama-reference-20261103/phase-c-protocol.json`.

## Phase C: direkter Basiskanal

Je Konfiguration liefen 16 balancierte positive Vierergruppen und
vier unvorgewärmte Kontrollen mit neuer Engine und identischer
Fallfolge bei frischen Salts. Alle 160 Antworten waren vollständig
und hatten je 549 Prompt- und 16 Ausgabetokens. Nur die warme
Probe hatte 544 gecachte Tokens; das Cache-Diagnosefeld wurde
aus allen Clientantworten entfernt.

| Direkte Freigabe | C0 | C1 |
| --- | ---: | ---: |
| R1, warme Antwort zuerst | **16/16** | 7/16 |
| Alte Qwen-Paarabstandsregel | 4/16 | **16/16** |
| Warme Backend-Antwort zuerst (Mechanismus) | 16/16 | 7/16 |
| Unvorgewärmte Kontrollen mit engem Paarabstand | 0/4 | 0/4 |

Die Wilson-95-%-Intervalle für 16/16 reichen von 80,6 bis 100 %.
Der C0/C1-Formunterschied der direkten Clientbeobachtung zeigt
sich damit auch unter Llama in diesem kleinen lokalen Pilot.
Die bereits vorab festgelegte Entscheidungshilfe wurde erfüllt;
ein gezielter BOS-Vergleich ist gerechtfertigt. Rohdaten und
Auswertung liegen unter `results/llama-reference-20261103/direct-c0/`,
`direct-c1/` und `direct-analysis.json`. Beide Server wurden beendet.
