# Evaluation

## Metrics

The main metric is coverage: the fraction of instances solved by executing the
learned policy from the initial state until a goal is reached. Training coverage
checks whether the learner solved the examples it was given; large-instance
coverage checks generalization.

Effective width measures whether the learned object acts as a direct policy or
needs extra search. Width 0 is best and means the policy selects an applicable
successor directly. The evaluator also records compactness constraints:
selected feature count, policy rule count, wrapper iteration counts, and plan
length ratio against the domain planner.

## Baselines and Targets

The paper reports that Gripper is solved with 100% large-instance coverage and
effective width 0. In the training table, Gripper uses one outer iteration, one
inner iteration, three selected features, and four policy rules.

## Evaluation Protocol

The reusable benchmark trains on small Gripper instances and evaluates on larger
instances with more balls. The evaluator reads a policy JSON artifact written by
the method and executes it independently using only the problem dynamics in
`data/`. Scores are written to `scoring/scores.json`.
