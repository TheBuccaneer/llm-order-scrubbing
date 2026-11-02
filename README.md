# Latency-Bounded Order Scrubbing for LLM Services

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

Environment setup and experiment instructions will be added
after the experimental stack has been selected.

## Project Structure

- docs/     Research documentation and decisions
- src/      Measurement and analysis code
- configs/  Experimental configurations
- data/     Dataset descriptions
- results/  Analysis results and figures
- paper/    Manuscript and references

## Collaboration

See AGENTS.md for project conventions and research workflow.
