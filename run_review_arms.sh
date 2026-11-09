#!/bin/sh
# Review 002 arms, one run at a time; stops at the first failure. EXPERIMENT-seed-confirmation.md.
cd "$(dirname "$0")"
export PATH="/c/Users/reese/projects/rsi/.venv/Scripts:$PATH" RSI_WORKERS=6
for arm in full accept-all point matched no-guidance frequency no-invention; do
  for pair in c24:919127 c25:919128 c26:919129; do
    tag=${pair%:*}; seed=${pair#*:}; name=${arm}_$tag
    [ -f "seeds/$name/done" ] && continue
    sha256sum -c --quiet v11.1.sha256 arms.sha256 || { echo "hashes changed, stopping"; exit 1; }
    echo "$(date '+%m-%d %H:%M') start $name"
    python run_arms.py "$arm" "$tag" "$seed" > "runs_arms_$name.log" 2>&1 || { echo "$name failed"; exit 1; }
    touch "seeds/$name/done"
    echo "$(date '+%m-%d %H:%M') done $name"
  done
done
