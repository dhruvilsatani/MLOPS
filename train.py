import numpy as np
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os
import argparse

# MLflow is optional: if it isn't installed (or tracking is disabled) the
# pipeline still trains and saves the model exactly as before.
try:
    import mlflow
    import mlflow.sklearn

    _MLFLOW_AVAILABLE = True
except ImportError:
    _MLFLOW_AVAILABLE = False

MODEL_DIR = "model"

MODEL_PATH = os.path.join(MODEL_DIR, "model.pkl")

# Name of the MLflow experiment runs are grouped under.
EXPERIMENT_NAME = "iris-classifier"

# Order matches sklearn's Iris target indices (0, 1, 2)
CLASS_NAMES = ["Setosa", "Versicolor", "Virginica"]
FEATURE_NAMES = ["sepal_length", "sepal_width", "petal_length", "petal_width"]


def train(add_noise: bool = False, noise_std: float = 0.4, random_state: int = 42,
          track: bool = True):
    """Train a RandomForest classifier on the Iris dataset and persist it.

    By default the model is trained on the clean dataset so that the features
    seen at serving time (real measurements) match the training distribution.
    Optional Gaussian noise can be enabled for experimentation, but it is off
    by default to avoid a train/serve skew.

    When ``track`` is True and MLflow is installed, parameters, metrics and the
    trained model are logged to a local MLflow run (view with ``mlflow ui``).
    Tracking is best-effort: it never blocks producing model/model.pkl.
    """
    use_mlflow = track and _MLFLOW_AVAILABLE
    if track and not _MLFLOW_AVAILABLE:
        print("Note: mlflow not installed; skipping experiment tracking.")

    print("Step 1: Loading Iris dataset...")
    iris = load_iris()
    X = iris.data
    y = iris.target

    if add_noise:
        print(f"        Injecting Gaussian noise (std={noise_std}) for experimentation...")
        rng = np.random.default_rng(random_state)
        X = X + rng.normal(0, noise_std, X.shape)

    print("Step 2: Splitting data (80% Training, 20% Testing)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state, stratify=y
    )

    print("Step 3: Training RandomForest Classifier...")
    n_estimators = 100
    max_depth = 3
    clf = RandomForestClassifier(
        n_estimators=n_estimators, random_state=random_state, max_depth=max_depth
    )
    clf.fit(X_train, y_train)

    print("Step 4: Evaluating Model Performance...")
    predictions = clf.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    report = classification_report(y_test, predictions, target_names=iris.target_names)
    cv_scores = cross_val_score(clf, X, y, cv=5)


    print("\n" + "=" * 50 + "\n             RANDOM FOREST METRICS             \n" + "=" * 50)
    print(f"1. General Accuracy (Test Set) : {(accuracy * 100):.2f}%")
    print(f"2. Cross-Validation (5 Folds)  : {(cv_scores.mean() * 100):.2f}% (+/- {(cv_scores.std() * 100):.2f}%)")
    print(f"   (Fold breakdown: {[round(s, 3) for s in cv_scores]})\n")
    print("3. Detailed Classification Report :")
    print(report)
    print("=" * 50 + "\n")
    
    print("Step 5: Exporting Model...")
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    print(f"-> Successfully saved trained model to '{MODEL_PATH}'")

    if use_mlflow:
        print("Step 6: Logging run to MLflow...")
        try:
            mlflow.set_experiment(EXPERIMENT_NAME)
            with mlflow.start_run():
                # Parameters that define this run.
                mlflow.log_params({
                    "n_estimators": n_estimators,
                    "max_depth": max_depth,
                    "random_state": random_state,
                    "add_noise": add_noise,
                    "noise_std": noise_std if add_noise else 0.0,
                })
                # Metrics we measured.
                mlflow.log_metric("test_accuracy", accuracy)
                mlflow.log_metric("cv_accuracy_mean", cv_scores.mean())
                mlflow.log_metric("cv_accuracy_std", cv_scores.std())
                # The trained model itself, as a versioned artifact.
                mlflow.sklearn.log_model(clf, artifact_path="model")
            print(f"-> Run logged to experiment '{EXPERIMENT_NAME}'. View with: mlflow ui")
        except Exception as e:  # never let tracking break the pipeline
            print(f"Warning: MLflow logging failed ({e}). Model was still saved.")

    return clf



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the Iris RandomForest model.")
    parser.add_argument("--add-noise", action="store_true", help="Inject Gaussian noise (off by default).")
    parser.add_argument("--noise-std", type=float, default=0.4, help="Std dev of Gaussian noise when enabled.")
    parser.add_argument("--no-tracking", action="store_true", help="Disable MLflow experiment tracking.")
    args = parser.parse_args()
    train(add_noise=args.add_noise, noise_std=args.noise_std, track=not args.no_tracking)
