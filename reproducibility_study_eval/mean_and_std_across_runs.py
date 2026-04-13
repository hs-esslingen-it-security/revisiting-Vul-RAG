import os
import json
import pandas as pd
import numpy as np
import argparse

# Configuration
BASE_PATH = "output"
SAVE_DIR = "results_summary"
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

def load_json(path):
    if os.path.exists(path):
        with open(path, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not decode JSON in {path}")
                return None
    return None

def format_stat(mean, std):
    """Formats mean and std into a single string: 0.1234 (±0.01)"""
    if np.isnan(mean):
        return "N/A"
    return f"{mean:.4f} (±{std:.4f})"

def process_model_results(model_name):
    model_dir = os.path.join(BASE_PATH, model_name)
    
    if not os.path.exists(model_dir):
        print(f"Error: Model folder '{model_dir}' does not exist.")
        return None

    # Define the three run metric directories
    runs = [
        os.path.join(model_dir, "metrics"),
        os.path.join(model_dir, "r2", "metrics"),
        os.path.join(model_dir, "r3", "metrics")
    ]

    # 1. Extract Total Metrics
    total_metrics_list = []
    for run_path in runs:
        file_path = os.path.join(run_path, "total_metrics.json")
        data = load_json(file_path)
        if data:
            total_metrics_list.append(data)

    if not total_metrics_list:
        print(f"Error: No 'total_metrics.json' files found in {model_name} runs.")
        return None

    print(f"Found {len(total_metrics_list)} runs for {model_name}")

    # Helper to get mean/std for a specific key
    def get_stats(key, data_list):
        values = [d[key] for d in data_list if key in d]
        return np.mean(values), np.std(values, ddof=1) #np.std(values)

    m_acc, s_acc = get_stats('pair_accuracy', total_metrics_list)
    m_rec, s_rec = get_stats('recall', total_metrics_list)
    m_pre, s_pre = get_stats('precision', total_metrics_list)
    mean_pairs = np.mean([d['pair_total'] for d in total_metrics_list])

    # 2. Extract CWE-specific Pair Accuracies
    cwe_results = {}
    for dataset in DATASETS:
        cwe_values = []
        for run_path in runs:
            filename = f"{dataset}_result_{model_name}_metrics.json"
            file_path = os.path.join(run_path, filename)
            data = load_json(file_path)
            if data and 'pair_accuracy' in data:
                cwe_values.append(data['pair_accuracy'])
        
        column_name = dataset.split('_')[-1] # e.g. "CWE-20"
        if cwe_values:
            cwe_results[column_name] = format_stat(np.mean(cwe_values), np.std(cwe_values, ddof=1))
        else:
            cwe_results[column_name] = "N/A"

    row = {
        "Detect Model": model_name,
        "Pair. Accuracy": format_stat(m_acc, s_acc),
        "Recall": format_stat(m_rec, s_rec),
        "Precision": format_stat(m_pre, s_pre),
        "Pairs": int(mean_pairs)
    }
    row.update(cwe_results)
    
    return row

def main():
    parser = argparse.ArgumentParser(description='Calculate mean and std metrics for a model.')
    parser.add_argument('model_name', type=str, help='The folder name inside "output/"')
    
    args = parser.parse_args()
    model_name = args.model_name

    result_row = process_model_results(model_name)
    
    if result_row:
        if not os.path.exists(SAVE_DIR):
            os.makedirs(SAVE_DIR)
        df = pd.DataFrame([result_row])

        # Define Column Order
        cwe_cols = [d.split('_')[-1] for d in DATASETS]
        column_order = ["Detect Model", "Pair. Accuracy", "Recall", "Precision", "Pairs"] + cwe_cols
        
        final_cols = [c for c in column_order if c in df.columns]
        df = df[final_cols]

        # Print to Console
        print(f"\nResults for {model_name}:")
        print(df.to_string(index=False))

        # # Save to CSV
        # csv_path = os.path.join(SAVE_DIR, f"{model_name}_metrics.csv")
        # df.to_csv(csv_path, index=False)
        
        # # Save to Text File (Pretty Table)
        # txt_path = os.path.join(SAVE_DIR, f"{model_name}_table.txt")
        # with open(txt_path, "w", encoding="utf-8") as f:
        #     f.write(f"Results for model: {model_name}\n")
        #     f.write("-" * 50 + "\n")
        #     f.write(df.to_string(index=False))

        # print(f"\n[Files Saved]")
        # print(f"CSV: {csv_path}")
        # print(f"TXT: {txt_path}")

if __name__ == "__main__":
    main()