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

Initial repository setup (October 2026).

No experimental results have been established yet.
Research hypotheses and implementation choices remain subject
to experimental validation.

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
