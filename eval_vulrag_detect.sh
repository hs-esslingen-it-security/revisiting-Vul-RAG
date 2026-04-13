#!/bin/bash
# -----------------------------
if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
    echo "Usage: $0 <MODEL_NAME> <SUMMARY_MODEL_NAME> [KNOWLEDGE_MODEL]"
    echo "  If KNOWLEDGE_MODEL is provided, knowledge will be loaded from add_vulnerability_knowledge/<KNOWLEDGE_MODEL>/*_data.json"
    exit 1
fi

MODEL="$1"
export MODEL
SM="$2"
export SM

# If a knowledge model is provided, use its folder and *_data.json files.
if [ "$#" -eq 3 ]; then
    KNOW_MODEL="$3"
    export KNOW_MODEL
    KNOW_BASE_DIR="add_vulnerability_knowledge/${KNOW_MODEL}"
    KNOW_SUFFIX="_data.json"
    KB_NAME_SUFFIX="__kb-${KNOW_MODEL}"
else
    KNOW_BASE_DIR="vulnerability_knowledge"
    KNOW_SUFFIX="_knowledge.json"
    KB_NAME_SUFFIX=""
fi

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
# Log directory / Paths
# -----------------------------
OUT_ROOT="output/detect"

# -----------------------------
# Iterate over combinations
# -----------------------------
# output dir for this (MODEL, SM) combo
MODEL_COMBO="${MODEL}__sum-${SM}${KB_NAME_SUFFIX}"
MODEL_SM_DIR="${OUT_ROOT}/${MODEL_COMBO}"
mkdir -p "${MODEL_SM_DIR}"

echo "============================================================"
echo "Combo: detect=${MODEL} | summary=${SM}"
echo "Output dir: ${MODEL_SM_DIR}"
echo "============================================================"

for DATASET in "${DATASETS[@]}"; do
  BASE="${DATASET}"  # already without suffix
  OUT_FILE="${BASE}_result_${MODEL}__sum-${SM}${KB_NAME_SUFFIX}.json"
  OUT_PATH="${MODEL_SM_DIR}/${OUT_FILE}"
  KNOW_FILE="${BASE}${KNOW_SUFFIX}"

  echo "------------------------------------------------------------"
  echo "Running detect"
  echo "  detect model : ${MODEL}"
  echo "  summary model: ${SM}"
  echo "  dataset      : ${DATASET}_testset.json"
  echo "  knowledge    : ${KNOW_FILE}"
  echo "  out          : ${OUT_PATH}"
  echo "------------------------------------------------------------"

  # Run detection
  {
    echo "START detect ${MODEL} + ${SM} on ${DATASET}"
    set -x
    python src/vulnerability_detect.py \
      --input_file_name "${BASE}_testset.json" \
      --output_file_name "${MODEL_COMBO}/${OUT_FILE}" \
      --knowledge_dir "${KNOW_BASE_DIR}" \
      --knowledge_file_name "${KNOW_FILE}" \
      --model_name "${MODEL}" \
      --summary_model_name "${SM}" \
      --resume \
      --retrieval_top_k 20 \
      --thread_pool_size 1 \
      --early_return \
      --model_settings "temperature=0.01" \
      --max_knowledge 3
    { set +x; } 2>/dev/null
    echo "DONE  detect ${MODEL} + ${SM} on ${DATASET}"
  } 
done

# -----------------------------
# Evaluate this (MODEL, SM) folder
# -----------------------------
echo "============================================================"
echo "Evaluating results for: ${MODEL_SM_DIR}"
echo "============================================================"

shopt -s nullglob
MODEL_SM_JSONS=( "${MODEL_SM_DIR}"/*.json )
shopt -u nullglob

if (( ${#MODEL_SM_JSONS[@]} == 0 )); then
  echo "No result JSONs found in ${MODEL_SM_DIR}; skipping evaluation."
else
  {
    echo "START evaluation for ${MODEL_COMBO}"
    set -x
    python src/evaluate_result.py --input_files "${MODEL_SM_JSONS[@]}" --output_dir "${MODEL_SM_DIR}"
    { set +x; } 2>/dev/null
    echo "DONE  evaluation for ${MODEL_COMBO}"
  } 
fi

echo "🎯 Evaluation finished."