# train_pipeline.py
import os
import pandas as pd
import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler, LabelEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import warnings
warnings.filterwarnings("ignore")

HAS_PLOTTING = True
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
except ImportError:
    HAS_PLOTTING = False

DATA_PATH = "JobRole.xlsx"   # ensure file present
OUT_DIR = "artifacts"
os.makedirs(OUT_DIR, exist_ok=True)

print("Loading dataset:", DATA_PATH)
df = pd.read_excel(DATA_PATH)
df.columns = [c.strip() for c in df.columns]

# drop rows without target
df = df.dropna(subset=['Job Role']).copy()

# Text columns cleaning
text_cols = ['Skills', 'Degree', 'Major', 'Specialization',
             'Certification', 'Preferred Industry']
for c in text_cols:
    if c in df.columns:
        df[c] = df[c].fillna('').astype(str).str.strip()

# numeric and categorical lists
numeric_cols = [c for c in ['CGPA', 'Years of Experience'] if c in df.columns]
categorical_cols = [c for c in ['Degree', 'Major', 'Specialization',
                                'Certification', 'Preferred Industry'] if c in df.columns]

# -----------------------------------------------------------------------
# 📊 VISUALIZATION 1 — Job Role Distribution
# -----------------------------------------------------------------------
if HAS_PLOTTING:
    plt.figure(figsize=(10,5))
    df['Job Role'].value_counts().plot(kind='bar')
    plt.title("Job Role Distribution")
    plt.xlabel("Job Roles")
    plt.ylabel("Count")
    plt.tight_layout()
    jobrole_plot_path = os.path.join(OUT_DIR, "jobrole_distribution.png")
    plt.savefig(jobrole_plot_path)
    plt.close()
    print("Saved:", jobrole_plot_path)

# -----------------------------------------------------------------------
# 📊 VISUALIZATION 2 — Scatter Plot (CGPA vs Years of Experience)
# -----------------------------------------------------------------------
if set(['CGPA', 'Years of Experience']).issubset(df.columns):
    if HAS_PLOTTING:
        plt.figure(figsize=(7,5))
        sns.scatterplot(x=df['CGPA'], y=df['Years of Experience'])
        plt.title("CGPA vs Years of Experience")
        plt.tight_layout()
        scatter_path = os.path.join(OUT_DIR, "cgpa_vs_experience.png")
        plt.savefig(scatter_path)
        plt.close()
        print("Saved:", scatter_path)

# -----------------------------------------------------------------------
# 📊 VISUALIZATION 3 — Correlation Heatmap (numeric only)
# -----------------------------------------------------------------------
if len(numeric_cols) > 1:
    if HAS_PLOTTING:
        plt.figure(figsize=(6,5))
        sns.heatmap(df[numeric_cols].corr(), annot=True, cmap="coolwarm")
        plt.title("Correlation Heatmap (Numeric Features)")
        heatmap_path = os.path.join(OUT_DIR, "correlation_heatmap.png")
        plt.savefig(heatmap_path)
        plt.close()
        print("Saved:", heatmap_path)

# -----------------------------------------------------------------------

# Features & target
feature_columns = numeric_cols + categorical_cols + ['Skills']
X = df[feature_columns]
y = df['Job Role'].astype(str)

# Label encoding
le = LabelEncoder()
y_enc = le.fit_transform(y)

# Pipelines
num_pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])

cat_pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
    ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
])

tfidf = TfidfVectorizer(max_features=2000, ngram_range=(1,2))

preprocessor = ColumnTransformer([
    ('num', num_pipeline, numeric_cols),
    ('cat', cat_pipeline, categorical_cols),
    ('text', tfidf, 'Skills'),
], remainder='drop')

clf = RandomForestClassifier(
    n_estimators=500,
    max_depth=40,
    random_state=42,
    n_jobs=-1
)

pipeline = Pipeline([
    ('pre', preprocessor),
    ('clf', clf)
])

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y_enc, test_size=0.2, random_state=42, stratify=y_enc
)

print("Training model...")
pipeline.fit(X_train, y_train)

# Evaluate
y_pred = pipeline.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"Test accuracy: {acc*100:.2f}%")
print("\nClassification Report:\n", classification_report(y_test, y_pred, zero_division=0))

# Save artifacts
pipeline_path = os.path.join(OUT_DIR, "pipeline.pkl")
le_path = os.path.join(OUT_DIR, "label_encoder.pkl")
joblib.dump(pipeline, pipeline_path)
joblib.dump(le, le_path)
print("Saved pipeline:", pipeline_path)
print("Saved label encoder:", le_path)

# -----------------------------------------------------------------------
# (existing) Feature importance remains unchanged
# -----------------------------------------------------------------------
if HAS_PLOTTING:
    print("Generating feature importance plot...")

    feature_names = []
    if numeric_cols:
        feature_names.extend(numeric_cols)
    if categorical_cols:
        ohe = pipeline.named_steps['pre'].named_transformers_['cat']['onehot']
        try:
            feature_names.extend(ohe.get_feature_names_out(categorical_cols))
        except:
            for col in categorical_cols:
                feature_names.append(col)
    if "Skills" in X.columns:
        tf = pipeline.named_steps['pre'].named_transformers_['text']
        try:
            feature_names.extend(list(tf.get_feature_names_out()))
        except:
            feature_names.extend([f"skill_{i}" for i in range(2000)])

    importances = pipeline.named_steps['clf'].feature_importances_
    minlen = min(len(feature_names), len(importances))
    feat_df = pd.DataFrame({
        "feature": feature_names[:minlen],
        "importance": importances[:minlen]
    })
    feat_df = feat_df.sort_values(by="importance", ascending=False).head(40)

    plt.figure(figsize=(10, 10))
    plt.barh(feat_df["feature"], feat_df["importance"])
    plt.gca().invert_yaxis()
    plt.title("Top Feature Importances")
    plt.tight_layout()
    plot_path = os.path.join(OUT_DIR, "feature_importance.png")
    plt.savefig(plot_path)
    print("Saved feature importance:", plot_path)

print("Training script finished.")
