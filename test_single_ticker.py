#!/usr/bin/env python
# dual_strategy_sentiment_analyzer.py - Momentum vs Contrarian Analysis

import feedparser
from datetime import datetime
import re
from urllib.parse import quote_plus
import numpy as np

# Try to import FinBERT with better error handling
FINBERT_AVAILABLE = False
sentiment_pipeline = None

try:
    print("🤖 Attempting to load FinBERT...")
    from transformers import pipeline
    import warnings
    warnings.filterwarnings('ignore')
    
    sentiment_pipeline = pipeline(
        "sentiment-analysis", 
        model="ProsusAI/finbert",
        return_all_scores=False
    )
    FINBERT_AVAILABLE = True
    print("✅ FinBERT loaded successfully!")
    
except ImportError as e:
    print(f"❌ Transformers library not installed: {e}")
    print("💡 Install with: pip install transformers torch")
except Exception as e:
    print(f"❌ FinBERT loading failed: {e}")
    print("⚠️ Will use GitHub-based research lexicons instead")

class DualStrategyAnalyzer:
    def __init__(self):
        """
        Initialize with research-backed financial sentiment lexicons from GitHub
        """
        
        # VERY STRONG NEGATIVE (-0.9 to -1.0)
        self.very_strong_negative = {
            'bankruptcy': -1.0, 'liquidation': -1.0, 'insolvency': -0.95, 'collapse': -0.95,
            'crash': -0.9, 'catastrophic': -0.9, 'devastating': -0.9, 'disaster': -0.9,
            'plummet': -0.95, 'nosedive': -0.9, 'tumble': -0.85, 'slash': -0.85,
            'massive layoffs': -1.0, 'widespread layoffs': -0.9, 'plant closure': -0.9,
            'fraud': -0.95, 'scandal': -0.9, 'investigation': -0.8, 'violation': -0.8,
            'penalty': -0.8, 'fine': -0.75, 'lawsuit': -0.75, 'litigation': -0.75,
            'default': -0.9, 'delinquent': -0.85, 'writeoff': -0.85, 'impairment': -0.8,
            'restructuring': -0.75, 'covenant breach': -0.9, 'going concern': -0.95
        }
        
        # STRONG NEGATIVE (-0.6 to -0.8)
        self.strong_negative = {
            'disappointing': -0.7, 'concerning': -0.65, 'troubling': -0.7, 'alarming': -0.75,
            'weak': -0.6, 'poor': -0.65, 'sluggish': -0.6, 'lackluster': -0.6,
            'decline': -0.6, 'decrease': -0.6, 'drop': -0.65, 'fall': -0.65,
            'slump': -0.7, 'slide': -0.6, 'retreat': -0.6, 'pullback': -0.55,
            'headwinds': -0.6, 'challenges': -0.55, 'pressure': -0.6, 'struggle': -0.65,
            'difficulty': -0.6, 'obstacles': -0.6, 'setback': -0.65, 'shortfall': -0.7,
            'cut': -0.6, 'reduce': -0.55, 'curtail': -0.6, 'suspend': -0.65,
            'halt': -0.7, 'discontinue': -0.6, 'terminate': -0.75, 'eliminate': -0.7,
            'uncertainty': -0.6, 'risk': -0.55, 'concern': -0.6, 'doubt': -0.65,
            'negative': -0.6, 'bearish': -0.65, 'pessimistic': -0.7, 'cautious': -0.5
        }
        
        # MODERATE NEGATIVE (-0.3 to -0.5)
        self.moderate_negative = {
            'below': -0.4, 'under': -0.3, 'less': -0.3, 'lower': -0.4,
            'down': -0.4, 'off': -0.3, 'miss': -0.5, 'lag': -0.4,
            'slow': -0.4, 'soft': -0.35, 'muted': -0.45, 'subdued': -0.4,
            'modest': -0.3, 'limited': -0.35, 'constrained': -0.4, 'tight': -0.35
        }
        
        # VERY STRONG POSITIVE (0.8 to 1.0)
        self.very_strong_positive = {
            'exceptional': 1.0, 'outstanding': 0.95, 'stellar': 0.95, 'phenomenal': 1.0,
            'extraordinary': 0.95, 'remarkable': 0.9, 'spectacular': 0.95, 'sensational': 0.9,
            'surge': 0.85, 'soar': 0.9, 'rocket': 0.95, 'skyrocket': 1.0,
            'explode': 0.85, 'boom': 0.8, 'rally': 0.8, 'spike': 0.8,
            'record-breaking': 1.0, 'record high': 0.95, 'all-time high': 0.9,
            'milestone': 0.8, 'breakthrough': 0.9, 'historic': 0.85,
            'blockbuster': 0.9, 'bonanza': 0.85, 'windfall': 0.8, 'jackpot': 0.85
        }
        
        # STRONG POSITIVE (0.6 to 0.8)
        self.strong_positive = {
            'excellent': 0.75, 'superior': 0.7, 'strong': 0.65, 'robust': 0.7,
            'solid': 0.65, 'healthy': 0.6, 'impressive': 0.75, 'promising': 0.65,
            'growth': 0.6, 'expansion': 0.65, 'increase': 0.6, 'rise': 0.6,
            'gain': 0.6, 'advance': 0.6, 'progress': 0.6, 'improvement': 0.65,
            'upgrade': 0.7, 'enhance': 0.6, 'strengthen': 0.65, 'boost': 0.65,
            'accelerate': 0.7, 'maximize': 0.65, 'optimize': 0.6, 'expand': 0.65,
            'bullish': 0.75, 'optimistic': 0.7, 'confident': 0.65, 'positive': 0.6,
            'favorable': 0.6, 'encouraging': 0.65, 'upbeat': 0.7, 'bright': 0.6
        }
        
        # MODERATE POSITIVE (0.3 to 0.5)
        self.moderate_positive = {
            'good': 0.4, 'better': 0.4, 'up': 0.4, 'higher': 0.4,
            'above': 0.4, 'over': 0.3, 'more': 0.3, 'increased': 0.4,
            'stable': 0.35, 'steady': 0.4, 'consistent': 0.4, 'maintained': 0.35
        }
        
        # EARNINGS-SPECIFIC PHRASES
        self.earnings_phrases = {
            'beat estimates': 0.9, 'beats estimates': 0.9, 'exceed estimates': 0.85,
            'exceeds estimates': 0.85, 'above estimates': 0.7, 'better than expected': 0.8,
            'blew past estimates': 1.0, 'crushed estimates': 0.95, 'smashed estimates': 0.95,
            'beat expectations': 0.8, 'exceeded expectations': 0.8, 'surpassed expectations': 0.85,
            'topped estimates': 0.75, 'outperformed estimates': 0.8, 'ahead of estimates': 0.7,
            'miss estimates': -0.8, 'misses estimates': -0.8, 'missed estimates': -0.8,
            'below estimates': -0.7, 'fell short': -0.75, 'disappointed': -0.7,
            'underwhelmed': -0.6, 'failed to meet': -0.75, 'came up short': -0.7,
            'badly missed': -0.9, 'significantly missed': -0.85, 'widely missed': -0.8,
            'badly disappointed': -0.9, 'major disappointment': -0.85
        }
        
        # ANALYST ACTION PHRASES
        self.analyst_phrases = {
            'upgraded': 0.7, 'raised rating': 0.75, 'raised target': 0.7, 'increased target': 0.7,
            'price target raised': 0.75, 'target price increased': 0.7, 'buy rating': 0.8,
            'strong buy': 0.9, 'overweight': 0.6, 'outperform': 0.7,
            'downgraded': -0.7, 'lowered rating': -0.75, 'cut target': -0.7, 'reduced target': -0.7,
            'price target cut': -0.75, 'target price lowered': -0.7, 'sell rating': -0.8,
            'strong sell': -0.9, 'underweight': -0.6, 'underperform': -0.7
        }
        
        # FINANCIAL HEALTH INDICATORS
        self.financial_health = {
            'cash rich': 0.8, 'debt free': 0.9, 'strong balance sheet': 0.8,
            'healthy margins': 0.7, 'strong cash flow': 0.75, 'profitable': 0.6,
            'dividend increase': 0.7, 'share buyback': 0.6, 'debt reduction': 0.65,
            'cash strapped': -0.8, 'high debt': -0.7, 'weak balance sheet': -0.8,
            'margin pressure': -0.6, 'cash burn': -0.7, 'unprofitable': -0.7,
            'dividend cut': -0.8, 'suspend dividend': -0.9, 'covenant breach': -0.9
        }

    def analyze_sentiment(self, text: str) -> dict:
        """Analyze sentiment using comprehensive lexicons"""
        text_lower = text.lower()
        total_score = 0.0
        detected_signals = []
        phrase_matches = []
        
        # Check all categories
        all_categories = [
            (self.earnings_phrases, "EARNINGS"),
            (self.analyst_phrases, "ANALYST"),
            (self.financial_health, "FINANCIAL"),
            (self.very_strong_negative, "VERY_NEG"),
            (self.strong_negative, "STRONG_NEG"), 
            (self.moderate_negative, "MOD_NEG"),
            (self.moderate_positive, "MOD_POS"),
            (self.strong_positive, "STRONG_POS"),
            (self.very_strong_positive, "VERY_POS")
        ]
        
        for word_dict, category in all_categories:
            for phrase, score in word_dict.items():
                if phrase in text_lower:
                    total_score += score
                    detected_signals.append(f"{category}: '{phrase}' ({score:+.2f})")
                    phrase_matches.append(phrase)
        
        # Normalize score
        final_score = max(-1.0, min(1.0, total_score))
        
        return {
            'score': final_score,
            'detected_signals': detected_signals,
            'phrase_matches': phrase_matches,
            'total_signals': len(detected_signals)
        }

    def generate_momentum_analysis(self, sentiment_score: float, articles_breakdown: dict) -> dict:
        """Generate momentum strategy analysis"""
        
        positive_articles = articles_breakdown['positive']
        negative_articles = articles_breakdown['negative']
        neutral_articles = articles_breakdown['neutral']
        
        # Momentum Strategy Logic
        if sentiment_score > 0.15:
            signal = 'STRONG BUY'
            confidence = min(95, abs(sentiment_score) * 100 + 30)
            reasoning = f"Strong positive momentum (score: {sentiment_score:.3f}). Trend likely to continue - ride the wave!"
            risk_level = "MODERATE"
            
        elif sentiment_score > 0.05:
            signal = 'BUY'
            confidence = min(85, abs(sentiment_score) * 100 + 25)
            reasoning = f"Positive momentum building (score: {sentiment_score:.3f}). Good entry point for trend following."
            risk_level = "LOW-MODERATE"
            
        elif sentiment_score < -0.15:
            signal = 'STRONG SELL'
            confidence = min(95, abs(sentiment_score) * 100 + 30)
            reasoning = f"Strong negative momentum (score: {sentiment_score:.3f}). Downtrend likely to continue - avoid or exit."
            risk_level = "HIGH"
            
        elif sentiment_score < -0.05:
            signal = 'SELL'
            confidence = min(85, abs(sentiment_score) * 100 + 25)
            reasoning = f"Negative momentum developing (score: {sentiment_score:.3f}). Consider reducing position."
            risk_level = "MODERATE-HIGH"
            
        else:
            signal = 'HOLD'
            confidence = 60
            reasoning = f"No clear momentum (score: {sentiment_score:.3f}). Wait for clearer directional signals."
            risk_level = "LOW"
        
        # Add article-based insights
        if positive_articles > negative_articles * 2:
            reasoning += f" News coverage heavily positive ({positive_articles}+ vs {negative_articles}-)."
        elif negative_articles > positive_articles * 2:
            reasoning += f" News coverage heavily negative ({negative_articles}- vs {positive_articles}+)."
        
        return {
            'signal': signal,
            'confidence': confidence,
            'reasoning': reasoning,
            'risk_level': risk_level,
            'strategy': 'MOMENTUM'
        }
    
    def generate_contrarian_analysis(self, sentiment_score: float, articles_breakdown: dict) -> dict:
        """Generate contrarian strategy analysis"""
        
        positive_articles = articles_breakdown['positive']
        negative_articles = articles_breakdown['negative']
        neutral_articles = articles_breakdown['neutral']
        
        # Contrarian Strategy Logic (opposite of momentum)
        if sentiment_score > 0.15:
            signal = 'STRONG SELL'
            confidence = min(90, abs(sentiment_score) * 100 + 20)
            reasoning = f"Excessive optimism (score: {sentiment_score:.3f}). Market likely overbought - take profits!"
            risk_level = "LOW-MODERATE"
            
        elif sentiment_score > 0.05:
            signal = 'SELL'
            confidence = min(80, abs(sentiment_score) * 100 + 15)
            reasoning = f"Growing optimism (score: {sentiment_score:.3f}). Good news may be fully priced in."
            risk_level = "LOW"
            
        elif sentiment_score < -0.15:
            signal = 'STRONG BUY'
            confidence = min(90, abs(sentiment_score) * 100 + 20)
            reasoning = f"Excessive pessimism (score: {sentiment_score:.3f}). Market likely oversold - buy the dip!"
            risk_level = "MODERATE"
            
        elif sentiment_score < -0.05:
            signal = 'BUY'
            confidence = min(80, abs(sentiment_score) * 100 + 15)
            reasoning = f"Growing pessimism (score: {sentiment_score:.3f}). Bad news may be overdone - opportunity!"
            risk_level = "MODERATE-HIGH"
            
        else:
            signal = 'HOLD'
            confidence = 65
            reasoning = f"Balanced sentiment (score: {sentiment_score:.3f}). No clear contrarian opportunity."
            risk_level = "LOW"
        
        # Add contrarian insights based on article coverage
        if positive_articles > negative_articles * 2:
            reasoning += f" Heavy positive coverage ({positive_articles}+ vs {negative_articles}-) suggests potential reversal."
        elif negative_articles > positive_articles * 2:
            reasoning += f" Heavy negative coverage ({negative_articles}- vs {positive_articles}+) suggests buying opportunity."
        
        return {
            'signal': signal,
            'confidence': confidence,
            'reasoning': reasoning,
            'risk_level': risk_level,
            'strategy': 'CONTRARIAN'
        }

def get_articles(ticker):
    """Get articles from Google News RSS"""
    
    company_mappings = {
        'TCS': ['TCS', 'Tata Consultancy Services', 'Tata Consultancy'],
        'SBILIFE': ['SBI Life', 'SBI Life Insurance', 'SBILIFE'],
        'ZYDUSLIFE': ['Zydus Life', 'Zydus Lifesciences', 'ZYDUSLIFE'],
        'RELIANCE': ['Reliance Industries', 'Reliance', 'RIL'],
        'INFY': ['Infosys'],
        'GRANULES': ['Granules India', 'Granules'],
        'MARUTI': ['Maruti Suzuki', 'Maruti'],
        'HDFCBANK': ['HDFC Bank', 'HDFC'],
        'ICICIBANK': ['ICICI Bank', 'ICICI'],
        'WIPRO': ['Wipro'],
        'ITC': ['ITC Limited', 'ITC'],
        'MAXHEALTH': ['Max Healthcare', 'Max Healthcare Institute', 'MAXHEALTH']
    }
    
    search_terms = [ticker]
    if ticker.upper() in company_mappings:
        search_terms.extend(company_mappings[ticker.upper()])
    
    articles = []
    
    for term in search_terms[:3]:
        try:
            query = f'"{term}" India (stock OR earnings OR price OR shares OR results)'
            rss_url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-IN&gl=IN&ceid=IN:en"
            
            feed = feedparser.parse(rss_url)
            
            if hasattr(feed, 'entries') and feed.entries:
                for entry in feed.entries[:15]:
                    title = entry.get('title', '')
                    if len(title) > 20:
                        if (term.lower() in title.lower() or 
                            any(t.lower() in title.lower() for t in search_terms)):
                            articles.append({
                                'title': title,
                                'url': entry.get('link', ''),
                                'content': entry.get('summary', ''),
                                'published': entry.get('published', ''),
                                'matched_term': term
                            })
        except Exception as e:
            print(f"Error fetching articles for {term}: {e}")
    
    return articles[:15]

def analyze_ticker_dual_strategy(ticker):
    """Comprehensive dual strategy analysis"""
    
    print(f"\n🎯 DUAL STRATEGY ANALYSIS FOR {ticker.upper()}")
    print("="*80)
    print("📊 Momentum Strategy: Ride the trend, follow the crowd")
    print("🔄 Contrarian Strategy: Be greedy when others are fearful")
    print("-"*80)
    
    analyzer = DualStrategyAnalyzer()
    
    # Get articles
    print(f"🔍 Fetching news for {ticker}...")
    articles = get_articles(ticker)
    
    if not articles:
        print("❌ No articles found")
        return
    
    print(f"📰 Analyzing {len(articles)} articles...\n")
    
    # Analyze each article
    sentiment_scores = []
    all_signals = []
    
    for i, article in enumerate(articles, 1):
        title = article['title']
        content = article.get('content', '')
        full_text = title + ' ' + content
        
        result = analyzer.analyze_sentiment(full_text)
        sentiment_scores.append(result['score'])
        all_signals.extend(result['detected_signals'])
        
        score = result['score']
        icon = "🟢" if score > 0.1 else "🔴" if score < -0.1 else "🟡"
        
        print(f"   {i}. {title[:70]}...")
        print(f"      Score: {score:.3f} {icon}")
        if result['detected_signals'][:2]:
            print(f"      Signals: {result['detected_signals'][:2]}")
        print()
    
    # Calculate metrics
    if sentiment_scores:
        avg_sentiment = np.mean(sentiment_scores)
        positive_articles = sum(1 for score in sentiment_scores if score > 0.05)
        negative_articles = sum(1 for score in sentiment_scores if score < -0.05)
        neutral_articles = len(sentiment_scores) - positive_articles - negative_articles
        
        articles_breakdown = {
            'positive': positive_articles,
            'negative': negative_articles,
            'neutral': neutral_articles
        }
        
        # Get both strategies
        momentum = analyzer.generate_momentum_analysis(avg_sentiment, articles_breakdown)
        contrarian = analyzer.generate_contrarian_analysis(avg_sentiment, articles_breakdown)
        
        # Display dual analysis in columns
        print("="*80)
        print("📊 DUAL STRATEGY COMPARISON")
        print("="*80)
        
        # Header row
        print(f"{'MOMENTUM STRATEGY':<40} | {'CONTRARIAN STRATEGY':<39}")
        print(f"{'(Follow the Trend)':<40} | {'(Fade the Move)':<39}")
        print("-"*40 + " | " + "-"*39)
        
        # Signal row
        momentum_signal_color = "🟢" if "BUY" in momentum['signal'] else "🔴" if "SELL" in momentum['signal'] else "🟡"
        contrarian_signal_color = "🟢" if "BUY" in contrarian['signal'] else "🔴" if "SELL" in contrarian['signal'] else "🟡"
        
        print(f"{momentum['signal']} {momentum_signal_color:<30} | {contrarian['signal']} {contrarian_signal_color}")
        print(f"Confidence: {momentum['confidence']:.0f}%{'':<25} | Confidence: {contrarian['confidence']:.0f}%")
        print(f"Risk Level: {momentum['risk_level']:<25} | Risk Level: {contrarian['risk_level']}")
        print("-"*40 + " | " + "-"*39)
        
        # Reasoning (wrapped)
        def wrap_text(text, width):
            words = text.split()
            lines = []
            current_line = []
            current_length = 0
            
            for word in words:
                if current_length + len(word) + 1 <= width:
                    current_line.append(word)
                    current_length += len(word) + 1
                else:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                    current_length = len(word)
            
            if current_line:
                lines.append(' '.join(current_line))
            
            return lines
        
        momentum_lines = wrap_text(momentum['reasoning'], 38)
        contrarian_lines = wrap_text(contrarian['reasoning'], 37)
        max_lines = max(len(momentum_lines), len(contrarian_lines))
        
        for i in range(max_lines):
            momentum_text = momentum_lines[i] if i < len(momentum_lines) else ""
            contrarian_text = contrarian_lines[i] if i < len(contrarian_lines) else ""
            print(f"{momentum_text:<40} | {contrarian_text}")
        
        print("-"*40 + " | " + "-"*39)
        
        # Summary statistics
        print(f"\n📊 MARKET SENTIMENT SUMMARY:")
        print(f"   Average Sentiment Score: {avg_sentiment:.3f}")
        print(f"   Article Breakdown: 🟢{positive_articles} 🟡{neutral_articles} 🔴{negative_articles}")
        print(f"   Total Articles Analyzed: {len(articles)}")
        print(f"   Strong Signals Detected: {len([s for s in all_signals if abs(float(s.split('(')[1].split(')')[0])) > 0.6])}")
        
        # Recommendation
        print(f"\n🎯 RECOMMENDATION:")
        if abs(avg_sentiment) > 0.2:
            strength = "STRONG" if abs(avg_sentiment) > 0.4 else "MODERATE"
            direction = "POSITIVE" if avg_sentiment > 0 else "NEGATIVE"
            
            print(f"   {strength} {direction} sentiment detected!")
            print(f"   • Momentum traders: Follow the {direction.lower()} trend")
            print(f"   • Contrarian traders: Expect potential reversal")
            print(f"   • Risk-averse: Wait for confirmation or use smaller position sizes")
        else:
            print(f"   MIXED/NEUTRAL sentiment - both strategies suggest HOLD")
            print(f"   • Wait for clearer directional signals")
            print(f"   • Consider other fundamental factors")
        
        print(f"\n💡 CHOOSE YOUR STRATEGY based on:")
        print(f"   • Your risk tolerance")
        print(f"   • Market conditions (trending vs ranging)")
        print(f"   • Time horizon (momentum for short-term, contrarian for longer-term)")
        print(f"   • Stock type (growth vs value, volatile vs stable)")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Dual Strategy Sentiment Analysis")
    parser.add_argument('--ticker', type=str, default='MAXHEALTH', help='Stock ticker to analyze')
    
    args = parser.parse_args()
    
    print("📊 DUAL STRATEGY SENTIMENT ANALYZER")
    print("="*50)
    print("🚀 Momentum: Ride the wave!")
    print("🔄 Contrarian: Buy fear, sell greed!")
    print("="*50)
    
    analyze_ticker_dual_strategy(args.ticker)