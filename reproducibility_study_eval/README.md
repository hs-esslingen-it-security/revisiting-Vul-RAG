# Revisiting Vul-RAG: Reproducibility and Replicability of RAG-based Vulnerability Detection with Open-Weight Models 🧠👩‍💻🔍

This subdirectory contains all artifacts related to the reproducibility and replicability study of Vul-RAG.

## 📁 Directory Structure
```
/reproducibility_study_eval
├── README.md                   
├── eval_logs                       # Example logs from model runs (incl. failures)
├── output/                         # Detection outputs and metrics
├── analysis_RQs.ipynb              # Notebook containing the analyses from the paper 📊
├── calculate_iterations.py         # Script to analyze iterative behavior (RQ4)
├── mean_and_std_across_runs.py     # Script to calculate mean and std values (RQ1)
├── token_stats.py                  # Script to analyze input and prompt lengths (RQ1, RQ4)
```

## 📊 Results 
Experiments are executed via the main Vul-RAG scripts (see root README).
All outputs referenced in the paper are stored in ``output/``.
Output files follow this structure: `<VULRAG>-<MODEL>-<SUMMARY_MODEL>`.
In the experiments, the same model was used for detection and summarization.
The output for qwen2.5-coder-32b-instruct/ contains multiple runs.



## Appendix
In preliminary experiments, we evaluated a broad set of models with the Vul-RAG framework. We considered open-weight models of varying parameter sizes across the Qwen, DeepSeek, Llama, and OpenAI model families.

We observed that several models exhibited practical limitations, including failures to process inputs (e.g., due to context limitations), as well as inconsistent or non-compliant output formats that prevented parsing.
We also observed robustness issues. 
For example, gpt-oss-20b tended to enter reasoning loops, repeatedly evaluating the same code without progressing towards a final answer.
This behavior was often accompanied by explicit signals (_“Stop repeating”_) and ultimately resulted in termination due to the token limit (see example eval log [here](eval_logs/VulRAG-eval-gpt-oss-20b-gpt-oss-20b_64574.out)).

### 📈 Full Table of evaluations:
> **_NOTE:_** * = incomplete coverage of dataset items; best results in bold.

| Family        | Model Identifier                          | Pair. Accuracy | Pairs   |
|---------------|-------------------------------------------|----------------|---------|
| Qwen          | Qwen2.5-Coder-3B-Instruct                 | 0.24           | 586/586 |
| Qwen          | Qwen2.5-Coder-7B-Instruct                 | 0.08           | 586/586 |
| Qwen          | Qwen2.5-Coder-14B-Instruct                | 0.24           | 586/586 |
| Qwen          | Qwen2.5-Coder-32B-Instruct                | 0.26           | 586/586 |
| Qwen          | Qwen2.5-3B-Instruct                      | 0.23           | 585/586*|
| Qwen          | Qwen2.5-7B-Instruct                      | 0.21           | 585/586*|
| Qwen          | Qwen2.5-14B-Instruct                     | 0.27           | 585/586*|
| Qwen          | Qwen2.5-32B-Instruct                     | 0.25           | 586/586 |
| Qwen          | Qwen3-Coder-30B-A3B-Instruct             | 0.28           | 586/586 |
| Qwen          | Qwen3-4B                                 | 0.25           | 586/586 |
| Qwen          | Qwen3-8B                                 | 0.24           | 586/586 |
| Qwen          | Qwen3-14B                                | 0.22           | 586/586 |
| Qwen          | Qwen3-30B-A3B-Instruct-2507              | 0.25           | 586/586 |
| Qwen          | QwQ-32B                                  | **0.29**       | 586/586 |
| deepseek-ai   | deepseek-coder-6.7b-instruct             | 0.10           | 422/586*|
| deepseek-ai   | deepseek-coder-33b-instruct              | 0.06           | 418/586*|
| deepseek-ai   | DeepSeek-Coder-V2-Instruct               | 0.22           | 565/586*|
| deepseek-ai   | DeepSeek-Coder-V2-Lite-Instruct          | 0.14           | 584/586*|
| deepseek-ai   | DeepSeek-V2                              | 0.00           | 0/586*  |
| deepseek-ai   | DeepSeek-V2.5                            | 0.00           | 0/586*  |
| deepseek-ai   | DeepSeek-V2-Lite                         | 0.00           | 0/586*  |
| deepseek-ai   | DeepSeek-R1-Distill-Qwen-7B              | 0.21           | 585/586*|
| deepseek-ai   | DeepSeek-R1-Distill-Llama-8B             | **0.29**       | 586/586 |
| deepseek-ai   | DeepSeek-R1-Distill-Qwen-14B             | 0.27           | 586/586 |
| deepseek-ai   | DeepSeek-R1-Distill-Qwen-32B             | **0.29**       | 586/586 |
| codellama     | CodeLlama-7b-Instruct-hf                 | 0.14           | 372/586*|
| codellama     | CodeLlama-13b-Instruct-hf                | 0.05           | 383/586*|
| codellama     | CodeLlama-34b-Instruct-hf                | 0.03           | 416/586*|
| meta-llama    | Meta-Llama-3-8B-Instruct                 | 0.11           | 400/586*|
| meta-llama    | Llama-3.1-8B-Instruct                    | 0.25           | 573/586*|
| meta-llama    | Llama-3.2-1B-Instruct                    | 0.00           | 0/586*  |
| meta-llama    | Llama-3.2-3B-Instruct                    | 0.13           | 562/586*|
| openai        | gpt-oss-20b                              | 0.23           | 583/586*|
| openai        | gpt-oss-120b                             | 0.24           | 585/586*|

