#!/usr/bin/env python3
"""
AIDE Sem2 Feature #2: NLP Article Summarizer (Fixed v2.2)
RSS to 50-word summaries JSON pipeline
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from transformers import BartForConditionalGeneration, BartTokenizer
import torch
import re
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MODEL_NAME = "facebook/bart-large-cnn"
MAX_SUMMARY_WORDS = 50
INPUT_FILE = "rss_output.json"
OUTPUT_FILE = "nlp_summaries.json"

class NLPSummarizer:
    def __init__(self):
        self.model, self.tokenizer, self.device = self._load_model()
        logger.info("NLP Summarizer initialized")
    
    def _load_model(self) -> Tuple['BartForConditionalGeneration', 'BartTokenizer', str]:
        tokenizer = BartTokenizer.from_pretrained(MODEL_NAME)
        model = BartForConditionalGeneration.from_pretrained(MODEL_NAME)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        model.eval()
        return model, tokenizer, device
    
    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text.strip())
        text = re.sub(r'[^\w\s.,!?]', '', text)
        return text[:1024]
    
    def summarize_article(self, title: str, description: str, content: str) -> Dict[str, Any]:
        full_text = f"{title}. {description} {content}".strip()
        cleaned = self.clean_text(full_text)
        
        if len(cleaned.split()) < 30:
            words = cleaned.split()[:MAX_SUMMARY_WORDS]
            return {"summary": ' '.join(words) + "...", "word_count": len(words)}
        
        inputs = self.tokenizer(cleaned, return_tensors="pt", truncation=True, max_length=1024)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            summary_ids = self.model.generate(
                inputs.input_ids,
                max_length=MAX_SUMMARY_WORDS + 20,
                min_length=20,
                length_penalty=2.0,
                num_beams=4,
                early_stopping=True
            )
        
        summary = self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        words = summary.split()
        
        if len(words) > MAX_SUMMARY_WORDS:
            summary = ' '.join(words[:MAX_SUMMARY_WORDS]) + "..."
        
        return {
            "summary": summary.strip(),
            "word_count": len(words),
            "model": MODEL_NAME
        }
    
    def process_rss_file(self, input_path: Path) -> List[Dict[str, Any]]:
        summaries = []
        
        with open(input_path, 'r', encoding='utf-8') as f:
            rss_data = json.load(f)
        
        articles = rss_data.get('articles', [])
        logger.info(f"Processing {len(articles)} articles")
        
        for i, article in enumerate(articles, 1):
            logger.info(f"Article {i}/{len(articles)}")
            
            summary_data = self.summarize_article(
                article.get('title', ''),
                article.get('description', ''),
                article.get('content', '')
            )
            
            summaries.append({
                **article,
                "nlp_summary": summary_data["summary"],
                "summary_stats": {
                    "word_count": summary_data["word_count"],
                    "processed_at": datetime.now().isoformat()
                }
            })
        
        logger.info(f"Generated {len(summaries)} summaries")
        return summaries

def main():
    try:
        summarizer = NLPSummarizer()
        input_path = Path(INPUT_FILE)
        
        if not input_path.exists():
            print(f"{INPUT_FILE} not found. Run rss_data_collection.py first.")
            return
        
        summaries = summarizer.process_rss_file(input_path)
        
        output_data = {
            "platform": "AIDE-GD-Prep",
            "feature": "NLP Summaries v2.2",
            "articles": summaries,
            "generated_at": datetime.now().isoformat()
        }
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"Success: {OUTPUT_FILE} created with {len(summaries)} summaries")
        
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Pipeline failed: {e}")

if __name__ == "__main__":
    main()
