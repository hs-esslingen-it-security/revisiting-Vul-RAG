
# Revisiting Vul-RAG: Reproducibility and Replicability of RAG-based Vulnerability Detection with Open-Weight Models 🧠👩‍💻🔍

LLMs have shown strong potential for automated software vulnerability detection, particularly in retrieval-augmented generation (RAG) settings. However, for approaches relying on proprietary models and APIs, reproducibility and replicability remain unexplored, raising the question of whether reported results generalize or depend primarily on specific model choices. In this work, we present a reproducibility study of Vul-RAG in a fully local and open-weights setting. 

We revisit Vul-RAG under the following conditions:
- Fully local inference using HuggingFace models
- Broad model coverage, including:
    - Code-specialized models (baselines)
    - Newer generations of baseline models
    - General-purpose LLMs
    - Reasoning-oriented models



**Contributions**:
- We dapt Vul-RAG to use HuggingFace and local inference: [llm_client.py](utils/llm_client.py)
- We reproduce reported results using the reported open-weight baseline models: [Reproducibility Study](reproducibility_study_eval)
- We evaluate Vul-RAG using recent open-weight LLMs, including code-specialized, general-purpose, and reasoning models of various parameter sizes: [Reproducibility Study](reproducibility_study_eval)


💡 We find that Vul-RAG is reproducible for Qwen2.5-Coder but not for DeepSeek-Coder-V2.
Across a diverse set of LLMs, including newer model generations (RQ2), general-purpose models (RQ3), and reasoning models (RQ4) with varying parameter scales (RQ5), we observe only limited performance differences.
Reasoning models achieve the the highest pairwise accuracy of 0.29 (code pairs for which both the vulnerable and the patched function are correctly classified).
In contrast, neither increased model scale nor newer model generations yield substantial improvements.
These results consistently indicate a performance plateau in Vul-RAG, suggesting that effectiveness is largely independent of model choice. 
Instead, the primary bottleneck lies in the quality of knowledge representation and retrieval.
From a practical perspective, the findings show that large parameter scales are not required for competitive performance, enabling efficient on-premise deployment with smaller models. 
Future work should focus on improving knowledge base quality and retrieval strategies to overcome these limitations.


For more details, see our 📚 publication. If you use this work, please cite!
```bibtex
@article{kaniewskiRevisitingVulRAG2026,
    title={Revisiting Vul-RAG: Reproducibility and Replicability of RAG-based Vulnerability Detection with Open-Weight Models}, 
    author={Kaniewski, Sabrina and Schmidt, Fabian and Heer, Tobias},
    year={2026}
}
```



To 🔁 reproduce our results:
- Use the modified Vul-RAG pipeline (see below)
- Select a model from `utils/llm_client.py`
- Run: ``bash eval_vulrag_detect.sh <MODEL_NAME> <SUMMARY_MODEL_NAME>``
- Analyze outputs using provided scripts or notebook

<br>

_______
_______

<br>

# Vul-RAG

This repository is an adapted copy of the original [Vul-RAG implementation](https://github.com/KnowledgeRAG4LLMVulD/KnowledgeRAG4LLMVulD/tree/main/VUL-RAG).


Vul-RAG is a vulnerability detection tool based on LLMs that incorporates RAG to improve detection accuracy. It mainly consists of three core components: knowledge extraction, vulnerability detection, and result evaluation.
For more details, see the official publication of Vul-RAG:
```bibtex
@article{10.1145/3797277,
    author = {Du, Xueying and Zheng, Geng and Wang, Kaixin and Zou, Yi and Wang, Yujia and Deng, Wentai and Feng, Jiayi and Liu, Mingwei and Chen, Bihuan and Peng, Xin and Ma, Tao and Lou, Yiling},
    title = {Vul-RAG: Enhancing LLM-based Vulnerability Detection via Knowledge-level RAG},
    year = {2026},
    doi = {10.1145/3797277},
    note = {Just Accepted},
    journal = {ACM Transactions on Software Engineering and Methodology}
}
```

## 📁 Directory Structure

```
/
├── README.md                   # Project description document
├── vul-rag-rep.yml             # ✨ Updated project dependencies
├── data/                       # Dataset directory
│   ├── test/                   # Test dataset
│   └── train/                  # Training dataset
├── vulnerability_knowledge/    # Vulnerability knowledge
├── output/                     # Output directory, see specific results in /reproducibility_study_eval
│   ├── detect/                 # Detection results
│   │   ├── metrics/            # Evaluation metrics
│   │   └── ...                 # Detection result files
├── src/                        # Source code directory
│   ├── baseline_detect.py      # Baseline vulnerability detection script
│   ├── evaluate_result.py      # Result evaluation script
│   ├── extract_knowledge.py    # Knowledge extraction/generation script
│   └── vulnerability_detect.py # Main vulnerability detection script
└── utils/                      # Utility scripts directory
|   ├── bm25_retriever.py       # BM25 retrieval module
|   └── llm_client.py           # ✨ Updated LLM client interface (huggingface)
├── eval_vulrag_detect.sh       # ✨ Script to automate detection
├── generate_knowledge.sh       # ✨ Script to automate knowlegde generation
```


## Dependencies
> **_NOTE:_** initial dependencies updated; can be found in ``vul-rag-rep.yml``

Python version 3.12

You can install the dependencies via conda using the following command:
```bash
conda create --file vul-rag-rep.yml
```



## 🔍 Method Overview

### Detection

We re-implemented parts of the llm_client.py to use HuggingFace Transformers (instead of OPENAI/Replicate API keys). In addition, we separated model use: you can use different models for detection, summarization, and knowlegde generation. 
To add models, update `_MODEL_DICT_LLM` in `utils/llm_client.py`. Otherwise, choose a model from the dictionary (`<_MODEL_DICT_LLM model name>`, e.g., qwq-32b).

Start vulnerability detection as follows:

```bash
python src/vulnerability_detect.py --input_file_name linux_kernel_CWE-401_testset.json --output_file_name linux_kernel_CWE-401_result.json --knowledge_file_name linux_kernel_CWE-401_knowledge.json --model_name qwq-32b --summary_model_name qwq-32b --retrieval_top_k 20 --thread_pool_size 10 --resume --model_settings temperature=0.01 --early_return --max_knowledge 3
```


This command uses the extracted knowledge base to detect vulnerabilities in the test dataset and saves the detection results to the specified output file. Parameter descriptions:
- `--input_file_name`: Input test dataset file name.
- `--output_file_name`: Output detection result file name.
- `--knowledge_file_name`: Knowledge base file name used.
- `--knowledge_dir`: Directory containing knowledge JSONs (default: `vulnerability_knowledge`).
- `--model_name`: LLM model name used for detection.
- `--summary_model_name`: LLM model name used for generating summary function information for retrieval.
- `--retrieval_top_k`: Number of Top-K retrieval results.
- `--thread_pool_size`: Thread pool size for parallel processing.
- `--resume`: If an existing detection result file exists, resume processing from it.
- `--model_settings`: LLM model setting parameters.
- `--early_return`: Return early if a clear solution behavior is found.
- `--max_knowledge`: Maximum number of knowledge entries to use.
- `--retrieve_by_code`: Whether to use only code for knowledge retrieve and detect.



Alternatively, start with the default values via command line using the `eval_vulrag_detect.sh` script:
```bash
bash eval_vulrag_detect.sh <MODEL_NAME> <SUMMARY_MODEL_NAME> [KNOWLEDGE_MODEL]
```



### Calculate Evaluation Metrics
To calculate evaluation metrics for the detection results and save the evaluation results to the output directory, run (this is already implemented within `eval_vulrag_detect.sh`):

```bash
python src/evaluate_result.py --input_files $(ls -F output/detect | grep -v '/$')
```
Parameter descriptions:
- `--input_files`: List of input detection result files.
- `--baseline`: Whether to calculate baseline evaluation metrics.





### Knowledge Extraction
The original Vul-RAG implementation leveraged GPT-3.5-turbo-0125 to extract high-level vulnerability knowledge from the top-10 CVEs in the benchmark's training set. The extracted knowledge for each CWE is stored in ``./vulnerability knowledge``.

```bash
python src/extract_knowledge.py --input_file_name linux_kernel_CWE-20_data.json --model_name qwq-32b --thread_pool_size 1 --model_settings temperature=0.01
```

This command extracts vulnerability-related knowledge from the training dataset and saves it to the specified output file. Parameter descriptions:
- `--input_file_name`: Input training dataset file name.
- `--model_name`: Name of the LLM model used.
- `--thread_pool_size`: Thread pool size for parallel processing.
- `--resume`: If an existing knowledge base file exists, resume processing from it.
- `--model_settings`: LLM model setting parameters.


> **_NOTE:_** when re-generating knowledge, it is stored in `add_vulnerability_knowledge/{args.model_name}/{args.input_file_name}`. To use this model-specific knowledge in detection, pass the model name as a third argument to the evaluation scripts (e.g., `bash eval_vulrag_detect.sh <MODEL> <SUMMARY_MODEL> <KNOWLEDGE_MODEL>`).




## Benchmark 
Vul-RAG uses a custom benchmark based on Linux Kernel CVEs, enriched with more vulnerability information. The full dataset encompasses 4667 vulnerable and patched code function pairs across 2174 CVEs. For Vul-RAG, the authors focused on the top-10 CWEs within the dataset. The specific data fields in the benchmark contain the following information for each vulnerability:

- **CVE ID**: The unique identifier assigned to a reported vulnerability in the Common Vulnerabilities and Exposures (CVE).
- **CVE Description**: A detailed description of the vulnerability provided by the CVE system, including the manifestation of the vulnerability, potential impact, and the environment in which the vulnerability may occur.
- **CWE ID**: The Common Weakness Enumeration identifier that categorizes the type of vulnerability exploits.
- **Vulnerable Code**: The source code snippet containing the vulnerability that requires patching, which will be modified in the commit.
- **Patched Code**: The source code snippet that has been committed to fix the vulnerability in the vulnerable code.
- **Patch Diff**: A detailed line-level difference between the vulnerable and patched code, consisting of added and deleted lines.

The vulnerable and patched code pairs from the top-10 CWE categories were divided into a training set and a test set—the training set was utilized to construct the vulnerability knowledge base, while the test set was for experimental evaluation. The training set contains 1154 CVEs with 2317 pairs of vulnerable and patched code snippets, while the test set includes 420 CVEs with 586 pairs.


