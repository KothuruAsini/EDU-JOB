import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
import joblib

# Load dataset
df = pd.read_excel("JobRole.xlsx")

print("Before Cleaning:\n", df.head())

# Drop duplicates and nulls
df.drop_duplicates(inplace=True)
df.dropna(inplace=True)

# Encoding categorical columns
le = LabelEncoder()

for col in df.columns:
    if df[col].dtype == "object":
        df[col] = le.fit_transform(df[col])

print("\nAfter Encoding:\n", df.head())

# Fix target column (correct name from dataset)
TARGET_COL = "Job Role"

X = df.drop(TARGET_COL, axis=1)
y = df[TARGET_COL]

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train RandomForest model
model = RandomForestClassifier(n_estimators=200, random_state=42)
model.fit(X_train, y_train)

# Save trained model
joblib.dump(model, "jobrole_model.pkl")

print("\n🎉 Model successfully saved as jobrole_model.pkl")
print("Training Accuracy:", model.score(X_train, y_train))
print("Testing Accuracy:", model.score(X_test, y_test))
