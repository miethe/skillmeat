# Debugging Rules

Symbol-first debugging methodology.

## Prime Directive

**Start with symbols. Fall back to exploration only when needed.**

Symbols provide 96% token savings. Always query first.

## Quick Workflow

1. **Identify module** from stack trace
2. **Query symbols** (~150 tokens): `grep "[name]" ai/symbols-*.json`
3. **Analyze locally** with grep/jq
4. **Delegate** to specialist agent with symbol context
5. **Implement fix** via Task()

## Decision Guide

| Approach | When | Cost |
|----------|------|------|
| Symbols | Name lookups, structure, dependencies | ~150 tokens |
| codebase-explorer | Implementation logic, patterns | ~5-15K tokens |
| Hybrid | Symbols → targeted file reads | ~2-5K tokens |

## Detailed Reference

For bug categories, delegation patterns, and bash examples:
**Read**: `.claude/context/key-context/debugging-patterns.md`
