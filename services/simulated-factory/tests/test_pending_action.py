from __future__ import annotations

import asyncio

import pytest

from simulated_factory.models import PendingAction


async def test_wait_for_resolution_returns_true_when_resolved() -> None:
    action = PendingAction(
        id="a1", robot_name="left", commands=[{"type": "move"}], correlation_id="c1"
    )
    waiter = asyncio.create_task(action.wait_for_resolution(timeout=1.0))
    await asyncio.sleep(0.01)
    action.resolve("success", "ok")
    result = await waiter
    assert result is True
    assert action.outcome == "success"
    assert action.reason == "ok"


async def test_wait_for_timeout_returns_false() -> None:
    action = PendingAction(id="a2", robot_name="right", commands=[], correlation_id="c2")
    result = await action.wait_for_resolution(timeout=0.05)
    assert result is False
    assert action.outcome is None


async def test_mark_timed_out_sets_flag_and_unblocks_waiters() -> None:
    action = PendingAction(id="a3", robot_name="left", commands=[], correlation_id="c3")
    waiter = asyncio.create_task(action.wait_for_resolution(timeout=1.0))
    await asyncio.sleep(0.01)
    action.mark_timed_out()
    result = await waiter
    assert result is True
    assert action.timed_out is True
