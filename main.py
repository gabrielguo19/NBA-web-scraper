"""
NBA Intelligence Dispatcher - Main Entry Point

Orchestrates the complete workflow:
1. Scrape ESPN headlines and NBA scoreboard
2. Analyze sentiment using Gemini 2.5 Flash
3. Generate executive briefing
4. Send HTML email with results

All sensitive data (API keys, email credentials) is loaded from .env file.
"""

import os
import sys
from dotenv import load_dotenv
import logging
import traceback

# Import custom modules
from scraper import scrape_espn_headlines, get_todays_scoreboard
from engine import initialize_gemini, analyze_sentiment, generate_briefing
from notifier import send_email

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_environment():
    """
    Validate that all required environment variables are present.
    
    Returns:
        tuple: (gemini_key, gmail_email, gmail_password, recipient_email) if valid
        None: If validation fails
    """
    required_vars = {
        'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY'),
        'GMAIL_EMAIL': os.getenv('GMAIL_EMAIL'),
        'GMAIL_APP_PASSWORD': os.getenv('GMAIL_APP_PASSWORD'),
        'EMAIL_RECIPIENT': os.getenv('EMAIL_RECIPIENT')
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value or value.strip() == ""]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please check your .env file and ensure all variables are set")
        return None
    
    # Check for placeholder values
    if 'your_' in required_vars['GEMINI_API_KEY'].lower():
        logger.error("GEMINI_API_KEY appears to be a placeholder. Please set your actual API key in .env")
        return None
    
    if 'your_' in required_vars['GMAIL_EMAIL'].lower() or '@' not in required_vars['GMAIL_EMAIL']:
        logger.error("GMAIL_EMAIL appears to be invalid. Please set your actual Gmail address in .env")
        return None
    
    logger.info("Environment variables validated successfully")
    return (
        required_vars['GEMINI_API_KEY'],
        required_vars['GMAIL_EMAIL'],
        required_vars['GMAIL_APP_PASSWORD'],
        required_vars['EMAIL_RECIPIENT']
    )


def main():
    """
    Main execution function that orchestrates the complete workflow.
    
    Workflow:
    1. Load environment variables
    2. Initialize Gemini model
    3. Scrape ESPN headlines
    4. Fetch today's scoreboard
    5. Analyze sentiment
    6. Generate executive briefing
    7. Send email
    
    Returns:
        int: 0 on success, 1 on failure
    """
    try:
        print("Starting NBA Intelligence Dispatcher...")
        logger.info("=" * 60)
        logger.info("NBA Intelligence Dispatcher - Starting")
        logger.info("=" * 60)
        
        # Load environment variables
        logger.info("Loading environment variables from .env")
        load_dotenv()
        
        # Validate environment
        env_vars = validate_environment()
        if not env_vars:
            logger.error("Environment validation failed. Exiting.")
            return 1
        
        gemini_key, gmail_email, gmail_password, recipient_email = env_vars
        
        # Initialize Gemini
        logger.info("Initializing Gemini 2.5 Flash model")
        try:
            model = initialize_gemini(gemini_key)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            logger.error("Please check your GEMINI_API_KEY in .env")
            return 1
        
        # Scrape ESPN headlines
        logger.info("Step 1: Scraping ESPN headlines")
        try:
            headlines_df = scrape_espn_headlines(limit=5)
            if headlines_df.empty:
                logger.warning("No headlines scraped. Continuing with empty DataFrame.")
            else:
                logger.info(f"Successfully scraped {len(headlines_df)} headlines")
        except Exception as e:
            logger.error(f"Error scraping headlines: {e}")
            logger.warning("Continuing with empty headlines DataFrame")
            import pandas as pd
            headlines_df = pd.DataFrame(columns=['headline', 'description', 'link', 'date', 'team'])
        
        # Fetch today's scoreboard
        logger.info("Step 2: Fetching today's NBA scoreboard")
        try:
            scoreboard_df = get_todays_scoreboard()
            if scoreboard_df.empty:
                logger.warning("No games found for today. Continuing with empty DataFrame.")
            else:
                logger.info(f"Successfully fetched {len(scoreboard_df)} games")
        except Exception as e:
            logger.error(f"Error fetching scoreboard: {e}")
            logger.warning("Continuing with empty scoreboard DataFrame")
            import pandas as pd
            scoreboard_df = pd.DataFrame(columns=['home_team', 'away_team', 'home_score', 
                                                  'away_score', 'status', 'game_id', 'game_date'])
        
        # Analyze sentiment
        logger.info("Step 3: Analyzing sentiment of headlines")
        try:
            if not headlines_df.empty:
                headlines_df = analyze_sentiment(headlines_df, model)
                logger.info("Sentiment analysis complete")
            else:
                logger.warning("Skipping sentiment analysis - no headlines available")
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            logger.warning("Continuing without sentiment scores")
            if 'sentiment' not in headlines_df.columns:
                headlines_df['sentiment'] = 0.0
        
        # Generate executive briefing
        logger.info("Step 4: Generating executive briefing")
        try:
            briefing = generate_briefing(headlines_df, scoreboard_df, model)
            logger.info("Executive briefing generated successfully")
        except Exception as e:
            logger.error(f"Error generating briefing: {e}")
            logger.warning("Using fallback briefing")
            briefing = """Today's NBA schedule presents several key matchups worth monitoring. Recent news sentiment and injury reports will significantly impact game outcomes and team performance.

The most critical games today feature teams dealing with various challenges, from injury concerns to momentum shifts based on recent performance. Teams with negative news sentiment may face additional pressure, while those with positive momentum could capitalize on their current form.

Executives should pay close attention to games involving teams with significant injury reports or recent roster changes, as these factors often determine game outcomes more than historical matchups."""
        
        # Send email
        logger.info("Step 5: Sending email")
        try:
            success = send_email(
                briefing=briefing,
                news_df=headlines_df,
                scoreboard_df=scoreboard_df,
                sender_email=gmail_email,
                app_password=gmail_password,
                recipient_email=recipient_email
            )
            
            if success:
                logger.info("=" * 60)
                logger.info("NBA Intelligence Dispatcher - Completed Successfully")
                logger.info("=" * 60)
                return 0
            else:
                logger.error("Failed to send email")
                return 1
                
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            logger.error(traceback.format_exc())
            return 1
        
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error in main execution: {e}")
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
