import argparse
import json
import logging
import os
import re
import tarfile

import torch
from datasets import load_from_disk
from tqdm.auto import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from transformers.pipelines.pt_utils import KeyDataset

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


def clean_prediction(generated_response: str) -> str:
    """
    Extract SQL statements from generated response.
    Args:
        generated_response: response returned from the model

    Returns:
        str: generated SQL statement

    """
    # Define the pattern to match text between <SQL> tags, accounting for whitespace
    pattern = r"<SQL>\s*(.*?)\s*<\/SQL>"

    # Find all matches of the pattern in the long string
    matches = re.findall(pattern, generated_response, re.DOTALL)

    # Extract the SQL query from the first match (assuming there is only one match)
    if matches:
        return matches[0]
    else:
        return ""  # Return empty string to avoid issues downstream


def normalise_string(s) -> str:
    """
    Normalise string using pre-defined rules to allow for easier evaluation.
    For example, if the prediction only differs in letter case or spaces.
    Args:
        s: input string to be transformed

    Returns:
        str: Normalised string

    """
    # Remove spaces and newlines, convert to lowercase
    normalized = s.translate(str.maketrans("", "", " \n")).lower()
    # Change single quotes to double quotes
    normalized = normalized.replace("'", '"')
    # Delete any trailing semicolons
    normalized = normalized.rstrip(";")
    # Strip leading and trailing whitespaces
    normalized = normalized.strip()
    return normalized


def evaluate_model(args):
    """
    Evaluate the model performance.

    Args:
        args: input arguments from SageMaker pipeline.

    Returns:

    """
    logger.info("Decompressing model assets.")
    with tarfile.open(name=os.path.join(args.model_dir, "model.tar.gz"), mode="r:gz") as tar_file:
        os.makedirs(args.model_dir, exist_ok=True)
        tar_file.extractall(args.model_dir)

    logger.info(f"Decompressed Model assets: {os.listdir( args.model_dir )}")

    # Load test dataset
    test_dataset = load_from_disk(args.test_data_dir)
    if (
        args.dry_run != "False"
    ):  # Needs to be string matching because of way arguments are passed in SageMaker Processing Job
        test_dataset = test_dataset.select(range(8))
    # ensure that we do not have any trailing/leading whitespaces, this can lead to issues during inference
    test_data = test_dataset.map(lambda sample: {"prompt": sample["prompt"].strip()})
    logger.info("Loading test dataset")
    logger.info(f"Test dataset has {len( test_data )} samples")

    model = AutoModelForCausalLM.from_pretrained(args.model_dir, device_map="auto", torch_dtype=torch.float16)

    # Load the tokeinzer --> same model_dir
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)

    logger.info("Successfully loaded the model and tokenizer")

    predictions = []
    gt_queries = []
    pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, return_full_text=False)
    pipe.tokenizer.pad_token_id = model.config.eos_token_id
    for i, prediction in enumerate(
        tqdm(
            pipe(
                KeyDataset(test_data, "prompt"),
                max_new_tokens=args.max_new_tokens,
                do_sample=args.do_sample,
                temperature=args.temperature,
                top_k=args.top_k,
                top_p=args.top_p,
                repetition_penalty=args.repetition_penalty,
                batch_size=args.batch_size,
                pad_token_id=tokenizer.pad_token_id,
            ),
            desc="Generating Predictions",
        )
    ):
        predictions.extend(prediction)
        # gt_queries.append(samples["answer"][i])
        gt_queries.append(test_data["answer"][i])

    cleaned_predictions = [clean_prediction(prediction["generated_text"]) for prediction in predictions]

    prediction_result = [
        1 if normalise_string(prediction) == normalise_string(query) else 0
        for prediction, query in zip(cleaned_predictions, gt_queries)
    ]

    # compute accuracy
    accuracy = sum(prediction_result) / len(prediction_result)

    logger.info(f"Accuracy: {accuracy * 100:.2f}%")

    eval_report_dict = {"metrics": {"accuracy": {"value": accuracy, "standard_deviation": "NaN"}}}

    os.makedirs(args.output_dir, exist_ok=True)
    logger.info(
        f"""Writing out evaluation report with accuracy score: {accuracy}
        for a total number of samples of {len(prediction_result)}."""
    )
    evaluation_path = os.path.join(args.output_dir, "evaluation.json")

    with open(evaluation_path, "w") as f:
        f.write(json.dumps(eval_report_dict))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model_dir",
        type=str,
        default="/opt/ml/processing/model",
        help="Local path to load model",
    )
    parser.add_argument(
        "--test_data_dir",
        type=str,
        default="/opt/ml/processing/test",
        help="Local path to load test data",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="/opt/ml/processing/evaluation",
        help="Directory where output will be saved.",
    )
    parser.add_argument(
        "--max_new_tokens",
        type=int,
        default=256,
        help="Maximum number of new tokens to generate.",
    )
    parser.add_argument("--do_sample", default=True, help="Whether to use sampling for generation.")
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.001,
        help="Sampling temperature for generation.",
    )
    parser.add_argument("--top_k", type=int, default=50, help="Value of top-k sampling.")
    parser.add_argument("--top_p", type=float, default=0.95, help="Value of top-p sampling.")
    parser.add_argument(
        "--repetition_penalty",
        type=float,
        default=1.03,
        help="Repetition penalty for generation.",
    )
    parser.add_argument("--batch_size", type=int, default=6, help="Batch size for inference.")
    parser.add_argument(
        "--dry_run",
        type=str,
        default="True",
        help="Run with subset of data for testing",
    )

    args, _ = parser.parse_known_args()
    logger.info("Starting model evaluation...")
    evaluate_model(args)
