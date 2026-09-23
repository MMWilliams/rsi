from rsi.meta_ast import choose_candidate, features, genome_score


def test_meta_ast_genome_ranks_candidates_deterministically():
    candidates = [{"program": "div mul", "oracle_correct": True}, {"program": "mask", "oracle_correct": False}]
    genome = {"weights": [10, 10, 0, 0, 0, 0, -1]}
    assert choose_candidate(candidates, genome)["program"] == "div mul"
    assert len(features(candidates[0]["program"])) == 7
    assert genome_score(candidates[0]["program"], genome) > genome_score(candidates[1]["program"], genome)
