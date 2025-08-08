#!/bin/bash

mkdir -p logs

commands=(
  "ruff check ." \
  "mypy backend || true" \
  "python -m pytest -q" \
  "command -v npm >/dev/null && npm --prefix web run format:check || echo 'npm not found, skipping format check'" \
  "command -v npm >/dev/null && npm --prefix web run lint --if-present || echo 'npm not found, skipping lint'" \
  "command -v npm >/dev/null && npm --prefix web run test -- --run || echo 'npm not found, skipping web tests'" \
  "command -v npm >/dev/null && npm --prefix web run build || echo 'npm not found, skipping web build'"
)

labels=(
  "Ruff Lint (Python)" \
  "Mypy Type Check" \
  "Backend Pytests" \
  "Prettier Format Check (Web)" \
  "ESLint (Web)" \
  "Web Unit Tests" \
  "Web Build"
)

statuses=()
exit_codes=()
log_files=()

echo "🔧 Available Steps:"
for i in "${!labels[@]}"; do
  printf "%d) %s\n" $((i+1)) "${labels[$i]}"
done

echo
echo "📝 Options:"
echo "  a) Run all"
echo "  m) Select multiple steps (e.g. 1 3 5)"
echo

read -rp "👉 Choose an option (number/a/m): " choice

selected_indices=()

if [[ "$choice" == "a" || "$choice" == "A" ]]; then
  for i in "${!commands[@]}"; do
    selected_indices+=("$i")
  done
elif [[ "$choice" == "m" || "$choice" == "M" ]]; then
  read -rp "🔢 Enter step numbers separated by space (e.g. 1 2 4): " -a nums
  for n in "${nums[@]}"; do
    index=$((n - 1))
    if [[ $index -ge 0 && $index -lt ${#commands[@]} ]]; then
      selected_indices+=("$index")
    else
      echo "⚠️ Skipping invalid selection: $n"
    fi
  done
else
  index=$((choice - 1))
  if [[ $index -ge 0 && $index -lt ${#commands[@]} ]]; then
    selected_indices+=("$index")
  else
    echo "❌ Invalid choice. Exiting."
    exit 1
  fi
fi

# Run and log selected commands
for i in "${selected_indices[@]}"; do
  label="${labels[$i]}"
  cmd="${commands[$i]}"
  log_file="logs/step_${i}_${label// /_}.log"
  log_files[$i]="$log_file"

  echo "🔄 Running: $label"
  echo "→ Logging to: $log_file"

  eval "$cmd" 2>&1 | tee "$log_file"
  code=${PIPESTATUS[0]}
  
  if [ $code -eq 0 ]; then
    statuses[$i]="✅ PASSED"
  else
    statuses[$i]="❌ FAILED"
  fi

  exit_codes[$i]=$code
  echo
done

# Summary
echo "==================== Summary ===================="
for i in "${selected_indices[@]}"; do
  label="${labels[$i]}"
  status="${statuses[$i]}"
  log="${log_files[$i]}"
  code="${exit_codes[$i]}"
  errors=$(grep -i -E "error|fail" "$log" | wc -l)
  printf "%-25s %s (exit: %d, ~%d error(s), log: %s)\n" \
    "$label" "$status" "$code" "$errors" "$log"
done
echo "================================================="

# Prompt: View errors?
read -rp "🧐 Do you want to view errors? (y/n): " show_errors
if [[ "$show_errors" != "y" && "$show_errors" != "Y" ]]; then
  echo "👋 Exiting without viewing logs."
  exit 0
fi

# Loop through failed sections
for i in "${selected_indices[@]}"; do
  if [[ "${statuses[$i]}" == "❌ FAILED" ]]; then
    label="${labels[$i]}"
    log="${log_files[$i]}"
    read -rp "🔍 View log for failed step \"$label\"? (y/n): " view_log
    if [[ "$view_log" == "y" || "$view_log" == "Y" ]]; then
      echo "📄 Showing log for $label:"
      more "$log"
    else
      echo "⏭️ Skipping $label"
    fi
    echo
  fi
done

echo "✅ Done reviewing logs."
