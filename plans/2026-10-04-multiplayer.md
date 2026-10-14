# Multiplayer plan (future, not scheduled)

Status: planning only, 2026-10-04. No code changes. Not in the Luna queue until Tomek approves.

## Goal

Several players in the village at the same time: each sees the others walking (position,
direction, animation), can chat, and later interact (2P minigames, shared objects, trading).

## Starting point

- Static site on GitHub Pages, plain JS, no build step, no backend.
- `docs/js/chat.js` already does Nostr: nostr-tools from esm.sh, guest key in localStorage,
  NIP-28 channel (kind 42) on 5 public relays.
- E01 session participant/input model and E02 2-key local race exist (same keyboard only).

## What each transport is good for

| Need | Nostr (public relays) | WebRTC P2P (Nostr as signaling) | Own WebSocket room server |
|---|---|---|---|
| See others walking, delayed ~0.5-3 s | yes | yes | yes |
| Smooth real-time movement, 10-20 updates/s | no (relay rate limits, latency, bans for flooding) | yes, small rooms (<= ~8) | yes |
| Shared objects, "who picked the mushroom first" | no authority, conflicts | weak (one peer acts as host) | yes, server decides |
| Anti-cheat for scores | signatures only, values can be faked | no | yes |
| Persistent global map state | only per-player owned data, last-writer-wins | no | yes (DB) |
| Identity, chat, scores, public history | yes, best fit | - | possible, but Nostr fits better |
| Cost / ops | free, nothing to run | free, ~10-20% of players need a TURN relay | small monthly cost |

Conclusion: Nostr is the identity + social + persistence layer. Real-time movement and
interactions need either P2P or a small authoritative server.

## Recommended architecture (hybrid)

- Nostr: player identity (guest key now, NIP-07 extension login later), chat (existing),
  signed score records, optional public "world log" (who built/left what).
- Room server: one WebSocket room per instance of the village (max ~16-20 players),
  authoritative for positions and interactions, 10-15 Hz snapshots, client interpolation.
- Hosting candidates:
  - Cloudflare Durable Objects / PartyServer: one object per room, no VM to maintain,
    free tier for experiments, pairs well with a static GitHub Pages client. Preferred.
  - exe.dev VM (Personal from $15/mo, 2 vCPU / 4 GB): fine for prototype and agent-driven
    deploys over SSH; could also host our own strfry relay. Downside: a VM we maintain.
  - Plain VPS (Hetzner etc.): cheapest always-on, same ops cost as exe.dev.

## Stages

- M0 - prep in the client (no network, can happen any time): pull player state into a
  serializable object `{id, name, x, y, dir, anim, area}`, keep input -> state -> render
  separate, add a "remote players" render layer with interpolation (reuse the race ghost).
  Acceptance: a fake remote player driven by recorded input walks smoothly.
- M1 - "I see others" over Nostr only: ephemeral presence event (kind 2xxxx) every 2-3 s
  and on area change; drop players silent > 30 s; nickname from chat. Test which of the
  5 relays accept ephemeral kinds and their rate limits first. Cheap way to check interest.
- M2 - room server prototype: WebSocket join/leave/move, server-side bounds, 15 Hz
  snapshots, reconnect; same render layer as M1. Keep Nostr chat unchanged.
- M3 - interactions: online 2P race (reuse E02 rules), shared pickups, emotes; the server
  decides outcomes; final scores published as signed Nostr events.
- M4 - persistent world: server DB as source of truth for shared map changes, optional
  periodic snapshot to Nostr.

## Open decisions for Tomek

- Expected players at once (5? 50?) - picks P2P vs server.
- Is cheating / griefing acceptable for a casual village game?
- Budget for hosting (0 vs ~5-15 USD/month).
- Login: guest keys only, or Nostr extension login too.
