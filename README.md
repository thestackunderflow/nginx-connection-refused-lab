# NGINX `connect() failed (111: Connection refused)`: three Docker causes, reproduced

The lab behind the video "NGINX 502 connect() failed (111: Connection refused): 3 Docker Causes"
(The Stack Underflow, How It Actually Works): https://youtu.be/AEfWyQNrh9c
NGINX 1.30.6 in front of Tomcat 11.0.27 on one Docker network.
Everything runs in Docker; nothing is installed on your machine.

```
bash run-scenarios.sh          # reproduce every scenario, write evidence/<scenario>/   (about 3 minutes)
bash tests/run-tests.sh        # 13 tests that check the evidence says what the video says
bash run-scenarios.sh c2-localhost   # one scenario
```

| Scenario | What we break | NGINX log | Through NGINX |
|---|---|---|---|
| `good` | nothing | no error | 200 |
| `c1-bind-loopback` | Tomcat Connector `address="127.0.0.1"` | `connect() failed (111: Connection refused)`, upstream = Tomcat's network address | 502 |
| `fix-bind-all` | `address="0.0.0.0"` (or leave it out) | no error | 200 |
| `c2-localhost` | `proxy_pass http://localhost:8080` in the NGINX container | 111 twice (localhost resolved to 127.0.0.1 twice in this image) + 2 x "temporarily disabled" | 502 |
| `c3-wrong-port` | `proxy_pass http://app:8081` | 111, upstream port 8081 | 502 |
| `x-unknown-host` | `proxy_pass http://appp:8080` | `[emerg] host not found in upstream`, NGINX exits | (no NGINX) |
| `x-dead-address` | an address with nothing behind it, `proxy_connect_timeout 3s` | `upstream timed out (110: Connection timed out)` | 504 |
| `race` | Tomcat starts 8 s late, `depends_on: service_started` | 111 for the first ~8 s | 502, then 200 |
| `race-fix` | health check + `depends_on: condition: service_healthy` | no error | 200 from the first request |

Files: `compose.yaml` (the setup, variables per scenario), `compose.healthy.yaml` (the race fix), `app/start.sh`
(binds Tomcat and delays its start), `nginx/templates/default.conf.template` (rendered by the nginx image's envsubst).
Evidence of the run used in the video: `evidence/` (19 Oct 2026). Tests: `tests/` (red phase before the lab existed,
then green).

## Licence

Lab code: Apache License 2.0 (`LICENSE`). NGINX, Tomcat, curl and Python run from their official Docker images
under their own licences; nothing from them is copied into this repository.
