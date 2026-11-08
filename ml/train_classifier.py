import json
import math
import os
import re
from collections import Counter, defaultdict
from ml.dataset import TRAINING_DATA

EXPORT_DIR = "/home/ratul/Athena/ml/exports"
MODEL_FILE = os.path.join(EXPORT_DIR, "classifier_model.json")

def tokenize(text: str):
    tokens = re.findall(r"\b[a-z0-9']+\b", text.lower())
    unigrams = tokens
    bigrams = [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]
    return unigrams + bigrams

def train_and_export():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    print(f"Training Athina Intent & Emotion Classifier on {len(TRAINING_DATA)} samples...")

    labels = sorted(list(set(label for _, label in TRAINING_DATA)))
    label_to_idx = {l: i for i, l in enumerate(labels)}
    idx_to_label = {i: l for i, l in enumerate(labels)}

    # 1. Build Vocabulary & Document Frequencies
    doc_freq = Counter()
    total_docs = len(TRAINING_DATA)
    tokenized_corpus = []

    for text, label in TRAINING_DATA:
        tokens = set(tokenize(text))
        tokenized_corpus.append(tokens)
        for t in tokens:
            doc_freq[t] += 1

    # Filter features that appear at least once
    vocab = {t: idx for idx, (t, count) in enumerate(doc_freq.items()) if count >= 1}
    vocab_size = len(vocab)
    print(f"Vocabulary size: {vocab_size} n-gram features across {len(labels)} classes: {labels}")

    # Compute IDF weights: log(1 + (N + 1) / (DF + 1)) + 1
    idf = {}
    for token, idx in vocab.items():
        df = doc_freq[token]
        idf[token] = math.log((1 + total_docs) / (1 + df)) + 1.0

    # 2. Vectorize Documents with TF-IDF
    vectors = []
    class_docs = defaultdict(list)

    for doc_idx, (text, label) in enumerate(TRAINING_DATA):
        tokens = tokenize(text)
        tf = Counter(tokens)
        vec = {}
        norm_sq = 0.0
        for t, count in tf.items():
            if t in vocab:
                val = count * idf[t]
                vec[t] = val
                norm_sq += val * val
        # L2 Normalize
        norm = math.sqrt(norm_sq) if norm_sq > 0 else 1.0
        normalized_vec = {t: val / norm for t, val in vec.items()}
        vectors.append(normalized_vec)
        class_docs[label].append(normalized_vec)

    # 3. Train Centroid / Cosine Classifier Weights for each Class
    # (High accuracy, fast, zero numerical instability, natively serializable to JSON/ONNX)
    class_weights = {}
    for label in labels:
        docs = class_docs[label]
        centroid = Counter()
        for d in docs:
            for t, val in d.items():
                centroid[t] += val
        # Normalize class centroid
        c_norm = math.sqrt(sum(v * v for v in centroid.values()))
        class_weights[label] = {t: v / (c_norm or 1.0) for t, v in centroid.items()}

    # 4. Save to Model JSON for zero-dependency high-speed inference
    model_payload = {
        "classes": labels,
        "vocabulary": vocab,
        "idf": idf,
        "class_weights": class_weights
    }

    with open(MODEL_FILE, "w", encoding="utf-8") as f:
        json.dump(model_payload, f, indent=2)

    print(f"Model successfully trained and saved to: {MODEL_FILE}")

    # Test sample predictions
    test_samples = [
        "Can you send me a selfie?",
        "I feel so lonely and exhausted today",
        "Set an alarm for 7:30am please",
        "Save a note: architecture review on Monday",
        "We won the championship, I am so thrilled!"
    ]

    print("\n--- Test Sample Predictions ---")
    for sample in test_samples:
        pred_label, confidence = predict_sample(sample, model_payload)
        print(f"'{sample}' -> {pred_label} (Confidence: {confidence:.2f})")

def predict_sample(text: str, model: dict):
    tokens = tokenize(text)
    tf = Counter(tokens)
    vocab = model["vocabulary"]
    idf = model["idf"]

    # Compute normalized query vector
    vec = {}
    norm_sq = 0.0
    for t, count in tf.items():
        if t in vocab:
            val = count * idf[t]
            vec[t] = val
            norm_sq += val * val
    norm = math.sqrt(norm_sq) if norm_sq > 0 else 1.0
    norm_vec = {t: val / norm for t, val in vec.items()}

    # Compute dot product against each class weights
    scores = {}
    for label, weights in model["class_weights"].items():
        dot = sum(norm_vec[t] * weights[t] for t in norm_vec if t in weights)
        scores[label] = dot

    best_label = max(scores, key=scores.get)
    best_score = scores[best_label]
    return best_label, best_score

if __name__ == "__main__":
    train_and_export()
