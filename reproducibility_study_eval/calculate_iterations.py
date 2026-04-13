import os
import json
import pandas as pd
import numpy as np
import argparse

# distinguish between the two different types of prompts:
#   Detect (Cause Analysis): Checking if the code matches a known vulnerability pattern.
#   Sol (Fixing Analysis): Checking if the code is missing the required fix.

# Configuration
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

def process_iterations(model_name, base_path="output"):
    model_dir = os.path.join(base_path, model_name)
    if not os.path.exists(model_dir):
        print(f"Error: Folder {model_dir} not found.")
        return None

    cwe_results = []
    raw_logs = [] 

    for dataset in DATASETS:
        filename = f"{dataset}_result_{model_name}.json"
        file_path = os.path.join(model_dir, filename)
        cwe_label = dataset.split('_')[-1]
        
        if not os.path.exists(file_path):
            continue

        with open(file_path, 'r') as f:
            data = json.load(f)

        v_iters = []   # Vulnerable iterations
        nv_iters = []  # Non-Vulnerable iterations

        for item in data:
            # Before (Vulnerable)
            if "detect_result_before" in item:
                count = len(item["detect_result_before"].get("detect_result", []))

                v_iters.append(count)
                raw_logs.append({"CWE": cwe_label, "Class": "Vulnerable", "Iterations": count})

            # After (Non-Vulnerable)
            if "detect_result_after" in item:
                count = len(item["detect_result_after"].get("detect_result", []))

                nv_iters.append(count)
                raw_logs.append({"CWE": cwe_label, "Class": "Non-Vulnerable", "Iterations": count})

        # Calculate Stats for this CWE
        if v_iters or nv_iters:
            mean_v = np.mean(v_iters) if v_iters else 0
            mean_nv = np.mean(nv_iters) if nv_iters else 0
            cwe_results.append({
                "CWE": cwe_label,
                "Mean Iters (Vuln)": mean_v,
                "Mean Iters (Non-V)": mean_nv,
                "Max Iters (Vuln)": np.max(v_iters) if v_iters else 0,
                "Max Iters (Non-V)": np.max(nv_iters) if nv_iters else 0,
                "Total Calls (Avg)": (mean_v + mean_nv) # 1 Iter = 2 Calls, so (V+NV)/2 * 2
            })

    df = pd.DataFrame(cwe_results)

    # Add Overall Row
    overall_means = df.mean(numeric_only=True).to_dict()
    overall_means["CWE"] = "OVERALL"
    # We want the absolute maximum found across all CWEs for the overall row
    overall_means["Max Iters (Vuln)"] = df["Max Iters (Vuln)"].max()
    overall_means["Max Iters (Non-V)"] = df["Max Iters (Non-V)"].max()
    
    df = pd.concat([df, pd.DataFrame([overall_means])], ignore_index=True)

    # Save detailed log for plotting
    pd.DataFrame(raw_logs).to_csv(f"iteration_dist_{model_name}.csv", index=False)
    
    return df

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('model_name', type=str)
    args = parser.parse_args()

    df = process_iterations(args.model_name)

    if df is not None:
        print(f"\nVUL-RAG ITERATION ANALYSIS: {args.model_name}")
        print("Note: One iteration includes 1 Detect call and 1 Sol call.")
        print("-" * 110)
        # Reorder and format
        cols = [
            "CWE", 
            "Mean Iters (Vuln)", "Max Iters (Vuln)", 
            "Mean Iters (Non-V)", "Max Iters (Non-V)", 
            "Total Calls (Avg)"
        ]
        print(df[cols].round(2).to_string(index=False))
        print("-" * 110)
        print(f"Distribution data saved to: iteration_dist_{args.model_name}.csv")

if __name__ == "__main__":
    main()