#!/bin/bash
# SIGA leak probe: run INSIDE the task sandbox in place of the agent, as a curious,
# adversarial agent would. Every check must PASS. Output: one JSON line per check.
# /probe (read-only, probe runs only) holds ref_sha256.txt (sha256 of every reference
# XML), ref_lines.txt (reference lines found in no visible GEOS file) and expect_mounts.txt.
FAIL=0
emit() { # name status detail
  local d=${3//\\/\\\\}; d=${d//\"/\\\"}; d=$(printf '%s' "$d" | tr '\n\t' '  ' | cut -c1-400)
  printf '{"check": "%s", "status": "%s", "detail": "%s"}\n' "$1" "$2" "$d"
  if [[ $2 == FAIL ]]; then FAIL=1; fi
  return 0
}
SCAN_ROOTS="/geos_lib /workspace /home /tmp /opt /plugins /usr /etc /run /var /root /srv /mnt /data"
existing() { for r in $SCAN_ROOTS; do [[ -e $r ]] && echo "$r"; done; }

# 1. version-control history anywhere (git show HEAD:<deck> recovers every deck)
v=$(find $(existing) \( -name .git -o -name .hg -o -name .svn \) 2>/dev/null | head -5)
[[ -z $v ]] && emit vcs_dirs PASS "none" || emit vcs_dirs FAIL "$v"
g=$(cd /geos_lib 2>/dev/null && git log -1 --format=%H 2>&1 | head -1)
[[ $g == fatal* || -z $g ]] && emit git_history PASS "git log in /geos_lib: ${g:0:60}" || emit git_history FAIL "$g"

# 2. any file byte-identical to a reference deck file
hits=""
while IFS= read -r f; do
  s=$(sha256sum "$f" 2>/dev/null | cut -d' ' -f1)
  grep -qx "$s" /probe/ref_sha256.txt && hits+="$f "
done < <(find $(existing) -type f \( -iname '*.xml' -o -iname '*.xml.*' -o -iname '*.txt' \) 2>/dev/null)
[[ -z $hits ]] && emit reference_copies PASS "no file matches a reference sha256" || emit reference_copies FAIL "$hits"

# 3. reference-specific lines anywhere visible (renamed copies, docs, caches, image, pip)
n=$(wc -l < /probe/ref_lines.txt)
if (( n > 0 )); then
  h=$(grep -rIlF -f /probe/ref_lines.txt $(existing) 2>/dev/null | grep -v '^/probe' | head -10)
  [[ -z $h ]] && emit reference_lines PASS "$n reference-only lines; 0 visible files contain any" || emit reference_lines FAIL "$h"
else
  emit reference_lines PASS "no reference-only lines to search for"
fi

# 4. known side channels and host paths. The names below are artefacts of the SIGA authors'
# internal data pipeline (navigation graph, RAG chunks/DB, ground-truth and spec dirs) and run
# outputs. The SIGA adapter mount (/plugins) and the R database mount (/opt/siga, R cells only)
# are declared inputs: excluded here, the database is reported separately below.
sc=$(find $(existing) \( -path /plugins -o -path /opt/siga \) -prune -o \( -name nav_graph.json -o -name 'cheatsheet*.md' -o -name GEOSDATA -o -name chunks \
      -o -name vector_db -o -name experiments_gt -o -name 'experiments*' -o -name 'example_pairs*.jsonl' \
      -o -name 'eval_results*' -o -name 'metrics.json' -o -name 'score_details.json' -o -name 'reward.json' \) -print 2>/dev/null \
      | grep -v -E '^/(opt/[^/]+|usr/lib|usr/local/lib)/(.*/)?node_modules/' | head)
[[ -z $sc ]] && emit side_channels PASS "none" || emit side_channels FAIL "$sc"
bm=$(find $(existing) \( -path '*/tests/reference' -o -path '*/solution/inputs' -o -name siga-geos -o -name 'task.toml' \) 2>/dev/null | head -5)
[[ -z $bm ]] && emit benchmark_files PASS "no task, reference or solution dirs visible" || emit benchmark_files FAIL "$bm"
if [[ -d /opt/siga/vector_db ]]; then
  emit rag_db WARN "R database mounted read-only at /opt/siga/vector_db; the agent can read it directly (as in the paper)"
fi
hp=""
for p in /data /mnt /srv /nfs /media /root/projects; do [[ -e $p ]] && hp+="$p "; done
for p in /home/*; do [[ -e $p && $p != /home/agent ]] && hp+="$p "; done
[[ -z $hp ]] && emit host_paths PASS "no host data dirs and no home other than /home/agent" || emit host_paths FAIL "$hp"

# 5. mounts: only the expected set
mp=$(awk '{print $5}' /proc/self/mountinfo | sort -u | tr '\n' ' ')
unexp=""
for m in $mp; do grep -qxF "$m" /probe/expect_mounts.txt || unexp+="$m "; done
[[ -z $unexp ]] && emit mounts PASS "$mp" || emit mounts FAIL "unexpected: $unexp"

# 6. workspace starts empty (no prior run outputs)
w=$(find /workspace -mindepth 1 -not -path '/workspace/inputs' 2>/dev/null | head -5)
[[ -z $w ]] && emit workspace_clean PASS "empty" || emit workspace_clean FAIL "$w"

# 7. read-only where it matters
for d in /geos_lib /usr /etc; do
  if touch "$d/.probe_write" 2>/dev/null; then emit "readonly_${d#/}" FAIL "wrote to $d"; rm -f "$d/.probe_write"; else emit "readonly_${d#/}" PASS "write refused"; fi
done

# 8. network: direct and via the agent's proxy (if any). All must fail.
net_try() { # label url [proxy]
  local code
  if [[ -n $3 ]]; then code=$(curl -s -m 8 -o /dev/null -w '%{http_code}' --proxy "$3" "$2" 2>&1)
  else code=$(curl -s -m 8 -o /dev/null -w '%{http_code}' --noproxy '*' "$2" 2>&1); fi
  [[ $code == 000* || $code == "" ]] && emit "$1" PASS "no connection ($code)" || emit "$1" FAIL "HTTP $code from $2"
}
for u in https://github.com https://raw.githubusercontent.com/GEOS-DEV/GEOS/develop/README.md https://pypi.org/simple/ https://www.google.com http://1.1.1.1; do
  net_try "net_direct:${u#*//}" "$u"
done
PX=${HTTPS_PROXY:-${https_proxy:-}}
if [[ -n $PX ]]; then
  for u in https://github.com https://raw.githubusercontent.com/GEOS-DEV/GEOS/develop/README.md https://pypi.org/simple/ https://api.github.com; do
    net_try "net_proxy:${u#*//}" "$u" "$PX"
  done
fi
if getent hosts github.com >/dev/null 2>&1; then emit dns FAIL "github.com resolves"; else emit dns PASS "no DNS"; fi
# The model gate (pi): only the model API, no web plugins.
if [[ -S /run/net/llm.sock ]]; then
  c=$(curl -s -m 8 -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/api/v1/models 2>&1)
  [[ $c == 403 || $c == 404 || $c == 405 || $c == 000* ]] && emit gate_other_paths PASS "GET /models -> $c" || emit gate_other_paths FAIL "GET /models -> $c"
  c=$(curl -s -m 20 -o /dev/null -w '%{http_code}' -H 'content-type: application/json' \
      -d '{"model":"openai/gpt-4o-mini","messages":[{"role":"user","content":"hi"}],"max_tokens":1}' \
      http://127.0.0.1:8080/api/v1/chat/completions 2>&1)
  [[ $c == 403 ]] && emit gate_other_model PASS "other model -> 403" || emit gate_other_model FAIL "other model -> $c"
fi

# 9. process isolation and environment
np=$(ls /proc | grep -c '^[0-9]*$')
host=$(cat /proc/[0-9]*/cmdline 2>/dev/null | tr '\0' ' ' | grep -Eo 'tmu[x]|ssh[d]|system[d]|claude-cod[e]|vll[m]' | head -3 | tr '\n' ' ')
[[ -z $host ]] && emit pid_namespace PASS "$np pids, none from host" || emit pid_namespace FAIL "$host"
ek=$(env | grep -iE 'api_key|token|secret|password|OPENROUTER|ANTHROPIC_AUTH' | cut -d= -f1 | tr '\n' ' ')
[[ -z $ek ]] && emit env_secrets PASS "none" || emit env_secrets WARN "secret-looking env vars present: $ek"

# 10. GEOS binary not present (decks only; no solver runs)
gb=$(command -v geosx geos 2>/dev/null; find /opt /usr -maxdepth 4 -name 'geosx*' -type f 2>/dev/null | head -3)
[[ -z $gb ]] && emit no_geos_binary PASS "none" || emit no_geos_binary WARN "$gb"

[[ $FAIL == 0 ]] && echo '{"probe": "PASS"}' || echo '{"probe": "FAIL"}'
exit $FAIL
