# 5. Item color owned by inventory

Date: 2026-03-24

## Status

Accepted

## Context

The color of an order item can be specified on order. Multiple services need consistent access to this value during processing, e.g. during manufacturing. We had to decide whether color should be sent in the order message or resolved from a shared source.

## Decision

Use inventory as the source of truth for item color.

- The order message does **not** contain color.
- The order message contains only:
  - `orderId` (string, Order UUID)
  - `itemType` (enum, name of item to manufacture)
- Services that need color read it from inventory using order/item context.

## Consequences

- Color data is managed in one place, avoiding duplication and mismatches across services.
- Order payloads stay smaller and more stable.
- If we look only at exchanged commands, the selected color is not visible.
- Services depend on inventory availability to resolve color.
- Inventory schema/versioning for color must be managed carefully because multiple services rely on it.
