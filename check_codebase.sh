#!/usr/bin/env bash
# Comprehensive code-quality script.
# Usage:
#   ./check_codebase.sh         # interactive menu (default)
#   ./check_codebase.sh --ci    # non-interactive, run everything & fail on error

set -euo pipefail

mkdir -p logs

commands=(
  "ruff check ." 
  "mypy backend" 
  "python -m pytest -q" 
  "command -v npm >/dev/null && npm --prefix web run format:check --silent" 
  "command -v npm >/dev/null && npm --prefix web run lint -- --max-warnings=0" 
  "command -v npm >/dev/null && npm --prefix web run test -- --run --silent" 
  "command -v npm >/dev/null && npm --prefix web run build"
)

labels=(
  "Ruff Lint (Python)" 
  "Mypy Type Check" 
  "Backend Pytests" 
  "Prettier Format Check (Web)" 
  "ESLint (Web)" 
  "Web Unit Tests" 
  "Web Build"
)

# Show interactive menu unless --ci supplied
if [[ "${1:-}" != "--ci" ]]; then
  echo "🔧 Available Steps:"
  for idx in "${!labels[@]}"; do
    printf "%2d) %s\n" "$((idx+1))" "${labels[$idx]}"
  done
  echo -e "\na) Run all\n"
  read -rp "👉 Choose steps (e.g. 1 3 5 or 'a'): " choice
  if [[ "$choice" == "a" ]]; then
    selected_indices=( $(seq 0 $((${#commands[@]}-1))) )
  else
    read -ra num <<< "$choice"
    selected_indices=()
    for n in "${num[@]}"; do
      selected_indices+=( $((n-1)) )
    done
  fi
else
  selected_indices=( $(seq 0 $((${#commands[@]}-1))) )
  echo "▶️  Running all steps in CI mode (non-interactive)"
fi


# Run selected commands
results=()
for i in "${selected_indices[@]}"; do
  label="${labels[$i]}"
  cmd="${commands[$i]}"
  log="logs/step_${i}_${label// /_}.log"
  echo -e "\n🔄 $label"
  echo "   → $cmd"
  echo "   → log: $log"

  set +e
  bash -c "$cmd" 2>&1 | tee "$log"
  status=$?
  set -e

# record status
  if [[ $status -ne 0 ]]; then
    step_status="❌ FAILED"
  else
    step_status="✅ PASSED"
  fi
  results+=("$label|$step_status|$status|$log")
  echo "$step_status"
done

# summary
echo -e "\n================== Summary =================="
failures=0
for entry in "${results[@]}"; do
  IFS='|' read -r lbl stat code logfile <<< "$entry"
  printf "%s — %s (exit %s, log: %s)\n" "$lbl" "$stat" "$code" "$logfile"
  if [[ $code -ne 0 ]]; then failures=1; fi
done

if [[ $failures -ne 0 ]]; then
  echo "🚨 Some steps failed. See logs above."
  exit 1
else
  echo "🏁 All selected steps completed successfully"
fi
