#!/bin/sh
# Frozen confirmation schedule v6 (EXPERIMENT-seed-confirmation.md): usage confirm_seed.sh <name> <seed>
set -e
name=$1; seed=$2
export RSI_WORKERS=${RSI_WORKERS:-4}
for step in "mech 4" "drawn7 3" "metric777001 3" "drawn11 2" "drawn13 2" "metric555001 2" "mech 2"; do
  set -- $step
  python seed_run.py --name "$name" --seed "$seed" --area "$1" --lives "$2" --worlds 96 --held-out 48
done
python seed_check.py --name "$name" --seed "$seed" --areas mech,drawn7,metric777001,drawn11,drawn13,metric555001
python audit_seed.py --name "$name"
