import os
import sys
import json
import re

os.environ["CUDA_VISIBLE_DEVICES"] = "1,2"

import fire
import torch
import transformers
from peft import PeftModel
from transformers import GenerationConfig, LlamaForCausalLM, LlamaTokenizer
from tqdm import tqdm

from utils.sap.alpaca_lora_utils.prompter import Prompter

if torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"

try:
    if torch.backends.mps.is_available():
        device = "mps"
except:  # noqa: E722
    pass


def main(
        load_8bit: bool = False,
        base_model: str = "decapoda-research/llama-7b-hf",# decapoda-research/llama-13b-hf
        lora_weights: str = "tloen/alpaca-lora-7b",# chansung/gpt4-alpaca-lora-13b、tloen/alpaca-lora-7b
        prompt_template: str = "",  # The prompt template to use, will default to alpaca.
        data_path: str = "GPT_50",  # GPT_50 or heuristic_100
        output_file_name: str = "alpaca_finetune"  # alpaca or alpaca_finetune
):
    base_model = base_model or os.environ.get("BASE_MODEL", "")
    assert (base_model), "Please specify a --base_model, e.g. --base_model='huggyllama/llama-7b'"

    prompter = Prompter(prompt_template)
    tokenizer = LlamaTokenizer.from_pretrained(base_model)
    if device == "cuda":
        model = LlamaForCausalLM.from_pretrained(
            base_model,
            load_in_8bit=load_8bit,
            torch_dtype=torch.float16,
            device_map="auto",
        )
        model = PeftModel.from_pretrained(
            model,
            lora_weights,
            torch_dtype=torch.float16,
        )
    elif device == "mps":
        model = LlamaForCausalLM.from_pretrained(
            base_model,
            device_map={"": device},
            torch_dtype=torch.float16,
        )
        model = PeftModel.from_pretrained(
            model,
            lora_weights,
            device_map={"": device},
            torch_dtype=torch.float16,
        )
    else:
        model = LlamaForCausalLM.from_pretrained(base_model, device_map={"": device}, low_cpu_mem_usage=True)
        model = PeftModel.from_pretrained(
            model,
            lora_weights,
            device_map={"": device},
        )

    # unwind broken decapoda-research config
    model.config.pad_token_id = tokenizer.pad_token_id = 0  # unk
    model.config.bos_token_id = 1
    model.config.eos_token_id = 2

    if not load_8bit:
        model.half()  # seems to fix bugs for some users.

    model.eval()
    if torch.__version__ >= "2" and sys.platform != "win32":
        model = torch.compile(model)

    def evaluate(
        instruction,
        input=None,
        temperature=0.1,
        top_p=0.75,
        top_k=40,
        num_beams=4,
        max_new_tokens=256,
        **kwargs,
    ):
        prompt = prompter.generate_prompt(instruction, input)
        inputs = tokenizer(prompt, return_tensors="pt")
        input_ids = inputs["input_ids"].to(device)
        generation_config = GenerationConfig(
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            num_beams=num_beams,
            **kwargs,
        )

        with torch.no_grad():
            generation_output = model.generate(
                input_ids=input_ids,
                generation_config=generation_config,
                return_dict_in_generate=True,
                output_scores=True,
                max_new_tokens=max_new_tokens,
            )
        s = generation_output.sequences[0]
        output = tokenizer.decode(s)
        return prompter.get_response(output)

    with open(f"./data/{data_path}/generated_cases.json", mode='r', encoding="utf8") as f:
        cases = json.load(f)

    results = list()
    for case in tqdm(cases):
        match = re.search(r'###(.*?)###', case, re.DOTALL)
        content = match.group(1)
        result = evaluate(content)
        results.append(result)

    if not os.path.exists(f'./data/{data_path}/{output_file_name}/'):
        os.makedirs(f'./data/{data_path}/{output_file_name}/')

    with open(f'./data/{data_path}/{output_file_name}/{output_file_name}_output.json', 'w', encoding="utf8") as file:
        json.dump(
            results,
            file,
            ensure_ascii=False,
        )


if __name__ == "__main__":
    fire.Fire(main)
