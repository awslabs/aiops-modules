import logging
from functools import partial
from itertools import chain
from typing import Any, Dict

from datasets import Dataset, load_dataset
from transformers import AutoTokenizer

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


# Code adapted from:


class CodeLlamaDataProcessor:
    PROMPT_TEMPLATE = """
    ### Instruction
    Given an input question, use SQLite syntax to generate a SQL query by choosing one or
    multiple of the following tables.
    The foreign and primary keys will be supplied. Write the query in between <SQL></SQL>.
    Answer the following question with the context below:
    {question}

    ### Context
    {schema} | {foreign_keys} | {primary_keys}

    ### Answer
    {query}
    {eos_token}
    """
    REMAINDER: Dict[str, Any] = {"input_ids": [], "attention_mask": [], "token_type_ids": []}
    MODEL_ID: str = "codellama/CodeLlama-7b-hf"
    TOKENIZER: Any = AutoTokenizer.from_pretrained(MODEL_ID)

    def __init__(self, dataset: Dataset, is_training: bool):
        self.dataset = dataset
        self.is_training = is_training

    @staticmethod
    def load_hf_dataset(dataset_name: str) -> Any:
        if isinstance(dataset_name, str):
            try:
                dataset = load_dataset(dataset_name)
                logger.info("Dataset loaded successfully.")
            except Exception as e:
                logger.info(f"Failed to load dataset: {e}")
                raise RuntimeError(f"Failed to load dataset: {e}")
        else:
            raise TypeError("Dataset is not a string.")

        return dataset

    def _assemble_prompt(self, sample: Dict[str, Any]) -> str:
        prompt = self.PROMPT_TEMPLATE.format(
            question=sample["question"],
            schema=sample["schema"],
            foreign_keys=sample["foreign_keys"],
            primary_keys=sample["primary_keys"],
            query=f"<SQL> {sample['query']} </SQL>" if self.is_training else "",
            eos_token=self.TOKENIZER.eos_token if self.is_training else "",
        )
        return prompt

    def template_dataset(self, sample: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self._assemble_prompt(sample=sample)
        sample["prompt"] = prompt.strip()

        if not self.is_training:
            sample["answer"] = sample["query"]
        return sample

    @classmethod
    def _chunk(cls, sample: Dict[str, Any], chunk_length: int) -> Any:
        concatenated_examples = {k: list(chain(*sample[k])) for k in sample.keys()}
        concatenated_examples = {k: cls.REMAINDER[k] + concatenated_examples[k] for k in concatenated_examples.keys()}

        batch_total_length = len(concatenated_examples[list(sample.keys())[0]])
        if batch_total_length >= chunk_length:
            batch_chunk_length = (batch_total_length // chunk_length) * chunk_length
        else:
            raise ValueError("Batch length is less than chunk length.")

        result = {
            k: [t[i : i + chunk_length] for i in range(0, batch_chunk_length, chunk_length)]
            for k, t in concatenated_examples.items()
        }
        cls.REMAINDER = {k: concatenated_examples[k][batch_chunk_length:] for k in concatenated_examples.keys()}
        result["labels"] = result["input_ids"].copy()
        return result

    @classmethod
    def chunk_and_tokenize(cls, prompt_dataset: Dataset, chunk_length: int) -> Any:
        chunked_tokenized_dataset = prompt_dataset.map(
            lambda sample: cls.TOKENIZER(sample["prompt"]),
            batched=True,
            remove_columns=list(prompt_dataset.features),
        ).map(
            partial(cls._chunk, chunk_length=chunk_length),
            batched=True,
        )
        return chunked_tokenized_dataset

    def _get_sample_prompts(self) -> Any:
        prompt_dataset = self.dataset.map(self.template_dataset, remove_columns=list(self.dataset.features))
        return prompt_dataset

    def prepare_data(self) -> Any:
        return self._get_sample_prompts()
