import json
import os
import sys
import argparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import utils.llm_client as llm_client
from tqdm import tqdm
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
import time
import re
from functools import wraps

MODEL_CLIENT = None

output_lock = threading.Lock()
file_lock = threading.Lock()

def retry_on_failure(max_retries: int = 5, delay: float = 1.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1: 
                        print(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                        time.sleep(delay)
                    continue
            raise last_exception 
        return wrapper
    return decorator

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_file_name", type=str, required=True)
    # parser.add_argument("--output_file_name", type=str, required=True)
    parser.add_argument("--model_name", type=str, required=True)
    parser.add_argument(
        '--model_settings',
        type = str,
        default = None,
        help = (
            'The settings of the model, format is a key-value pair separated by ";". '
            'e.g. "temperature=0.2;max_tokens=1024;stream=true"'
        )
    )
    parser.add_argument(
        '--thread_pool_size',
        type = int,
        default = 1,
        help = "Size of thread pool when detecting"
    )
    parser.add_argument(
        '--retry_time',
        type = int,
        default = 2,
        help = "Number of retries when API call fails"
    )
    parser.add_argument(
        '--resume',
        action = 'store_true',
        help = 'Whether to resume from a checkpoint.'
    )
    args = parser.parse_args()
    args.model_settings = llm_client.parse_kv_string_to_dict(args.model_settings)
    return args

def generate_extract_prompt(CVE_id, CVE_description, modified_lines, code_before_change, code_after_change):
    prefix_str = f"""This is a code snippet with a vulnerability {CVE_id}:
'''
{code_before_change}
'''
The vulnerability is described as follows:
{CVE_description}
"""

    # extract purpose prompt
    purpose_prompt = f"""{prefix_str}
What is the purpose of the function in the above code snippet? \
Please summarize the answer in one sentence with following format: Function purpose: \"\"
"""

    # extract function prompt
    function_prompt = f"""{prefix_str}
Please summarize the functions of the above code snippet in the list format without other \
explanation: \"The functions of the code snippet are: 1. 2. 3.\"
"""

    # extract analysis prompt
    analysis_prompt = f"""{prefix_str}
The correct way to fix it is by adding/deleting\n'''\n{modified_lines}\n'''\n."""

    if modified_lines["added"] != []:
        analysis_prompt += f"""The code after modification is as follows:\n'''\n{code_after_change}\n'''\n"""

    analysis_prompt += """Why is the above modification necessary?"""

    knowledge_extraction_prompt = """
I want you to act as a vulnerability detection expert and organize vulnerability knowledge based on the above \
vulnerability repair information. Please summarize the generalizable specific behavior of the code that \
leads to the vulnerability and the specific solution to fix it. Format your findings in JSON.
Here are some examples to guide you on the level of detail expected in your extraction:
Example 1:
{
    "vulnerability_behavior": {
        "preconditions_for_vulnerability": "Lack of proper handling for asynchronous events during device removal process.",
        "trigger_condition": "A physically proximate attacker unplugs a device while the removal function is executing, \
leading to a race condition and use-after-free vulnerability.",
        "specific_code_behavior_causing_vulnerability": "The code does not cancel pending work associated with a specific \
functionality before proceeding with further cleanup during device removal. This can result in a use-after-free scenario if \
the device is unplugged at a critical moment."
    }, 
    "solution": "To mitigate the vulnerability, it is necessary to cancel any pending work related to the specific \
functionality before proceeding with further cleanup during device removal. This ensures that the code handles asynchronous \
events properly and prevents the use-after-free vulnerability. In this case, the solution involves adding a line to cancel the \
pending work associated with the specific functionality before continuing with the cleanup process."
}
Note that in the "solution" field of your response's JSON, the solution should be described in natural language format. Do not nest dictionaries or arrays within the "solution" field. Plus, do not nest within other field either. Your answer should be exactly the same format as the example we provide.
Please be mindful to omit specific resource names in your descriptions to ensure the knowledge remains generalized. \
For example, instead of writing mutex_lock(&dmxdev->mutex), simply use mutex_lock.
"""

    return purpose_prompt, function_prompt, analysis_prompt, knowledge_extraction_prompt


## had problems such as: Error occurred while processing item 1079: Expecting property name enclosed in double quotes: line 2 column 9 (char 37); 
## Error occurred while processing item 198: Expecting ':' delimiter: line 1 column 26 (char 25)

# def get_dict(vul_knowledge_output):
#     # Extract content after "vulnerability_behavior"
#     vul_knowledge_output = vul_knowledge_output.split("\"vulnerability_behavior\"")[-1] # use [-1] (last item) instead of [1]
#     vul_knowledge_output = "{\"vulnerability_behavior\"" + vul_knowledge_output
#     if "\n```" in vul_knowledge_output:
#         vul_knowledge_output = vul_knowledge_output.split("\n```")[0]
#     return json.loads(vul_knowledge_output)

# enhanced dict parsing
def get_dict(vul_knowledge_output):
    # try to find the first '{' and last '}'
    match = re.search(r'(\{.*\})', vul_knowledge_output, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in LLM output")
    
    json_str = match.group(1)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        try:
            # Replace single quotes with double quotes, then try again
            fixed_json = json_str.replace("'", '"')
            return json.loads(fixed_json)
        except:
            raise json.JSONDecodeError("Failed to parse JSON", json_str, 0)



def extract_knowledge(args, item, output_data: List[Dict[str, Any]]) -> None:
    try:
        global MODEL_CLIENT
        
        def generate_with_retry(prompt_dict, settings):
            last_exception = None
            for attempt in range(args.retry_time):
                try:
                    return MODEL_CLIENT.generate_text(prompt_dict, settings)
                except Exception as e:
                    last_exception = e
                    if attempt < args.retry_time - 1:
                        print(f"Attempt {attempt + 1}/{args.retry_time} failed: {str(e)}")
                        time.sleep(1.0)
                    continue
            raise last_exception

        purpose_prompt, function_prompt, analysis_prompt, knowledge_extraction_prompt = generate_extract_prompt(
            item["cve_id"], 
            item["cve_description"], 
            item["function_modified_lines"], 
            item["code_before_change"], 
            item["code_after_change"]
        )

        purpose_prompt_dict = llm_client.generate_simple_prompt(purpose_prompt)
        # print(purpose_prompt_dict)
        purpose_output = generate_with_retry(purpose_prompt_dict, args.model_settings)
        # print("get purpose output")

        function_prompt_dict = llm_client.generate_simple_prompt(function_prompt)
        function_output = generate_with_retry(function_prompt_dict, args.model_settings)
        # print("get function output")

        messages = llm_client.generate_simple_prompt(analysis_prompt)
        analysis_output = generate_with_retry(messages, args.model_settings)
        # print("get analysis output")

        messages.append({"role": "assistant", "content": analysis_output})
        messages.append({"role": "user", "content": knowledge_extraction_prompt})
        #print("get knowledge extraction prompt")
        #print(knowledge_extraction_prompt)
        
        knowledge_extraction_output = generate_with_retry(messages, args.model_settings)
        #print("get knowledge extraction output")
        #print(knowledge_extraction_output)
        #vul_knowledge_output = knowledge_extraction_output.split("\"vulnerability_behavior\"")[-1]
        #print(vul_knowledge_output)

        output_dict = get_dict(knowledge_extraction_output)
        output_dict["GPT_analysis"] = analysis_output
        output_dict["GPT_purpose"] = llm_client.extract_LLM_response_by_prefix(
                        purpose_output,
                        "Function purpose:"
                    )
        output_dict["GPT_function"] = llm_client.extract_LLM_response_by_prefix(
                        function_output,
                        "The functions of the code snippet are:"
                    )
        
        output_dict["CVE_id"] = item["cve_id"]
        output_dict["id"] = item["id"]
        output_dict["code_before_change"] = item["code_before_change"]
        output_dict["code_after_change"] = item["code_after_change"]
        output_dict["modified_lines"] = item["function_modified_lines"]

        if "solution" in output_dict["vulnerability_behavior"]:
            output_dict["solution"] = output_dict["vulnerability_behavior"]["solution"]
        
        output_dict["preconditions_for_vulnerability"] = output_dict["vulnerability_behavior"]["preconditions_for_vulnerability"]
        output_dict["trigger_condition"] = output_dict["vulnerability_behavior"]["trigger_condition"]
        output_dict["specific_code_behavior_causing_vulnerability"] = output_dict["vulnerability_behavior"]["specific_code_behavior_causing_vulnerability"]

        with output_lock:
            output_data.append(output_dict)
            with file_lock:
                with open(f"add_vulnerability_knowledge/{args.model_name}/{args.input_file_name}", "w") as f:
                    json.dump(output_data, f, indent=4)
    except Exception as e:
        print(f"Error occurred while processing item {item['id']}: {str(e)}")
        return

def process_item(args, item, output_data):
    if item["id"] not in resume_set:
        extract_knowledge(args, item, output_data)

def extract_knowledge_pipeline(args):
    global MODEL_CLIENT, resume_set
    MODEL_CLIENT = llm_client.get_llm_client(args.model_name)
    print(MODEL_CLIENT.model_name)
    
    # normalize the output filename to use _knowledge.json
    base_prefix = args.input_file_name.replace(".json", "").replace("_data", "")
    output_filename = f"{base_prefix}_knowledge.json"

    # output directory and file path
    output_dir = os.path.join("add_vulnerability_knowledge", args.model_name)
    output_file_path = os.path.join(output_dir, output_filename)

    if not os.path.exists(output_dir):
        print(f"Creating directory: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)


    with open(f"data/train/{args.input_file_name}", "r") as f:
        data = json.load(f)
    
    output_data = []
    resume_set = set()
    
    if args.resume:
        if os.path.exists(output_file_path):
            with open(output_file_path, "r") as f:
                output_data = json.load(f)
                resume_set = set([item["id"] for item in output_data])
    
    with ThreadPoolExecutor(max_workers=args.thread_pool_size) as executor:
        list(tqdm(
            executor.map(
                lambda item: process_item(args, item, output_data),
                data
            ),
            total=len(data)
        ))

if __name__ == "__main__":
    args = parse_args()
    extract_knowledge_pipeline(args)

