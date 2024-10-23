import os

import evaluate
import numpy as np
import pandas as pd
import ray
import ray.data
import torch
from datasets import load_dataset
from ray import train
from ray.train import RunConfig, ScalingConfig
from ray.train.huggingface.transformers import RayTrainReportCallback, prepare_trainer
from ray.train.torch import TorchTrainer
from transformers import (
    AutoTokenizer,
    GPTJForCausalLM,
    Trainer,
    TrainingArguments,
    default_data_collator,
)
from transformers.utils.logging import disable_progress_bar, enable_progress_bar

model_name = "EleutherAI/gpt-j-6B"
use_gpu = True
num_workers = 5
cpus_per_worker = 12
block_size = 512
storage_path = "/ray/export"


ray.init(
    runtime_env={
        "pip": [
            "datasets",
            "evaluate",
            # The latest combination accelerate==0.25.0, transformers==4.36.0, deepspeed==0.12.4
            # has issues with DeepSpeed process group initialization,
            # and will result in a batch_size validation problem.
            # TODO(ml-team): get rid of the pins once the issue is fixed.
            "accelerate==0.18.0",
            "transformers==4.26.0",
            "torch>=1.12.0",
            "deepspeed==0.12.3",
        ],
    },
)

print("Loading tiny_shakespeare dataset")
current_dataset = load_dataset("tiny_shakespeare")

ray_datasets = {
    "train": ray.data.from_huggingface(current_dataset["train"]),
    "validation": ray.data.from_huggingface(current_dataset["validation"]),
}


def split_text(batch: pd.DataFrame) -> pd.DataFrame:
    text = list(batch["text"])
    flat_text = "".join(text)
    split_text = [x.strip() for x in flat_text.split("\n") if x.strip() and not x.strip()[-1] == ":"]
    return pd.DataFrame(split_text, columns=["text"])


def tokenize(batch: pd.DataFrame) -> dict:
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)
    tokenizer.pad_token = tokenizer.eos_token
    ret = tokenizer(
        list(batch["text"]),
        truncation=True,
        max_length=block_size,
        padding="max_length",
        return_tensors="np",
    )
    ret["labels"] = ret["input_ids"].copy()
    return dict(ret)


processed_datasets = {
    key: (ds.map_batches(split_text, batch_format="pandas").map_batches(tokenize, batch_format="pandas"))
    for key, ds in ray_datasets.items()
}


def train_func(config):
    # Use the actual number of CPUs assigned by Ray
    os.environ["OMP_NUM_THREADS"] = str(train.get_context().get_trial_resources().bundles[-1].get("CPU", 1))
    # Enable tf32 for better performance
    torch.backends.cuda.matmul.allow_tf32 = True

    batch_size = config.get("batch_size", 4)
    epochs = config.get("epochs", 2)
    warmup_steps = config.get("warmup_steps", 0)
    learning_rate = config.get("learning_rate", 0.00002)
    weight_decay = config.get("weight_decay", 0.01)
    steps_per_epoch = config.get("steps_per_epoch")

    deepspeed = {
        "fp16": {
            "enabled": "auto",
            "initial_scale_power": 8,
            "hysteresis": 4,
            "consecutive_hysteresis": True,
        },
        "bf16": {"enabled": "auto"},
        "optimizer": {
            "type": "AdamW",
            "params": {
                "lr": "auto",
                "betas": "auto",
                "eps": "auto",
            },
        },
        "zero_optimization": {
            "stage": 3,
            "offload_optimizer": {
                "device": "cpu",
                "pin_memory": False,  # out of mmeory
            },
            "overlap_comm": False,  # running out of GRAM
            "contiguous_gradients": True,
            "reduce_bucket_size": "auto",
            "stage3_prefetch_bucket_size": "auto",
            "stage3_param_persistence_threshold": "auto",
            "gather_16bit_weights_on_model_save": True,
            "round_robin_gradients": True,
        },
        "gradient_accumulation_steps": "auto",
        "gradient_clipping": "auto",
        "steps_per_print": 10,
        "train_batch_size": "auto",
        "train_micro_batch_size_per_gpu": "auto",
        "wall_clock_breakdown": False,
    }

    print("Preparing training arguments")
    training_args = TrainingArguments(
        "output",
        logging_steps=1,
        save_strategy="steps",
        save_steps=steps_per_epoch,
        max_steps=steps_per_epoch * epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=1,
        learning_rate=learning_rate,
        weight_decay=weight_decay,
        warmup_steps=warmup_steps,
        label_names=["input_ids", "attention_mask"],
        push_to_hub=False,
        report_to="none",
        disable_tqdm=True,  # declutter the output a little
        fp16=True,
        gradient_checkpointing=True,
        deepspeed=deepspeed,
    )
    disable_progress_bar()

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token

    print("Loading model")

    model = GPTJForCausalLM.from_pretrained(model_name, use_cache=False)
    model.resize_token_embeddings(len(tokenizer))

    print("Model loaded")

    enable_progress_bar()

    metric = evaluate.load("accuracy")

    train_ds = train.get_dataset_shard("train")
    eval_ds = train.get_dataset_shard("validation")

    train_ds_iterable = train_ds.iter_torch_batches(
        batch_size=batch_size,
        local_shuffle_buffer_size=train.get_context().get_world_size() * batch_size,
    )
    eval_ds_iterable = eval_ds.iter_torch_batches(batch_size=batch_size)

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        predictions = np.argmax(logits, axis=-1)
        return metric.compute(predictions=predictions, references=labels)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds_iterable,
        eval_dataset=eval_ds_iterable,
        compute_metrics=compute_metrics,
        tokenizer=tokenizer,
        data_collator=default_data_collator,
    )

    # Add callback to report checkpoints to Ray Train
    trainer.add_callback(RayTrainReportCallback())
    trainer = prepare_trainer(trainer)
    trainer.train()


batch_size = 12
train_ds_size = processed_datasets["train"].count()
steps_per_epoch = train_ds_size // (batch_size * num_workers)

trainer = TorchTrainer(
    train_loop_per_worker=train_func,
    train_loop_config={
        "epochs": 1,
        "batch_size": batch_size,  # per device
        "steps_per_epoch": steps_per_epoch,
    },
    scaling_config=ScalingConfig(
        num_workers=num_workers,
        use_gpu=use_gpu,
        resources_per_worker={"GPU": 1, "CPU": cpus_per_worker},
    ),
    datasets=processed_datasets,
    run_config=RunConfig(storage_path=storage_path),
)

results = trainer.fit()
