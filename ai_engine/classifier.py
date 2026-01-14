import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import make_pipeline
import joblib
import os

# Save model in the ai_engine directory or root
MODEL_FILE = os.path.join(os.path.dirname(__file__), "expense_model.pkl")

class ExpenseClassifier:
    def __init__(self):
        # Advanced NLP: Character N-Grams + SVM
        # analyzer='char_wb': Looks at inside patterns of words (e.g. "book" inside "notebook")
        # ngram_range=(2, 5): Learns patterns of 2 to 5 letters.
        self.pipeline = make_pipeline(
            TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 5), min_df=1),
            SGDClassifier(loss='modified_huber', random_state=42) # SVM with probabilities
        )
        self.is_trained = False

    def train(self):
        """Trains the model on the cultural dataset."""
        from .pakistani_data import TRAINING_DATA
        
        print("Training Neuro-NLP Model...")
        df = pd.DataFrame(TRAINING_DATA, columns=["text", "category"])
        
        # Train on the patterns
        self.pipeline.fit(df['text'], df['category'])
        self.is_trained = True
        self.save_model()
        print("Neuro-NLP Model trained.")

    def predict(self, text):
        """
        Predicts category using Character Pattern Recognition (Fuzzy AI).
        Understand words it has never seen before if they share roots.
        """
        if not self.is_trained:
            self.load_model()
            
        text_lower = text.lower().strip()
        
        # --- LAYER 1: Rule-Based Overrides (Specific Ambiguities) ---
        # We keep this ONLY for things regular patterns can't catch (like "Oil")
        
        # Oil Ambiguity Rule
        if "oil" in text_lower:
            if any(x in text_lower for x in ["engine", "mobil", "car", "bike", "brake", "change", "filter", "zong"]):
                return "Transportation"
            if not "cooking" in text_lower: 
                return "Food & Dining" # Default (Cooking Oil)

        # --- LAYER 2: Advanced Pattern Prediction ---
        # This will catch "Textbooks" as Education because it knows "Books"
        # This will catch "Ciggies" as Food because it knows "Cigarettes"
        prediction = self.pipeline.predict([text_lower])[0]
        return prediction

    def save_model(self):
        joblib.dump(self.pipeline, MODEL_FILE)

    def load_model(self):
        if os.path.exists(MODEL_FILE):
            self.pipeline = joblib.load(MODEL_FILE)
            self.is_trained = True
        else:
            print("Model file not found. Training new model...")
            self.train()
