# registration-relay-selfhost

A ready-to-run, self-hosted copy of **[Beeper's registration-relay](https://github.com/beeper/registration-relay)**,
the server that sits behind `registration-relay.beeper.com`.

Use it in place of Beeper's public relay with anything that already works
with it: JJTech's ValidationRelay, Copper's relayserver, Beeper's Mac and
jailbreak registration providers, OpenBubbles, and Beeper's iMessage bridge.

**The relay code is Beeper's, unmodified.** This repo only packages it so it
installs with one command and keeps working if the original repo or Beeper's
hosted service goes away.

---

## What's in this repo

| Part | Who wrote it | Changed? |
|---|---|---|
| Relay source code (repo root, with its full git history) | Beeper (Nick Mills-Barrett, Tulir Asokan, Brad Murray) | **No**, identical to upstream commit [`c00b355`](https://github.com/beeper/registration-relay/commit/c00b355110b2f8de9a8246feff8c7c3914ecd88c) |
| `vendor/` (Go libraries the relay uses) | Their respective authors | **No**, byte-identical to the versions pinned in Beeper's `go.sum` |
| `deploy/` (Docker Compose, routing filter, Dockerfile) | This repo | New |
| This README and the image workflow | This repo | New |

Only one upstream file was removed: Beeper's CI workflow
(`.github/workflows/deploy.yaml`), which publishes to Beeper's private
registry and would fail anywhere else. Beeper's own `README.md` and
`Dockerfile` at the repo root are left exactly as published.

Vendoring means the build needs nothing from Beeper or the Go module mirror,
only the Docker base images.

## Why there's a routing filter

Beeper's relay forwards every `/api/v1/bridge/<command>` request to the
connected phone or Mac. Every relay app implements exactly two commands:
`get-version-info` and `get-validation-data`. If anything else arrives, the
device ignores it and the relay:

1. waits 60 seconds for an answer that never comes,
2. holds up that device's other requests meanwhile, then
3. drops the device's connection to force a reconnect.

OpenBubbles 2.0 sends two such commands, `sign-data` and `activate`, several
times a day. Beeper's **hosted** relay answers them with an instant, empty
`401`, and the app carries on. Beeper's **published** code doesn't, so on its
own it would keep dropping your iPhone.

`deploy/nginx.conf` reproduces the hosted behavior: the two real commands and
the device connection pass straight through; any other bridge command gets an
instant empty `401`. Everything else is untouched. Tested against the
unmodified relay, every response a client or device sees is byte-for-byte the
same as Beeper's code, except those extra commands now get the hosted relay's
answer.

## Requirements

- A Linux machine or VM that stays on, with Docker and Docker Compose
  (Intel or ARM, e.g. a free Oracle Cloud ARM VM)
- A domain on Cloudflare (for the free Cloudflare Tunnel; no ports to open)
- A relay app on your iPhone or Mac that lets you set a custom relay URL

## Install

**1. Get the files**
```bash
git clone https://github.com/mkitchingh/registration-relay-selfhost.git
cd registration-relay-selfhost/deploy
cp .env.example .env && chmod 600 .env
```

**2. Create a secret.** Put the output in `.env` as `REGISTRATION_RELAY_SECRET=`:
```bash
openssl rand -base64 32
```
Back it up somewhere safe. It lets your device keep its relay code across
restarts; if it's lost or changed, every device gets a new code and must
register again.

**3. Create a Cloudflare Tunnel.** Cloudflare dashboard → Zero Trust →
Networks → Tunnels → Create a tunnel → Cloudflared.
- Copy only the token (the long `eyJ...` string) into `.env` as `TUNNEL_TOKEN=`.
  Don't run the install commands Cloudflare shows.
- Add a route: **Published application**, a subdomain of your choice
  (e.g. `relay.example.com`), service type **HTTP**, URL **`rr-filter:8080`**.

**4. Start it**
```bash
docker compose up -d
```

**5. Check it** (replace with your hostname):
```bash
curl -s -o /dev/null -w '%{http_code}\n' https://relay.example.com/health                         # 204
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://relay.example.com/api/v1/bridge/sign-data  # 401
```

## Point your devices and apps at it

- **Relay app** (e.g. ValidationRelay): set the relay to custom,
  `wss://relay.example.com/api/v1/provider`. It will show a new code.
- **Client** (e.g. OpenBubbles, Beeper's bridge): wherever you'd enter
  Beeper's relay address, use `https://relay.example.com`, with the new code.
  In OpenBubbles setup that's **Change Relay URL** at the phone-number step.

Moving from Beeper's relay to yours gives your device a new code, so it means
registering once more.

## Updating

```bash
cd registration-relay-selfhost && git pull
cd deploy && docker compose pull && docker compose up -d
```

## Not using Cloudflare?

Remove the `cloudflared` service from `deploy/docker-compose.yml`, uncomment
the `ports` line on `filter`, and point your own HTTPS reverse proxy (with
websocket support) at `127.0.0.1:8080`.

## Troubleshooting

```bash
docker compose ps                 # all three should be Up (relay: healthy)
docker compose logs -f relay      # device connects, commands, errors
docker compose logs -f filter     # every request and its status code
```
- `404` on a command: no device is connected with that code. Check the relay
  app shows Connected, and that it's pointed at your relay, not Beeper's.
- Device keeps getting new codes: the secret changed. Restore it from your backup.

## Credits

- **[Beeper](https://github.com/beeper/registration-relay)**: the relay itself.
  Nick Mills-Barrett, Tulir Asokan and Brad Murray wrote every line of the
  server code in this repo, and Beeper ran the public relay that made
  self-hosted iMessage registration practical for years.
- **[JJTech](https://github.com/JJTech0130/ValidationRelay)**: ValidationRelay
  and the reverse-engineering that much of this ecosystem builds on.
- **[OpenBubbles](https://github.com/OpenBubbles) / Tae Hagen (Copper)**:
  OpenBubbles, rustpush and the jailbreak relayserver.
- **Library authors**: go-chi (Peter Kieltyka and contributors), Gorilla
  WebSocket, zerolog (Olivier Poitrey), Prometheus client_golang, and others
  in `vendor/`, each under its own license.

Packaged by [@mkitchingh](https://github.com/mkitchingh). This repo is not
affiliated with or endorsed by Beeper, JJTech or OpenBubbles.

## License

The relay is licensed **AGPL-3.0** by Beeper (see [`LICENSE`](../LICENSE)),
and this repo is distributed under the same license. Vendored libraries keep
their own licenses, included alongside their code in `vendor/`.
