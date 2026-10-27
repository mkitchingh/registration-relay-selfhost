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
- A domain on Cloudflare (for the free Cloudflare Tunnel; no ports to open)
- A registration provider that lets you set a custom relay URL

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
- `404` on a command: no device is connected with that code. Check the
  provider shows connected, and that it's pointed at your relay, not Beeper's.
- Device keeps getting new codes: the secret changed. Restore it from your backup.

## License

AGPL-3.0, the same as Beeper's registration-relay (see [`LICENSE`](../LICENSE)).
Vendored libraries keep their own licenses, included alongside their code in
`vendor/`. Not affiliated with or endorsed by Beeper.
