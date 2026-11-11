#!/bin/sh
# Review 002 follow-up (EXPERIMENT-seed-confirmation.md, tag prereg-review002-v2): one run at
# a time, resumable, stops at the first failure. VENV names the Python environment.
cd "$(dirname "$0")"
export PATH="${VENV:-$PWD/.venv}/Scripts:$PATH" RSI_WORKERS=6

run() {   # run <marker file> <log> <command...>
  marker=$1; log=$2; shift 2
  [ -f "$marker" ] && return 0
  sha256sum -c --quiet v11.1.sha256 arms.sha256 arms2.sha256 || { echo "hashes changed, stopping"; exit 1; }
  echo "$(date '+%m-%d %H:%M') start $marker"
  "$@" >> "$log" 2>&1 || { echo "$marker failed"; exit 1; }
  touch "$marker"
  echo "$(date '+%m-%d %H:%M') done $marker"
}

first="c24:919127 c25:919128 c26:919129"
rest="c22:919121 c23:919122 c27:919130 c28:919131 c29:919132 c30:919133 c31:919134"

# what each tested candidate really did: the full arm again with every proof's states saved, then the truth sets
for pair in $first; do
  tag=${pair%:*}; seed=${pair#*:}
  run "seeds/record_$tag/done" "runs_arms_record_$tag.log" python run_record.py record "$tag" "$seed"
done
run seeds/record_c26/replayed runs_truth.log python truth_labels.py check
run seeds/record_c26/scored runs_truth.log python truth_labels.py score

# the time-matched arm on the first three seeds, against the clock of the recorded runs just made
for pair in $first; do
  tag=${pair%:*}; seed=${pair#*:}
  run "seeds/time-matched_$tag/done" "runs_arms_time-matched_$tag.log" python run_time_matched.py "$tag" "$seed" --of record
done

# every arm on the seven other seeds of the final protocol, seed by seed
for pair in $rest; do
  tag=${pair%:*}; seed=${pair#*:}
  for arm in full accept-all point matched no-guidance frequency no-invention; do
    run "seeds/${arm}_$tag/done" "runs_arms_${arm}_$tag.log" python run_arms.py "$arm" "$tag" "$seed"
  done
  run "seeds/time-matched_$tag/done" "runs_arms_time-matched_$tag.log" python run_time_matched.py "$tag" "$seed"
done
echo "$(date '+%m-%d %H:%M') all done"
