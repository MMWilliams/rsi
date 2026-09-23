"""Task-balanced verified replay for the isolated frontier experiment."""
import random
import time
import contextlib

from .common import digest
from .neural import LocalModel, adapter_hash
from .oracle import correct
from dsl import render
from parse import parse


def harvest_arm(frontier, arm):
    if arm.endswith("_selected"):
        return frontier[:1] if frontier and frontier[0]["oracle_correct"] else []
    verified = [r for r in frontier if r["oracle_correct"]]
    if arm == "corrected_first_verified":
        return verified[:1]
    if arm == "corrected_frontier":
        return verified
    raise ValueError("Unknown harvest arm")


def build_pool(anchors, harvest, tasks):
    if {r["task_id"] for r in anchors} & {r["task_id"] for r in harvest}:
        raise ValueError("Anchor and harvested task strata overlap")
    rows, seen = [], set()
    for stratum, source in (("anchor", anchors), ("harvest", harvest)):
        for row in source:
            task = tasks[row["task_id"]]
            if row.get("oracle_correct") is not True or not correct(row["program"], task["visible"] + task["hidden"]):
                raise ValueError("Unverified frontier target")
            program = render(parse(row["program"]))
            key = (row["task_id"], program)
            if key not in seen:
                rows.append({"task_id": key[0], "program": program, "oracle_correct": True, "stratum": stratum})
                seen.add(key)
    rows.sort(key=lambda r: (r["stratum"], r["task_id"], r["program"]))
    anchor_ids = {r["task_id"] for r in rows if r["stratum"] == "anchor"}
    if anchor_ids & {r["task_id"] for r in rows if r["stratum"] == "harvest"}:
        raise ValueError("Anchor and harvested task strata overlap")
    return rows


def draw_schedule(rows, seed, steps, batch_size, anchor_count):
    if not 0 < anchor_count < batch_size:
        raise ValueError("Both training strata need positive allocation")
    groups = {name: {} for name in ("anchor", "harvest")}
    for index, row in enumerate(rows):
        groups[row["stratum"]].setdefault(row["task_id"], []).append(index)
    if not all(groups.values()):
        return []
    task_rngs = {"anchor": random.Random(seed), "harvest": random.Random(seed ^ 0xA71C)}
    program_rng = random.Random(seed ^ 0xB93D)
    result = []
    for _ in range(steps):
        indices = []
        for position in range(batch_size):
            stratum = "anchor" if position < anchor_count else "harvest"
            task_ids = sorted(groups[stratum])
            task_id = task_ids[task_rngs[stratum].randrange(len(task_ids))]
            choices = groups[stratum][task_id]
            indices.append(choices[program_rng.randrange(len(choices))])
        result.append(indices)
    return result


class FrontierModel(LocalModel):
    def generate_prompts(self, prompts, seed, max_new_tokens=None):
        """Preserve completion token IDs so generated-token charges are auditable."""
        torch = self.torch
        self.model.eval()
        self.model.config.use_cache = True
        self.tokenizer.padding_side = "left"
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        outputs, traces = [], []
        start = time.perf_counter()
        limit = self.config["generation_batch_size"]
        manager = self.model.disable_adapter() if self.active is None else contextlib.nullcontext()
        with manager, torch.inference_mode():
            for offset in range(0, len(prompts), limit):
                batch = self.tokenizer(prompts[offset:offset + limit], return_tensors="pt", padding=True, add_special_tokens=False).to(self.config["device"])
                generated = self.model.generate(**batch, max_new_tokens=max_new_tokens or self.config["max_new_tokens"], do_sample=True,
                    temperature=0.8, top_p=0.95, top_k=20, pad_token_id=self.tokenizer.pad_token_id, eos_token_id=self.tokenizer.eos_token_id)
                completions = generated[:, batch.input_ids.shape[1]:]
                ids = completions.cpu().tolist()
                lengths = batch.attention_mask.sum(dim=1).cpu().tolist()
                self.ledger["generated_tokens"] += sum(t != self.tokenizer.pad_token_id for row in ids for t in row)
                self.ledger["prompt_tokens"] += sum(lengths)
                outputs.extend(self.tokenizer.batch_decode(completions, skip_special_tokens=True))
                traces.append({"offset": offset, "prompt_lengths": lengths, "completion_ids": ids})
        self.ledger["generation_seconds"] += time.perf_counter() - start
        self.last_generation_trace = traces
        return outputs

    def train_balanced(self, rows, task_map, adapter, output, seed, change_id):
        torch = self.torch
        verified = []
        for row in rows:
            task = task_map[row["task_id"]]
            self.ledger["oracle_string_executions"] += len(task["visible"]) + len(task["hidden"])
            if row.get("oracle_correct") is not True or not correct(row["program"], task["visible"] + task["hidden"]):
                raise ValueError("Unverified trajectory attempted to enter distillation")
            verified.append((self.prompt(task), row["program"] + self.tokenizer.eos_token))
        certificate = {"change_id": change_id, "arm": adapter, "rows": len(rows), "rows_sha256": digest(rows),
                       "task_ids": [r["task_id"] for r in rows], "anchor_per_batch": self.config["anchor_per_batch"]}
        self.journal.append("distillation_certificate", certificate)
        schedule = draw_schedule(rows, seed, self.config["lora_steps"], self.config["lora_batch_size"], self.config["anchor_per_batch"])
        self.activate(adapter)
        parent_hash = adapter_hash(self.snapshot(adapter))
        if not schedule:
            self.save_adapter(adapter, output)
            result = {**certificate, "steps": 0, "skipped": "empty_training_stratum", "parent_sha256": parent_hash,
                      "candidate_sha256": parent_hash, "seed": seed, "losses": [], "schedule_sha256": digest(schedule)}
            self.journal.append("balanced_distillation", result)
            return result
        self.model.train()
        self.model.config.use_cache = False
        self.tokenizer.padding_side = "right"
        optimizer = torch.optim.AdamW([p for p in self.model.parameters() if p.requires_grad], lr=self.config["lora_learning_rate"])
        torch.manual_seed(seed)
        encoded = []
        for prompt, completion in verified:
            prefix = self.tokenizer(prompt, add_special_tokens=False).input_ids
            suffix = self.tokenizer(completion, add_special_tokens=False).input_ids
            if len(prefix) + len(suffix) > 1024:
                raise ValueError("Training target would be truncated")
            encoded.append((prefix + suffix, [-100] * len(prefix) + suffix))
        started, losses = time.perf_counter(), []
        for step, indices in enumerate(schedule, 1):
            batch = [encoded[index] for index in indices]
            width = max(len(ids) for ids, _ in batch)
            ids = torch.tensor([x + [self.tokenizer.pad_token_id] * (width - len(x)) for x, _ in batch], device=self.config["device"])
            labels = torch.tensor([x + [-100] * (width - len(x)) for _, x in batch], device=self.config["device"])
            attention = torch.tensor([[1] * len(x) + [0] * (width - len(x)) for x, _ in batch], device=self.config["device"])
            optimizer.zero_grad(set_to_none=True)
            loss = self.model(input_ids=ids, attention_mask=attention, labels=labels).loss
            if not torch.isfinite(loss):
                raise RuntimeError("Non-finite training loss")
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_([p for p in self.model.parameters() if p.requires_grad], 1.0, error_if_nonfinite=True)
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
            tokens = int((labels != -100).sum().item())
            self.ledger["supervised_tokens"] += tokens
            self.journal.append("optimizer_step", {"change_id": change_id, "arm": adapter, "seed": seed, "step": step,
                "rows_sha256": digest(rows), "row_indices": indices, "loss": losses[-1], "gradient_norm_before_clip": float(norm.detach().cpu()),
                "supervised_tokens": tokens, "learning_rate": self.config["lora_learning_rate"],
                "anchor_draws": self.config["anchor_per_batch"], "harvest_draws": len(indices) - self.config["anchor_per_batch"]})
            if step % 16 == 0:
                print(f"{change_id}: step {step}/{len(schedule)}, loss {losses[-1]:.4f}", flush=True)
        elapsed = time.perf_counter() - started
        self.ledger["training_seconds"] += elapsed
        self.ledger["training_steps"] += len(schedule)
        self.save_adapter(adapter, output)
        self.model.eval()
        self.tokenizer.padding_side = "left"
        result = {**certificate, "steps": len(schedule), "losses": losses, "parent_sha256": parent_hash,
                  "candidate_sha256": adapter_hash(self.snapshot(adapter)), "seed": seed, "seconds": elapsed,
                  "optimizer": "AdamW", "learning_rate": self.config["lora_learning_rate"], "schedule_sha256": digest(schedule)}
        self.journal.append("balanced_distillation", result)
        return result
