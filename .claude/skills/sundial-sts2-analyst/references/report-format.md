# Report format

Use these sections, in this order. Aim for 350–600 words. Use the player's floor numbers throughout.

```
## <Character> A<asc>: <result> on floor <N> (<version>)
**Verdict:** one sentence: what decided this run.

### What ended it
Proximate cause (the final fight) and root cause (the earlier decisions), each with floor references
and the key comparison with their own history.

### Turning points
3–5 bullets, in floor order. Each: **F<n> <what happened>**: why it mattered, with a number.

### Deck & draft
Start with one line: **Coverage:** AoE ✓/✗ · Scaling ✓/✗ · Block ✓/✗ · Draw ✓/✗ at the boss or fight that
mattered. Then 2–4 bullets on the picks that made or broke it. Name passed cards that would have covered a gap.

### HP, rests, gold & potions
2–4 bullets. Rest vs smith decisions, unspent gold, potions held or burned.

### What went right
1–3 bullets. Real credit, not consolation.

### Lessons for next run
2–3 numbered, specific, actionable lessons, phrased as rules of thumb the player can apply mid-run
("If HP is under 50% after F5, path around the first elite unless the deck has 2+ AoE cards").
Mark any that repeat a saved lesson or a habit from `player_summary`.

### Confidence
One or two lines: what the data couldn't show (no combat log, unknown card text, small samples).

---
## Expert slots
(Only if get_enabled_experts returned cards. One block per expert, in slot order.)

### Slot 1 · <Expert name>
*<kind> · card v<version>*
- 2–4 bullets: what this expert's principles say about the run, each citing a principle ID and a floor.
- **<Name>'s lesson:** one lesson in the expert's framing.
- **Your data:** one line, only if the player's own stats support or contradict this expert's view here.

### Slot 2 · <Expert name>
…

**Where the experts differ:** one line when two or more experts disagree or emphasise different things.
```

Then offer: "Want me to save lesson 1 or 2?"
