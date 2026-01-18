"""
NBA Intelligence Dispatcher - AI Engine Module

This module handles Gemini text-out model initialization (automatically selects best available),
sentiment analysis, and executive briefing generation.

Functions:
    - initialize_gemini(): Initializes Gemini text-out model (automatically selects best available)
    - analyze_sentiment(): Analyzes sentiment and generates 5-sentence summaries using Gemini
    - generate_briefing(): Generates 3-paragraph executive briefing using Gemini

Note: Automatically detects and uses the best available Gemini text-out model (currently gemini-2.5-flash-lite)
"""

from google import genai
import pandas as pd
import logging

# Configure logging for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_gemini(api_key):
    """
    Initialize Google GenAI client with Gemini text-out model, automatically selecting best available.
    
    This function creates a GenAI client and checks available Gemini text-out models to select
    the one with the best rate limits. It dynamically detects which Gemini models are
    available through the API and uses the best one.
    
    Args:
        api_key (str): Google Gemini API key from environment variables
        
    Returns:
        tuple: (genai.Client, str) - Client instance and Gemini model name
        
    Raises:
        ValueError: If API key is invalid, missing, or no Gemini models are available
        Exception: If initialization fails for all models
        
    Note:
        - Prefers gemini-2.5-flash-lite (10 RPM, 20 RPD) - confirmed working
        - Falls back to other Gemini Flash models if preferred unavailable
        - Only uses text-out models (required for this use case)
        - Dynamically checks available Gemini models via API
        - Tests model with simple prompt to verify it works before returning
    """
    try:
        if not api_key or api_key.strip() == "":
            raise ValueError("GEMINI_API_KEY is missing or empty")
        
        logger.info("Initializing Google GenAI client with Gemini text-out models (checking for best rate limits)")
        
        # Create client with API key
        client = genai.Client(api_key=api_key)
        
        # First, check what Gemini text-out models are actually available
        try:
            available_models = client.models.list()
            # Filter to only text-out models (required for this use case)
            text_out_models = [m.name for m in available_models if 'text-out' in str(m.category).lower() or 'flash' in m.name.lower()]
            model_names = text_out_models if text_out_models else [m.name for m in available_models]
            
            # Try to find Gemini models with best rate limits in order of preference
            # gemini-2.5-flash-lite has 10 RPM and 20 RPD (better than regular flash)
            preferred_models = [
                'gemini-2.5-flash-lite',  # 10 RPM, 20 RPD - confirmed working
                'gemini-3-flash',         # 5 RPM, 20 RPD
                'gemini-2.5-flash',       # 5 RPM, 20 RPD
                'gemini-2.0-flash-exp',   # Experimental
                'gemini-2.0-flash',       # Fallback
            ]
            
            model_name = None
            
            # Try preferred models first
            for preferred in preferred_models:
                if preferred in model_names:
                    try:
                        logger.info(f"Testing model: {preferred}")
                        # Test the model with a simple prompt
                        test_response = client.models.generate_content(
                            model=preferred,
                            contents="Say 'OK' if you're ready."
                        )
                        model_name = preferred
                        logger.info(f"Successfully initialized {preferred}")
                        break
                    except Exception as e:
                        logger.debug(f"{preferred} failed: {e}")
                        continue
            
            # If no preferred model worked, try any Gemini Flash model
            if model_name is None:
                flash_models = [m for m in model_names if 'flash' in m.lower() and 'gemini' in m.lower()]
                for flash_model in flash_models:
                    try:
                        logger.info(f"Trying available Gemini Flash model: {flash_model}")
                        test_response = client.models.generate_content(
                            model=flash_model,
                            contents="Say 'OK' if you're ready."
                        )
                        model_name = flash_model
                        logger.info(f"Successfully initialized {flash_model}")
                        break
                    except Exception as e:
                        logger.debug(f"{flash_model} failed: {e}")
                        continue
            
            if model_name is None:
                raise ValueError("No working models found. Please check your API key and model availability.")
                
        except Exception as e:
            # Fallback: try hardcoded list if list_models fails
            logger.warning(f"Could not list models, trying hardcoded list: {e}")
            fallback_models = [
                'gemini-2.5-flash-lite',
                'gemini-3-flash',
                'gemini-2.5-flash',
                'gemini-2.0-flash-exp',
                'gemini-2.0-flash'
            ]
            model_name = None
            
            for fallback_name in fallback_models:
                try:
                    logger.info(f"Trying fallback model: {fallback_name}")
                    test_response = client.models.generate_content(
                        model=fallback_name,
                        contents="Say 'OK' if you're ready."
                    )
                    model_name = fallback_name
                    logger.info(f"Successfully initialized {fallback_name}")
                    break
                except Exception:
                    continue
            
            if model_name is None:
                raise ValueError("No available models found. Please check your API key and model availability.")
        
        return client, model_name
        
    except ValueError as e:
        logger.error(f"Invalid API key: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize Gemini: {e}")
        raise


def analyze_sentiment(headlines_df, client, model_name):
    """
    Analyze sentiment and generate 5-sentence summaries for each headline using Gemini text-out model.
    
    This function processes each headline by:
    1. Using full article content (if available) for better analysis
    2. Asking Gemini model to provide sentiment score (-1.0 to 1.0)
    3. Asking Gemini model to generate a detailed 5-sentence summary
    4. Parsing the response and adding results to the DataFrame
    
    Sentiment scores:
    - Range from -1.0 (bad news/injuries) to 1.0 (good news/hype)
    - 0.0 indicates neutral sentiment
    
    Args:
        headlines_df (pd.DataFrame): DataFrame with columns: headline, description, link, date, team, article_content
        client (genai.Client): Initialized Google GenAI client instance
        model_name (str): Name of the model to use (e.g., 'gemini-2.5-flash-lite')
        
    Returns:
        pd.DataFrame: Original DataFrame with added columns:
            - sentiment: Float values from -1.0 to 1.0
            - summary: 5-sentence summary text (up to 500 characters)
        
    Note:
        - Uses full article content if available (better summaries)
        - Falls back to description if article content is unavailable
        - All 5 requests can be made immediately (current model has 10 RPM limit)
        - Handles parsing errors gracefully (defaults to neutral sentiment)
    """
    if headlines_df.empty:
        logger.warning("Empty headlines DataFrame provided for sentiment analysis")
        headlines_df['sentiment'] = 0.0
        headlines_df['summary'] = ""
        return headlines_df
    
    logger.info(f"Analyzing sentiment and generating summaries for {len(headlines_df)} headlines")
    
    sentiments = []
    summaries = []
    
    # Process each headline
    for idx, row in headlines_df.iterrows():
        try:
            headline = str(row.get('headline', ''))
            description = str(row.get('description', ''))
            
            if not headline:
                logger.warning(f"Empty headline at index {idx}, assigning neutral sentiment")
                sentiments.append(0.0)
                summaries.append("No summary available")
                continue
            
            # Get article content if available (preferred for better summaries)
            article_content = str(row.get('article_content', ''))
            
            # Use full article content if available, otherwise use description
            # Article content provides much better context for AI analysis
            content_to_analyze = article_content if article_content and len(article_content) > 50 else description
            
            # Create prompt for sentiment analysis AND summary generation
            # Gemini text-out model will analyze the content and provide both outputs
            prompt = f"""Analyze this NBA news article and provide:
1. A sentiment score from -1.0 (bad news/injuries) to 1.0 (good news/hype) as a float
2. A detailed 5-sentence summary of what this news is about, including key details, context, and implications

Headline: {headline}
Article Content: {content_to_analyze}

Format your response exactly as:
SENTIMENT: [score]
SUMMARY: [5-sentence summary covering key details, context, and implications]"""
            
            # Call Gemini API using new Google GenAI SDK
            # Note: Current Gemini model has 10 RPM limit - all 5 can be made immediately
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            response_text = response.text.strip()
            
            # Parse sentiment and summary from response
            sentiment_score = 0.0
            summary = "No summary available"
            
            try:
                import re
                # Extract sentiment score using regex
                sentiment_match = re.search(r'SENTIMENT:\s*(-?\d+\.?\d*)', response_text, re.IGNORECASE)
                if sentiment_match:
                    sentiment_score = float(sentiment_match.group(1))
                    # Clamp to valid range [-1.0, 1.0]
                    sentiment_score = max(-1.0, min(1.0, sentiment_score))
                else:
                    # Fallback: try to find any number in the response
                    numbers = re.findall(r'-?\d+\.?\d*', response_text)
                    if numbers:
                        sentiment_score = float(numbers[0])
                        sentiment_score = max(-1.0, min(1.0, sentiment_score))
                
                # Extract summary text
                summary_match = re.search(r'SUMMARY:\s*(.+?)(?:\n|$)', response_text, re.IGNORECASE | re.DOTALL)
                if summary_match:
                    summary = summary_match.group(1).strip()
                else:
                    # Fallback: if no SUMMARY tag, try to get text after SENTIMENT line
                    lines = response_text.split('\n')
                    for i, line in enumerate(lines):
                        if 'SENTIMENT' in line.upper() and i + 1 < len(lines):
                            summary = lines[i + 1].strip()
                            break
                    if not summary or summary == "":
                        # Last resort: use last line of response
                        summary = response_text.split('\n')[-1].strip() if response_text else "No summary available"
                
                # Clean up summary
                summary = summary.replace('SUMMARY:', '').strip()
                # For 5-sentence summaries, allow up to 500 characters
                if len(summary) > 500:
                    summary = summary[:500] + "..."
                    
            except (ValueError, IndexError) as e:
                logger.warning(f"Error parsing response: {e}, response: {response_text}, using defaults")
            
            sentiments.append(sentiment_score)
            summaries.append(summary)
            
        except Exception as e:
            logger.error(f"Error analyzing headline at index {idx}: {e}")
            sentiments.append(0.0)  # Default to neutral on error
            summaries.append("Error generating summary")
            continue
    
    # Add sentiment and summary columns to DataFrame
    headlines_df = headlines_df.copy()
    headlines_df['sentiment'] = sentiments
    headlines_df['summary'] = summaries
    
    logger.info(f"Analysis complete. Average sentiment: {headlines_df['sentiment'].mean():.2f}")
    return headlines_df


def generate_briefing(news_df, scoreboard_df, client, model_name):
    """
    Generate a 3-paragraph Executive Pregame Briefing using Gemini text-out model.
    
    This function creates a comprehensive executive briefing that:
    1. Focuses on injury impacts and how they affect today's matchups
    2. Highlights high-stakes storylines based on recent news sentiment
    3. Identifies the most important games to watch and why
    
    The briefing is generated by sending combined news and scoreboard data
    to the Gemini model with a structured prompt.
    
    Args:
        news_df (pd.DataFrame): DataFrame with news headlines, descriptions, sentiment scores, and summaries
        scoreboard_df (pd.DataFrame): DataFrame with today's game matchups, scores, and status
        client (genai.Client): Initialized Google GenAI client instance
        model_name (str): Name of the model to use (e.g., 'gemini-2.5-flash-lite')
        
    Returns:
        str: 3-paragraph executive briefing text
        
    Note:
        - Merges news sentiment with teams playing today to identify relevant storylines
        - Includes top negative and positive sentiment news
        - Provides fallback briefing if AI generation fails
    """
    try:
        logger.info("Generating executive briefing")
        
        # Prepare data summary for Gemini model
        news_summary = ""
        if not news_df.empty:
            # Get top headlines with sentiment (most negative and most positive)
            top_negative = news_df.nsmallest(3, 'sentiment') if len(news_df) >= 3 else news_df.nsmallest(len(news_df), 'sentiment')
            top_positive = news_df.nlargest(3, 'sentiment') if len(news_df) >= 3 else news_df.nlargest(len(news_df), 'sentiment')
            
            news_summary = "Top News Headlines:\n"
            news_summary += "\nNegative Sentiment News:\n"
            for _, row in top_negative.iterrows():
                news_summary += f"- {row['headline']} (Sentiment: {row['sentiment']:.2f}, Team: {row.get('team', 'N/A')})\n"
            
            news_summary += "\nPositive Sentiment News:\n"
            for _, row in top_positive.iterrows():
                news_summary += f"- {row['headline']} (Sentiment: {row['sentiment']:.2f}, Team: {row.get('team', 'N/A')})\n"
        
        # Prepare games summary
        games_summary = ""
        if not scoreboard_df.empty:
            games_summary = "\nToday's Games:\n"
            for _, game in scoreboard_df.iterrows():
                games_summary += f"- {game['away_team']} @ {game['home_team']} (Status: {game['status']}"
                if game['home_score'] > 0 or game['away_score'] > 0:
                    games_summary += f", Score: {game['away_team']} {game['away_score']} - {game['home_team']} {game['home_score']}"
                games_summary += ")\n"
        else:
            games_summary = "\nNo games scheduled for today.\n"
        
        # Merge news with games by team to identify relevant storylines
        relevant_storylines = ""
        if not news_df.empty and not scoreboard_df.empty:
            relevant_storylines = "\nRelevant Storylines (News matching teams playing today):\n"
            teams_playing = set()
            for _, game in scoreboard_df.iterrows():
                teams_playing.add(game['home_team'])
                teams_playing.add(game['away_team'])
            
            # Find news articles that mention teams playing today
            matching_news = news_df[news_df['team'].isin(teams_playing)]
            if not matching_news.empty:
                for _, row in matching_news.iterrows():
                    relevant_storylines += f"- {row['headline']} (Team: {row['team']}, Sentiment: {row['sentiment']:.2f})\n"
            else:
                relevant_storylines += "- No direct news matches for teams playing today.\n"
        
        # Create comprehensive prompt for Gemini model
        prompt = f"""Write a 3-paragraph Executive Pregame Briefing for today's NBA games.

Focus on:
1. Injury impacts and how they affect today's matchups
2. High-stakes storylines based on recent news sentiment
3. The most important games to watch and why

{news_summary}

{games_summary}

{relevant_storylines}

Write a professional, concise 3-paragraph briefing that executives can quickly read. Each paragraph should be 3-5 sentences. Focus on actionable insights about injuries, team momentum, and game importance."""
        
        # Generate briefing using Gemini text-out model (new Google GenAI SDK)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        briefing = response.text.strip()
        
        # Ensure it's roughly 3 paragraphs (split by double newlines)
        paragraphs = [p.strip() for p in briefing.split('\n\n') if p.strip()]
        if len(paragraphs) < 3:
            # If not enough paragraphs, try splitting by single newlines
            paragraphs = [p.strip() for p in briefing.split('\n') if p.strip() and len(p.strip()) > 50]
        
        # Format as 3 paragraphs
        if len(paragraphs) >= 3:
            briefing = '\n\n'.join(paragraphs[:3])
        elif len(paragraphs) > 0:
            briefing = '\n\n'.join(paragraphs)
        
        logger.info("Executive briefing generated successfully")
        return briefing
        
    except Exception as e:
        logger.error(f"Error generating briefing: {e}")
        # Return a fallback briefing if AI generation fails
        fallback = """Today's NBA schedule presents several key matchups worth monitoring. Recent news sentiment and injury reports will significantly impact game outcomes and team performance.

The most critical games today feature teams dealing with various challenges, from injury concerns to momentum shifts based on recent performance. Teams with negative news sentiment may face additional pressure, while those with positive momentum could capitalize on their current form.

Executives should pay close attention to games involving teams with significant injury reports or recent roster changes, as these factors often determine game outcomes more than historical matchups."""
        return fallback
