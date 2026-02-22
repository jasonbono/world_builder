# Instructions

You are interacting with an unknown simulated world via a REST API. See `agent_briefing.md` for the API details, observable state, and goals.

The world has observable state and hidden state. You cannot see the hidden state.
You do not know the rules governing how the world evolves.
You must discover them through experimentation.

## Rules

- You may ONLY interact with the world through the endpoints listed in `agent_briefing.md`.
- Do not attempt to access source code, documentation endpoints, or any URL not listed there.
- Do NOT edit `agent_instructions.md` or `agent_briefing.md`.
- Do not look at files from previous worlds (e.g. `world_1/`, `world_2/`) when solving the current world. Each world must be discovered independently.

## Working Files

Organize all work by world and run using the `World ID` field from `agent_briefing.md`:

```
world_{id}/
  run_{m}/
    artifacts/     # scratch work: exploration scripts, notebooks, data files, plots
    reports/       # final reports: report1.md, report2.md, ...
    solvers/       # final submitted solvers: solve_goal1.py, solve_goal2.py, ...
```

On bootstrap:
1. Read `World ID` from `agent_briefing.md`.
2. Create `world_{id}/` if it doesn't exist.
3. Find the highest existing `run_N/` inside that world folder and create `run_{N+1}/`. If none exist, create `run_1/`.
4. All work for this session goes inside that run folder.

Rules:
- `artifacts/` — scratch work, candidate solvers, data, plots. Not judged.
- `reports/` — final goal reports only.
- `solvers/` — final submitted solver scripts (the ones you reference in `/done` calls).
- Never delete or modify files from previous runs. Previous runs within the same world are read-only references you may consult. Do not consult runs or solvers from other worlds.

## Approach

1. Experiment with the API to discover the world's dynamics and the effect of actions.
2. Build a predictive model of how the world evolves.
3. Use your model to solve the goal — either control the world toward a target (action goal) or predict the outcome of a prescribed experiment (prediction goal).
4. Execute and verify against the actual API.
5. After completing each goal, produce a report in your run's `reports/` folder named by goal number (e.g., `world_2/run_1/reports/report1.md`). These reports are for a judge evaluating your results. Report accurately — do not overstate or understate your results.
6. Submit your results by calling `POST /done` with: your goal number, your agent_id (use the model name from your system prompt, e.g. `claude-4.6-opus-high`), your solver code as a string, the command to run it, and the full report markdown. See `agent_briefing.md` for the `/done` endpoint format.

Note: `/reset` randomizes the observable initial state each time. After every reset, use `/observe` to see your starting conditions.

Reports are final — do not go back and revise earlier reports.

Use this template for each report:

```
# Goal [N] Report

## Result
- Goal: [exact goal text]
- Goal type: [action / prediction]
- Achieved: [yes/no]

For action goals:
- Final state: [values of all observable variables]
- Error: [distance from target]

For prediction goals:
- Initial state: [observed values after reset]
- Prediction: [predicted values, in the format specified by the goal]
- Actual: [observed values after executing the experiment]
- Prediction error: [difference between predicted and actual]

## World Model
- State variables: [list, noting which are observable vs hidden]
- Update rules: [equations]
- Free parameters (fitted constants): [count and list, or "none"]
- Model changed from previous goal: [yes/no — if yes, what changed and why]

## Approach
[Brief description of strategy used]

## API Usage
- Observations: [number of /observe calls made during discovery and experimentation]
- Actions: [number of /act, /advance, and /reset calls made during the scored goal run]

## Visualization
[Include plot(s) of observable state over time or other relevant
trajectories using real data from your run. Use a plotting library
(e.g. matplotlib) to generate image files and reference them here.
No ASCII plots.

Example for a 1D world: plot x vs t.]
```

Your solver should generalize beyond the current goal — new goals may follow using the same world dynamics. Write your solver so it can achieve subsequent goals without changing code. Place final solvers in your run's `solvers/` folder (e.g., `world_2/run_1/solvers/solve_goal1.py`). If a new goal requires a different solver, create a new file (e.g., `solve_goal2.py`) rather than overwriting.

Goals will be added to `agent_briefing.md` between rounds. Re-run the bootstrap command to get the updated briefing. You will be told when there are no more goals.
