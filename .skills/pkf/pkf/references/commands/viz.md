---
type: Command
title: /pkf viz [path]
description: Regenerate the bundle's link graph as viz.html and graph.mmd.
resource: file://../../scripts/visualize.py
tags: [pkf, command, visualization]
timestamp: 2026-07-04
---

# Schema

Run `python <skill-dir>/scripts/visualize.py <bundle>` to (re)generate `viz.html` (interactive
graph) and `graph.mmd` (aggregated Mermaid) from the explicit concept links. No LLM involved —
purely reads Markdown links.
