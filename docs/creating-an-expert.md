# Creating an expert

Every run analysis starts with the **Sundial analyst**: neutral, and based only on your own run history.
**Experts** are optional extra viewpoints you add on top. Each one is a short card describing a way of thinking
about the game, and every expert you enable gets its own section in each analysis. In the dashboard you can toggle
them on and off or compare them side by side.

Experts are yours to write. A good set gives you different angles on the same run: a cautious voice and a greedy
one, a rulebook you're trying to stick to, a summary of a guide you like. When they disagree, that's the useful
part.

Sundial ships with three examples in `experts/`:

| Expert | Kind | Viewpoint |
|---|---|---|
| `steady-hand` | persona | Survival first: arrive at bosses healthy, keep a potion, elites only with an exit. |
| `greedy-climber` | persona | Power compounds: more elites, more relics, upgrade instead of resting. |
| `house-rules` | personal | Your own rules of thumb, scored as kept / broken / not tested. |

Copy them into `~/.sundial-sts2/experts/` and enable one or two to see how it works.

## What an expert is

A folder in `~/.sundial-sts2/experts/<slug>/`:

```
steady-hand/
  expert.md     the card the analyst reads (under ~1,500 words)
  sources/      optional: your own notes the card was written from (not sent to the analyst)
```

Kinds:
- **persona**: a playstyle or coaching voice you invent ("The Steady Hand", "The Speedrunner").
- **personal**: your own rules of thumb. The analyst scores each rule as kept, broken (with the floor) or not tested.
- **community**: your summary of a written guide or a group's shared advice, in your own words.
- **creator**: your summary of one content creator's advice, credited, in your own words.

The template is [`src/sundial_sts2/expert_template.md`](../src/sundial_sts2/expert_template.md).

## Three ways to make one

### 1. Write it yourself
1. Ask Claude *"create an expert called The Speedrunner"* (runs `create_expert`), or copy the template to
   `~/.sundial-sts2/experts/<slug>/expert.md` by hand.
2. Fill in the sections. Start with 4–6 principles; you can add more after you've seen it in a few analyses.
3. Enable it: *"enable the speedrunner expert"*.

### 2. Let AI interview you (recommended)
In Claude Desktop with Sundial connected, pick the **write_expert** prompt (or say *"help me write an
expert"*). Claude asks you about the viewpoint, how it handles elites, rests, potions, drafting and risk, drafts the
card in the template's shape, shows it to you, and saves it once you approve.

Using a different AI (ChatGPT, Gemini, a local model)? Paste this, then answer its questions:

```text
Help me write an "expert card" for Sundial, a Slay the Spire 2 run analyser. An expert card describes one
point of view on how to play, and an AI analyst uses it to comment on my runs.

Interview me one question at a time (about 6–8 questions) to pin down:
- the viewpoint in one sentence, and what it's willing to sacrifice
- how it approaches elites, pathing, rest sites, potions, gold and shops, and card drafting
- any character-specific opinions (only if I have them)
- whether it changes in Blitz mode (only if I have a view)
- the tone its section should have
- what it doesn't cover

Then write the card in exactly this format, under 1,500 words:
- YAML frontmatter: name, slug (lowercase-with-hyphens), description (one line), kind (persona, personal or
  community), characters ([all] or a list like [IRONCLAD]), modes: [all], version: 1, sources: []
- sections: ## Who this is, ## Core principles, ## What to look for in a run, ## Character notes,
  ## Mode notes (with a ### Blitz subsection, only if I gave a Blitz view), ## How it should read, ## Limits, ## Sources
- 4–10 principles, each with a short ID (e.g. SR1, SR2), each specific enough to judge a run against (name a
  number, floor or situation)
- "What to look for in a run" maps each principle to things a run log shows: HP entering fights, damage per
  fight, elites per act, cards taken and skipped, deck roles (AoE, scaling, block, draw, ...) and archetype states, rest vs upgrade,
  gold, potions, relics, card removals
Use only what I tell you; don't add strategy I didn't give you.
```

Save the result as `~/.sundial-sts2/experts/<slug>/expert.md`.

### 3. Turn your notes into a card
Already have notes, a spreadsheet of lessons, or your own write-up of a guide? Put them as `.md` or `.txt` files in
the expert's `sources/` folder and ask Claude *"build the <slug> expert card from its sources"* (the
**build_expert** prompt). Claude reads them, drafts the card, and saves it once you approve.

## What makes a good card

- **Specific principles.** "Play safe" can't be checked against a run. "Don't take an Act 1 elite under 50% HP
  unless a rest site comes straight after" can.
- **IDs on every principle** (SH1, GC3…) so analyses can cite them and you can see which rules fire most.
- **Mapped to the data.** "What to look for in a run" should point at things the run summary shows. The analyst
  can't see turn-by-turn combat or map routes you didn't take, so rules about those can't be scored.
- **Honest limits.** Say what the viewpoint undervalues. The analyst will respect it and won't stretch the card.
- **A clear voice.** "How it should read" decides whether the section is a scorecard, a story or a pep talk.

Try it on two or three of your runs, then adjust. Bump `version` when you change it.

## Blitz and other game modes

Standard, Daily and Dread runs play on the usual map, so every card applies to them. **Blitz** doesn't: every act is
the same eight rooms, gold stays at 99 and the merchant sells services. Advice about routing, elite counts, gold and
shops has nothing to judge there. For a Blitz run:

| The card | In a Blitz analysis |
|---|---|
| has a `### Blitz` section under `## Mode notes` | applied, using those notes where they differ |
| lists modes without `blitz` (`modes: [standard]`) | one line: doesn't cover Blitz |
| is `creator` or `community` with no Blitz notes | one line: not applicable in Blitz (its sources don't cover it) |
| is `persona` or `personal` with no Blitz notes | applied, minus its routing, elite-count, gold and shop principles |

Blitz analysis is optional. Sundial still analyses Blitz runs (more lightly) and only compares them with your other
Blitz runs, but Standard is where your baselines and habits are. Add Blitz notes to a card only if that viewpoint
really has something to say about Blitz; for a card that summarises someone else's advice, only if their own advice
covers it.

## Writing about other people's ideas

You can base a card on advice you've learned from others: a guide you like, a community's rules of thumb. Keep it
in your own words, credit the ideas in `sources`, and don't present the card as that person's own view or speak
for them. Say so in "Who this is" (e.g. "my summary of ideas from …").

## Managing experts

- *"List my experts"* → `list_experts`
- *"Enable / disable greedy-climber"* → `set_expert_enabled`. Sections appear in the order you enabled them.
- With two or more enabled, each analysis ends with a one-line **Where the experts differ**.

## Sharing

An expert folder is self-contained: zip `expert.md` and share it. Others drop it into their
`~/.sundial-sts2/experts/` and enable it.
