import argparse
import logging

from data_processing import CodeLlamaDataProcessor

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


def preprocess(args):
    """
    Preprocess the dataset and save it to disk.

    Args:
        args: input arguments from SageMaker pipeline

    Returns:

    """
    dataset = CodeLlamaDataProcessor.load_hf_dataset(dataset_name=args.dataset_name)

    data_processor_training = CodeLlamaDataProcessor(dataset=dataset["train"], is_training=True)
    dataset_processor_test = CodeLlamaDataProcessor(dataset=dataset["validation"], is_training=False)

    logger.info("Processing training dataset.")
    dataset_train = data_processor_training.prepare_data()

    logger.info("Processing test dataset.")
    dataset_test = dataset_processor_test.prepare_data()

    if (
        args.dry_run != "False"
    ):  # Needs to be string matching because of way arguments are passed in SageMaker Processing Job
        logger.info(
            """Dry run, only processing a couple of examples for testing and demonstration.
            If this is not intended, please set the flag dry_run to False."""
        )
        dataset_train = dataset_train.select(range(12))
        dataset_test = dataset_test.select(range(8))

    logger.info(f"Writing out datasets to {args.train_data_path} and {args.test_data_path}")
    dataset_train.save_to_disk(args.train_data_path)
    dataset_test.save_to_disk(args.test_data_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # add model id and dataset path argument
    parser.add_argument(
        "--dataset_name",
        type=str,
        default="philikai/Spider-SQL-LLAMA2_train",
        help="HuggingFace dataset to use",
    )
    parser.add_argument(
        "--train_data_path",
        type=str,
        default="/opt/ml/processing/train",
        help="Local path to save train data",
    )
    parser.add_argument(
        "--test_data_path",
        type=str,
        default="/opt/ml/processing/test",
        help="Local path to save test data",
    )
    parser.add_argument(
        "--dry_run",
        type=str,
        default="True",
        help="Run with subset of data for testing",
    )

    args, _ = parser.parse_known_args()
    logger.info("Starting preprocessing")
    preprocess(args)
