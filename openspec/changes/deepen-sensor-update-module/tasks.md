## 1. Move input coercion into Pydantic validators

- [ ] 1.1 Add `@field_validator("raw_color", mode="before")` on `SensorUpdateRequest` that coerces CSV string to `list[int]` and list-of-strings to `list[int]`
- [ ] 1.2 Add `@field_validator("scripted_values", mode="before")` that coerces CSV string to `list[int|float]` and list items from strings to numbers
- [ ] 1.3 Add `@field_validator("value", mode="before")` that coerces `"true"`/`"false"` to bool and numeric strings to int/float
- [ ] 1.4 Write parametrized unit tests for all three validators (CSV, array-of-strings, already-typed inputs, empty/null inputs)

## 2. Remove response polymorphism from PUT handler

- [ ] 2.1 Remove the `HX-Request` header check and HTML empty-response branch from `update_sensor()` in `api.py`
- [ ] 2.2 Remove the ad-hoc coercion block (60+ lines of `parse_number_or_string`, CSV splitting, bool parsing) from the PUT handler since validators now own this
- [ ] 2.3 Return `JSONResponse(jsonable_encoder(sensor))` unconditionally from the handler
- [ ] 2.4 Update `test_put_sensor_returns_html_for_htmx_caller` to assert JSON response with correct sensor data instead of empty HTML

## 3. Update specs and documentation

- [ ] 3.1 Update `services/simulated-factory/README.md` to remove the statement about returning HTML fragments for HX-Request callers
- [ ] 3.2 Update `services/simulated-factory/simulated_factory/DEVELOPER.md` to document the JSON-only response contract
- [ ] 3.3 Archive the spec deltas by running `openspec archive` after implementation is verified

## 4. Verify

- [ ] 4.1 Run the full test suite (`pytest`) and confirm all tests pass
- [ ] 4.2 Start the service locally and verify sensor form submission still updates the twin panel via SSE
