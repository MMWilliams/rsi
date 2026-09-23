"""Pinned local Qwen, independent LoRA arms, and oracle-verified distillation."""
from __future__ import annotations

import contextlib
import json
import math
import random
import time

from .common import canonical, digest, write_json
from .operators import validate_operator
from .oracle import correct

ADAPTER_NAMES = {"search": "amplified", "selftrain": "selftrain", "fixed_search": "frozen", "bootstrap": "bootstrap"}


def adapter_hash(state):
    import hashlib
    h = hashlib.sha256()
    for key in sorted(state):
        h.update(key.encode())
        h.update(str(tuple(state[key].shape)).encode())
        h.update(state[key].detach().float().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def make_adapters(base, lora):
    from peft import get_peft_model, get_peft_model_state_dict, set_peft_model_state_dict
    model = get_peft_model(base, lora, adapter_name=ADAPTER_NAMES["search"])
    for logical_name in ("selftrain", "fixed_search", "bootstrap"):
        model.add_adapter(ADAPTER_NAMES[logical_name], lora)
    # PEFT's initial adapter and later add_adapter calls can use different dtypes.
    # Normalize all trainable adapter tensors before cloning the common initial state.
    for name, parameter in model.named_parameters():
        if ".lora_" in name:
            parameter.data = parameter.data.float()
    initial = {key: value.detach().clone() for key, value in get_peft_model_state_dict(model, adapter_name=ADAPTER_NAMES["search"]).items()}
    for logical_name in ("selftrain", "fixed_search", "bootstrap"):
        set_peft_model_state_dict(model, initial, adapter_name=ADAPTER_NAMES[logical_name])
    return model


def identify_operator(operator):
    operator = validate_operator(operator)
    if operator["origin"] != "model":
        raise ValueError("Invalid model operator origin")
    return {**operator, "name": "model_" + digest(operator["updates"])[:16]}


def user_prompt(visible):
    return (
        "Infer one string transformation program that fits every example. Return exactly one line of DSL code, no markdown or explanation.\n"
        "Grammar: Concat(atom, ...). An atom is a quoted string, Sub(start,end), upper(atom), lower(atom), or cap(atom). "
        "Positions are C0, C1, C2, ... (absolute indices); C-1 means length minus one. "
        "M(WORD,1,start) and M(WORD,1,end) mark the first alphabetic word; the second argument may be 2. "
        "Tokens: WORD=[A-Za-z]+, DIGITS=[0-9]+, UPPER=[A-Z]+, LOWER=[a-z]+. "
        "Sub excludes its end position. Token names and start/end are unquoted.\n"
        "Example: first name in uppercase is Concat(upper(Sub(M(WORD,1,start),M(WORD,1,end)))).\n"
        "Examples to solve:\n" + "\n".join(json.dumps(inp) + " -> " + json.dumps(out) for inp, out in visible)
    )


class LocalModel:
    def __init__(self, config, journal):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import LoraConfig
        self.torch, self.config, self.journal = torch, config, journal
        torch.set_num_threads(8)
        torch.manual_seed(config["neural_seed"])
        if not torch.cuda.is_available():
            raise RuntimeError("Neural pilot requires CUDA; CPU pilot is available separately")
        self.tokenizer = AutoTokenizer.from_pretrained(config["model_id"], revision=config["model_revision"], local_files_only=True)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = "left"
        base = AutoModelForCausalLM.from_pretrained(config["model_id"], revision=config["model_revision"], local_files_only=True,
                                                  torch_dtype=torch.bfloat16, attn_implementation="sdpa").to(config["device"])
        lora = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.0, bias="none", task_type="CAUSAL_LM", target_modules=["q_proj", "v_proj"])
        self.model = make_adapters(base, lora)
        self.active = None
        self.ledger = {"generated_tokens": 0, "prompt_tokens": 0, "generation_seconds": 0.0,
                       "training_steps": 0, "training_seconds": 0.0, "supervised_tokens": 0, "oracle_string_executions": 0}
        journal.append("model_loaded", {"model_id": config["model_id"], "revision": config["model_revision"], "dtype": "bfloat16", "device": config["device"], "lora_rank": 8})

    def chat(self, content):
        return self.tokenizer.apply_chat_template([{"role": "user", "content": content}], tokenize=False, add_generation_prompt=True, enable_thinking=False)

    def prompt(self, task):
        return self.chat(user_prompt(task["visible"]))

    def activate(self, adapter=None):
        self.active = adapter
        if adapter is not None:
            self.model.set_adapter(ADAPTER_NAMES[adapter])

    def snapshot(self, adapter):
        from peft import get_peft_model_state_dict
        return {key: value.detach().cpu().clone() for key, value in
                get_peft_model_state_dict(self.model, adapter_name=ADAPTER_NAMES[adapter]).items()}

    def restore(self, adapter, state):
        from peft import set_peft_model_state_dict
        set_peft_model_state_dict(self.model, state, adapter_name=ADAPTER_NAMES[adapter])
        actual = adapter_hash(self.snapshot(adapter))
        if actual != adapter_hash(state):
            raise RuntimeError("Adapter rollback/copy failed exact tensor hash check")
        self.activate(adapter)
        return actual

    def save_adapter(self, adapter, output):
        self.model.save_pretrained(output, selected_adapters=[ADAPTER_NAMES[adapter]], safe_serialization=True)

    def copy_bootstrap(self):
        import hashlib
        from peft import get_peft_model_state_dict, set_peft_model_state_dict
        state = {key: value.detach().clone() for key, value in get_peft_model_state_dict(self.model, adapter_name="bootstrap").items()}
        def state_hash(weights):
            h = hashlib.sha256()
            for key in sorted(weights):
                h.update(key.encode())
                h.update(weights[key].detach().float().cpu().numpy().tobytes())
            return h.hexdigest()
        expected = state_hash(state)
        for name in ("search", "selftrain", "fixed_search"):
            set_peft_model_state_dict(self.model, state, adapter_name=ADAPTER_NAMES[name])
            actual = state_hash(get_peft_model_state_dict(self.model, adapter_name=ADAPTER_NAMES[name]))
            if actual != expected:
                raise RuntimeError("Bootstrap adapters are not identical")
        self.journal.append("shared_bootstrap", {"adapter_sha256": expected, "arms": ["search", "selftrain", "fixed_search"]})

    def generate_prompts(self, prompts, seed, max_new_tokens=None):
        torch = self.torch
        self.model.eval()
        self.model.config.use_cache = True
        self.tokenizer.padding_side = "left"
        outputs = []
        started = time.perf_counter()
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        limit = self.config["generation_batch_size"]
        manager = self.model.disable_adapter() if self.active is None else contextlib.nullcontext()
        with manager, torch.inference_mode():
            for offset in range(0, len(prompts), limit):
                batch = self.tokenizer(prompts[offset:offset + limit], return_tensors="pt", padding=True, add_special_tokens=False).to(self.config["device"])
                generated = self.model.generate(**batch, max_new_tokens=max_new_tokens or self.config["max_new_tokens"], do_sample=True,
                                                temperature=0.8, top_p=0.95, top_k=20,
                                                pad_token_id=self.tokenizer.pad_token_id, eos_token_id=self.tokenizer.eos_token_id)
                completions = generated[:, batch.input_ids.shape[1]:]
                self.ledger["generated_tokens"] += int((completions != self.tokenizer.pad_token_id).sum().item())
                self.ledger["prompt_tokens"] += int(batch.attention_mask.sum().item())
                outputs.extend(self.tokenizer.batch_decode(completions, skip_special_tokens=True))
        self.ledger["generation_seconds"] += time.perf_counter() - started
        return outputs

    def sample(self, tasks, n, seed):
        prompts = [self.prompt(task) for task in tasks for _ in range(n)]
        generated = self.generate_prompts(prompts, seed)
        return {task["id"]: generated[index * n:(index + 1) * n] for index, task in enumerate(tasks)}

    def distill(self, rows, task_map, adapter, output, seed, steps=None):
        torch = self.torch
        verified = []
        for row in rows:
            task = task_map[row["task_id"]]
            self.ledger["oracle_string_executions"] += len(task["visible"]) + len(task["hidden"])
            if row.get("oracle_correct") is not True or not correct(row["program"], task["visible"] + task["hidden"]):
                raise ValueError("Unverified trajectory attempted to enter distillation")
            verified.append((self.prompt(task), row["program"] + self.tokenizer.eos_token))
        certificate = {"arm": adapter, "rows": len(rows), "rows_sha256": digest(rows), "task_ids": [row["task_id"] for row in rows]}
        self.journal.append("distillation_certificate", certificate)
        if not verified:
            return {**certificate, "skipped": "no_verified_trajectories", "steps": 0}
        self.activate(adapter)
        parent_hash = adapter_hash(self.snapshot(adapter))
        self.model.train()
        self.model.config.use_cache = False
        self.tokenizer.padding_side = "right"
        optimizer = torch.optim.AdamW([parameter for parameter in self.model.parameters() if parameter.requires_grad], lr=self.config["lora_learning_rate"])
        rng = random.Random(seed)
        torch.manual_seed(seed)
        encoded = []
        for prompt, completion in verified:
            prefix = self.tokenizer(prompt, add_special_tokens=False).input_ids
            suffix = self.tokenizer(completion, add_special_tokens=False).input_ids
            if len(prefix) + len(suffix) > 1024:
                raise ValueError("Training example too long; do not silently truncate verified targets")
            encoded.append((prefix + suffix, [-100] * len(prefix) + suffix))
        started = time.perf_counter()
        losses = []
        step_count = self.config["lora_steps"] if steps is None else steps
        for step in range(step_count):
            indices = [rng.randrange(len(encoded)) for _ in range(self.config["lora_batch_size"])]
            samples = [encoded[index] for index in indices]
            width = max(len(ids) for ids, _ in samples)
            ids = torch.tensor([row + [self.tokenizer.pad_token_id] * (width - len(row)) for row, _ in samples], device=self.config["device"])
            labels = torch.tensor([row + [-100] * (width - len(row)) for _, row in samples], device=self.config["device"])
            attention = torch.tensor([[1] * len(row) + [0] * (width - len(row)) for row, _ in samples], device=self.config["device"])
            optimizer.zero_grad(set_to_none=True)
            loss = self.model(input_ids=ids, attention_mask=attention, labels=labels).loss
            if not torch.isfinite(loss):
                raise RuntimeError("Non-finite training loss")
            loss.backward()
            gradient_norm = torch.nn.utils.clip_grad_norm_([p for p in self.model.parameters() if p.requires_grad], 1.0,
                                                        error_if_nonfinite=True)
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
            self.ledger["supervised_tokens"] += int((labels != -100).sum().item())
            self.journal.append("optimizer_step", {"arm": adapter, "seed": seed, "step": step + 1,
                "rows_sha256": certificate["rows_sha256"], "row_indices": indices,
                "loss": losses[-1], "gradient_norm_before_clip": float(gradient_norm.detach().cpu()),
                "supervised_tokens": int((labels != -100).sum().item()), "learning_rate": self.config["lora_learning_rate"]})
            if (step + 1) % 16 == 0:
                print(f"  {adapter}: step {step + 1}/{step_count}, loss {losses[-1]:.4f}", flush=True)
        elapsed = time.perf_counter() - started
        self.ledger["training_seconds"] += elapsed
        self.ledger["training_steps"] += len(losses)
        self.model.save_pretrained(output, selected_adapters=[ADAPTER_NAMES[adapter]], safe_serialization=True)
        self.model.eval()
        self.tokenizer.padding_side = "left"
        result = {**certificate, "steps": len(losses), "first_loss": losses[0], "last_loss": losses[-1], "seconds": elapsed,
                  "adapter_path": str(output), "parent_sha256": parent_hash, "candidate_sha256": adapter_hash(self.snapshot(adapter)),
                  "seed": seed, "optimizer": "AdamW", "learning_rate": self.config["lora_learning_rate"], "losses": losses}
        self.journal.append("distillation", result)
        return result

    def propose_operators(self, table, seed):
        prompt = (
            "Design one new arithmetic search-config edit using the measured edit statistics below. "
            "Return ONLY JSON with keys name, origin, updates. origin must be model. "
            "Allowed fields: absolute_cost, match_cost, constant_cost, case_cost, length_cost, progress_weight, widening, macro_discount. "
            "An expression is a number, field name, or [operation,left,right] where operation is add, sub, mul, min, max. "
            "Change at most four fields. Costs must stay in [0.1,4], length_cost in [0.02,1.5], widening in [0.25,1], macro_discount in [0,0.8]. "
            'Example format: {"name":"coupled","origin":"model","updates":{"match_cost":["max",0.1,["mul","match_cost",0.8]],"absolute_cost":["min",4,["mul","absolute_cost",1.1]]}}\n'
            "Measured statistics: " + canonical(table)
        )
        self.activate(None)
        raw = self.generate_prompts([self.chat(prompt)] * 3, seed, max_new_tokens=240)
        proposals = []
        seen = set()
        for text in raw:
            try:
                start, stop = text.index("{"), text.rindex("}") + 1
                operator = identify_operator(json.loads(text[start:stop]))
                if operator["name"] in seen:
                    raise ValueError("Duplicate operator expression")
                seen.add(operator["name"])
                proposals.append(operator)
                self.journal.append("model_operator_proposal", {"raw": text, "valid": True, "operator": operator})
            except (ValueError, TypeError, KeyError, RecursionError) as exc:
                self.journal.append("model_operator_proposal", {"raw": text, "valid": False, "reason": str(exc)})
        return proposals


def pass_at_k(n, c, k):
    if not 0 <= c <= n or not 1 <= k <= n:
        raise ValueError("pass@k requires n >= k")
    if n - c < k:
        return 1.0
    return 1 - math.prod((n - c - i) / (n - i) for i in range(k))


def raw_scores(tasks, samples, ks):
    per_task = []
    for task in tasks:
        programs = [text.strip().splitlines()[0] if text.strip() else "" for text in samples[task["id"]]]
        successes = sum(correct(program, task["visible"] + task["hidden"]) for program in programs)
        per_task.append({"id": task["id"], "n": len(programs), "correct": successes,
                         "pass_at_k": {str(k): pass_at_k(len(programs), successes, k) for k in ks}})
    return {"tasks": per_task, "pass_at_k": {str(k): sum(row["pass_at_k"][str(k)] for row in per_task) / len(per_task) for k in ks}}
