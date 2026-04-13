#!/bin/bash

# -----------------------------
# Configuration
# -----------------------------
MODEL="$1"

DATASETS=(
  "linux_kernel_CWE-20"
  "linux_kernel_CWE-119"
  "linux_kernel_CWE-125"
  "linux_kernel_CWE-200"
  "linux_kernel_CWE-264"
  "linux_kernel_CWE-362"
  "linux_kernel_CWE-401"
  "linux_kernel_CWE-416"
  "linux_kernel_CWE-476"
  "linux_kernel_CWE-787"
)

# -----------------------------
# Iterate over combinations
# -----------------------------
echo "============================================================"
echo "Starting Knowledge Extraction for Model: ${MODEL}"
echo "============================================================"

for DATASET in "${DATASETS[@]}"; do
  INPUT_FILE="${DATASET}_data.json"
  
  echo "------------------------------------------------------------"
  echo "Processing Dataset: ${INPUT_FILE}"
  echo "Model:              ${MODEL}"
  echo "------------------------------------------------------------"

  # Run the extraction script
  python src/extract_knowledge.py \
    --input_file_name "${INPUT_FILE}" \
    --model_name "${MODEL}" \
    --thread_pool_size 1 \
    --model_settings "temperature=0.01" \
    --resume

  echo "Finished processing ${DATASET}"
done

echo "🎯 Knowledge generation finished for all datasets."