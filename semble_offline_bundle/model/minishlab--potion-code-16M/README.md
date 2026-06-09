---
language:
- code
license: mit
library_name: model2vec
tags:
- model2vec
- embeddings
- code
- retrieval
- static-embeddings
datasets:
- minishlab/tokenlearn-cornstack-queries-coderankembed
- minishlab/tokenlearn-cornstack-docs-coderankembed
- nomic-ai/cornstack-python-v1
- nomic-ai/cornstack-java-v1
- nomic-ai/cornstack-php-v1
- nomic-ai/cornstack-go-v1
- nomic-ai/cornstack-javascript-v1
- nomic-ai/cornstack-ruby-v1
---

# potion-code-16M Model Card

## Overview

**potion-code-16M** is a fast static code embedding model optimized for code retrieval tasks. It powers [Semble](https://github.com/MinishLab/semble), a code search library for agents. It is distilled from [nomic-ai/CodeRankEmbed](https://huggingface.co/nomic-ai/CodeRankEmbed) and trained on the [CornStack](https://huggingface.co/datasets/nomic-ai/cornstack-python-v1) code corpus using [Tokenlearn](https://github.com/MinishLab/tokenlearn) and contrastive fine-tuning.

It uses static embeddings, allowing text and code embeddings to be computed orders of magnitude faster than transformer-based models on both GPU and CPU.

## Installation

```bash
pip install model2vec
```

## Usage

```python
from model2vec import StaticModel

model = StaticModel.from_pretrained("minishlab/potion-code-16M")

# Embed natural language queries
query_embeddings = model.encode(["How to read a file in Python?"])

# Embed code documents
code_embeddings = model.encode(["def read_file(path):\n    with open(path) as f:\n        return f.read()"])
```

## How it works

potion-code-16M is created using the following pipeline:

1. **Vocabulary mining**: code-specific tokens are mined from CornStack and added to the base CodeRankEmbed tokenizer (42k extra tokens → ~62.5k total)
2. **Distillation**: the extended vocabulary is distilled from CodeRankEmbed using Model2Vec (256-dimensional embeddings, PCA whitening)
3. **Tokenlearn**: the distilled model is fine-tuned on 240k (query, document) pairs from CornStack using cosine similarity loss
4. **Contrastive fine-tuning**: the model is further fine-tuned using MultipleNegativesRankingLoss on 120k CornStack query-document pairs
5. **Post-SIF re-regularization**: token weights are re-regularized using SIF weighting after each training stage

## Results

Results on the [CoIR benchmark](https://github.com/CoIR-team/coir) on [MTEB](https://github.com/embeddings-benchmark/mteb) (NDCG@10, `mteb>=2.10`):

| Model | Params | AVG | AppsRetrieval | COIRCodeSearchNet | CodeFeedbackMT | CodeFeedbackST | CodeSearchNetCC | CodeTransContest | CodeTransDL | CosQA | StackOverflow | Text2SQL |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CodeRankEmbed | 137M | 59.14 | 23.46 | 94.70 | 42.61 | 78.11 | 76.39 | 66.43 | 34.84 | 35.92 | 80.53 | 58.37 |
| **potion-code-16M + Hybrid** | **16M** | **40.41** | **5.23** | **34.03** | **51.23** | **64.26** | **33.22** | **52.67** | **31.14** | **21.63** | **69.65** | **41.03** |
| BM25 | — | 39.11 | 4.76 | 32.45 | 59.69 | 67.85 | 33.00 | 47.29 | 32.97 | 15.53 | 69.54 | 28.07 |
| **potion-code-16M** | **16M** | **37.05** | **3.97** | **42.99** | **36.26** | **50.27** | **43.40** | **39.76** | **31.72** | **21.37** | **57.47** | **43.34** |
| potion-retrieval-32M | 32M | 32.10 | 4.22 | 31.80 | 36.71 | 45.11 | 38.64 | 29.97 | 32.62 | 8.70 | 56.26 | 36.93 |
| potion-base-32M | 32M | 31.42 | 3.37 | 29.58 | 34.77 | 42.69 | 37.88 | 28.51 | 30.55 | 14.61 | 53.36 | 38.88 |

CoIR covers a broad range of code retrieval scenarios. For the use case of finding code given a natural language query, **CosQA** and **CodeFeedback (ST/MT)** are the most relevant tasks. Others are less so: **COIRCodeSearchNetRetrieval** retrieves text given a code query (the reverse direction), and the **CodeTransOcean** tasks target cross-language code translation. The hybrid row combines dense retrieval with BM25 using min-max score normalization and equal weighting (alpha=0.5).

## Model Details

| Property | Value |
|---|---|
| Parameters | ~16M |
| Embedding dimensions | 256 |
| Vocabulary size | ~62,500 |
| Teacher model | nomic-ai/CodeRankEmbed |
| Training corpus | CornStack (6 languages: Python, Java, JavaScript, Go, PHP, Ruby) |
| Max sequence length | 1,000,000 tokens (static, no limit in practice) |

## Additional Resources

- [Semble repository](https://github.com/MinishLab/semble)
- [Model2Vec repository](https://github.com/MinishLab/model2vec)
- [Tokenlearn repository](https://github.com/MinishLab/tokenlearn)
- [CornStack dataset](https://huggingface.co/datasets/nomic-ai/cornstack-python-v1)
- [CoIR benchmark](https://github.com/CoIR-team/coir)

## Reproducibility

The full training pipeline (distill → tokenlearn → contrastive) is in [`train.py`](./train.py). It requires `minishlab/tokenlearn-cornstack-docs-coderankembed` and `minishlab/tokenlearn-cornstack-queries-coderankembed` (20k samples per language used).

```
pip install model2vec tokenlearn sentence-transformers datasets skeletoken einops
python train.py
```

## Citation

```bibtex
@software{minishlab2024model2vec,
  author       = {Stephan Tulkens and {van Dongen}, Thomas},
  title        = {Model2Vec: Fast State-of-the-Art Static Embeddings},
  year         = {2024},
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.17270888},
  url          = {https://github.com/MinishLab/model2vec},
  license      = {MIT}
}
```
