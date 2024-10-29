import glob

import torch
from transformers import AutoTokenizer, GPTJForCausalLM, pipeline

# Get the latest checkpoint path
checkpoint_path = list(glob.iglob("/ray/export/TorchTrainer_*/TorchTrainer_*/checkpoint_*/checkpoint"))[-1]

model = GPTJForCausalLM.from_pretrained(checkpoint_path)
tokenizer = AutoTokenizer.from_pretrained(checkpoint_path)

pipe = pipeline(
    model=model,
    tokenizer=tokenizer,
    task="text-generation",
    torch_dtype=torch.float16,
    device_map="auto",
)

# Generate from prompts!
for sentence in pipe(["Romeo and Juliet", "war", "blood"], do_sample=True, min_length=20):
    print(sentence)
