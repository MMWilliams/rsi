#!/bin/sh
# Regenerates every analysis file and generated table behind the papers from the
# committed runs, then checks that nothing changed. No agent is run and only
# numpy is needed; about two minutes. usage: sh reproduce_tables.sh
# (PYTHON=path/to/python chooses the interpreter)
set -e
py=${PYTHON:-python}
sha256sum -c --quiet v11.1.sha256 arms.sha256
for script in summarize_v11_replication rejudge_proofs summarize_arms summarize_limits second_draw paper_tables; do
  "$py" "$script.py" > /dev/null
done
git diff --exit-code --stat -- analysis paper
echo "reproduced: analysis files and tables equal the committed ones"
