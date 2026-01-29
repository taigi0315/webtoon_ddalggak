# Prompt Authority Phase 1.5 - Task List

Status key: [ ] todo  [~] in progress  [x] done

## EPIC 1 — Character Identity Authority & Prompt Compiler Fix
- [x] 1.1 Canonical Character Registry (data model + persistence)
- [x] 1.2 Reference Image Authority clause injected into all image prompts
- [x] 1.3 CharacterIdentityInjector (rule-based)
- [x] 1.4 Strip forbidden character descriptors when references exist

## EPIC 2 — Panel Layout & Pacing Control
- [x] 2.1 Add scene_importance attribute to scene planning output
- [x] 2.2 LayoutResolver rules for hero scenes and panel counts
- [x] 2.3 Asymmetric/inset panel layouts (normalized x,y,w,h)

## EPIC 3 — Prompt Structure Cleanup & Consistency
- [x] 3.1 Validate panel count/layout mismatches
- [x] 3.2 Standardize scene image prompt skeleton

## EPIC 4 — LangGraph Node Cleanup
- [x] 4.1 Separate LLM vs rule-based nodes
- [x] 4.2 Move blind test to story phase

## EPIC 5 — UX Stability
- [x] 5.1 Persist state across tabs
- [x] 5.2 Generation progress visibility

## Notes
- Start with EPIC 1 (P0). Target: eliminate identity drift and prompt conflicts.
