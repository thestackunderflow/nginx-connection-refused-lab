"""What the video claims, asserted against the lab's recorded evidence (written before the scenarios: red, then green).
Run the scenarios first (bash run-scenarios.sh), then: bash tests/run-tests.sh"""
import json
import os
import re

import pytest

EV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'evidence')
REFUSED = 'connect() failed (111: Connection refused) while connecting to upstream'


def read(scenario, name):
    with open(os.path.join(EV, scenario, name), encoding='utf8') as f:
        return f.read()


def status(scenario):
    return read(scenario, 'curl.txt').strip()


def refused_lines(scenario):
    return [l for l in read(scenario, 'nginx.log').splitlines() if REFUSED in l]


def upstreams(lines):
    return [re.search(r'upstream: "([^"]+)"', l).group(1) for l in lines]


def test_versions_are_pinned():
    assert 'nginx/1.30.6' in read('good', 'versions.txt')
    assert 'Apache Tomcat/11.0.27' in read('good', 'versions.txt')


def test_working_setup_returns_200_and_logs_no_error():
    assert status('good') == '200'
    assert refused_lines('good') == []


def test_cause1_tomcat_on_127_0_0_1_gives_502_and_111():
    assert status('c1-bind-loopback') == '502'
    lines = refused_lines('c1-bind-loopback')
    assert len(lines) == 1
    assert re.fullmatch(r'http://10\.199\.33\.\d+:8080/', upstreams(lines)[0])  # the app's address: right host, right port


def test_cause1_evidence_tomcat_listens_on_loopback_only():
    socks = read('c1-bind-loopback', 'app-listen.txt')
    assert '127.0.0.1:8080' in socks
    assert '0.0.0.0:8080' not in socks and ':::8080' not in socks


def test_cause1_fix_listens_on_all_addresses_and_returns_200():
    assert status('fix-bind-all') == '200'
    socks = read('fix-bind-all', 'app-listen.txt')
    assert '0.0.0.0:8080' in socks or ':::8080' in socks


def test_cause2_localhost_inside_nginx_is_nginx_itself():
    assert status('c2-localhost') == '502'
    ups = upstreams(refused_lines('c2-localhost'))
    assert 'http://127.0.0.1:8080/' in ups  # localhost = the NGINX container, where nothing listens on 8080


def test_cause2_localhost_resolves_to_two_peers_both_127_0_0_1():
    # Measured 19 Oct (the plan review expected 127.0.0.1 and ::1): in the nginx:1.30.6 image the resolver returns
    # 127.0.0.1 twice for localhost, so NGINX gets two peers, logs two refusals for ONE request, and marks each peer
    # "temporarily disabled" (max_fails applies because the group has two servers).
    lines = refused_lines('c2-localhost')
    assert upstreams(lines) == ['http://127.0.0.1:8080/', 'http://127.0.0.1:8080/']
    assert read('c2-localhost', 'nginx.log').count('upstream server temporarily disabled') == 2
    assert read('c2-localhost', 'nginx.log').count('"GET / HTTP/1.1" 502') == 1  # one request
    hosts = [l.split()[0] for l in read('c2-localhost', 'nginx-localhost.txt').splitlines() if 'STREAM' in l]
    assert hosts == ['127.0.0.1', '127.0.0.1']


def test_cause3_wrong_port_gives_502_and_111_on_that_port():
    assert status('c3-wrong-port') == '502'
    ups = upstreams(refused_lines('c3-wrong-port'))
    assert len(ups) == 1 and ups[0].endswith(':8081/')


def test_not_this_error_unknown_host_stops_nginx_at_startup():
    log = read('x-unknown-host', 'nginx.log')
    assert '[emerg]' in log and 'host not found in upstream' in log
    assert REFUSED not in log
    assert read('x-unknown-host', 'nginx-state.txt').strip().startswith('exited')


def test_not_this_error_address_with_nothing_behind_it_is_not_111():
    log = read('x-dead-address', 'nginx.log')
    assert REFUSED not in log
    assert status('x-dead-address') in ('502', '504')
    assert re.search(r'\((110|113): ', log)  # a timeout or no route, never a refusal


def test_startup_race_refuses_then_serves():
    seq = json.loads(read('race', 'curl-sequence.json'))
    codes = [s['code'] for s in seq]
    assert codes[0] == '502' and '200' in codes
    first_ok = codes.index('200')
    assert all(c == '502' for c in codes[:first_ok])
    assert refused_lines('race')


def test_race_fix_waits_for_a_healthy_app():
    seq = json.loads(read('race-fix', 'curl-sequence.json'))
    assert seq[0]['code'] == '200'
    assert refused_lines('race-fix') == []


def test_evidence_has_no_host_paths_or_secrets():
    for root, _, files in os.walk(EV):
        for f in files:
            text = open(os.path.join(root, f), encoding='utf8', errors='replace').read()
            assert 'C:/Users' not in text and 'C:\\Users' not in text, f
            assert not re.search(r'sk-ant|Authorization:', text), f
