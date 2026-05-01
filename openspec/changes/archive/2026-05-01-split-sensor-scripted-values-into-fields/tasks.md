# Tasks: implement split inputs for scripted sensor values

- [x] Update UI: `services/simulated-factory/templates/fragments/twin.html`
   - Replace CSV text inputs for `scripted_values` with repeated inputs named `scripted_values[]` and add add/remove controls.
   - Replace raw RGB CSV input with three inputs named `raw_color[]`.

- [x] Update API parsing: `services/simulated-factory/simulated_factory/api.py`
   - In `update_sensor`, coerce `scripted_values` whether it arrives as a CSV string or a JSON array.
   - Coerce individual list items to numbers where possible; keep strings where parsing fails.

- [x] Tests: `services/simulated-factory/tests/`
   - Add unit tests for CSV fallback parsing.
   - Add tests that `update_sensor` accepts arrays (both numeric and string typed).
   - (Optional) Add a small template rendering test asserting `scripted_values[]` inputs are rendered for the twin.

- [x] Examples & docs
   - Update `services/simulated-factory/presets.yml` examples to demonstrate the array form.
   - Add a short note to `services/simulated-factory/README.md` and `doc/test-plan-simulated-factory.md` describing the new UI.

- [x] QA & migration
   - Run the existing test-suite: `pytest services/simulated-factory` and fix regressions.
   - Sanity-check the twin UI in a dev compose: `docker compose -f docker-compose-development.yml up --build simulated-factory`.

- [ ] Review & merge
   - Create a PR with the changeset and a short description linking to this change.

Estimates: small change (UI + small API parsing logic, ~2–4 hours). Backwards-compatible behavior kept by design.
