# Builds Beeper's registration-relay exactly as published, from this repo's
# source and vendored dependencies. No network access is needed for the Go build.
#
# Beeper's own Dockerfile (at the repo root, left unchanged) also installs a
# live-reload dev tool at its latest version, which no longer builds on the
# Go 1.21 image it uses. This file builds the same relay without that step.
FROM golang:1.24-alpine AS build
WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 go build -mod=vendor -trimpath \
    -ldflags "-s -w -X main.Commit=c00b355110b2f8de9a8246feff8c7c3914ecd88c" \
    -o /registration_relay ./cmd/registration_relay

FROM alpine:3.21
RUN apk add --no-cache ca-certificates \
 && adduser -D -H -u 10001 relay
COPY --from=build /registration_relay /usr/local/bin/registration_relay
USER relay
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD wget -q -O /dev/null http://127.0.0.1:8000/health || exit 1
ENTRYPOINT ["registration_relay"]
