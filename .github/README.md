# registration-relay-selfhost

A ready-to-run, self-hosted registration relay, initially copied from
[Beeper's registration-relay](https://github.com/beeper/registration-relay),
the server behind `registration-relay.beeper.com`.

It's meant as a drop-in replacement for Beeper's public relay: anything that
works with it should work here by changing the relay address.

This repo packages the relay so it installs with one command, with its Go
dependencies vendored so builds don't depend on outside sources.

## Why there's a routing filter

The relay forwards every `/api/v1/bridge/<command>` request to the connected
device. Registration providers implement two commands: `get-version-info` and
`get-validation-data`. If a client sends any other command, the device ignores
it and the relay:

1. waits 60 seconds for an answer that never comes,
2. holds up that device's other requests meanwhile, then
3. drops the device's connection to force a reconnect.

Some clients send other commands periodically. Beeper's hosted relay answers
them with an instant, empty `401`, and those clients carry on.

`deploy/nginx.conf` does the same: the two provider commands and the device
connection pass straight through, and any other bridge command gets an
instant empty `401`. Everything else goes to the relay as-is.

## Requirements

- A Linux machine or VM that stays on, with Docker and Docker Compose (Intel or ARM)
- A permanent public HTTPS address. Either works, and neither needs open ports:
  - **Cloudflare Tunnel (recommended).** Free, but requires a domain you own,
    added to Cloudflare. If you don't have one, Cloudflare sells domains at
    cost, about $10/year for a `.com`.
  - **Tailscale Funnel.** Free, no domain needed. You get an address like
    `https://myserver.tail1234.ts.net`. Only the server runs Tailscale; phones
    and apps connect to it like any other website.
- A registration provider that lets you set a custom relay URL

The address must never change: devices and clients store it, and if it
changes, registration renewals fail. That's why temporary addresses such as
Cloudflare's `trycloudflare.com` quick tunnels won't work.

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

**3. Set up the public address**, either A or B.

**A. Cloudflare Tunnel (recommended)**

Cloudflare dashboard → Zero Trust → Networks → Tunnels → Create a tunnel →
Cloudflared.
- Copy only the token (the long `eyJ...` string) into `.env` as `TUNNEL_TOKEN=`.
  Don't run the install commands Cloudflare shows.
- Add a route: **Published application**, a subdomain of your choice
  (e.g. `relay.example.com`), service type **HTTP**, URL **`rr-filter:8080`**.
- Leave `COMPOSE_PROFILES=cloudflare` in `.env`.

Then start it:
```bash
docker compose up -d
```
Your relay address is `https://relay.example.com`.

**B. Tailscale Funnel**

- In `.env`, change the line to `COMPOSE_PROFILES=` (empty) and leave
  `TUNNEL_TOKEN` blank.
- Start the relay:
  ```bash
  docker compose up -d
  ```
- Install Tailscale on the server and sign in:
  ```bash
  curl -fsSL https://tailscale.com/install.sh | sh
  sudo tailscale up
  ```
- Publish the relay. `--bg` keeps it running across reboots:
  ```bash
  sudo tailscale funnel --bg http://127.0.0.1:8080
  ```
  The first time, this prints a link to enable HTTPS and Funnel for your
  tailnet. Open it, approve, then run the command again.
- Get your address:
  ```bash
  tailscale funnel status
  ```
  It's `https://<machine-name>.<your-tailnet>.ts.net`. It's based on the
  machine's name in Tailscale, so don't rename the machine afterward.

**4. Check it** (replace with your address):
```bash
curl -s -o /dev/null -w '%{http_code}\n' https://relay.example.com/health                         # 204
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://relay.example.com/api/v1/bridge/sign-data  # 401
```

## Point your devices and apps at it

- **Registration provider**: set a custom relay URL of
  `wss://relay.example.com/api/v1/provider`. It will show a new code.
- **Client**: wherever you'd enter Beeper's relay address, use
  `https://relay.example.com`, with the new code.

Moving from Beeper's relay to yours gives your device a new code, so it means
registering once more.

## Updating

```bash
cd registration-relay-selfhost && git pull
cd deploy && docker compose pull && docker compose up -d
```

## Using your own reverse proxy instead

Set `COMPOSE_PROFILES=` (empty) in `.env` and point your HTTPS reverse proxy,
with websocket support, at `127.0.0.1:8080` on the server.

## Troubleshooting

```bash
docker compose ps                 # relay (healthy), filter, and cloudflared if using Cloudflare: all Up
docker compose logs -f relay      # device connects, commands, errors
docker compose logs -f filter     # every request and its status code
```
- `404` on a command: no device is connected with that code. Check the
  provider shows connected, and that it's pointed at your relay, not Beeper's.
- Device keeps getting new codes: the secret changed. Restore it from your backup.

## License

AGPL-3.0, the same as Beeper's registration-relay (see [`LICENSE`](../LICENSE)).
Vendored libraries keep their own licenses, included alongside their code in
`vendor/`. Not affiliated with or endorsed by Beeper.
