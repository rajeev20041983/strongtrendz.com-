def filter_news_for_ticker(self, articles: List[Dict], ticker: str) -> List[Dict]:
    """DEBUG VERSION: Shows exactly why articles are being rejected"""
    search_terms = self.normalize_ticker_for_search(ticker)
    relevant_articles = []
    
    print(f"🔍 Filtering {len(articles)} articles for {ticker} using terms: {search_terms}")
    print(f"🔍 DEBUG MODE: Will show why articles are accepted/rejected")
    
    articles_checked = 0
    
    for article in articles:
        text_to_search = f"{article['headline']} {article['content']}".upper()
        
        # DEBUG: Show first few articles being checked
        if articles_checked < 10:
            print(f"\n📝 CHECKING Article {articles_checked + 1}:")
            print(f"   Headline: {article['headline'][:80]}...")
            print(f"   Content: {article.get('content', 'No content')[:80]}...")
        
        best_match = None
        best_score = 0
        
        for term in search_terms:
            term_upper = term.upper()
            
            if articles_checked < 10:
                print(f"   🔍 Testing term: '{term}'")
            
            # Check for exact word boundary match
            if re.search(r'\b' + re.escape(term_upper) + r'\b', text_to_search):
                if articles_checked < 10:
                    print(f"      ✅ FOUND: '{term}' in text")
                
                # Now test validation
                validation_result = self._validate_company_match(text_to_search, ticker, term)
                
                if articles_checked < 10:
                    print(f"      🔍 VALIDATION: {validation_result}")
                
                if validation_result:
                    match_type = 'exact_company_name' if len(term) >= 4 else 'exact_ticker'
                    relevance_score = 90 if len(term) >= 4 else 100
                    
                    if relevance_score > best_score:
                        best_score = relevance_score
                        best_match = {
                            'term': term,
                            'match_type': match_type,
                            'score': relevance_score
                        }
                        if articles_checked < 10:
                            print(f"      ✅ ACCEPTED: Score {relevance_score}")
                else:
                    if articles_checked < 10:
                        print(f"      ❌ REJECTED: Failed validation")
            else:
                if articles_checked < 10:
                    print(f"      ❌ NOT FOUND: '{term}' not in text")
        
        # Only add article if we found a validated match
        if best_match and best_score >= 80:
            article_copy = article.copy()
            article_copy['matched_term'] = best_match['term']
            article_copy['match_type'] = best_match['match_type']
            article_copy['ticker'] = ticker
            article_copy['relevance_score'] = best_score
            relevant_articles.append(article_copy)
            
            if articles_checked < 10:
                print(f"   ✅ ARTICLE ACCEPTED!")
        else:
            if articles_checked < 10:
                print(f"   ❌ ARTICLE REJECTED!")
        
        articles_checked += 1
        
        # Stop debugging after 10 articles
        if articles_checked >= 10:
            if articles_checked == 10:
                print(f"\n... (checked {articles_checked} articles, continuing without debug output)")
    
    print(f"\n📊 FINAL RESULTS for {ticker}:")
    print(f"   Total articles checked: {len(articles)}")
    print(f"   Articles with term matches: [will count this]")
    print(f"   Articles passing validation: {len(relevant_articles)}")
    
    return relevant_articles

def _validate_company_match(self, text: str, ticker: str, matched_term: str) -> bool:
    """DEBUG VERSION: Shows exactly why validation passes/fails"""
    
    text_upper = text.upper()
    ticker_upper = ticker.upper()
    term_upper = matched_term.upper()
    
    print(f"         🔍 VALIDATING: '{matched_term}' for {ticker}")
    print(f"         📝 Text sample: {text_upper[:100]}...")
    
    # Specific validation rules for problematic tickers
    validation_rules = {
        'TATASTEEL': {
            'required_any': ['TATA STEEL', 'TISCO', 'STEEL PRODUCTION', 'TATA STEEL LIMITED'],
            'forbidden_any': ['TATA MOTORS', 'TATA CONSULTANCY', 'TATA POWER', 'TATA CONSUMER']
        },
        'NATIONALUM': {
            'required_any': ['NALCO', 'NATIONAL ALUMINIUM COMPANY LIMITED', 'ALUMINIUM PRODUCTION'],
            'forbidden_any': ['HEALTHCARE', 'PHARMA', 'BIOTECH', 'MEDICAL']
        },
        'SAIL': {
            'required_any': ['SAIL', 'STEEL AUTHORITY', 'STEEL PRODUCTION'],
            'forbidden_any': ['BANDH', 'GENERAL MARKET', 'SENSEX TODAY', 'NIFTY TODAY']
        },
        'HINDALCO': {
            'required_any': ['HINDALCO', 'ALUMINUM', 'ALUMINIUM', 'COPPER'],
            'forbidden_any': ['SAFARI', 'TEXTILES', 'HEALTHCARE']
        }
    }
    
    if ticker_upper in validation_rules:
        rules = validation_rules[ticker_upper]
        
        # Check for required context
        if 'required_any' in rules:
            required_terms = rules['required_any']
            has_required = any(req in text_upper for req in required_terms)
            
            print(f"         📋 Required terms: {required_terms}")
            print(f"         ✅ Has required: {has_required}")
            
            if not has_required:
                print(f"         ❌ FAILED: No required context found")
                return False
        
        # Check for forbidden context
        if 'forbidden_any' in rules:
            forbidden_terms = rules['forbidden_any']
            has_forbidden = any(forb in text_upper for forb in forbidden_terms)
            
            print(f"         📋 Forbidden terms: {forbidden_terms}")
            print(f"         ❌ Has forbidden: {has_forbidden}")
            
            if has_forbidden:
                print(f"         ❌ FAILED: Forbidden context found")
                return False
    
    # Additional validation for short terms
    if len(matched_term) <= 6:
        financial_context = ['STOCK', 'SHARE', 'PRICE', 'TRADING', 'EARNINGS', 'REVENUE', 'PROFIT', 'RESULTS', 'QUARTER']
        has_financial_context = any(fc in text_upper for fc in financial_context)
        
        print(f"         💰 Financial context check: {has_financial_context}")
        
        if not has_financial_context:
            print(f"         ❌ FAILED: No financial context for short term")
            return False
    
    print(f"         ✅ VALIDATION PASSED!")
    return True

# Test function to run debugging
def debug_ticker_matching(service, ticker):
    """Run debug analysis for a specific ticker"""
    
    print(f"\n🔍 DEBUG ANALYSIS FOR {ticker}")
    print("=" * 60)
    
    # Get all news
    all_news = service.fetch_news()
    print(f"📰 Total articles available: {len(all_news)}")
    
    # Show some sample headlines
    print(f"\n📝 SAMPLE HEADLINES (first 10):")
    for i, article in enumerate(all_news[:10]):
        headline = article['headline'][:80] + "..." if len(article['headline']) > 80 else article['headline']
        print(f"   [{i+1}] {headline}")
    
    # Test search terms
    search_terms = service.normalize_ticker_for_search(ticker)
    print(f"\n🔍 Search terms for {ticker}: {search_terms}")
    
    # Now run the debug filtering
    relevant_articles = service.filter_news_for_ticker(all_news, ticker)
    
    print(f"\n📊 SUMMARY for {ticker}:")
    print(f"   Total articles: {len(all_news)}")
    print(f"   Relevant articles found: {len(relevant_articles)}")
    
    if relevant_articles:
        print(f"\n✅ FOUND ARTICLES:")
        for i, article in enumerate(relevant_articles):
            print(f"   [{i+1}] {article['headline'][:60]}...")
    else:
        print(f"\n❌ NO ARTICLES FOUND - Check debug output above to see why")
    
    return relevant_articles

# Instructions for testing
print("""
🧪 DEBUG INSTRUCTIONS:

1. Replace your filter_news_for_ticker method with the debug version above
2. Replace your _validate_company_match method with the debug version above
3. Run this test:

# Test debugging
service = SentimentAnalysisService(days_back=30, min_headlines=1)
debug_ticker_matching(service, 'TATASTEEL')

This will show you exactly:
- Which articles are being checked
- Which search terms are being tested
- Why validation is passing/failing
- What the required/forbidden terms are
""")