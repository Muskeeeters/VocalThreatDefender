from transformers import pipeline

class VishingTextClassifier:
    def __init__(self):
        # Utilizing a robust Zero-Shot classification pipeline to identify malicious intent instantly
        self.classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
        
        # Security vectors targeted by phone scammers
        self.threat_labels = [
            "legitimate customer service", 
            "urgent financial wire request", 
            "credential harvesting or password request", 
            "impersonation of authority or law enforcement"
        ]

    def analyze_transcript(self, text):
        if not text.strip():
            return {"intent": "silent/unknown", "threat_confidence": 0.0}
            
        res = self.classifier(text, self.threat_labels)
        top_label = res['labels'][0]
        top_score = res['scores'][0]
        
        # Calculate overall risk based on malicious categories
        is_malicious = top_label != "legitimate customer service"
        
        return {
            "dominant_intent": top_label,
            "intent_confidence": float(top_score),
            "is_malicious_intent": is_malicious
        }