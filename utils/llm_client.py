import torch
import torch.cuda
import os
import re
import triton
import transformers
import accelerate
import warnings
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig, BitsAndBytesConfig, pipeline
from typing import List, Dict, Optional, Any, Union

# helpful defaults to avoid fragmentation & enable TF32 speedups on L40S
os.environ.setdefault("PYTORCH_ALLOC_CONF", "expandable_segments:True")

MAX_NEW_TOKEN = 4096
_MODEL_DICT_LLM = {
    'qwen2.5-coder-32b-instruct': ('Qwen/Qwen2.5-Coder-32B-Instruct', 32768),
    'qwen2.5-coder-14b-instruct': ('Qwen/Qwen2.5-Coder-14B-Instruct', 32768),
    'qwen2.5-coder-7b-instruct': ('Qwen/Qwen2.5-Coder-7B-Instruct', 32768),
    'qwen2.5-coder-3b-instruct': ('Qwen/Qwen2.5-Coder-3B-Instruct', 32768),

    'qwen2.5-32b-instruct': ('Qwen/Qwen2.5-32B-Instruct', 32768),
    'qwen2.5-14b-instruct': ('Qwen/Qwen2.5-14B-Instruct', 32768),
    'qwen2.5-7b-instruct': ('Qwen/Qwen2.5-7B-Instruct', 32768),
    'qwen2.5-3b-instruct': ('Qwen/Qwen2.5-3B-Instruct', 32768),

    'qwq-32b': ('Qwen/QwQ-32B', 131072),

    'qwen3-coder-30b-instruct': ('Qwen/Qwen3-Coder-30B-A3B-Instruct', 262144),
    'qwen3-30b-instruct': ('Qwen/Qwen3-30B-A3B-Instruct-2507', 131072),
    'qwen3-14b-instruct': ('Qwen/Qwen3-14B', 32768),
    'qwen3-8b-instruct': ('Qwen/Qwen3-8B', 131072),
    'qwen3-4b-instruct': ('Qwen/Qwen3-4B', 32768),

    'deepseek-coder-v2-instruct': ('deepseek-ai/DeepSeek-Coder-V2-Instruct', 131072),
    'deepseek-v2': ('deepseek-ai/DeepSeek-V2', 131072),
    'deepseek-v2.5': ('deepseek-ai/DeepSeek-V2.5', 131072),
    'deepseek-coder-v2-16b-instruct': ('deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct', 128000),
    'deepseek-coder-6.7b-instruct': ('deepseek-ai/deepseek-coder-6.7b-instruct', 16384),
    'deepseek-coder-33b-instruct': ('deepseek-ai/deepseek-coder-33b-instruct', 16384),
    'deepseek-v2-16b': ('deepseek-ai/DeepSeek-V2-Lite', 32768),
    'deepseek-r1-7b': ('deepseek-ai/DeepSeek-R1-Distill-Qwen-7B', 131072),
    'deepseek-r1-8b': ('deepseek-ai/DeepSeek-R1-Distill-Llama-8B', 131072),
    'deepseek-r1-14b': ('deepseek-ai/DeepSeek-R1-Distill-Qwen-14B', 131072),
    'deepseek-r1-32b': ('deepseek-ai/DeepSeek-R1-Distill-Qwen-32B', 131072),

    'gpt-oss-20b': ('openai/gpt-oss-20b', 131072),
    'gpt-oss-120b': ('openai/gpt-oss-120b', 131072),

    'codellama-7b-instruct': ('codellama/CodeLlama-7b-Instruct-hf', 16384),
    'codellama-13b-instruct': ('codellama/CodeLlama-13b-Instruct-hf', 16384),
    'codellama-34b-instruct': ('codellama/CodeLlama-34b-Instruct-hf', 16384),

    'llama3.2-1b-instruct': ('meta-llama/Llama-3.2-1B-Instruct', 131072),
    'llama3.2-3b-instruct': ('meta-llama/Llama-3.2-3B-Instruct', 131072),
    'llama3.1-8b-instruct': ('meta-llama/Llama-3.1-8B-Instruct', 131072),
    'llama3-8b-instruct': ('meta-llama/Meta-Llama-3-8B-Instruct', 8192),

    'codeqwen1.5-7b': ('Qwen/CodeQwen1.5-7B', 65536),
    'codeqwen1.5-7b-chat': ('Qwen/CodeQwen1.5-7B-Chat', 65536),
    'codegemma-7b': ('google/codegemma-7b', 8192),
    'codegemma-7b-it': ('google/codegemma-7b-it', 8192),
    'starcoder2-7b': ('bigcode/starcoder2-7b', 16384),
}

class TransformersClient:
    def __init__(self,llm_name):
        assert llm_name in _MODEL_DICT_LLM
        model_name, model_max_length = _MODEL_DICT_LLM[llm_name]

        self.model_name = llm_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=False)
        if self.tokenizer.pad_token is None:
            # reuse eos as pad
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.model_max_length = model_max_length
        self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = 'left'

        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=False,
            device_map="auto", # torch.device("cuda"),
            dtype="auto"
        )
        self.model.config.pad_token_id = self.tokenizer.pad_token_id
        self.model.generation_config.pad_token_id = self.tokenizer.pad_token_id

    def _build_prompt_text(self, messages_or_text):
        # If already a string, just return it
        if isinstance(messages_or_text, str):
            return messages_or_text

        # If it's a chat message list, use chat template when defined
        if getattr(self.tokenizer, "chat_template", None):
            return self.tokenizer.apply_chat_template(
                messages_or_text, tokenize=False, add_generation_prompt=True
            )

        # Fallback formatting for base models without a template
        parts = []
        for m in messages_or_text:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                parts.append(f"<<SYS>>\n{content}\n<</SYS>>")
            elif role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
        parts.append("Assistant:")
        return "\n".join(parts)

    @torch.inference_mode()
    def generate_text(self, prompt, model_settings = None):
        model_settings = model_settings or {}
        
        text = self._build_prompt_text(prompt)

        try:
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, return_token_type_ids=False)
        except TypeError:
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True)
        inputs.pop("token_type_ids", None)
        # move to model.device / GPU
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        output_ids = self.model.generate(**inputs, max_new_tokens=MAX_NEW_TOKEN, eos_token_id=self.tokenizer.eos_token_id, pad_token_id=self.tokenizer.pad_token_id, **model_settings)
        gen_only = output_ids[0][inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(gen_only, skip_special_tokens=True, clean_up_tokenization_spaces=False).strip()


def get_llm_client(llm_name):
    return TransformersClient(llm_name)
                     
def push_prompt(prompt:list, role:str, content:str):
    prompt.append({"role": role, "content": content})
    return prompt

def remove_thinking(text:str):
    return re.sub(r"<think>.*?</think>", "", text)

def generate_simple_prompt(prompt:str):
    return [{"role": "user", "content": prompt}]

def parse_kv_string_to_dict(
        key_value_string: str, 
        arg_sep: str = ";",
        kv_sep: str = "="
    ) -> dict:
    """
    This function parses a key-value string argument into a dictionary.
    The input string should have key-value pairs separated by 'arg_sep' (default is ';')
    and keys and values separated by 'kv_sep' (default is '=').
    For example, the string "key1=value1;key2=value2" will be parsed into the dictionary
    {"key1": "value1", "key2": "value2"}.
    The function also attempts to convert the values to int, float, or boolean types if possible.
    """
    key_value_list = key_value_string.split(arg_sep)
    key_value_dict = {}
    for key_value in key_value_list:
        try:
            key, value_str = key_value.split(kv_sep, 1)
        except ValueError:
            # logging.warning(f"Skipping invalid key-value pair: {key_value}")
            print(f"Skipping invalid key-value pair: {key_value}")
            continue
        key = key.strip()
        value_str = value_str.strip()
        try:
            value = int(value_str)
        except ValueError:
            try:
                value = float(value_str)
            except ValueError:
                if value_str.lower() == "true":
                    value = True
                elif value_str.lower() == "false":
                    value = False
                else:
                    value = value_str
        key_value_dict[key] = value
    return key_value_dict

def extract_LLM_response_by_prefix(response: str, prefix: str) -> str:
    """
    This function extracts the response from the LLM output that is prefixed by a given string.
    """
    if prefix in response:
        return response.split(prefix)[1].strip()
    else:
        return response.strip()


if __name__ == "__main__":
    print(f"PyTorch version:     {torch.__version__}")
    print(f"Transformers version: {transformers.__version__}")
    print(f"Triton version:       {triton.__version__}")
    client = TransformersClient("gpt-oss-20b")

    messages = [
    {"role": "user", "content": "Explain in one sentence what MXFP4 quantization is."},]
    out = client.generate_text(messages)
    print(out)
