import os
import json
import pandas as pd
import numpy as np
import argparse
import importlib.util
from transformers import AutoTokenizer

# --- DYNAMIC LOADING SECTION ---
# This looks for the dict in vul-rag/utils/llm_client.py
def load_model_dict():
    file_path = "/beegfs/scratch/workspace/es_sakaniew-rag_benchmark/vul-rag/utils/llm_client.py"
    if not os.path.exists(file_path):
        print(f"Warning: Could not find {file_path}. Falling back to empty dictionary.")
        return {}

    # Load the module from the file path
    spec = importlib.util.spec_from_file_location("llm_client", file_path)
    llm_client = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(llm_client)
        return getattr(llm_client, "_MODEL_DICT_LLM", {})
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return {}

_MODEL_DICT_LLM = load_model_dict()
DATASETS = [
    "linux_kernel_CWE-20",
    "linux_kernel_CWE-119",
    "linux_kernel_CWE-125",
    "linux_kernel_CWE-200",
    "linux_kernel_CWE-264",
    "linux_kernel_CWE-362",
    "linux_kernel_CWE-401",
    "linux_kernel_CWE-416",
    "linux_kernel_CWE-476",
    "linux_kernel_CWE-787"
]

def get_token_count(tokenizer, text):
    if not text or not isinstance(text, str):
        return 0
    # Use fast tokenizer and avoid adding special tokens to get a raw count
    return len(tokenizer.encode(text, add_special_tokens=False))

def process_token_stats(model_dir_name, llm_key, base_path="output"):
    if llm_key not in _MODEL_DICT_LLM:
        print(f"Error: {llm_key} not found in the loaded _MODEL_DICT_LLM.")
        return None
    
    hf_path, _ = _MODEL_DICT_LLM[llm_key]
    print(f"Loading tokenizer for {hf_path}...")
    tokenizer = AutoTokenizer.from_pretrained(hf_path, trust_remote_code=False)
    
    model_path = os.path.join(base_path, model_dir_name)
    all_data = []

    for dataset in DATASETS:
        filename = f"{dataset}_result_{model_dir_name}.json"
        file_path = os.path.join(model_path, filename)
        cwe_label = dataset.split('_')[-1]

        if not os.path.exists(file_path):
            continue

        with open(file_path, 'r') as f:
            data = json.load(f)

        for item in data:
            # Iterating through Before (Vulnerable) and After (Non-Vulnerable)
            for state_key, class_label in [("detect_result_before", "Vulnerable"), 
                                           ("detect_result_after", "Non-Vulnerable")]:
                
                if state_key in item:
                    # 'detect_result' is the array of iterative reasoning steps
                    iterations = item[state_key].get("detect_result", [])
                    for it in iterations:
                        # Extract tokens for the Detection Prompt and Output
                        d_p = get_token_count(tokenizer, it.get("vul_detect_prompt", ""))
                        d_a = get_token_count(tokenizer, it.get("vul_output", ""))
                        
                        # Extract tokens for the Solution Prompt and Output
                        s_p = get_token_count(tokenizer, it.get("sol_detect_prompt", ""))
                        s_a = get_token_count(tokenizer, it.get("sol_output", ""))

                        # Add results to our list
                        all_data.append({"CWE": cwe_label, "Class": class_label, "Phase": "Detect", "Side": "Prompt", "Tokens": d_p})
                        all_data.append({"CWE": cwe_label, "Class": "Vulnerable" if class_label=="Vulnerable" else "Non-Vulnerable", "Phase": "Detect", "Side": "Answer", "Tokens": d_a})
                        all_data.append({"CWE": cwe_label, "Class": class_label, "Phase": "Solution", "Side": "Prompt", "Tokens": s_p})
                        all_data.append({"CWE": cwe_label, "Class": class_label, "Phase": "Solution", "Side": "Answer", "Tokens": s_a})

    return pd.DataFrame(all_data)

def display_table(df):
    # Pivot the data
    summary = df.groupby(['CWE', 'Phase', 'Class', 'Side'])['Tokens'].agg(['min', 'mean', 'max']).reset_index()
    
    # Calculate Overall Stats (Across all CWEs)
    overall = df.groupby(['Phase', 'Class', 'Side'])['Tokens'].agg(['min', 'mean', 'max']).reset_index()
    overall.insert(0, 'CWE', 'OVERALL')
    
    final = pd.concat([summary, overall], ignore_index=True)
    
    # Rounding means for the console
    final['mean'] = final['mean'].round(1)
    
    return final

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('model_dir', type=str, help="Folder name in output/")
    parser.add_argument('llm_key', type=str, help="Key in MODEL_DICT (e.g. qwen2.5-coder-32b-instruct)")
    args = parser.parse_args()

    raw_df = process_token_stats(args.model_dir, args.llm_key)
    
    if raw_df is not None and not raw_df.empty:
        summary_table = display_table(raw_df)
        
        print(f"\nTOKEN USAGE BREAKDOWN: {args.model_dir}")
        print("="*100)
        # cleaner view
        view = summary_table.sort_values(['CWE', 'Phase', 'Class'])
        print(view.to_string(index=False))
        print("="*100)
        
        # Save to CSV
        output_csv = f"token_usage_{args.model_dir.replace('/', '_')}.csv"
        summary_table.to_csv(output_csv, index=False)
        print(f"Results saved to {output_csv}")

if __name__ == "__main__":
    main()