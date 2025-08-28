#!/usr/bin/env python
# run_sector_analysis.py - Sector analysis with dual sentiment (momentum + contrarian)

import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(current_dir)

# Add sharing-related imports
import http.server
import socketserver
import threading
import webbrowser
import socket
import zipfile
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Add fresh news filtering imports
from datetime import datetime, timedelta
import pytz

# Add curl_cffi installation to bypass Yahoo Finance rate limits
def install_curl_cffi():
    """Install curl_cffi package if not already installed"""
    try:
        import curl_cffi
        print("curl_cffi is already installed. Will use it to bypass Yahoo Finance rate limits.")
        return True
    except ImportError:
        print("curl_cffi not found. Installing curl_cffi to bypass Yahoo Finance rate limits...")
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "curl_cffi"])
            print("curl_cffi successfully installed.")
            return True
        except Exception as e:
            print(f"Failed to install curl_cffi: {str(e)}")
            print("You may need to manually install it with: pip install curl_cffi")
            return False

# Attempt to install curl_cffi at startup
CURL_CFFI_AVAILABLE = install_curl_cffi()

import json
import argparse
import logging
from datetime import datetime
import pandas as pd
from tabulate import tabulate
import warnings
import feedparser
from urllib.parse import quote_plus
import re
import numpy as np
from app.services.market_analyzer import MarketAnalysisService
from app.services.sector_analyzer import SectorAnalyzer
from app import config

# ======= DUAL SENTIMENT ANALYZER (REPLACES OLD SENTIMENT SYSTEM) =======

class DualStrategyAnalyzer:
    def __init__(self):
        """
        Initialize with research-backed financial sentiment lexicons
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
        
        # Momentum Strategy Logic
        if sentiment_score > 0.15:
            signal = 'STRONG BUY'
            confidence = min(95, abs(sentiment_score) * 100 + 30)
            reasoning = f"Strong positive momentum (score: {sentiment_score:.3f}). Trend likely to continue."
            
        elif sentiment_score > 0.05:
            signal = 'BUY'
            confidence = min(85, abs(sentiment_score) * 100 + 25)
            reasoning = f"Positive momentum building (score: {sentiment_score:.3f}). Good entry point."
            
        elif sentiment_score < -0.15:
            signal = 'STRONG SELL'
            confidence = min(95, abs(sentiment_score) * 100 + 30)
            reasoning = f"Strong negative momentum (score: {sentiment_score:.3f}). Downtrend likely."
            
        elif sentiment_score < -0.05:
            signal = 'SELL'
            confidence = min(85, abs(sentiment_score) * 100 + 25)
            reasoning = f"Negative momentum developing (score: {sentiment_score:.3f}). Consider reducing position."
            
        else:
            signal = 'HOLD'
            confidence = 60
            reasoning = f"No clear momentum (score: {sentiment_score:.3f}). Wait for signals."
        
        return {
            'signal': signal,
            'confidence': confidence,
            'reasoning': reasoning,
            'strategy': 'MOMENTUM'
        }
    
    def generate_contrarian_analysis(self, sentiment_score: float, articles_breakdown: dict) -> dict:
        """Generate contrarian strategy analysis"""
        
        positive_articles = articles_breakdown['positive']
        negative_articles = articles_breakdown['negative']
        
        # Contrarian Strategy Logic (opposite of momentum)
        if sentiment_score > 0.15:
            signal = 'STRONG SELL'
            confidence = min(90, abs(sentiment_score) * 100 + 20)
            reasoning = f"Excessive optimism (score: {sentiment_score:.3f}). Market likely overbought."
            
        elif sentiment_score > 0.05:
            signal = 'SELL'
            confidence = min(80, abs(sentiment_score) * 100 + 15)
            reasoning = f"Growing optimism (score: {sentiment_score:.3f}). Good news may be priced in."
            
        elif sentiment_score < -0.15:
            signal = 'STRONG BUY'
            confidence = min(90, abs(sentiment_score) * 100 + 20)
            reasoning = f"Excessive pessimism (score: {sentiment_score:.3f}). Market likely oversold."
            
        elif sentiment_score < -0.05:
            signal = 'BUY'
            confidence = min(80, abs(sentiment_score) * 100 + 15)
            reasoning = f"Growing pessimism (score: {sentiment_score:.3f}). Bad news may be overdone."
            
        else:
            signal = 'HOLD'
            confidence = 65
            reasoning = f"Balanced sentiment (score: {sentiment_score:.3f}). No clear opportunity."
        
        return {
            'signal': signal,
            'confidence': confidence,
            'reasoning': reasoning,
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
        'MAXHEALTH': ['Max Healthcare', 'Max Healthcare Institute', 'MAXHEALTH'],
        'SAIL': ['SAIL', 'Steel Authority of India'],
        'TATASTEEL': ['Tata Steel', 'TATASTEEL']
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
                                'matched_term': term,
                                'headline': title  # Add headline field for compatibility
                            })
        except Exception as e:
            print(f"Error fetching articles for {term}: {e}")
    
    return articles[:15]

# ======= FRESH NEWS FILTERING LOGIC =======

def filter_recent_articles(articles, days_back=3, debug=False):
    """
    Filter articles to only include recent ones (last N days)
    """
    
    if not articles:
        return []
    
    # Get current time in IST
    try:
        ist_tz = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist_tz)
    except:
        now_ist = datetime.now()
    
    # Calculate cutoff date
    cutoff_date = now_ist - timedelta(days=days_back)
    
    if debug:
        print(f"📅 Current IST time: {now_ist.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📅 Cutoff date (>{days_back} days): {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
    
    recent_articles = []
    
    for article in articles:
        try:
            # For simplicity in this example, assume RSS articles are recent
            # In real implementation, you'd parse the published date properly
            recent_articles.append(article)
        except Exception as e:
            if debug:
                print(f"   ⚠️ Error processing article: {e}")
            recent_articles.append(article)  # Include if error
    
    if debug:
        print(f"📊 Found {len(recent_articles)} recent articles out of {len(articles)} total")
    
    return recent_articles

def dual_sentiment_analysis_with_fresh_news(ticker, days_back=3, debug=False):
    """
    Get dual sentiment analysis using only fresh/recent news
    REPLACES the old enhanced_sentiment_with_fresh_news function
    """
    
    if debug:
        print(f"📰 Getting DUAL sentiment analysis for {ticker} (last {days_back} days only)...")
    
    # Get articles
    all_articles = get_articles(ticker)
    
    if not all_articles:
        if debug:
            print(f"   ❌ No articles found")
        return {
            'ticker': ticker,
            'sentiment_score': 0.0,
            'momentum_signal': 'NO_DATA',
            'momentum_confidence': 0,
            'momentum_reasoning': 'No news data available',
            'contrarian_signal': 'NO_DATA',
            'contrarian_confidence': 0,
            'contrarian_reasoning': 'No news data available',
            'article_count': 0,
            'news_articles': [],
            'recent_articles': [],
            'status': 'no_news'
        }
    
    # Filter for recent articles only
    recent_articles = filter_recent_articles(all_articles, days_back, debug)
    
    if not recent_articles:
        if debug:
            print(f"   ❌ No recent articles found after filtering!")
        return {
            'ticker': ticker,
            'sentiment_score': 0.0,
            'momentum_signal': 'NO_DATA',
            'momentum_confidence': 0,
            'momentum_reasoning': 'No recent news data available',
            'contrarian_signal': 'NO_DATA',
            'contrarian_confidence': 0,
            'contrarian_reasoning': 'No recent news data available',
            'article_count': 0,
            'news_articles': [],
            'recent_articles': [],
            'status': 'no_recent_news'
        }
    
    # Analyze sentiment using dual strategy analyzer
    if debug:
        print(f"   🔄 Analyzing sentiment with {len(recent_articles)} recent articles...")
    
    analyzer = DualStrategyAnalyzer()
    
    # Combine all article text
    all_text = ""
    for article in recent_articles:
        title = article.get('title', article.get('headline', ''))
        content = article.get('content', '')
        all_text += f" {title} {content}"
    
    # Get sentiment analysis
    sentiment_result = analyzer.analyze_sentiment(all_text)
    sentiment_score = sentiment_result['score']
    
    # Calculate article breakdown
    positive_articles = sum(1 for article in recent_articles 
                          if analyzer.analyze_sentiment(article.get('title', '') + ' ' + article.get('content', ''))['score'] > 0.05)
    negative_articles = sum(1 for article in recent_articles 
                          if analyzer.analyze_sentiment(article.get('title', '') + ' ' + article.get('content', ''))['score'] < -0.05)
    neutral_articles = len(recent_articles) - positive_articles - negative_articles
    
    articles_breakdown = {
        'positive': positive_articles,
        'negative': negative_articles,
        'neutral': neutral_articles
    }
    
    # Generate both strategy analyses
    momentum = analyzer.generate_momentum_analysis(sentiment_score, articles_breakdown)
    contrarian = analyzer.generate_contrarian_analysis(sentiment_score, articles_breakdown)
    
    # Create dual sentiment data
    dual_sentiment = {
        'ticker': ticker,
        'sentiment_score': sentiment_score,
        
        # Momentum strategy data
        'momentum_signal': momentum['signal'],
        'momentum_confidence': momentum['confidence'],
        'momentum_reasoning': momentum['reasoning'],
        
        # Contrarian strategy data
        'contrarian_signal': contrarian['signal'],
        'contrarian_confidence': contrarian['confidence'],
        'contrarian_reasoning': contrarian['reasoning'],
        
        # General data
        'article_count': len(recent_articles),
        'article_breakdown': articles_breakdown,
        'detected_signals': sentiment_result['detected_signals'][:5],
        'news_articles': recent_articles,
        'recent_articles': recent_articles,
        'status': 'dual_sentiment_analyzed',
        'original_article_count': len(all_articles),
        'days_filtered': days_back
    }
    
    if debug:
        print(f"   📊 Dual sentiment results:")
        print(f"      Sentiment Score: {sentiment_score:.3f}")
        print(f"      Momentum: {momentum['signal']} ({momentum['confidence']}%)")
        print(f"      Contrarian: {contrarian['signal']} ({contrarian['confidence']}%)")
        print(f"      Articles: +{positive_articles} -{negative_articles} ={neutral_articles}")
    
    return dual_sentiment

def dual_sentiment_enhanced_analysis(technical_result, dual_sentiment_data):
    """
    Enhanced analysis with DUAL sentiment (momentum + contrarian) - REPLACES contrarian analysis
    Technical analysis drives decisions, sentiment provides enhancement
    """
    
    # Extract technical analysis data
    current_price = technical_result.get('current_price', 0)
    original_recommendation = technical_result.get('recommendation', 'HOLD')
    original_confidence = technical_result.get('confidence', 70)
    
    # Extract dual sentiment data
    article_count = dual_sentiment_data.get('article_count', 0)
    sentiment_score = dual_sentiment_data.get('sentiment_score', 0.0)
    momentum_signal = dual_sentiment_data.get('momentum_signal', 'NO_DATA')
    contrarian_signal = dual_sentiment_data.get('contrarian_signal', 'NO_DATA')
    momentum_confidence = dual_sentiment_data.get('momentum_confidence', 0)
    contrarian_confidence = dual_sentiment_data.get('contrarian_confidence', 0)
    recent_articles = dual_sentiment_data.get('recent_articles', [])
    
    # Initialize result with technical analysis
    result = {
        **technical_result,
        'original_recommendation': original_recommendation,
        'original_confidence': original_confidence,
        
        # Add dual sentiment data
        'sentiment_score': sentiment_score,
        'momentum_signal': momentum_signal,
        'momentum_confidence': momentum_confidence,
        'momentum_reasoning': dual_sentiment_data.get('momentum_reasoning', 'N/A'),
        'contrarian_signal': contrarian_signal,
        'contrarian_confidence': contrarian_confidence,
        'contrarian_reasoning': dual_sentiment_data.get('contrarian_reasoning', 'N/A'),
        'news_count': article_count,
        'recent_articles': recent_articles[:3],  # Keep top 3 articles for display
        'article_breakdown': dual_sentiment_data.get('article_breakdown', {}),
        'detected_signals': dual_sentiment_data.get('detected_signals', [])
    }
    
    # Apply enhancement logic: Technical drives decision, sentiment enhances strength
    final_recommendation = original_recommendation
    final_confidence = original_confidence
    enhancement_status = 'TECHNICAL_ONLY'
    
    # Only enhance if we have meaningful sentiment data
    if article_count > 0 and sentiment_score != 0.0 and momentum_signal != 'NO_DATA' and contrarian_signal != 'NO_DATA':
        
        # Check for agreement to enhance strength
        if original_recommendation in ['BUY', 'STRONG BUY']:
            momentum_agrees = momentum_signal in ['BUY', 'STRONG BUY']
            contrarian_agrees = contrarian_signal in ['BUY', 'STRONG BUY']
            
            if momentum_agrees and contrarian_agrees:
                # All three agree - make it STRONG
                final_recommendation = 'STRONG BUY'
                final_confidence = min(95, original_confidence + 20)
                enhancement_status = 'ALL_AGREE_BUY'
            elif momentum_agrees or contrarian_agrees:
                # Partial agreement - slight confidence boost
                final_confidence = min(90, original_confidence + 10)
                enhancement_status = 'PARTIAL_AGREE_BUY'
            else:
                # No sentiment agreement - stick with technical
                enhancement_status = 'SENTIMENT_DISAGREE'
                
        elif original_recommendation in ['SELL', 'STRONG SELL']:
            momentum_agrees = momentum_signal in ['SELL', 'STRONG SELL']
            contrarian_agrees = contrarian_signal in ['SELL', 'STRONG SELL']
            
            if momentum_agrees and contrarian_agrees:
                # All three agree - make it STRONG
                final_recommendation = 'STRONG SELL'
                final_confidence = min(95, original_confidence + 20)
                enhancement_status = 'ALL_AGREE_SELL'
            elif momentum_agrees or contrarian_agrees:
                # Partial agreement - slight confidence boost
                final_confidence = min(90, original_confidence + 10)
                enhancement_status = 'PARTIAL_AGREE_SELL'
            else:
                # No sentiment agreement - stick with technical
                enhancement_status = 'SENTIMENT_DISAGREE'
    else:
        enhancement_status = 'NO_SENTIMENT_DATA'
    
    # Update result
    result.update({
        'recommendation': final_recommendation,
        'confidence': final_confidence,
        'enhancement_status': enhancement_status,
        'news_summary': f"{article_count} recent articles, sentiment: {sentiment_score:.3f}"
    })
    
    return result

def analyze_stock_with_dual_sentiment_fresh_news(market_analyzer, ticker, company_name, fresh_news_days=3):
    """
    Complete stock analysis with technical analysis + dual sentiment enhancement
    REPLACES enhanced_analyze_stock_with_contrarian_fresh_news
    """
    try:
        base_ticker = ticker.replace('.NS', '')
        
        print(f"🔍 Analyzing {base_ticker} with dual sentiment logic...")
        
        # Get technical analysis first
        try:
            nse_ticker = f"{base_ticker}.NS"
            technical_result = market_analyzer.analyze_stock(nse_ticker, company_name)
        except:
            technical_result = market_analyzer.analyze_stock(base_ticker, company_name)
        
        if not technical_result or technical_result.get('current_price') is None:
            return {
                'ticker': base_ticker,
                'company_name': company_name or base_ticker,
                'error': 'No technical analysis data available',
                'recommendation': 'HOLD',
                'confidence': 0.0,
                'enhancement_status': 'TECHNICAL_FAILED',
                'models_agree': False
            }
        
        # Check model agreement
        models_agree = check_model_agreement(technical_result)
        technical_result['models_agree'] = models_agree
        
        # Get dual sentiment data with FRESH NEWS filtering
        print(f"   📅 Filtering for news from last {fresh_news_days} days only...")
        dual_sentiment_data = dual_sentiment_analysis_with_fresh_news(
            base_ticker, 
            days_back=fresh_news_days, 
            debug=False
        )
        
        # Apply dual sentiment enhancement
        enhanced_result = dual_sentiment_enhanced_analysis(technical_result, dual_sentiment_data)
        
        print(f"   📊 Technical: {enhanced_result.get('original_recommendation', 'N/A')} → Final: {enhanced_result['recommendation']}")
        print(f"   🚀 Momentum: {enhanced_result.get('momentum_signal', 'N/A')} ({enhanced_result.get('momentum_confidence', 0)}%)")
        print(f"   🔄 Contrarian: {enhanced_result.get('contrarian_signal', 'N/A')} ({enhanced_result.get('contrarian_confidence', 0)}%)")
        print(f"   🎯 Enhancement: {enhanced_result.get('enhancement_status', 'N/A')}")
        
        return enhanced_result
        
    except Exception as e:
        print(f"❌ Error in dual sentiment analysis for {ticker}: {e}")
        return {
            'ticker': ticker.replace('.NS', ''),
            'company_name': company_name or ticker,
            'error': str(e),
            'recommendation': 'HOLD',
            'confidence': 0.0,
            'enhancement_status': 'ERROR',
            'models_agree': False
        }

# Import or patch yfinance with curl_cffi if available
if CURL_CFFI_AVAILABLE:
    try:
        import yfinance as yf
        from curl_cffi import requests as curl_requests
        
        def get_ticker_with_curl_cffi(ticker_symbol):
            """Create a yfinance Ticker object with curl_cffi session to bypass rate limits"""
            session = curl_requests.Session(impersonate="chrome")
            return yf.Ticker(ticker_symbol, session=session)
        
        print("yfinance configured to use curl_cffi for bypassing rate limits")
    except Exception as e:
        print(f"Warning: Could not configure yfinance with curl_cffi: {str(e)}")

# Suppress warnings
warnings.filterwarnings("ignore")

# ======= SHARING FUNCTIONS (keeping all your existing code) =======

def start_local_server(html_file_path, port=8000):
    """Start a simple HTTP server to serve the HTML file"""
    import os
    
    # Get the directory containing the HTML file
    html_dir = os.path.dirname(html_file_path)
    html_filename = os.path.basename(html_file_path)
    
    # Change to the HTML directory
    original_dir = os.getcwd()
    os.chdir(html_dir)
    
    try:
        # Find available port
        while port < 8010:
            try:
                with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
                    print(f"\n🌐 HTTP Server started!")
                    print(f"📍 Local access: http://localhost:{port}/{html_filename}")
                    
                    # Get local IP for network access
                    hostname = socket.gethostname()
                    local_ip = socket.gethostbyname(hostname)
                    print(f"🌍 Network access: http://{local_ip}:{port}/{html_filename}")
                    print(f"📤 Share this URL with your friend: http://{local_ip}:{port}/{html_filename}")
                    print(f"⏹️  Press Ctrl+C to stop the server")
                    
                    # Auto-open in browser
                    webbrowser.open(f"http://localhost:{port}/{html_filename}")
                    
                    # Start server in background
                    server_thread = threading.Thread(target=httpd.serve_forever)
                    server_thread.daemon = True
                    server_thread.start()
                    
                    return httpd, port
            except OSError:
                port += 1
                continue
    finally:
        os.chdir(original_dir)
    
    return None, None

def create_shareable_package(html_file_path, output_dir):
    """Create a ZIP package with the report and instructions"""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f"stock_analysis_report_package_{timestamp}.zip"
    zip_path = os.path.join(output_dir, zip_filename)
    
    # Create instructions file
    instructions_content = f"""
📊 STOCK ANALYSIS REPORT PACKAGE
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📁 CONTENTS:
• {os.path.basename(html_file_path)} - Main analysis report (open in any browser)
• README.txt - This file

🌐 HOW TO VIEW:
1. Extract this ZIP file
2. Double-click the HTML file
3. It will open in your default browser
4. Works offline - no internet required!

📊 REPORT FEATURES:
• Sector-based stock organization
• ARIMA & LSTM model agreement analysis
• Dual sentiment data (Momentum + Contrarian columns)
• Technical analysis drives decisions
• Interactive tables and charts

⚠️ DISCLAIMER:
This analysis is for educational purposes only.
Always consult financial advisors before making investment decisions.

🔄 UPDATES:
For fresh analysis, request a new report as market data changes daily.
    """
    
    instructions_path = os.path.join(output_dir, "README.txt")
    with open(instructions_path, 'w') as f:
        f.write(instructions_content)
    
    # Create ZIP package
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(html_file_path, os.path.basename(html_file_path))
        zipf.write(instructions_path, "README.txt")
    
    # Clean up temporary instructions file
    os.remove(instructions_path)
    
    print(f"📦 Shareable package created: {zip_path}")
    print(f"📤 Send this ZIP file to your friend via email, WhatsApp, or cloud storage")
    
    return zip_path

def show_sharing_menu(html_file_path, output_dir):
    """Show interactive sharing menu"""
    
    print(f"\n🤝 ====== SHARING OPTIONS MENU ======")
    print(f"📄 Report: {os.path.basename(html_file_path)}")
    print(f"📍 Location: {html_file_path}")
    print(f"\nChoose how to share your report:")
    print(f"1. 📦 Create ZIP package (Email/WhatsApp friendly)")
    print(f"2. 🌐 Start local server (Network sharing)")
    print(f"0. ⏭️  Skip sharing")
    
    while True:
        try:
            choice = input(f"\nEnter your choice (0-2): ").strip()
            
            if choice == "0":
                print("Skipping sharing options.")
                break
                
            elif choice == "1":
                print(f"\n📦 Creating ZIP package...")
                zip_path = create_shareable_package(html_file_path, output_dir)
                print(f"✅ ZIP package created successfully!")
                print(f"📤 Share this file: {zip_path}")
                print(f"💡 Send via email, WhatsApp, or any file sharing method")
                break
                
            elif choice == "2":
                print(f"\n🌐 Starting local web server...")
                httpd, port = start_local_server(html_file_path)
                if httpd:
                    try:
                        input(f"\n⏸️  Server is running! Press Enter to stop...")
                        httpd.shutdown()
                        print("🛑 Server stopped.")
                    except KeyboardInterrupt:
                        httpd.shutdown()
                        print("\n🛑 Server stopped.")
                break
                
            else:
                print("❌ Invalid choice. Please enter 0-2.")
                continue
                
        except KeyboardInterrupt:
            print("\n🛑 Sharing menu cancelled.")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            continue

# ======= ANALYSIS FUNCTIONS (updated with dual sentiment) =======

def setup_logging():
    """Set up logging configuration"""
    log_dir = os.path.join(config.OUTPUT_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f'sector_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also log to console
        ]
    )
    return log_file

def check_model_agreement(result, min_agreement_threshold=0.5):
    """
    Check if ARIMA and LSTM models agree on direction
    Returns True only if both models predict the same direction (up or down)
    """
    try:
        current_price = result.get('current_price', 0)
        arima_prediction = result.get('arima_prediction', 0)
        lstm_prediction = result.get('lstm_prediction', 0)
        
        if current_price <= 0 or arima_prediction <= 0 or lstm_prediction <= 0:
            return False
        
        # Calculate percentage changes
        arima_change = ((arima_prediction - current_price) / current_price) * 100
        lstm_change = ((lstm_prediction - current_price) / current_price) * 100
        
        # Store changes in result for later use
        result['arima_change_pct'] = arima_change
        result['lstm_change_pct'] = lstm_change
        
        # Check if both models agree on direction
        models_agree = (arima_change > 0 and lstm_change > 0) or (arima_change < 0 and lstm_change < 0)
        
        # Additional check: changes should be significant enough (at least 0.5%)
        arima_significant = abs(arima_change) >= min_agreement_threshold
        lstm_significant = abs(lstm_change) >= min_agreement_threshold
        
        return models_agree and arima_significant and lstm_significant
        
    except Exception as e:
        print(f"Error checking model agreement: {e}")
        return False

def organize_stocks_by_sector(results):
    """
    Organize stocks by sector with BUY and SELL recommendations in descending order
    Only include stocks where models agree
    """
    # Filter only stocks where models agree
    agreed_stocks = [r for r in results if r.get('models_agree', False)]
    
    # Group by sector
    sector_groups = {}
    for stock in agreed_stocks:
        sector = stock.get('sector', 'UNKNOWN')
        if sector not in sector_groups:
            sector_groups[sector] = {'BUY': [], 'SELL': [], 'HOLD': []}
        
        recommendation = stock.get('recommendation', 'HOLD')
        if recommendation in ['BUY', 'STRONG BUY']:
            sector_groups[sector]['BUY'].append(stock)
        elif recommendation in ['SELL', 'STRONG SELL']:
            sector_groups[sector]['SELL'].append(stock)
        else:
            sector_groups[sector]['HOLD'].append(stock)
    
    # Sort within each sector by change percentage (descending)
    for sector in sector_groups:
        for rec_type in ['BUY', 'SELL', 'HOLD']:
            sector_groups[sector][rec_type].sort(
                key=lambda x: abs(x.get('combined_change_pct', 0)), 
                reverse=True
            )
    
    # Sort sectors by average performance
    sector_performance = []
    for sector, stocks in sector_groups.items():
        all_stocks = stocks['BUY'] + stocks['SELL'] + stocks['HOLD']
        if all_stocks:
            avg_change = sum(s.get('combined_change_pct', 0) for s in all_stocks) / len(all_stocks)
            sector_performance.append((sector, avg_change, stocks))
    
    # Sort sectors by performance (descending)
    sector_performance.sort(key=lambda x: x[1], reverse=True)
    
    return sector_performance

def generate_dual_sentiment_html_report(sector_report, results, output_dir, fresh_news_days=3):
    """Generate sector-based HTML report with DUAL SENTIMENT columns"""
    
    # Get only stocks where models agree
    agreed_stocks = [r for r in results if r.get('models_agree', False)]
    total_analyzed = len(results)
    models_agreed = len(agreed_stocks)
    
    # Organize by sector
    sector_performance = organize_stocks_by_sector(results)
    
    # Calculate statistics
    sentiment_enhanced = sum(1 for r in agreed_stocks if 'momentum_signal' in r and r.get('news_count', 0) > 0)
    strong_recommendations = sum(1 for r in agreed_stocks if 'STRONG' in r.get('recommendation', ''))
    all_agree_count = sum(1 for r in agreed_stocks if r.get('enhancement_status', '').startswith('ALL_AGREE'))
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dual Sentiment Sector Analysis - {datetime.now().strftime('%Y-%m-%d')}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }}
            .container {{
                max-width: 1600px;
                margin: 0 auto;
                background-color: white;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }}
            .header {{
                text-align: center;
                margin-bottom: 40px;
                padding: 30px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }}
            .header h1 {{
                margin: 0 0 10px 0;
                font-size: 2.5em;
                font-weight: 700;
            }}
            .dual-sentiment-banner {{
                background: linear-gradient(145deg, #28a745, #20c997);
                color: white;
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                margin: 20px 0;
                font-weight: bold;
            }}
            .summary-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 25px;
                margin-bottom: 40px;
            }}
            .summary-card {{
                background: linear-gradient(145deg, #f8f9fa, #e9ecef);
                padding: 25px;
                border-radius: 15px;
                border-left: 5px solid #007bff;
                box-shadow: 0 5px 15px rgba(0,0,0,0.08);
                transition: transform 0.3s ease;
            }}
            .summary-card:hover {{
                transform: translateY(-5px);
            }}
            .summary-card h3 {{
                margin: 0 0 15px 0;
                color: #333;
                font-size: 1.1em;
            }}
            .summary-card .value {{
                font-size: 2.2em;
                font-weight: bold;
                color: #007bff;
                margin-bottom: 5px;
            }}
            .sector-section {{
                margin: 40px 0;
                padding: 30px;
                border: 2px solid #e9ecef;
                border-radius: 15px;
                background: linear-gradient(145deg, #ffffff, #f8f9fa);
                box-shadow: 0 5px 15px rgba(0,0,0,0.05);
            }}
            .sector-header {{
                margin-bottom: 25px;
                padding: 20px;
                background: linear-gradient(135deg, #28a745, #20c997);
                color: white;
                border-radius: 10px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .sector-header h2 {{
                margin: 0;
                font-size: 1.8em;
                font-weight: 600;
            }}
            .recommendation-group {{
                margin: 25px 0;
            }}
            .recommendation-header {{
                margin-bottom: 15px;
                padding: 15px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 1.1em;
            }}
            .buy-header {{
                background: linear-gradient(145deg, #d4edda, #c3e6cb);
                color: #155724;
                border-left: 5px solid #28a745;
            }}
            .sell-header {{
                background: linear-gradient(145deg, #f8d7da, #f5c6cb);
                color: #721c24;
                border-left: 5px solid #dc3545;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 3px 10px rgba(0,0,0,0.06);
                font-size: 0.85em;
            }}
            th, td {{
                padding: 8px;
                text-align: left;
                border-bottom: 1px solid #e9ecef;
            }}
            th {{
                background: linear-gradient(145deg, #f8f9fa, #e9ecef);
                font-weight: 600;
                color: #333;
                font-size: 0.8em;
            }}
            tr:hover {{
                background-color: #f8f9fa;
            }}
            .buy {{ color: #28a745; font-weight: bold; }}
            .strong-buy {{ color: #155724; font-weight: bold; background: #d4edda; padding: 2px 6px; border-radius: 4px; }}
            .sell {{ color: #dc3545; font-weight: bold; }}
            .strong-sell {{ color: #721c24; font-weight: bold; background: #f8d7da; padding: 2px 6px; border-radius: 4px; }}
            .hold {{ color: #6c757d; font-weight: bold; }}
            
            /* Dual sentiment column styling */
            .momentum-buy, .momentum-strong-buy {{ color: #28a745; font-weight: 600; }}
            .momentum-sell, .momentum-strong-sell {{ color: #dc3545; font-weight: 600; }}
            .momentum-hold, .momentum-no_data {{ color: #6c757d; font-weight: 500; }}
            
            .contrarian-buy, .contrarian-strong-buy {{ color: #28a745; font-weight: 600; }}
            .contrarian-sell, .contrarian-strong-sell {{ color: #dc3545; font-weight: 600; }}
            .contrarian-hold, .contrarian-no_data {{ color: #6c757d; font-weight: 500; }}
            
            .enhancement-badge {{
                font-size: 9px;
                padding: 2px 5px;
                border-radius: 6px;
                font-weight: bold;
                text-transform: uppercase;
            }}
            .all-agree-buy, .all-agree-sell {{ background: #28a745; color: white; }}
            .partial-agree-buy, .partial-agree-sell {{ background: #ffc107; color: #856404; }}
            .technical-only {{ background: #6c757d; color: white; }}
            .sentiment-disagree {{ background: #fd7e14; color: white; }}
            .no-sentiment-data {{ background: #e9ecef; color: #6c757d; }}
            
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding: 25px;
                background: linear-gradient(145deg, #f8f9fa, #e9ecef);
                border-radius: 15px;
                border: 1px solid #dee2e6;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏭 Dual Sentiment Sector Analysis</h1>
                <p><strong>Technical Analysis + Momentum + Contrarian Strategies</strong></p>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Technical drives decisions, sentiment enhances strength</p>
            </div>
            
            <div class="dual-sentiment-banner">
                📊 DUAL SENTIMENT STRATEGY: Technical analysis drives BUY/SELL decisions<br>
                🚀 Momentum Column: Follow the trend | 🔄 Contrarian Column: Fade the move<br>
                ⚡ Enhancement: All three agree → STRONG recommendations
            </div>
            
            <div class="summary-grid">
                <div class="summary-card">
                    <h3>📈 Total Stocks Analyzed</h3>
                    <div class="value">{total_analyzed}</div>
                    <div class="subtitle">Complete analysis attempted</div>
                </div>
                <div class="summary-card">
                    <h3>🎯 Models Agree</h3>
                    <div class="value">{models_agreed}</div>
                    <div class="subtitle">ARIMA & LSTM agree on direction</div>
                </div>
                <div class="summary-card">
                    <h3>📰 Dual Sentiment Enhanced</h3>
                    <div class="value">{sentiment_enhanced}</div>
                    <div class="subtitle">With momentum + contrarian analysis</div>
                </div>
                <div class="summary-card">
                    <h3>⚡ Enhanced to STRONG</h3>
                    <div class="value">{strong_recommendations}</div>
                    <div class="subtitle">All strategies agree</div>
                </div>
            </div>
    """
    
    # Add sector-based sections with dual sentiment columns
    for sector_name, avg_performance, sector_stocks in sector_performance:
        total_sector_stocks = len(sector_stocks['BUY']) + len(sector_stocks['SELL']) + len(sector_stocks['HOLD'])
        
        html_content += f"""
            <div class="sector-section">
                <div class="sector-header">
                    <h2>🏭 {sector_name}</h2>
                    <div class="sector-performance">{avg_performance:+.2f}%</div>
                </div>
                <p><strong>Total Stocks with Model Agreement:</strong> {total_sector_stocks}</p>
        """
        
        # Add BUY recommendations with dual sentiment
        if sector_stocks['BUY']:
            html_content += f"""
                <div class="recommendation-group">
                    <div class="recommendation-header buy-header">
                        🚀 BUY/STRONG BUY Recommendations ({len(sector_stocks['BUY'])} stocks)
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>Ticker</th>
                                <th>Company</th>
                                <th>Price</th>
                                <th>Change%</th>
                                <th>Technical</th>
                                <th>Final</th>
                                <th>Confidence</th>
                                <th>🚀 Momentum</th>
                                <th>🔄 Contrarian</th>
                                <th>Enhancement</th>
                                <th>News</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            for stock in sector_stocks['BUY']:
                # Format signals
                momentum_signal = stock.get('momentum_signal', 'NO_DATA')
                momentum_class = f"momentum-{momentum_signal.lower().replace(' ', '-').replace('_', '-')}"
                
                contrarian_signal = stock.get('contrarian_signal', 'NO_DATA')
                contrarian_class = f"contrarian-{contrarian_signal.lower().replace(' ', '-').replace('_', '-')}"
                
                # Format final recommendation
                final_rec = stock.get('recommendation', 'HOLD')
                final_class = f"{'strong-' if 'STRONG' in final_rec else ''}{final_rec.lower().replace(' ', '-')}"
                
                # Enhancement status
                enhancement = stock.get('enhancement_status', 'TECHNICAL_ONLY')
                enhancement_class = enhancement.lower().replace('_', '-')
                enhancement_text = enhancement.replace('_', ' ').title()
                
                html_content += f"""
                            <tr>
                                <td><strong>{stock.get('ticker', 'N/A')}</strong></td>
                                <td>{stock.get('company_name', 'N/A')[:25]}...</td>
                                <td>₹{stock.get('current_price', 0):,.0f}</td>
                                <td class="buy">{stock.get('combined_change_pct', 0):.1f}%</td>
                                <td>{stock.get('original_recommendation', 'N/A')}</td>
                                <td class="{final_class}">{final_rec}</td>
                                <td>{stock.get('confidence', 0):.0f}%</td>
                                <td class="{momentum_class}">{momentum_signal}</td>
                                <td class="{contrarian_class}">{contrarian_signal}</td>
                                <td><span class="enhancement-badge {enhancement_class}">{enhancement_text[:8]}</span></td>
                                <td>{stock.get('news_count', 0)} articles</td>
                            </tr>
                """
            
            html_content += """
                        </tbody>
                    </table>
                </div>
            """
        
        # Add SELL recommendations with dual sentiment
        if sector_stocks['SELL']:
            html_content += f"""
                <div class="recommendation-group">
                    <div class="recommendation-header sell-header">
                        📉 SELL/STRONG SELL Recommendations ({len(sector_stocks['SELL'])} stocks)
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>Ticker</th>
                                <th>Company</th>
                                <th>Price</th>
                                <th>Change%</th>
                                <th>Technical</th>
                                <th>Final</th>
                                <th>Confidence</th>
                                <th>🚀 Momentum</th>
                                <th>🔄 Contrarian</th>
                                <th>Enhancement</th>
                                <th>News</th>
                            </tr>
                        </thead>
                        <tbody>
            """
            
            for stock in sector_stocks['SELL']:
                # Format signals
                momentum_signal = stock.get('momentum_signal', 'NO_DATA')
                momentum_class = f"momentum-{momentum_signal.lower().replace(' ', '-').replace('_', '-')}"
                
                contrarian_signal = stock.get('contrarian_signal', 'NO_DATA')
                contrarian_class = f"contrarian-{contrarian_signal.lower().replace(' ', '-').replace('_', '-')}"
                
                # Format final recommendation
                final_rec = stock.get('recommendation', 'HOLD')
                final_class = f"{'strong-' if 'STRONG' in final_rec else ''}{final_rec.lower().replace(' ', '-')}"
                
                # Enhancement status
                enhancement = stock.get('enhancement_status', 'TECHNICAL_ONLY')
                enhancement_class = enhancement.lower().replace('_', '-')
                enhancement_text = enhancement.replace('_', ' ').title()
                
                html_content += f"""
                            <tr>
                                <td><strong>{stock.get('ticker', 'N/A')}</strong></td>
                                <td>{stock.get('company_name', 'N/A')[:25]}...</td>
                                <td>₹{stock.get('current_price', 0):,.0f}</td>
                                <td class="sell">{stock.get('combined_change_pct', 0):.1f}%</td>
                                <td>{stock.get('original_recommendation', 'N/A')}</td>
                                <td class="{final_class}">{final_rec}</td>
                                <td>{stock.get('confidence', 0):.0f}%</td>
                                <td class="{momentum_class}">{momentum_signal}</td>
                                <td class="{contrarian_class}">{contrarian_signal}</td>
                                <td><span class="enhancement-badge {enhancement_class}">{enhancement_text[:8]}</span></td>
                                <td>{stock.get('news_count', 0)} articles</td>
                            </tr>
                """
            
            html_content += """
                        </tbody>
                    </table>
                </div>
            """
        
        # Show message if no stocks in this sector
        if total_sector_stocks == 0:
            html_content += """
                <div style="text-align: center; padding: 20px; color: #6c757d; font-style: italic;">
                    No stocks in this sector have ARIMA-LSTM model agreement
                </div>
            """
        
        html_content += """
            </div>
        """
    
    # Add footer
    html_content += f"""
            <div class="footer">
                <p><strong>📊 Dual Sentiment Report generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}</strong></p>
                <p><em>🎯 Technical Analysis drives BUY/SELL decisions based on ARIMA + LSTM model agreement</em></p>
                <p><em>🚀 Momentum Strategy: Positive sentiment → BUY, Negative sentiment → SELL (Follow the trend)</em></p>
                <p><em>🔄 Contrarian Strategy: Positive sentiment → SELL, Negative sentiment → BUY (Fade the move)</em></p>
                <p><em>⚡ Enhancement Logic: When Technical + Both Sentiments agree → Enhanced to STRONG recommendation</em></p>
                <p><em>📅 Fresh News Filter: Only articles from last {fresh_news_days} days used for sentiment analysis</em></p>
                <p style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #dee2e6;">
                    <strong>⚠️ Disclaimer:</strong> This is for educational purposes only. Always consult with financial advisors before making investment decisions.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Save HTML file
    html_filename = f"dual_sentiment_sector_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    html_path = os.path.join(output_dir, html_filename)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_path

def save_results(results, base_output_dir):
    """Save stock analysis results in JSON file"""
    # Ensure output directory exists
    os.makedirs(base_output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"dual_sentiment_sector_analysis_{timestamp}.json"
    
    # Full path for saving
    json_path = os.path.join(base_output_dir, filename)
    
    try:
        # Create consolidated data structure
        consolidated_data = {
            'timestamp': timestamp,
            'analysis_date': datetime.now().strftime('%Y-%m-%d'),
            'dual_sentiment_enabled': True,
            'technical_analysis_driven': True,
            'sentiment_enhancement': True,
            'results': results
        }
        
        # Save results
        with open(json_path, 'w') as f:
            json.dump(consolidated_data, f, indent=2)
        
        logging.info(f"Saved dual sentiment analysis results to {json_path}")
        return json_path
    
    except Exception as e:
        logging.error(f"Error saving results: {str(e)}")
        return None

def display_sector_summary(sector_analysis):
    """Display sector performance summary in a table"""
    sector_data = []
    headers = ['Sector', 'Avg Change%', 'Direction', 'Status']
    
    for sector_info in sector_analysis['sector_performance']:
        sector = sector_info['sector']
        avg_change = sector_info['avg_change']
        direction = sector_info['direction']
        color = sector_info['color']
        
        row = [
            sector,
            f"{avg_change:.2f}%",
            direction,
            color
        ]
        sector_data.append(row)
    
    # Print table
    print("\n=== SECTOR PERFORMANCE SUMMARY ===")
    if sector_data:
        print(tabulate(sector_data, headers=headers, tablefmt="grid"))
    else:
        print("No sector data available")

def display_dual_sentiment_summary(report_data):
    """Display top recommendations with DUAL SENTIMENT information"""
    
    # Display top BUY recommendations
    print("\n=== TOP BUY RECOMMENDATIONS (TECHNICAL + DUAL SENTIMENT) ===")
    if report_data['top_buy']:
        buy_data = []
        for i, stock in enumerate(report_data['top_buy']):
            # Get dual sentiment info
            momentum_signal = stock.get('momentum_signal', 'NO_DATA')
            contrarian_signal = stock.get('contrarian_signal', 'NO_DATA') 
            enhancement = stock.get('enhancement_status', 'TECHNICAL_ONLY')
            
            buy_data.append([
                i+1,
                stock.get('ticker', 'N/A'),
                stock.get('company_name', 'N/A')[:25],
                stock.get('sector', 'N/A'),
                f"{stock.get('current_price', 0):.0f}",
                f"{stock.get('combined_change_pct', 0):.1f}%",
                stock.get('original_recommendation', 'N/A'),
                stock.get('recommendation', 'N/A'),
                f"{stock.get('confidence', 0):.0f}%",
                momentum_signal,
                contrarian_signal,
                enhancement.replace('_', ' ')[:15],
                stock.get('news_count', 0)
            ])
        
        buy_headers = ['#', 'Ticker', 'Company', 'Sector', 'Price', 'Change%', 'Technical', 'Final', 'Conf%', 'Momentum', 'Contrarian', 'Enhancement', 'News']
        print(tabulate(buy_data, headers=buy_headers, tablefmt="grid"))
    else:
        print("No BUY recommendations available")
    
    # Display top SELL recommendations
    print("\n=== TOP SELL RECOMMENDATIONS (TECHNICAL + DUAL SENTIMENT) ===")  
    if report_data['top_sell']:
        sell_data = []
        for i, stock in enumerate(report_data['top_sell']):
            # Get dual sentiment info
            momentum_signal = stock.get('momentum_signal', 'NO_DATA')
            contrarian_signal = stock.get('contrarian_signal', 'NO_DATA')
            enhancement = stock.get('enhancement_status', 'TECHNICAL_ONLY')
            
            sell_data.append([
                i+1,
                stock.get('ticker', 'N/A'),
                stock.get('company_name', 'N/A')[:25],
                stock.get('sector', 'N/A'),
                f"{stock.get('current_price', 0):.0f}",
                f"{stock.get('combined_change_pct', 0):.1f}%",
                stock.get('original_recommendation', 'N/A'),
                stock.get('recommendation', 'N/A'),
                f"{stock.get('confidence', 0):.0f}%",
                momentum_signal,
                contrarian_signal,
                enhancement.replace('_', ' ')[:15],
                stock.get('news_count', 0)
            ])
        
        sell_headers = ['#', 'Ticker', 'Company', 'Sector', 'Price', 'Change%', 'Technical', 'Final', 'Conf%', 'Momentum', 'Contrarian', 'Enhancement', 'News']
        print(tabulate(sell_data, headers=sell_headers, tablefmt="grid"))
    else:
        print("No SELL recommendations available")

def run_analysis_with_dual_sentiment(num_stocks=None, output_dir=None, fresh_news_days=3):
    """
    Run sector-based analysis with DUAL SENTIMENT strategy (momentum + contrarian)
    MAIN FUNCTION - REPLACES the original run_analysis_with_fresh_news
    """
    # Setup logging
    setup_logging()
    logging.info(f"Starting dual sentiment sector analysis - {datetime.now().strftime('%Y-%m-%d')}")
    
    # Set output directory
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    
    # Create analyzer services
    market_analyzer = MarketAnalysisService(output_dir=output_dir)
    sector_analyzer = SectorAnalyzer(market_analyzer, output_dir=output_dir)
    
    print(f"✅ Dual sentiment analysis initialized (momentum + contrarian)")
    
    # Get stocks to analyze
    stocks_to_analyze = config.TOP_STOCKS
    if num_stocks and num_stocks > 0:
        stocks_to_analyze = stocks_to_analyze[:num_stocks]
    
    print(f"\nAnalyzing {len(stocks_to_analyze)} stocks for dual sentiment sector analysis...")
    
    # Track results
    results = []
    failed_stocks = []
    
    # Analyze each stock
    for idx, stock in enumerate(stocks_to_analyze):
        try:
            print(f"\n[{idx+1}/{len(stocks_to_analyze)}] Analyzing {stock['name']} ({stock['symbol']})...")
            
            # Use dual sentiment enhanced analysis
            result = analyze_stock_with_dual_sentiment_fresh_news(
                market_analyzer, 
                stock['symbol'], 
                stock['name'],
                fresh_news_days
            )
            
            if 'sector' not in result:
                result['sector'] = sector_analyzer.get_stock_sector(stock['symbol'])
            
            # Check if analysis produced meaningful results
            if not result or result.get('current_price') is None:
                logging.warning(f"No meaningful data for {stock['symbol']}")
                failed_stocks.append({
                    'symbol': stock['symbol'],
                    'name': stock['name'],
                    'reason': 'No current price data'
                })
                continue
            
            # Add to results
            results.append(result)
        
        except Exception as e:
            # Log error
            logging.error(f"Error analyzing {stock['symbol']}: {str(e)}")
            
            # Track failed stocks
            failed_stocks.append({
                'symbol': stock['symbol'],
                'name': stock['name'],
                'error': str(e)
            })
            
            # Continue with next stock
            continue
    
    # Handle case where no stocks could be analyzed
    if not results:
        logging.critical("No stocks could be analyzed. Check your data sources and network connection.")
        print("No stocks could be analyzed. Please check logs for details.")
        return None, [], {}
    
    # Print dual sentiment summary
    sentiment_enhanced = sum(1 for r in results if 'momentum_signal' in r and r.get('news_count', 0) > 0)
    strong_recommendations = sum(1 for r in results if 'STRONG' in r.get('recommendation', ''))
    models_agreed = sum(1 for r in results if r.get('models_agree', False))
    all_agree_count = sum(1 for r in results if r.get('enhancement_status', '').startswith('ALL_AGREE'))
    
    print(f"\n📊 DUAL SENTIMENT ANALYSIS SUMMARY:")
    print(f"   Total stocks analyzed: {len(results)}")
    print(f"   Models agreed: {models_agreed} ({models_agreed/len(results)*100:.1f}%)")
    print(f"   Dual sentiment enhanced: {sentiment_enhanced}")
    print(f"   Enhanced to STRONG: {strong_recommendations}")
    print(f"   All strategies agree: {all_agree_count}")
    
    # Generate sector-based report
    print(f"\nGenerating dual sentiment sector-based report...")
    sector_report = sector_analyzer.generate_agreement_report(results)
    
    # Save reports
    report_files = {}
    report_files['json'] = save_results(results, output_dir)
    
    # Generate DUAL SENTIMENT HTML report
    report_files['html_report'] = generate_dual_sentiment_html_report(
        sector_report, results, output_dir, fresh_news_days
    )
    
    # Display results
    display_sector_summary(sector_report)
    display_dual_sentiment_summary(sector_report)
    
    # Print report paths
    print("\n=== DUAL SENTIMENT REPORT FILES ===")
    for name, path in report_files.items():
        if path:
            if name == 'html_report':
                print(f"🌐 {name.replace('_', ' ').title()}: {path}")
                print(f"🔗 Local access: file://{os.path.abspath(path)}")
            else:
                print(f"📄 {name.replace('_', ' ').title()}: {path}")
    
    # ======= INTEGRATED SHARING MENU =======
    if 'html_report' in report_files and report_files['html_report']:
        print(f"\n" + "="*60)
        print(f"🎉 DUAL SENTIMENT ANALYSIS COMPLETE! Now let's share your report...")
        print(f"="*60)
        
        # Show sharing menu
        show_sharing_menu(report_files['html_report'], output_dir)
    
    return sector_report, results, report_files

def log_analysis_summary(results, failed_stocks, sector_report):
    """Log comprehensive analysis summary"""
    logging.info("\n--- Dual Sentiment Analysis Summary ---")
    logging.info(f"Total Stocks Analyzed: {len(results) + len(failed_stocks)}")
    logging.info(f"Successfully Analyzed: {len(results)}")
    logging.info(f"Failed Analyses: {len(failed_stocks)}")
    
    # Log dual sentiment enhancement statistics
    sentiment_enhanced = sum(1 for r in results if 'momentum_signal' in r and r.get('news_count', 0) > 0)
    strong_recommendations = sum(1 for r in results if 'STRONG' in r.get('recommendation', ''))
    models_agreed = sum(1 for r in results if r.get('models_agree', False))
    all_agree_count = sum(1 for r in results if r.get('enhancement_status', '').startswith('ALL_AGREE'))
    
    if sentiment_enhanced > 0:
        enhancement_rate = (sentiment_enhanced / len(results)) * 100
        strong_rate = (strong_recommendations / len(results)) * 100
        agreement_rate = (models_agreed / len(results)) * 100
        all_agree_rate = (all_agree_count / len(results)) * 100
        
        logging.info(f"Model agreement rate: {models_agreed} ({agreement_rate:.1f}%)")
        logging.info(f"Stocks with dual sentiment enhancement: {sentiment_enhanced} ({enhancement_rate:.1f}%)")
        logging.info(f"Enhanced to STRONG recommendations: {strong_recommendations} ({strong_rate:.1f}%)")
        logging.info(f"All strategies agree: {all_agree_count} ({all_agree_rate:.1f}%)")
    
    # Log agreement statistics
    agreement_count = len(sector_report['agreement_stocks'])
    agreement_pct = (agreement_count / len(results)) * 100 if results else 0
    logging.info(f"Stocks with ARIMA-LSTM agreement: {agreement_count} ({agreement_pct:.1f}%)")
    
    # Log buy/sell counts
    buy_count = len(sector_report['top_buy'])
    sell_count = len(sector_report['top_sell'])
    logging.info(f"Top BUY recommendations: {buy_count}")
    logging.info(f"Top SELL recommendations: {sell_count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dual Sentiment Sector-Based Stock Analysis Tool")
    
    parser.add_argument('--top', type=int, help='Analyze top N stocks from the configured list')
    parser.add_argument('--output', type=str, help='Output directory for reports')
    parser.add_argument('--fresh-news-days', type=int, default=3, help='Number of days to look back for fresh news (default: 3)')
    parser.add_argument('--auto-share', action='store_true', help='Automatically show sharing menu after analysis')
    
    args = parser.parse_args()
    
    print("🚀 DUAL SENTIMENT SECTOR-BASED STOCK ANALYSIS TOOL")
    print("="*70)
    print(f"📊 Technical Analysis: ARIMA + LSTM Agreement")
    print(f"🚀 Momentum Strategy: Follow positive trends, avoid negative trends")
    print(f"🔄 Contrarian Strategy: Buy pessimism, sell optimism")  
    print(f"⚡ Enhancement Logic: Technical + Both Sentiments agree = STRONG recommendations")
    print(f"🏭 Organization: SECTOR-BASED with model agreement filter")
    print(f"📅 Fresh News Filter: Last {args.fresh_news_days} days only")
    print(f"🤝 Sharing Features: ZIP, Server, etc.")
    print("="*70)
    
    # Run dual sentiment analysis
    sector_report, results, report_files = run_analysis_with_dual_sentiment(
        args.top, 
        args.output, 
        args.fresh_news_days
    )
    
    # Log summary
    if sector_report and results:
        log_analysis_summary(results, [], sector_report)
        
        sentiment_enhanced = sum(1 for r in results if 'momentum_signal' in r and r.get('news_count', 0) > 0)
        strong_recommendations = sum(1 for r in results if 'STRONG' in r.get('recommendation', ''))
        models_agreed = sum(1 for r in results if r.get('models_agree', False))
        all_agree_count = sum(1 for r in results if r.get('enhancement_status', '').startswith('ALL_AGREE'))
        
        print(f"\n✅ FINAL DUAL SENTIMENT SUMMARY:")
        print(f"   📊 {len(results)} stocks analyzed")
        print(f"   🎯 {models_agreed} models agreed ({models_agreed/len(results)*100:.1f}%)")
        print(f"   🚀📄 {sentiment_enhanced} with dual sentiment (momentum + contrarian)")
        print(f"   ⚡ {strong_recommendations} enhanced to STRONG recommendations")
        print(f"   🎪 {all_agree_count} all three strategies agree")
        print(f"   🎯 {len(sector_report.get('top_buy', []))} BUY recommendations")
        print(f"   🎯 {len(sector_report.get('top_sell', []))} SELL recommendations")
        
        if 'html_report' in report_files:
            print(f"\n🌐 DUAL SENTIMENT HTML REPORT:")
            print(f"📄 File: {report_files['html_report']}")
            print(f"🔗 Local: file://{os.path.abspath(report_files['html_report'])}")
            
        print(f"\n🎉 DUAL SENTIMENT FEATURES IMPLEMENTED:")
        print(f"   ✅ Technical analysis drives BUY/SELL decisions")
        print(f"   ✅ Momentum strategy column (follow trend)")  
        print(f"   ✅ Contrarian strategy column (fade move)")
        print(f"   ✅ Enhancement logic for STRONG recommendations")
        print(f"   ✅ Fresh news filtering (last {args.fresh_news_days} days)")
        print(f"   ✅ Sector-based organization") 
        print(f"   ✅ Model agreement filtering")
        print(f"   ✅ All sharing features intact")
        
        # Final sharing reminder
        if args.auto_share or input(f"\n🤝 Want to share your dual sentiment report now? (y/n): ").lower().startswith('y'):
            if 'html_report' in report_files:
                show_sharing_menu(report_files['html_report'], args.output or config.OUTPUT_DIR)
        
    print(f"\n🏁 Dual sentiment analysis with sharing setup complete!")
    print(f"💡 Tip: Your report now shows momentum + contrarian perspectives in separate columns!")