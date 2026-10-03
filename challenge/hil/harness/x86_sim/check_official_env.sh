#!/usr/bin/env bash
# Record the identity of the official X86 (OpenExplorer) environment B3 uses.
# Run on the WSL host, not inside the container.
set -u

CONTAINER=${1:-b3_oe391_cpu}

docker start "$CONTAINER" >/dev/null 2>&1 || true

echo "== container =="
echo "name      : $CONTAINER"
echo "image     : $(docker inspect -f '{{.Config.Image}}' "$CONTAINER")"
echo "image id  : $(docker inspect -f '{{.Image}}' "$CONTAINER")"
echo "created   : $(docker inspect -f '{{.Created}}' "$CONTAINER")"

echo
echo "== mounts =="
docker inspect -f '{{range .Mounts}}  {{.Source}} -> {{.Destination}} ({{.Mode}}){{"\n"}}{{end}}' "$CONTAINER"

echo "== versions =="
echo "os        : $(docker exec "$CONTAINER" bash -lc 'grep PRETTY_NAME /etc/os-release | cut -d= -f2')"
echo "python    : $(docker exec "$CONTAINER" python3 -V 2>&1)"
docker exec "$CONTAINER" bash -lc '
for pkg in torch numpy onnxruntime psutil hbdk4 horizon_tc_ui; do
  v=$(python3 -c "import importlib; m=importlib.import_module(\"$pkg\"); print(getattr(m, \"__version__\", \"present\"))" 2>/dev/null)
  printf "%-14s: %s\n" "$pkg" "${v:-absent}"
done
printf "%-14s: %s\n" "hb_compile" "$(hb_compile --version 2>&1 | head -1)"
printf "%-14s: %s\n" "hb_verifier" "$(hb_verifier --version 2>&1 | head -1)"
printf "%-14s: %s\n" "hrt_model_exec" "$(ls /open_explorer/samples/ucp_tutorial/tools/hrt_model_exec/output_shared_J6_x86/x86/bin/hrt_model_exec 2>/dev/null || echo absent)"
'
