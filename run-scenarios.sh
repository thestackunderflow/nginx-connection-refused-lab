#!/usr/bin/env bash
# Reproduce every scenario of the video and save its evidence in evidence/<scenario>/:
#   curl.txt (HTTP status through NGINX), nginx.log (NGINX's own output: error log + access log),
#   app-listen.txt (sockets Tomcat listens on, from busybox netstat in the app's network namespace),
#   connector.txt (Tomcat's Connector line), nginx-conf.txt (the rendered proxy config), nginx-state.txt.
# Usage (Git Bash or Linux): bash run-scenarios.sh [scenario ...]   (default: all)
set -u
cd "$(dirname "$0")"
export MSYS_NO_PATHCONV=1
CURL=curlimages/curl:8.16.0

scenario() {  # scenario <name> [compose override file]   (env vars set by the caller)
  local name=$1 extra=${2:-} p="ncr-$1" out="evidence/$1"
  rm -rf "$out"; mkdir -p "$out"
  local files=(-f compose.yaml); [ -n "$extra" ] && files+=(-f "$extra")
  docker compose -p "$p" "${files[@]}" down -v >/dev/null 2>&1
  docker compose -p "$p" "${files[@]}" up -d >/dev/null 2>&1
  if [ "$name" != race ]; then
    for _ in $(seq 60); do  # wait until Tomcat answers inside its own container (or 60 s)
      [ "$(docker inspect -f '{{.State.Health.Status}}' "$p-app-1" 2>/dev/null)" = healthy ] && break; sleep 1
    done
    sleep 1
  fi
  if [ "$name" = x-unknown-host ]; then  # NGINX may spend seconds on the name lookup before it gives up: wait for the exit
    local w=0
    while [ "$(docker inspect -f '{{.State.Status}}' "$p-nginx-1" 2>/dev/null)" = running ] && [ $w -lt 60 ]; do sleep 1; w=$((w+1)); done
    docker inspect -f 'started {{.State.StartedAt}} finished {{.State.FinishedAt}}' "$p-nginx-1" > "$out/nginx-times.txt" 2>&1
    sleep 1
  fi
  if [ "$name" = race ] || [ "$name" = race-fix ]; then
    local t0 seq="[" first=1
    t0=$(date +%s.%N)
    for _ in $(seq 40); do  # 40 requests, 0.5 s apart plus about 0.6 s per curl container (the t values are real)
      local code t
      code=$(docker run --rm --network "${p}_lab" $CURL -s -o /dev/null -w '%{http_code}' --max-time 5 http://nginx/ 2>/dev/null)
      t=$(awk -v a="$(date +%s.%N)" -v b="$t0" 'BEGIN{printf "%.1f", a-b}')
      [ $first = 1 ] && first=0 || seq+=","
      seq+="{\"t\":$t,\"code\":\"$code\"}"
      sleep 0.5
    done
    echo "$seq]" > "$out/curl-sequence.json"
    grep -o '"code":"[0-9]*"' "$out/curl-sequence.json" | head -1 | grep -o '[0-9]\+' > "$out/curl.txt"
  else
    docker run --rm --network "${p}_lab" $CURL -s -o /dev/null -w '%{http_code}' --max-time 15 http://nginx/ > "$out/curl.txt" 2>/dev/null
    echo >> "$out/curl.txt"
  fi
  sleep 1
  docker compose -p "$p" "${files[@]}" logs --no-log-prefix nginx > "$out/nginx.log" 2>&1
  docker inspect -f '{{.State.Status}} exit={{.State.ExitCode}}' "$p-nginx-1" > "$out/nginx-state.txt" 2>&1
  docker run --rm --network "container:$p-app-1" busybox:1.37 netstat -ltn > "$out/app-listen.txt" 2>&1
  docker compose -p "$p" "${files[@]}" exec -T app cat /tmp/connector.txt > "$out/connector.txt" 2>&1
  docker compose -p "$p" "${files[@]}" exec -T nginx cat /etc/nginx/conf.d/default.conf > "$out/nginx-conf.txt" 2>&1
  docker compose -p "$p" "${files[@]}" exec -T nginx getent ahosts localhost > "$out/nginx-localhost.txt" 2>&1
  if [ "$name" = good ]; then
    { docker compose -p "$p" exec -T nginx nginx -v 2>&1
      docker compose -p "$p" exec -T app /usr/local/tomcat/bin/version.sh 2>/dev/null | grep -E 'Server version|JVM Version'
    } > "$out/versions.txt"
  fi
  docker compose -p "$p" "${files[@]}" down -v >/dev/null 2>&1
  echo "$name: $(cat "$out/curl.txt")"
}

run() {  # run <name> VAR=value ... [--file override.yaml]
  local name=$1; shift; local extra=""
  ( unset UPSTREAM BIND_ADDR START_DELAY CONNECT_TIMEOUT
    for a in "$@"; do case $a in --file=*) extra=${a#--file=};; *) export "$a";; esac; done
    scenario "$name" "$extra" )
}

want=" ${*:-all} "
go() { [ "$want" = " all " ] || [[ "$want" == *" $1 "* ]]; }
go good           && run good
go c1-bind-loopback && run c1-bind-loopback BIND_ADDR=127.0.0.1
go fix-bind-all   && run fix-bind-all BIND_ADDR=0.0.0.0
go c2-localhost   && run c2-localhost UPSTREAM=http://localhost:8080
go c3-wrong-port  && run c3-wrong-port UPSTREAM=http://app:8081
go x-unknown-host && run x-unknown-host UPSTREAM=http://appp:8080
go x-dead-address && run x-dead-address UPSTREAM=http://10.199.33.250:8080 CONNECT_TIMEOUT=3s
go race           && run race START_DELAY=8
go race-fix       && run race-fix START_DELAY=8 --file=compose.healthy.yaml
date -u '+%Y-%m-%d %H:%M:%S UTC' > evidence/RUN-DATE.txt
