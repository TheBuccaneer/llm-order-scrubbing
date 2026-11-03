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

**Nächster Mini-Schritt:** Den Cachetest durchführen. Erst bei
belegter Wiederverwendung folgt ein kleiner direkter
C0/C1-Basiskanal-Pilot.
