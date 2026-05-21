# Implementation Tasks

Below is a recommended sequence of tasks to implement the refactor safely and incrementally.

- [x] Codebase audit (1-2 days)
   - Run static analysis and complexity reports.
   - Identify duplicated code, high-complexity files, and flaky tests.
   - Produce a short list of candidate modules to refactor.

- [x] Add baseline tests for the first target (1-2 days)
   - Add focused unit tests that capture current behavior.
   - Add a small integration smoke test if the module interacts with other services.


- [x] Small refactor iteration (1-3 days per module)
   - Extract shared utilities or classes.
   - Replace duplicated code with calls to the new utilities.
   - Keep public APIs stable; add compatibility shims if needed.

 - [x] CI and integration validation (0.5-1 day)
   - Ensure CI runs unit and integration tests.
   - Address any flaky tests uncovered by refactor.

 - [x] Documentation and ownership (0.5 day)
   - Update inline docs and README for the refactored modules.
   - Record owners/reviewers for the modules.
   - Updated services/simulated-factory/README.md with developer notes about the helpers extraction and deps refactor.

- [x] Iterate across prioritized modules
 - [x] Iterate across prioritized modules
   - Repeat steps 2–6 for each selected module.
   - [x] Extracted helpers from `simulated_factory/engine.py`
   - [x] Added baseline tests for `simulated-factory`
   - [x] Refactored `simulated_factory/api.py` (introduced `deps.build_dependencies`)
   - [x] Refactored `simulated_factory/distance_publisher.py` (broker parsing moved to `utils`)
   - [x] Refactored `simulated_factory/kafka_observer.py` (value decoding moved to `utils`)
   - Completed initial prioritized iteration focused on `services/simulated-factory` (May 2, 2026). Additional modules may be scheduled in follow-up iterations.

- [x] Finalize and cleanup (1 day)
 - [x] Finalize and cleanup (1 day)
   - Documentation updated and developer notes added to the service README and design summary.
   - Unit and integration-style tests added and executed locally.
   - Remaining cleanup (remove compatibility shims) deferred to follow-up changes after consumer validation.
   - This change iteration is functionally complete as of May 2, 2026.

## Estimates

- Initial audit + first module: ~3–6 days
- Subsequent modules: ~1–3 days each depending on complexity

## Deliverables

- `proposal.md` — this document
- `design.md` — design and principles
- `tasks.md` — actionable task list and estimates
