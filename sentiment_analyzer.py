import os
import asyncio
from typing import Dict, Tuple, Optional
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification

class SentimentAnalyzer:
    """
    Advanced sentiment analyzer using NLP models.
    Uses VADER as primary (fast, no GPU required) and BERT as optional enhancement.
    """

    def __init__(self, use_bert: bool = False):
        """
        Initialize the sentiment analyzer.

        Args:
            use_bert: Whether to use BERT model (requires GPU, more accurate but slower)
        """
        self.use_bert = use_bert
        self.vader = SentimentIntensityAnalyzer()

        # BERT model for Spanish text (optional, GPU intensive)
        self.bert_model = None
        self.bert_tokenizer = None

        if use_bert:
            try:
                print("🤖 Loading BERT sentiment model...")
                model_name = "nlptown/bert-base-multilingual-uncased-sentiment"
                self.bert_tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.bert_model = AutoModelForSequenceClassification.from_pretrained(model_name)

                # Move to GPU if available
                if torch.cuda.is_available():
                    self.bert_model = self.bert_model.to('cuda')
                    print("✅ BERT model loaded on GPU")
                else:
                    print("⚠️ BERT model loaded on CPU (slower)")
            except Exception as e:
                print(f"⚠️ Could not load BERT model: {e}. Using VADER only.")
                self.use_bert = False

    def analyze_text_vader(self, text: str) -> Dict:
        """
        Analyze sentiment using VADER (fast, lexicon-based).

        Returns:
            dict: {'compound': float, 'pos': float, 'neu': float, 'neg': float}
        """
        return self.vader.polarity_scores(text)

    def analyze_text_bert(self, text: str) -> Dict:
        """
        Analyze sentiment using BERT (more accurate, slower).

        Returns:
            dict: {'label': str, 'score': float}
        """
        if not self.bert_model or not self.bert_tokenizer:
            raise ValueError("BERT model not loaded")

        inputs = self.bert_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)

        if torch.cuda.is_available():
            inputs = {k: v.to('cuda') for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.bert_model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)

        # Model returns 1-5 star ratings
        predicted_class = torch.argmax(predictions, dim=-1).item()
        confidence = predictions[0][predicted_class].item()

        # Convert to sentiment labels
        if predicted_class <= 2:  # 1-2 stars
            label = "negative"
        elif predicted_class == 3:  # 3 stars
            label = "neutral"
        else:  # 4-5 stars
            label = "positive"

        return {"label": label, "score": confidence, "stars": predicted_class + 1}

    def analyze_sentiment(self, text: str) -> Dict:
        """
        Analyze sentiment of text using available models.

        Args:
            text: Text to analyze

        Returns:
            dict: {
                'sentiment_score': float (-1 to 1),
                'sentiment_label': str ('positive', 'neutral', 'negative'),
                'confidence': float,
                'method': str ('vader' or 'bert'),
                'key_emotions': list
            }
        """
        if not text or len(text.strip()) < 10:
            return {
                'sentiment_score': 0.0,
                'sentiment_label': 'neutral',
                'confidence': 0.0,
                'method': 'insufficient_text',
                'key_emotions': []
            }

        # Use BERT if available and requested
        if self.use_bert:
            try:
                bert_result = self.analyze_text_bert(text)
                sentiment_score = self._bert_to_score(bert_result['label'], bert_result['score'])

                return {
                    'sentiment_score': sentiment_score,
                    'sentiment_label': bert_result['label'],
                    'confidence': bert_result['score'],
                    'method': 'bert',
                    'key_emotions': self._extract_key_emotions(text, bert_result['label'])
                }
            except Exception as e:
                print(f"BERT analysis failed: {e}. Falling back to VADER.")

        # Default to VADER
        vader_result = self.analyze_text_vader(text)
        sentiment_score = vader_result['compound']
        sentiment_label = self._compound_to_label(sentiment_score)
        confidence = max(vader_result['pos'], vader_result['neu'], vader_result['neg'])

        return {
            'sentiment_score': sentiment_score,
            'sentiment_label': sentiment_label,
            'confidence': confidence,
            'method': 'vader',
            'key_emotions': self._extract_key_emotions(text, sentiment_label)
        }

    def _compound_to_label(self, compound: float) -> str:
        """Convert VADER compound score to label."""
        if compound >= 0.05:
            return "positive"
        elif compound <= -0.05:
            return "negative"
        else:
            return "neutral"

    def _bert_to_score(self, label: str, confidence: float) -> float:
        """Convert BERT label to numerical score."""
        score_map = {
            "positive": confidence,
            "neutral": 0.0,
            "negative": -confidence
        }
        return score_map.get(label, 0.0)

    def _extract_key_emotions(self, text: str, sentiment: str) -> list:
        """Extract key emotional indicators from text."""
        emotions = []

        # Simple keyword-based emotion detection
        positive_words = ['excelente', 'fantástico', 'genial', 'perfecto', 'increíble', 'maravilloso']
        negative_words = ['terrible', 'horrible', 'malo', 'pesimo', 'decepcionante', 'frustrante']
        neutral_words = ['normal', 'regular', 'aceptable', 'promedio']

        text_lower = text.lower()

        if sentiment == "positive":
            emotions.extend([word for word in positive_words if word in text_lower])
        elif sentiment == "negative":
            emotions.extend([word for word in negative_words if word in text_lower])
        else:
            emotions.extend([word for word in neutral_words if word in text_lower])

        return list(set(emotions))  # Remove duplicates

    async def analyze_batch(self, texts: list) -> list:
        """
        Analyze sentiment for multiple texts concurrently.

        Args:
            texts: List of text strings

        Returns:
            list: List of sentiment analysis results
        """
        tasks = [asyncio.to_thread(self.analyze_sentiment, text) for text in texts]
        return await asyncio.gather(*tasks)


# Global analyzer instance
_analyzer = None

def get_sentiment_analyzer(use_bert: bool = False) -> SentimentAnalyzer:
    """Get or create global sentiment analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentAnalyzer(use_bert=use_bert)
    return _analyzer


if __name__ == "__main__":
    # Test the analyzer
    analyzer = SentimentAnalyzer(use_bert=False)  # Use VADER for testing

    test_texts = [
        "Este gimnasio es excelente, los entrenadores son muy profesionales",
        "La limpieza deja mucho que desear, está siempre sucio",
        "Es un gimnasio normal, nada especial pero cumple"
    ]

    print("🧠 Testing Sentiment Analyzer...")
    for text in test_texts:
        result = analyzer.analyze_sentiment(text)
        print(f"\nText: {text}")
        print(f"Result: {result}")
