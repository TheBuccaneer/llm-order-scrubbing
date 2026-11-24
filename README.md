# Client Timing Leakage in LLM Serving

Research project for ICCAI 2027.

## Research Question

What information remains observable through response completion
order and timing in LLM services after Budgeted Order Scrubbing
(BOS), and what individual delay is required for stronger protection?

## Previous Work

This project extends:

"Completion Order for Workload Inference in Asynchronous Services"
ICCAI 2026
https://doi.org/10.1145/3821244.3821268

Previous implementation:
https://github.com/TheBuccaneer/ordleak

## Research Objectives

- Evaluate information leakage beyond Order Distance Scores (ODS).
- Compare order-based and timing-based observations.
- Measure the protection-delay tradeoff.
- Investigate the applicability of BOS to LLM serving.

## Project Status

The final C2 background-load experiment is complete: all 24 paired
cold-minus-warm effects are positive (median 100.73 ms, paired 95% interval
87.14–107.26ms). Both old classifiers call every loaded case cold,
yielding 50% balanced accuracy, while their unchanged scores retain
AUC 1.0. This distinguishes a persistent timing effect from calibration
of a fixed decision rule. All 256 B probes have zero hits; C inference
progress overlaps the observation window in all 64 cases.
[Report and controls](docs/tenant-hintergrundlast-20261105.md).

Research for C1/C2 is complete. The next deliverable is the five-page
English ICCAI paper with C1/C2 as the main contributions:
[current manuscript plan](paper/short-paper-plan-20261105.md).
Seven pre-acquisition IPC startup failures and the corrected local
protocol commit are documented; no measured cohort was retried.

### Earlier C3 evidence

The final C3 direct positive control is complete: both train-frozen
observers classify all 48 new held-out cohorts correctly (BA/AUC 1.0),
using the unchanged 512/2048 pilot without protected prefill or release
delay. All 360 responses completed; A reuses 544 tokens when warm and
B has zero hits. The earlier protected-policy results remain unchanged
and do not establish timing security. The comparison and limits are in
[the updated C3 report](docs/protected-prefill-prototyp-20261103.md),
with raw data under `results/protected-prefill-direct-20261104-01/`.
Experimental work is complete. The next step is writing and typesetting
the English paper, at most ten single-column pages including references.

Protected-prefill development is stopped. The current deliverable is
[the contribution and manuscript plan](paper/manuskriptstruktur-20261103.md),
with three bounded empirical contributions, an eight-page single-column
ACM manuscript budget, two tables and three figures prepared exclusively
from existing results. The source-bound logical proof supports the
implementation case study; it is not a timing-security claim.

Figure PDFs, previews, CSVs and input hashes are in
[`paper/assets-20261103/`](paper/assets-20261103/).
The offline renderer `paper/render_existing_results.py` performs no new
inference or observer training. The next step is manuscript writing and
layout verification, without new research experiments.

### Existing implementation and evidence

The source-bound logical contract is documented in
[the noninterference report](docs/protected-prefill-nichtinterferenz-20261103.md).
It derives B-state convergence and equal logical decode decisions for
successful closed cohorts under an explicit functional backend contract.
It does not establish real client timing, HTTP completion-order or failure
noninterference. A concrete overrun counterexample and CPU checks against
the actual canonical copy/manager operations make those limits explicit.

The protected-prefill/shared-decode prototype now runs on the RTX 3090.
It uses two real tenant KV managers, a custom vLLM 0.17.1 scheduler,
canonical GPU KV relocation and a fixed public join. A warm/cold GPU
test produced byte-identical active KV data across all 28 layers while
retaining 512 private cached tokens. The bounded HTTP server, executable
checks, costs and limits are documented in
[the prototype report](docs/protected-prefill-prototyp-20261103.md).
Fixed 512-token protected chunks and a fused final phase reduce the
public join from 940ms to 700ms while retaining KV equality. The latest
configuration-controlled gate matches all policies at 512/2048: protected
prefill is about 110ms slower for A/B than ignoring hits, while retaining
about 12% lower warm CUDA intervals. All 72 protected cohorts met their
deadlines. Two frozen observers on held-out data show no significant
discrimination, but uncertainty is too wide for the preregistered limited
privacy gate. The combined gate did not pass; physical timing privacy
and method novelty remain open. The construction is retained.

The subsequent minimal eager CUDA pilot did not pass its hardware gate:
12 cold pairs gain 46.5ms with two streams (required 66ms plus 20ms reserve).
KV and frontier logits remain bit-identical across all 36 replays. The
two-runner scheduler will not be built on this result; no further architecture
or parameter search was started.

Earlier offline critical-path analysis finds no supported 110ms latency reduction
from removing idle time alone. A concrete concurrent protected-prefill
design would need about 31–66ms effective overlap; existing serial traces
cannot establish that hardware gain. A public two-cohort pipeline is
specified as a service-cost/throughput alternative and increases response
latency. The CUDA pilot above resolves that construction's hardware gate.

Local feasibility pilots (November 2026): Qwen2.5-7B-Instruct runs on the
RTX 3090 with vLLM 0.17.1. A cache-dependent completion-order signal is
visible in a deliberately tuned chunked-prefill configuration, including
small checks with 16-token responses and overlapping background work.
Four-response BOS shuffles response ranks but can leave a client-visible
batch-completion timing signal. A fixed, request-anchored release time
suppresses the tested first-response timing feature when all four responses
are ready; a separate 24-token test shows that late-response fallback
reintroduces observable order and timing patterns. The strong baseline
rank channel is reproducible with different prompt text, but depends
substantially on the serving configuration. Evidence, limits, and the
provisional paper decision are in `docs/entscheidungsvalidierung-20261102.md`.

The full ICCAI 2026 paper is archived in `references/` and has been
compared with the new results. Transfer to real multi-tenant workloads
and a broader novelty assessment remain open.

## Getting Started

Clone the repository:

git clone https://github.com/TheBuccaneer/llm-order-scrubbing.git
cd llm-order-scrubbing

On the existing measurement machine, launch the bounded local prototype
with a new output directory:

```bash
/home/rock/projects/porto/.venv-py313-repair/bin/python \
  src/protected_prefill_server.py results/protected-prefill-MY-RUN --port 8770
```

The prototype report describes the admin intake declaration and separate
A/B completion requests. Existing measurements are never overwritten.
The HTTP adapter retains the original 940ms policy. Run the controlled
real-engine contribution gate with a fresh output directory:

```bash
/home/rock/projects/porto/.venv-py313-repair/bin/python \
  src/protected_prefill_gate.py results/protected-prefill-gate-MY-RUN
```

## Project Structure

- docs/     Research documentation and decisions
- src/      Measurement and analysis code
- configs/  Experimental configurations
- data/     Dataset descriptions
- results/  Analysis results and figures
- paper/    Manuscript and references

## Collaboration

See AGENTS.md for project conventions and research workflow.
