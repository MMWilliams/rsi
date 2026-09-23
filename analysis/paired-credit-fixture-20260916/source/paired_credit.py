"""Source-only paired descendant probe. Independent of the live neural runner."""
import random

from rsi.operators import apply, initial_catalog


def bank_config(config):
    counts = {}
    for seed in config["source_seeds"]:
        counts[f"s{seed}_development"] = config["rounds"] * config["development_per_round"]
        counts[f"s{seed}_admission"] = config["rounds"] * config["admission_per_round"]
        counts[f"s{seed}_measurement"] = config["measurement_tasks"]
    return {**config, "bank_counts": counts}


def schedule(seed, rounds):
    rng = random.Random(seed + 126000)
    names = [op["name"] for op in initial_catalog()]
    return [rng.sample(names, 2) for _ in range(rounds)]


def effects(base_start, base_end, edited_start, edited_end):
    immediate = edited_start - base_start
    terminal = edited_end - base_end
    later = (edited_end - edited_start) - (base_end - base_start)
    return {"immediate": immediate, "total_descendant": terminal, "later_improvement": later}


def branch(evaluate, banks, config, seed, initial, label, plan):
    catalog = {op["name"]: op for op in initial_catalog()}
    state, decisions = dict(initial), []
    for index, names in enumerate(plan, 1):
        dev_split, guard_split = f"s{seed}_development", f"s{seed}_admission"
        width, guard_width = config["development_per_round"], config["admission_per_round"]
        dev = banks[dev_split][(index - 1) * width:index * width]
        guard = banks[guard_split][(index - 1) * guard_width:index * guard_width]
        prefix = f"{label}/g{index}"
        parent = evaluate(dev, state, prefix + "/parent", dev_split)
        candidates = []
        for name in names:
            candidate = apply(catalog[name], state)
            score = evaluate(dev, candidate, prefix + "/" + name, dev_split)
            candidates.append((score["correct"] - parent["correct"], name, candidate, score))
        best = max(candidates, key=lambda row: (row[0], row[1]))
        gp = evaluate(guard, state, prefix + "/guard_parent", guard_split)
        gc = evaluate(guard, best[2], prefix + "/guard_candidate", guard_split)
        accepted = best[0] > 0 and gc["correct"] >= gp["correct"]
        decision = {"round": index, "parent_config": dict(state), "operator_names": names,
                    "parent_ref": parent["id"], "candidate_refs": [r[3]["id"] for r in candidates],
                    "chosen_operator": best[1], "candidate_config": best[2],
                    "guard_parent_ref": gp["id"], "guard_candidate_ref": gc["id"],
                    "development_gain_count": best[0], "admission_gain_count": gc["correct"] - gp["correct"],
                    "accepted": accepted,
                    "reason": "positive_development_and_admission_nonregression" if accepted else
                    "no_positive_development_gain" if best[0] <= 0 else "admission_regression"}
        if accepted:
            state = best[2]
        decision["selected_config"] = dict(state)
        decisions.append(decision)
    return {"seed": seed, "label": label, "initial_config": initial,
            "terminal_config": state, "schedule": plan, "decisions": decisions}
