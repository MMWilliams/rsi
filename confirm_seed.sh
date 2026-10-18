#!/bin/sh
# Frozen confirmation schedule v11 (EXPERIMENT-seed-confirmation.md): v10's seven areas in two task forms, with the
# meta-level on (the seed tests changes to its own procedure): usage confirm_seed.sh <name> <seed>
set -e
name=$1; seed=$2
export RSI_WORKERS=${RSI_WORKERS:-4}
for step in "mech 4" "drawn7 3" "metric777001 3" "drawn11 2" "drawn13 2" "metric555001 2" "str7 3" "mech 2"; do
  set -- $step
  python seed_run.py --name "$name" --seed "$seed" --area "$1" --lives "$2" --worlds 96 --held-out 48 \
    --meta-every 2 --meta-lives 2 --meta-budget 0.3
done
python seed_check.py --name "$name" --seed "$seed" --areas mech,drawn7,metric777001,drawn11,drawn13,metric555001,str7
python audit_seed.py --name "$name"
