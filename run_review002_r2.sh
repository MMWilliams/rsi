#!/bin/sh
# Review 002, R2: v11.1 on eight sealed seeds, one at a time; stops at the first failed seed
cd "$(dirname "$0")"
export PATH="$PWD/.venv/Scripts:$PATH"   # the project venv has numpy; the system python may not
for i in 0 1 2 3 4 5 6 7; do
  name=c$((24 + i)); seed=$((919127 + i))
  [ -f "analysis/audit-seed-$name.json" ] && continue
  sha256sum -c --quiet v11.1.sha256 || { echo "v11.1 hashes changed, stopping"; exit 1; }
  echo "$(date '+%m-%d %H:%M') start $name $seed"
  sh confirm_seed.sh "$name" "$seed" > "runs_seed_conf_$name.log" 2>&1 || { echo "$name failed"; exit 1; }
  echo "$(date '+%m-%d %H:%M') done $name"
done
