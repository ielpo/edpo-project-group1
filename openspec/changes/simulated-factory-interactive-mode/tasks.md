## 1. Models

- [ ] 1.1 Add `InteractiveConfig` model to `models.py` with `intercepted: set[str]` and `timeout_seconds: int = 30`
- [ ] 1.2 Add `PendingAction` model to `models.py` with `id`, `robot_name`, `commands`, `created_at`, `_event: asyncio.Event`, `outcome: str | None`, `timed_out: bool`

## 2. Engine — Interactive Gating

- [ ] 2.1 Add `interactive_config: InteractiveConfig` and `_pending: dict[str, PendingAction]` to `SimulationEngine.__init__`
- [ ] 2.2 In `handle_dobot_commands`: check if any command type in batch is in `interactive_config.intercepted`; if yes, create `PendingAction`, store it, emit `PENDING_ACTION` event, and `await asyncio.wait_for(action._event.wait(), timeout)`
- [ ] 2.3 In `handle_dobot_commands`: return `outcome` field in result dict when action was resolved interactively
- [ ] 2.4 Add `resolve_action(action_id, outcome, reason)` coroutine to engine: set outcome, set event, remove from `_pending`, emit `ACTION_RESOLVED` event
- [ ] 2.5 Add `get_pending_actions()` and `get_interactive_config()` / `set_interactive_config()` to engine

## 3. API Routes

- [ ] 3.1 Add `GET /api/interactive/config` returning current `InteractiveConfig`
- [ ] 3.2 Add `PUT /api/interactive/config` accepting `InteractiveConfigRequest` and calling `engine.set_interactive_config`
- [ ] 3.3 Add `GET /api/interactive/pending` returning list of pending actions (serializable fields only, no internal `_event`)
- [ ] 3.4 Add `POST /api/interactive/{action_id}/resolve` accepting `ResolveActionRequest` (`outcome`, optional `reason`); return 404 if not found

## 4. UI — Pending Actions Panel

- [ ] 4.1 Add a pending-actions `<section>` to `web/index.html` (hidden when queue is empty)
- [ ] 4.2 Add `renderPending(actions)` function: render each action as a card with robot name, command types, and Success / Failure buttons
- [ ] 4.3 Wire Success/Failure buttons to `POST /api/interactive/{id}/resolve` and call `refresh()` after
- [ ] 4.4 Include pending actions in the WebSocket refresh path so the panel updates live

## 5. Tests

- [ ] 5.1 Unit test: `handle_dobot_commands` with no intercepted types auto-resolves immediately
- [ ] 5.2 Unit test: `handle_dobot_commands` with matching intercepted type suspends until `resolve_action` is called
- [ ] 5.3 Unit test: action auto-fails after timeout
- [ ] 5.4 Unit test: resolving unknown action ID raises `KeyError` / returns 404

## 6. Documentation

- [ ] 6.1 Update `services/simulated-factory/api.md` with new `/api/interactive/*` endpoint descriptions
- [ ] 6.2 Update `services/simulated-factory/README.md` with a short note on interactive mode and the `dobot-control` timeout consideration
