#!/bin/sh
# Frozen confirmation schedule (EXPERIMENT-seed-confirmation.md): usage confirm_seed.sh <name> <seed>
set -e
name=$1; seed=$2
export RSI_WORKERS=${RSI_WORKERS:-4}
for step in "mech 4" "drawn7 3" "metric777001 3" "mech 2"; do
  set -- $step
  python seed_run.py --name "$name" --seed "$seed" --area "$1" --lives "$2"
done
python seed_check.py --name "$name" --seed "$seed" --areas mech,drawn7,metric777001
python audit_seed.py --name "$name"
