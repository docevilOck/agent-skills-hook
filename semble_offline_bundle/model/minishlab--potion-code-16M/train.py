"""Reproduction script for potion-code-16M.

Runs the full pipeline: distill → tokenlearn → contrastive fine-tuning.

Requirements:
    pip install model2vec tokenlearn sentence-transformers datasets skeletoken einops

The three model checkpoints are saved to:
    ./models/potion-code-16M-distilled
    ./models/potion-code-16M-tokenlearn
    ./models/potion-code-16M-contrastive  ← final model
"""

from __future__ import annotations

import logging
import random

import numpy as np
import torch
from datasets import Dataset, concatenate_datasets, load_dataset
from huggingface_hub import snapshot_download
from model2vec import StaticModel
from model2vec.distill import distill_from_model
from model2vec.distill.inference import post_process_embeddings
from pathlib import Path
from sentence_transformers import (
    SentenceTransformer,
    SentenceTransformerTrainer,
    SentenceTransformerTrainingArguments,
)
from sentence_transformers.losses import MultipleNegativesRankingLoss
from sentence_transformers.models import StaticEmbedding
from sentence_transformers.training_args import BatchSamplers
from skeletoken import TokenizerModel
from sklearn.decomposition import PCA
from tokenlearn.losses import Loss
from tokenlearn.model import StaticModelForFineTuning
from tokenlearn.utils import create_vocab
from transformers import AutoModel, AutoTokenizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TEACHER_MODEL = "nomic-ai/CodeRankEmbed"
OUTPUT_DIR = Path("models")

# Distill
VOCAB_SIZE = 42_000  # extra tokens mined from CornStack → ~62.5k total → ~16M params
PCA_DIMS = 256
SIF_COEFFICIENT = 1e-4

# Tokenlearn
TOKENLEARN_DOCS_DATASET = "minishlab/tokenlearn-cornstack-docs-coderankembed"
TOKENLEARN_QUERIES_DATASET = "minishlab/tokenlearn-cornstack-queries-coderankembed"
TOKENLEARN_LANGUAGES = ["go", "java", "javascript", "php", "python", "ruby"]
TOKENLEARN_MAX_PER_LANGUAGE = 20_000  # 20k docs + 20k queries × 6 langs = 240k total
TOKENLEARN_LR = 1e-3
TOKENLEARN_MAX_EPOCHS = 20  # early stopping (patience=5) typically kicks in earlier
TOKENLEARN_BATCH_SIZE = 128

# Contrastive
CORNSTACK_DATASETS = {
    "python": "nomic-ai/cornstack-python-v1",
    "java": "nomic-ai/cornstack-java-v1",
    "php": "nomic-ai/cornstack-php-v1",
    "go": "nomic-ai/cornstack-go-v1",
    "javascript": "nomic-ai/cornstack-javascript-v1",
    "ruby": "nomic-ai/cornstack-ruby-v1",
}
CONTRASTIVE_MAX_PER_LANGUAGE = 20_000  # 20k × 6 langs = 120k pairs total
CONTRASTIVE_LR = 5e-3
CONTRASTIVE_EPOCHS = 3
CONTRASTIVE_BATCH_SIZE = 512
CONTRASTIVE_SEED = 42


def apply_post_sif(model: StaticModel, pca_dims: int, sif_coefficient: float) -> StaticModel:
    """Apply post-SIF re-regularization to a static model."""
    embeddings_np = model.embedding.astype(np.float32)
    processed, weights = post_process_embeddings(embeddings_np, pca_dims=pca_dims, sif_coefficient=sif_coefficient)
    logger.info("post_process_embeddings: %s → %s", embeddings_np.shape, processed.shape)
    model.embedding = processed
    model.weights = weights
    return model


def run_distill(save_path: Path) -> None:
    """Distill CodeRankEmbed into a static model with an extended code vocabulary."""
    logger.info("Downloading %s ...", TEACHER_MODEL)
    local_path = snapshot_download(TEACHER_MODEL)
    model = AutoModel.from_pretrained(local_path, trust_remote_code=True)
    tokenizer = AutoTokenizer.from_pretrained(local_path, trust_remote_code=True, use_fast=True)

    # Load tokenlearn corpus texts for vocab mining (docs + queries, 20k/lang)
    logger.info("Loading texts for vocabulary mining ...")
    shards = []
    for lang in TOKENLEARN_LANGUAGES:
        docs = load_dataset(TOKENLEARN_DOCS_DATASET, name=lang, split=f"train[:{TOKENLEARN_MAX_PER_LANGUAGE}]")
        queries = load_dataset(TOKENLEARN_QUERIES_DATASET, name=lang, split=f"train[:{TOKENLEARN_MAX_PER_LANGUAGE}]")
        shards.extend([docs, queries])
    corpus = concatenate_datasets(shards)
    texts: list[str] = list(corpus["text"])
    logger.info("Loaded %d texts for vocab mining.", len(texts))

    logger.info("Mining vocabulary (target size=%d) ...", VOCAB_SIZE)
    vocab = create_vocab(texts=texts, vocab_size=VOCAB_SIZE)
    logger.info("Mined %d tokens.", len(vocab))

    # Filter: keep only new single-token entries not already in CodeRankEmbed vocabulary.
    tokenizer_model = TokenizerModel.from_transformers_tokenizer(tokenizer).prune_added_tokens()
    preprocessor = tokenizer_model.preprocessor
    seen = set(tokenizer_model.sorted_vocabulary)
    filtered = []
    for token in vocab:
        preprocessed = preprocessor.preprocess(token)
        if len(preprocessed) == 1 and preprocessed[0] not in seen:
            seen.add(preprocessed[0])
            filtered.append(preprocessed[0])
    logger.info("Vocabulary after filtering: %d tokens added to CodeRankEmbed.", len(filtered))

    # NomicBERT requires monkey-patched embedding accessors.
    model.get_input_embeddings = lambda: model.embeddings.word_embeddings
    model.set_input_embeddings = lambda v: setattr(model.embeddings, "word_embeddings", v)

    logger.info("Distilling (pca_dims=%d, sif=%g) ...", PCA_DIMS, SIF_COEFFICIENT)
    static_model = distill_from_model(
        model=model,
        tokenizer=tokenizer,
        vocabulary=filtered,
        pca_dims=PCA_DIMS,
        sif_coefficient=SIF_COEFFICIENT,
        pooling="mean",
        quantize_to="float32",
    )

    save_path.mkdir(parents=True, exist_ok=True)
    static_model.save_pretrained(str(save_path))
    logger.info(
        "Distilled model saved to %s  (vocab=%d, dims=%d)",
        save_path,
        static_model.embedding.shape[0],
        static_model.embedding.shape[1],
    )


def run_tokenlearn(base_model_path: Path, save_path: Path) -> None:
    """Fine-tune the distilled model on CornStack using cosine similarity loss."""
    # Load 20k docs + 20k queries per language → 240k total
    logger.info(
        "Loading tokenlearn data (docs + queries, %d/lang × %d langs) ...",
        TOKENLEARN_MAX_PER_LANGUAGE,
        len(TOKENLEARN_LANGUAGES),
    )
    shards = []
    for lang in TOKENLEARN_LANGUAGES:
        docs = load_dataset(TOKENLEARN_DOCS_DATASET, name=lang, split=f"train[:{TOKENLEARN_MAX_PER_LANGUAGE}]")
        queries = load_dataset(TOKENLEARN_QUERIES_DATASET, name=lang, split=f"train[:{TOKENLEARN_MAX_PER_LANGUAGE}]")
        shards.extend([docs, queries])
    dataset = concatenate_datasets(shards)
    logger.info("Total samples: %d", len(dataset))

    train_txt: list[str] = list(dataset["text"])
    train_vec = np.array(dataset["embedding"], dtype=np.float32)
    non_nan_mask = ~np.isnan(train_vec).any(axis=1)
    train_txt = np.array(train_txt)[non_nan_mask].tolist()
    train_vec = train_vec[non_nan_mask]
    logger.info("Loaded %d samples, raw vector shape: %s", len(train_txt), train_vec.shape)

    logger.info("Fitting PCA to %d dims ...", PCA_DIMS)
    pca = PCA(n_components=PCA_DIMS)
    train_vec = pca.fit_transform(train_vec)
    logger.info("Explained variance: %.4f. Shape: %s", pca.explained_variance_ratio_.cumsum()[-1], train_vec.shape)

    logger.info("Loading base model from %s ...", base_model_path)
    base_model = StaticModel.from_pretrained(str(base_model_path), force_download=False)
    if base_model.embedding.dtype != np.float32:
        base_model.embedding = base_model.embedding.astype(np.float32)

    trainable = StaticModelForFineTuning.from_static_model(
        model=base_model,
        out_dim=PCA_DIMS,
        loss=Loss("cosine"),
    )
    logger.info(
        "Training tokenlearn (lr=%g, max_epochs=%d, batch=%d) ...",
        TOKENLEARN_LR,
        TOKENLEARN_MAX_EPOCHS,
        TOKENLEARN_BATCH_SIZE,
    )
    trainable.fit(
        X=train_txt,
        y=torch.from_numpy(train_vec.astype(np.float32)),
        batch_size=TOKENLEARN_BATCH_SIZE,
        learning_rate=TOKENLEARN_LR,
        max_epochs=TOKENLEARN_MAX_EPOCHS,
        early_stopping_patience=5,
        use_wandb=False,
    )
    logger.info("Tokenlearn training complete.")

    trained_model = trainable.to_static_model()
    trained_model = apply_post_sif(trained_model, pca_dims=PCA_DIMS, sif_coefficient=SIF_COEFFICIENT)

    save_path.mkdir(parents=True, exist_ok=True)
    trained_model.save_pretrained(str(save_path))
    logger.info("Tokenlearn model saved to %s", save_path)


def run_contrastive(base_model_path: Path, save_path: Path) -> None:
    """Fine-tune the tokenlearn model using MultipleNegativesRankingLoss on CornStack pairs."""
    random.seed(CONTRASTIVE_SEED)

    logger.info(
        "Streaming CornStack pairs (%d/lang × %d langs) ...", CONTRASTIVE_MAX_PER_LANGUAGE, len(CORNSTACK_DATASETS)
    )
    all_queries: list[str] = []
    all_docs: list[str] = []
    for lang, hf_name in CORNSTACK_DATASETS.items():
        hf_ds = load_dataset(hf_name, split="train", streaming=True)
        hf_ds = hf_ds.shuffle(seed=CONTRASTIVE_SEED, buffer_size=10_000)
        kept = 0
        seen_q: set[str] = set()
        seen_d: set[str] = set()
        for row in hf_ds:
            q, d = row.get("query"), row.get("document")
            if not isinstance(q, str) or not isinstance(d, str):
                continue
            if len(q) < 32 or len(d) < 32:
                continue
            if q in seen_q or d in seen_d:
                continue
            seen_q.add(q)
            seen_d.add(d)
            all_queries.append(q)
            all_docs.append(d)
            kept += 1
            if kept >= CONTRASTIVE_MAX_PER_LANGUAGE:
                break
        logger.info("  %s: %d pairs", lang, kept)

    logger.info("Total pairs: %d", len(all_queries))
    train_dataset = Dataset.from_dict({"anchor": all_queries, "positive": all_docs})

    static_embedding = StaticEmbedding.from_model2vec(str(base_model_path))
    model = SentenceTransformer(modules=[static_embedding])
    loss = MultipleNegativesRankingLoss(model)

    training_args = SentenceTransformerTrainingArguments(
        output_dir=str(save_path) + "-checkpoints",
        num_train_epochs=CONTRASTIVE_EPOCHS,
        per_device_train_batch_size=CONTRASTIVE_BATCH_SIZE,
        learning_rate=CONTRASTIVE_LR,
        warmup_steps=0.1,
        fp16=False,
        bf16=False,
        batch_sampler=BatchSamplers.NO_DUPLICATES,
        save_strategy="no",
        logging_steps=100,
        logging_first_step=True,
        report_to=[],
    )
    logger.info(
        "Training contrastive (lr=%g, epochs=%d, batch=%d) ...",
        CONTRASTIVE_LR,
        CONTRASTIVE_EPOCHS,
        CONTRASTIVE_BATCH_SIZE,
    )

    trainer = SentenceTransformerTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        loss=loss,
    )
    trainer.train()
    logger.info("Contrastive training complete.")

    base_m2v = StaticModel.from_pretrained(str(base_model_path), force_download=False)
    base_m2v.embedding = model[0].embedding.weight.detach().cpu().float().numpy()

    final_model = apply_post_sif(base_m2v, pca_dims=PCA_DIMS, sif_coefficient=SIF_COEFFICIENT)

    save_path.mkdir(parents=True, exist_ok=True)
    final_model.save_pretrained(str(save_path))
    logger.info("Final model saved to %s", save_path)


if __name__ == "__main__":
    distilled_path = OUTPUT_DIR / "potion-code-16M-distilled"
    tokenlearn_path = OUTPUT_DIR / "potion-code-16M-tokenlearn"
    contrastive_path = OUTPUT_DIR / "potion-code-16M-contrastive"

    logger.info("=== Step 1/3: Distill ===")
    run_distill(save_path=distilled_path)

    logger.info("=== Step 2/3: Tokenlearn ===")
    run_tokenlearn(base_model_path=distilled_path, save_path=tokenlearn_path)

    logger.info("=== Step 3/3: Contrastive ===")
    run_contrastive(base_model_path=tokenlearn_path, save_path=contrastive_path)

    logger.info("Done. Final model: %s", contrastive_path)
