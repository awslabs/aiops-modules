import torch
import torchvision

from transformers import pipeline, AutoTokenizer, GPTJForCausalLM

model = GPTJForCausalLM.from_pretrained("/ray/export/.../checkpoint")
tokenizer = AutoTokenizer.from_pretrained("/ray/export/.../checkpoint")

pipe = pipeline(
    model=model,
    tokenizer=tokenizer,
    task="text-generation",
    torch_dtype=torch.float16,
    device_map="auto",
)

# Generate from prompts!
for sentence in pipe(
    ["Romeo and Juliet", "war", "blood"], do_sample=True, min_length=20
):
    print(sentence)
