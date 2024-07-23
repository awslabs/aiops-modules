import argparse
import logging
import os
from typing import Any, List

import bitsandbytes as bnb
import torch
from data_processing import CodeLlamaDataProcessor
from datasets import load_from_disk
from peft import (
    AutoPeftModelForCausalLM,
    LoraConfig,
    PeftConfig,
    PeftModel,
    TaskType,
    get_peft_model,
    prepare_model_for_kbit_training,
)
from peft.tuners.lora import LoraLayer
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    Trainer,
    TrainingArguments,
    default_data_collator,
    set_seed,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


def find_all_linear_names(model: PeftModel) -> List[str]:
    """
    Find all the names of linear layers in the model.
    Args:
        model: the model to search for linear layers

    Returns: List containing linear layers

    """
    lora_module_names = set()
    for name, module in model.named_modules():
        if isinstance(module, bnb.nn.Linear4bit):
            names = name.split(".")
            lora_module_names.add(names[0] if len(names) == 1 else names[-1])

    if "lm_head" in lora_module_names:  # needed for 16-bit
        lora_module_names.remove("lm_head")
    return list(lora_module_names)


def create_peft_model(model: Any, gradient_checkpointing: bool = True, bf16: bool = True) -> PeftModel:
    """
    Create a PEFT model from a HuggingFace model.

    Args:
        model: the HuggingFace model to create the PEFT model from
        gradient_checkpointing: whether to use gradient checkpointing
        bf16: whether to use bf16

    Returns: the PEFT model

    """
    # prepare int-4 model for training
    model: PeftModel = prepare_model_for_kbit_training(model, use_gradient_checkpointing=gradient_checkpointing)  # type: ignore[no-redef]
    if gradient_checkpointing:
        model.gradient_checkpointing_enable()

    # get lora target modules
    modules = find_all_linear_names(model)
    logger.info(f"Found {len( modules )} modules to quantize: {modules}")

    peft_config = LoraConfig(
        r=64,
        lora_alpha=32,
        target_modules=modules,
        lora_dropout=0.1,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )

    model = get_peft_model(model, peft_config)

    # pre-process the model by upcasting the layer norms in float 32 for
    for name, module in model.named_modules():
        if isinstance(module, LoraLayer):
            if bf16:
                module = module.to(torch.bfloat16)
        if "norm" in name:
            module = module.to(torch.float32)
        if "lm_head" in name or "embed_tokens" in name:
            if hasattr(module, "weight"):
                if bf16 and module.weight.dtype == torch.float32:
                    module = module.to(torch.bfloat16)

    model.print_trainable_parameters()

    return model


def train(args: Any) -> None:
    """
    Fine-tune model from HuggingFace and save it.
    Args:
        args: input arguments from SageMaker pipeline

    Returns:

    """
    # os.environ["WANDB_DISABLED"] = "true"
    # set seed
    set_seed(args.seed)

    dataset = load_from_disk(args.train_data)

    # create tokenized dataset
    tokenized_dataset = CodeLlamaDataProcessor.chunk_and_tokenize(
        prompt_dataset=dataset, chunk_length=args.chunk_length
    )

    # load model from the hub with a bnb config
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    # set the pad token to the eos token to ensure that the model will pick it up during training
    tokenizer = AutoTokenizer.from_pretrained(args.model_id)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        use_cache=(False if args.gradient_checkpointing else True),  # this is needed for gradient checkpointing
        device_map="auto",
        quantization_config=bnb_config,
    )

    # create peft config
    model = create_peft_model(model, gradient_checkpointing=args.gradient_checkpointing, bf16=args.bf16)

    # Define training args
    training_args = TrainingArguments(
        output_dir=args.output_data_dir,
        per_device_train_batch_size=args.per_device_train_batch_size,
        bf16=args.bf16,  # Use BF16 if available
        learning_rate=args.lr,
        num_train_epochs=args.epochs,
        gradient_checkpointing=args.gradient_checkpointing,
        # logging strategies
        logging_dir=f"{args.output_data_dir}/logs",
        logging_strategy="steps",
        logging_steps=10,
        save_strategy="no",
        report_to=[],
    )

    # Create Trainer instance
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        data_collator=default_data_collator,
    )

    logger.info("Start training")
    # Start training
    trainer.train()

    logger.info("Save Model")
    # save model
    trainer.save_model()

    # free the memory again
    del model
    del trainer
    torch.cuda.empty_cache()

    ####  MERGE PEFT AND BASE MODEL ####

    logger.info("Merge Base model with Adapter")
    # Load PEFT model on CPU
    config = PeftConfig.from_pretrained(args.output_data_dir)
    model = AutoModelForCausalLM.from_pretrained(config.base_model_name_or_path, low_cpu_mem_usage=True)
    tokenizer = AutoTokenizer.from_pretrained(config.base_model_name_or_path)
    model.resize_token_embeddings(len(tokenizer))
    # model = PeftModel.from_pretrained( model, args.output_data_dir )
    model = AutoPeftModelForCausalLM.from_pretrained(
        args.output_data_dir,
        torch_dtype=torch.float16,
        low_cpu_mem_usage=True,
    )
    # Merge LoRA and base model and save
    merged_model = model.merge_and_unload()
    merged_model.save_pretrained(args.model_dir, safe_serialization=True, max_shard_size="2GB")

    # save tokenizer for easy inference
    logger.info("Saving tokenizer")
    tokenizer = AutoTokenizer.from_pretrained(config.base_model_name_or_path)
    tokenizer.save_pretrained(args.model_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # add model id and dataset path argument
    parser.add_argument(
        "--model_id",
        type=str,
        help="Model id to use for training.",
    )
    parser.add_argument(
        "--model_dir",
        type=str,
        default=os.environ.get("SM_MODEL_DIR"),
        help="Directory inside the container where the final model will be saved.",
    )
    parser.add_argument(
        "--output_data_dir",
        type=str,
        default=os.environ.get("SM_OUTPUT_DATA_DIR"),
    )
    parser.add_argument(
        "--train_data",
        type=str,
        default=os.environ.get("SM_CHANNEL_TRAINING"),
        help="Directory with the training data.",
    )
    parser.add_argument("--epochs", type=int, default=3, help="Number of epochs to train for.")
    parser.add_argument(
        "--per_device_train_batch_size",
        type=int,
        default=1,
        help="Batch size to use for training.",
    )
    parser.add_argument(
        "--chunk_length",
        type=int,
        default=2048,
        help="Chunk length for tokenized dataset.",
    )
    parser.add_argument("--lr", type=float, default=5e-5, help="Learning rate to use for training.")
    parser.add_argument("--seed", type=int, default=42, help="Seed to use for training.")
    parser.add_argument(
        "--gradient_checkpointing",
        type=bool,
        default=True,
        help="Path to deepspeed config file.",
    )
    parser.add_argument(
        "--bf16",
        type=bool,
        default=True if torch.cuda.get_device_capability()[0] == 8 else False,
        help="Whether to use bf16.",
    )
    parser.add_argument(
        "--merge_weights",
        type=bool,
        default=True,
        help="Whether to merge LoRA weights with base model.",
    )
    args, _ = parser.parse_known_args()
    train(args)
