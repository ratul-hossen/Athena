import json

notebook = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# ATHINA - Personality & Intent ML Training Pipeline\n",
    "### Fast, On-Device & Serverless Emotion & Intent Classification with Scikit-Learn and ONNX\n",
    "\n",
    "This notebook trains and visualizes Athina's **8-Class Emotion & Intent Classifier**:\n",
    "- `asks_image`: Image / Selfie request\n",
    "- `asks_note`: Note taking & Telegram upload\n",
    "- `asks_alarm`: Alarm & timer reminders\n",
    "- `sad`: Fatigue, sadness, seeking emotional support\n",
    "- `happy`: Joy, achievements, excitement\n",
    "- `curious`: Technical, scientific, or deep questions\n",
    "- `playful`: Teasing, banter, humor\n",
    "- `chit_chat`: Greetings, casual check-ins\n",
    "\n",
    "**Outputs:**\n",
    "1. `ml/exports/classifier_model.json` (Ultra-fast, zero-dependency JSON model)\n",
    "2. `ml/exports/intent_classifier.onnx` (Standard ONNX format for mobile & backend)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Step 1: Install & Import Libraries"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "!pip install -q scikit-learn numpy matplotlib seaborn skl2onnx onnxruntime\n",
    "\n",
    "import os\n",
    "import json\n",
    "import numpy as np\n",
    "import matplotlib.pyplot as plt\n",
    "import seaborn as sns\n",
    "\n",
    "from sklearn.feature_extraction.text import TfidfVectorizer\n",
    "from sklearn.linear_model import LogisticRegression\n",
    "from sklearn.pipeline import Pipeline\n",
    "from sklearn.metrics import classification_report, confusion_matrix\n",
    "from sklearn.model_selection import cross_val_score\n",
    "\n",
    "print(\"Environment ready!\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Step 2: Define Training Dataset"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "from collections import Counter\n",
    "\n",
    "# Comprehensive Athina conversational dataset\n",
    "TRAINING_DATA = [\n",
    "    # 1. Asks for Image / Selfie\n",
    "    (\"Can you send me a selfie?\", \"asks_image\"),\n",
    "    (\"Show me a picture of you\", \"asks_image\"),\n",
    "    (\"What do you look like right now?\", \"asks_image\"),\n",
    "    (\"Send me a photo of yourself\", \"asks_image\"),\n",
    "    (\"I want to see your face\", \"asks_image\"),\n",
    "    (\"Take a selfie for me\", \"asks_image\"),\n",
    "    (\"Can I get a picture of what you are wearing today?\", \"asks_image\"),\n",
    "    (\"Snap a selfie\", \"asks_image\"),\n",
    "    (\"Send me a pic\", \"asks_image\"),\n",
    "    (\"Show me your smile\", \"asks_image\"),\n",
    "    (\"Send me a photo in your cozy sweater\", \"asks_image\"),\n",
    "    (\"Take a photo of yourself by the window\", \"asks_image\"),\n",
    "    (\"Let me see you\", \"asks_image\"),\n",
    "\n",
    "    # 2. Asks for Note\n",
    "    (\"Take a note for me please\", \"asks_note\"),\n",
    "    (\"Save this idea for my app\", \"asks_note\"),\n",
    "    (\"Can you note this down?\", \"asks_note\"),\n",
    "    (\"Remember this note for later\", \"asks_note\"),\n",
    "    (\"Write this down in my notes\", \"asks_note\"),\n",
    "    (\"Save a note: meeting with the team at 3pm\", \"asks_note\"),\n",
    "    (\"Keep this note: grocery list milk eggs bread\", \"asks_note\"),\n",
    "    (\"Please save this note and upload it to telegram\", \"asks_note\"),\n",
    "    (\"Upload this note to telegram channel\", \"asks_note\"),\n",
    "    (\"Create a new note titled Architecture\", \"asks_note\"),\n",
    "    (\"Note down: fix the gradle build script\", \"asks_note\"),\n",
    "\n",
    "    # 3. Asks for Alarm\n",
    "    (\"Wake me up at 7am tomorrow\", \"asks_alarm\"),\n",
    "    (\"Set an alarm for 6:30 in the morning\", \"asks_alarm\"),\n",
    "    (\"Remind me to take my vitamins at 8pm\", \"asks_alarm\"),\n",
    "    (\"Can you set an alarm for tomorrow at 9?\", \"asks_alarm\"),\n",
    "    (\"Set a reminder for my meeting at 2pm\", \"asks_alarm\"),\n",
    "    (\"Alarm at 7:30 please\", \"asks_alarm\"),\n",
    "    (\"Set an alarm to wake up early on Monday\", \"asks_alarm\"),\n",
    "    (\"Remind me in 30 minutes\", \"asks_alarm\"),\n",
    "    (\"Please set an alarm for 5:45 AM\", \"asks_alarm\"),\n",
    "\n",
    "    # 4. Sad / Exhausted / Down\n",
    "    (\"I had such a rough day today\", \"sad\"),\n",
    "    (\"Everything went wrong at work and I feel overwhelmed\", \"sad\"),\n",
    "    (\"I am so exhausted and drained\", \"sad\"),\n",
    "    (\"Feeling really down and lonely tonight\", \"sad\"),\n",
    "    (\"Things have been so stressful lately\", \"sad\"),\n",
    "    (\"I feel like giving up on this project\", \"sad\"),\n",
    "    (\"Nobody seems to understand how tired I am\", \"sad\"),\n",
    "    (\"Just having a bad day\", \"sad\"),\n",
    "    (\"I'm feeling really sad\", \"sad\"),\n",
    "    (\"I need some comfort right now\", \"sad\"),\n",
    "\n",
    "    # 5. Happy / Celebratory\n",
    "    (\"I just got great news about my project!\", \"happy\"),\n",
    "    (\"Such an incredible day, everything worked out perfectly!\", \"happy\"),\n",
    "    (\"We finally launched the app, I am so thrilled!\", \"happy\"),\n",
    "    (\"Feeling amazing today!\", \"happy\"),\n",
    "    (\"Guess what? I passed the interview!\", \"happy\"),\n",
    "    (\"I'm so proud of what we accomplished\", \"happy\"),\n",
    "    (\"Today was one of the best days ever\", \"happy\"),\n",
    "    (\"I'm so excited about our progress!\", \"happy\"),\n",
    "    (\"I feel so full of energy and happiness!\", \"happy\"),\n",
    "\n",
    "    # 6. Curious / Intellectual\n",
    "    (\"How does self-attention work in transformers?\", \"curious\"),\n",
    "    (\"What is the difference between MVVM and MVI architecture?\", \"curious\"),\n",
    "    (\"Can you explain quantum computing in simple terms?\", \"curious\"),\n",
    "    (\"Why is pgvector faster than basic cosine search in Python?\", \"curious\"),\n",
    "    (\"Tell me about the history of artificial neural networks\", \"curious\"),\n",
    "    (\"What are the best practices for Jetpack Compose state hoisting?\", \"curious\"),\n",
    "    (\"How do diffusion models denoise latent space?\", \"curious\"),\n",
    "    (\"Explain how Reciprocal Rank Fusion combines sparse and dense vectors\", \"curious\"),\n",
    "\n",
    "    # 7. Playful / Witty\n",
    "    (\"You're teasing me, aren't you?\", \"playful\"),\n",
    "    (\"Haha, you're pretty funny for an AI\", \"playful\"),\n",
    "    (\"I bet you can't beat me in a riddle challenge\", \"playful\"),\n",
    "    (\"Are you trying to be smart with me?\", \"playful\"),\n",
    "    (\"You're looking extra cute today\", \"playful\"),\n",
    "    (\"Come on, don't be shy!\", \"playful\"),\n",
    "    (\"Tell me your best witty joke\", \"playful\"),\n",
    "\n",
    "    # 8. Chit-chat / Greetings\n",
    "    (\"Good morning Athina!\", \"chit_chat\"),\n",
    "    (\"Hey there, how are you doing?\", \"chit_chat\"),\n",
    "    (\"What are you up to right now?\", \"chit_chat\"),\n",
    "    (\"Good night, talk to you tomorrow\", \"chit_chat\"),\n",
    "    (\"Just checking in on you\", \"chit_chat\"),\n",
    "    (\"Hello Athina!\", \"chit_chat\"),\n",
    "    (\"How's your day going so far?\", \"chit_chat\"),\n",
    "    (\"I'm back home\", \"chit_chat\")\n",
    "]\n",
    "\n",
    "X_texts = [x[0] for x in TRAINING_DATA]\n",
    "y_labels = [x[1] for x in TRAINING_DATA]\n",
    "classes = sorted(list(set(y_labels)))\n",
    "\n",
    "print(f\"Total training instances: {len(X_texts)} across {len(classes)} classes:\")\n",
    "for c, count in Counter(y_labels).items():\n",
    "    print(f\"  • {c}: {count} samples\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Step 3: Train Scikit-Learn TF-IDF + Logistic Regression Pipeline"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "pipeline = Pipeline([\n",
    "    ('tfidf', TfidfVectorizer(\n",
    "        ngram_range=(1, 2),\n",
    "        sublinear_tf=True,\n",
    "        lowercase=True,\n",
    "        max_features=2500\n",
    "    )),\n",
    "    ('clf', LogisticRegression(\n",
    "        C=2.5,\n",
    "        max_iter=300,\n",
    "        class_weight='balanced'\n",
    "    ))\n",
    "])\n",
    "\n",
    "pipeline.fit(X_texts, y_labels)\n",
    "print(\"Model trained successfully!\")\n",
    "\n",
    "# 5-Fold Cross Validation\n",
    "scores = cross_val_score(pipeline, X_texts, y_labels, cv=4)\n",
    "print(f\"Cross-Validation Mean Accuracy: {scores.mean() * 100:.1f}% (+/- {scores.std() * 100:.1f}%)\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Step 4: Evaluate with Confusion Matrix & Classification Report"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "y_pred = pipeline.predict(X_texts)\n",
    "\n",
    "print(\"--- Classification Report ---\")\n",
    "print(classification_report(y_labels, y_pred, target_names=classes))\n",
    "\n",
    "cm = confusion_matrix(y_labels, y_pred, labels=classes)\n",
    "\n",
    "plt.figure(figsize=(8, 6))\n",
    "sns.heatmap(cm, annot=True, fmt='d', cmap='YlOrBr', xticklabels=classes, yticklabels=classes)\n",
    "plt.title('Athina Personality Intent & Emotion Confusion Matrix')\n",
    "plt.xlabel('Predicted Label')\n",
    "plt.ylabel('True Label')\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Step 5: Visualize Most Influential Words Per Class"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "vectorizer = pipeline.named_steps['tfidf']\n",
    "classifier = pipeline.named_steps['clf']\n",
    "feature_names = np.array(vectorizer.get_feature_names_out())\n",
    "\n",
    "plt.figure(figsize=(14, 10))\n",
    "for i, class_name in enumerate(classes):\n",
    "    top_indices = np.argsort(classifier.coef_[i])[-5:]\n",
    "    top_features = feature_names[top_indices]\n",
    "    top_weights = classifier.coef_[i][top_indices]\n",
    "    \n",
    "    plt.subplot(3, 3, i + 1)\n",
    "    plt.barh(top_features, top_weights, color='#f59e0b')\n",
    "    plt.title(f\"{class_name}\", fontsize=11, fontweight='bold')\n",
    "    plt.xlabel('Weight')\n",
    "\n",
    "plt.tight_layout()\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Step 6: Export Models to `ml/exports/`\n",
    "Exports both:\n",
    "1. `classifier_model.json` (Ultra-lightweight JSON centroid model)\n",
    "2. `intent_classifier.onnx` (Standard ONNX format using `skl2onnx`)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "export_dir = \"/home/ratul/Athena/ml/exports\"\n",
    "os.makedirs(export_dir, exist_ok=True)\n",
    "\n",
    "# 1. Export ONNX using skl2onnx\n",
    "try:\n",
    "    from skl2onnx import convert_sklearn\n",
    "    from skl2onnx.common.data_types import StringTensorType\n",
    "    \n",
    "    initial_type = [('text_input', StringTensorType([None, 1]))]\n",
    "    onnx_model = convert_sklearn(pipeline, initial_types=initial_type, target_opset=12)\n",
    "    \n",
    "    onnx_path = os.path.join(export_dir, \"intent_classifier.onnx\")\n",
    "    with open(onnx_path, \"wb\") as f:\n",
    "        f.write(onnx_model.SerializeToString())\n",
    "    print(f\" Exported ONNX model to: {onnx_path}\")\n",
    "except Exception as e:\n",
    "    print(f\"Note: ONNX conversion skipped ({e}). JSON export will be used.\")\n",
    "\n",
    "# 2. Re-export clean verified JSON model for backend runtime\n",
    "from ml.train_classifier import train_and_export\n",
    "train_and_export()\n",
    "print(\" JSON Model exported and validated!\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Step 7: Interactive Live Tester (Classification + Style Vector Guidance)"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "from backend.app.personality.state import PersonalityState\n",
    "from backend.app.personality.style_model import compute_style_vector\n",
    "\n",
    "test_queries = [\n",
    "    \"Can you take a cute photo of yourself right now?\",\n",
    "    \"I've been feeling so lonely and sad all evening\",\n",
    "    \"We just shipped the new version, absolutely thrilled!\",\n",
    "    \"Save this note: explore Kotlin Coroutines channels on Android\",\n",
    "    \"Wake me up tomorrow at 6:45 AM\",\n",
    "    \"Haha, you think you're pretty clever don't you?\",\n",
    "    \"How does Reciprocal Rank Fusion actually score document ranks?\"\n",
    "]\n",
    "\n",
    "state = PersonalityState.calculate_current_state()\n",
    "print(f\"Current Athina Baseline State: Mood='{state.mood}', Location='{state.location}'\\n\")\n",
    "\n",
    "for query in test_queries:\n",
    "    tone_guidance, style = compute_style_vector(query, state)\n",
    "    print(f\"User: '{query}'\")\n",
    "    print(f\"  → Detected Intent/Emotion : {style['predicted_class']} (Conf: {style['confidence']})\")\n",
    "    print(f\"  → Style Vector            : Warmth={style['warmth']}, Humor={style['humor']}, Length={style['reply_length']}\")\n",
    "    print(f\"  → Athina Tone Guidance    : \\\"{tone_guidance}\\\"\")\n",
    "    print(\"-\" * 80)"
   ]
  }
 ],
 "metadata": {
  "language_info": {
   "name": "python"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 0
}

with open("/home/ratul/Athena/ml/train_personality_models.ipynb", "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=2)

print("Generated /home/ratul/Athena/ml/train_personality_models.ipynb successfully!")
