"""
Quick test script to verify individual components work correctly.
Run this to test each component without running the full workflow.
"""

import os
from dotenv import load_dotenv
from scraper import scrape_espn_headlines, get_todays_scoreboard
from engine import initialize_gemini

# Load environment variables
load_dotenv()

def test_scraper():
    """Test ESPN headline scraping."""
    print("\n" + "="*60)
    print("Testing ESPN Headline Scraper")
    print("="*60)
    try:
        df = scrape_espn_headlines(limit=5)
        print(f"✓ Successfully scraped {len(df)} headlines")
        if not df.empty:
            print(f"\nSample headline:")
            print(f"  - {df.iloc[0]['headline']}")
            print(f"  - Description: {df.iloc[0]['description'][:100]}...")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_scoreboard():
    """Test NBA scoreboard fetching."""
    print("\n" + "="*60)
    print("Testing NBA Scoreboard")
    print("="*60)
    try:
        df = get_todays_scoreboard()
        print(f"✓ Successfully fetched {len(df)} games")
        if not df.empty:
            print(f"\nSample game:")
            game = df.iloc[0]
            print(f"  - {game['away_team']} @ {game['home_team']}")
            print(f"  - Status: {game['status']}")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_gemini():
    """Test AI model initialization."""
    print("\n" + "="*60)
    print("Testing AI Model Initialization (Google GenAI SDK)")
    print("="*60)
    try:
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("✗ GEMINI_API_KEY not found in .env")
            return False
        
        client, model_name = initialize_gemini(api_key)
        print(f"✓ AI model initialized successfully: {model_name}")
        
        # Test a simple prompt
        print("  Testing with a simple prompt...")
        response = client.models.generate_content(
            model=model_name,
            contents="Say 'OK' if you're working."
        )
        print(f"  Response: {response.text}")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_env_vars():
    """Test environment variables."""
    print("\n" + "="*60)
    print("Testing Environment Variables")
    print("="*60)
    required = ['GEMINI_API_KEY', 'GMAIL_EMAIL', 'GMAIL_APP_PASSWORD', 'EMAIL_RECIPIENT']
    all_set = True
    
    for var in required:
        value = os.getenv(var)
        if value and 'your_' not in value.lower():
            print(f"✓ {var}: Set")
        else:
            print(f"✗ {var}: Missing or placeholder")
            all_set = False
    
    return all_set

if __name__ == "__main__":
    print("\n" + "="*60)
    print("NBA Intelligence Dispatcher - Component Tests")
    print("="*60)
    
    results = []
    
    # Test environment variables
    results.append(("Environment Variables", test_env_vars()))
    
    # Test Gemini (only if env vars are set)
    if results[0][1]:
        results.append(("Gemini Initialization", test_gemini()))
    else:
        print("\n⚠ Skipping Gemini test - environment variables not set")
        results.append(("Gemini Initialization", False))
    
    # Test scraper
    results.append(("ESPN Scraper", test_scraper()))
    
    # Test scoreboard
    results.append(("NBA Scoreboard", test_scoreboard()))
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result[1] for result in results)
    print("\n" + "="*60)
    if all_passed:
        print("✓ All tests passed! Ready to run main.py")
    else:
        print("✗ Some tests failed. Please fix issues before running main.py")
    print("="*60 + "\n")
