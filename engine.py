"""
NBA Intelligence Dispatcher - AI Engine Module

This module handles Gemma 3 model initialization (with better rate limits),
sentiment analysis, and executive briefing generation.

Functions:
    - initialize_gemini(): Initializes Gemma 3 model (14.4K RPD vs 20 RPD for Gemini)
    - analyze_sentiment(): Analyzes sentiment and generates 5-sentence summaries
    - generate_briefing(): Generates 3-paragraph executive briefing

Note: Uses Gemma 3 models for much better rate limits (14.4K requests/day vs 20/day)
"""

import google.generativeai as genai
import pandas as pd
import logging

# Configure logging for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_gemini(api_key):
    """
    Initialize Google Generative AI client using Gemma 3 model with better rate limits.
    
    This function configures and tests the Gemma 3 model (14.4K RPD vs 20 RPD for Gemini).
    It includes fallback logic to try alternative models if Gemma is unavailable.
    
    Args:
        api_key (str): Google Gemini API key from environment variables
        
    Returns:
        genai.GenerativeModel: Configured Gemma 3 model instance
                               (or fallback model if Gemma is unavailable)
        
    Raises:
        ValueError: If API key is invalid, missing, or no models are available
        Exception: If initialization fails for all models
        
    Note:
        - Primary model: gemma-3-12b (14.4K RPD, 30 RPM - much better than Gemini's 20 RPD)
        - Fallback models: gemma-3-27b, gemma-3-4b, gemma-3-2b, gemma-3-1b
        - Secondary fallback: gemini-2.5-flash-lite, gemini-3-flash
        - Tests model with simple prompt to verify it works before returning
    """
    try:
        if not api_key or api_key.strip() == "":
            raise ValueError("GEMINI_API_KEY is missing or empty")
        
        logger.info("Initializing Gemma 3 model (better rate limits: 14.4K RPD)")
        genai.configure(api_key=api_key)
        
        # Use Gemma 3-12B as primary model (best rate limits: 14.4K RPD, 30 RPM)
        model_name = 'gemma-3-12b'
        try:
            model = genai.GenerativeModel(model_name)
            # Test the model with a simple prompt to verify it works
            test_response = model.generate_content("Say 'OK' if you're ready.")
            logger.info(f"Successfully initialized {model_name} (14.4K RPD limit)")
        except Exception as e:
            # Fallback: try other Gemma models with same great rate limits
            logger.warning(f"{model_name} not available, trying alternatives: {e}")
            fallback_models = [
                'gemma-3-27b',      # 14.4K RPD, 30 RPM
                'gemma-3-4b',       # 14.4K RPD, 30 RPM
                'gemma-3-2b',       # 14.4K RPD, 30 RPM
                'gemma-3-1b',       # 14.4K RPD, 30 RPM
                'gemini-2.5-flash-lite',  # 20 RPD, 10 RPM (if Gemma unavailable)
                'gemini-3-flash'    # 20 RPD, 5 RPM (last resort)
            ]
            model = None
            
            for fallback_name in fallback_models:
                try:
                    logger.info(f"Trying fallback model: {fallback_name}")
                    model = genai.GenerativeModel(fallback_name)
                    test_response = model.generate_content("Say 'OK' if you're ready.")
                    logger.info(f"Successfully initialized {fallback_name}")
                    break
                except Exception:
                    continue
            
            if model is None:
                # Last resort: try to list available models and use first available model
                try:
                    available_models = genai.list_models()
                    # Prefer Gemma models first, then Flash models
                    gemma_models = [m.name for m in available_models if 'gemma' in m.name.lower()]
                    flash_models = [m.name for m in available_models if 'flash' in m.name.lower()]
                    
                    if gemma_models:
                        model_name = gemma_models[0]
                        logger.info(f"Using available Gemma model: {model_name}")
                        model = genai.GenerativeModel(model_name)
                    elif flash_models:
                        model_name = flash_models[0]
                        logger.info(f"Using available Flash model: {model_name}")
                        model = genai.GenerativeModel(model_name)
                    else:
                        raise ValueError("No available models found. Please check your API key and model availability.")
                except Exception as list_error:
                    raise ValueError(f"Could not find an available model: {list_error}")
        
        return model
        
    except ValueError as e:
        logger.error(f"Invalid API key: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize Gemini: {e}")
        raise


def analyze_sentiment(headlines_df, model):
    """
    Analyze sentiment and generate 5-sentence summaries for each headline using Gemma 3 model.
    
    This function processes each headline by:
    1. Using full article content (if available) for better analysis
    2. Asking Gemini 2.5 Flash to provide sentiment score (-1.0 to 1.0)
    3. Asking Gemini 2.5 Flash to generate a detailed 5-sentence summary
    4. Parsing the response and adding results to the DataFrame
    
    Sentiment scores:
    - Range from -1.0 (bad news/injuries) to 1.0 (good news/hype)
    - 0.0 indicates neutral sentiment
    
    Args:
        headlines_df (pd.DataFrame): DataFrame with columns: headline, description, link, date, team, article_content
        model (genai.GenerativeModel): Initialized Gemini 2.5 Flash model instance
        
    Returns:
        pd.DataFrame: Original DataFrame with added columns:
            - sentiment: Float values from -1.0 to 1.0
            - summary: 5-sentence summary text (up to 500 characters)
        
    Note:
        - Uses full article content if available (better summaries)
        - Falls back to description if article content is unavailable
        - All 5 requests can be made immediately (Gemma 3 has 30 RPM limit)
        - Handles parsing errors gracefully (defaults to neutral sentiment)
        - Gemma 3 models have much better rate limits (14.4K RPD vs 20 RPD)
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
            # Gemma 3 model will analyze the content and provide both outputs
            prompt = f"""Analyze this NBA news article and provide:
1. A sentiment score from -1.0 (bad news/injuries) to 1.0 (good news/hype) as a float
2. A detailed 5-sentence summary of what this news is about, including key details, context, and implications

Headline: {headline}
Article Content: {content_to_analyze}

Format your response exactly as:
SENTIMENT: [score]
SUMMARY: [5-sentence summary covering key details, context, and implications]"""
            
            # Call Gemma 3 API
            # Note: 30 requests per minute limit - all 5 can be made immediately
            response = model.generate_content(prompt)
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


def generate_briefing(news_df, scoreboard_df, model):
    """
    Generate a 3-paragraph Executive Pregame Briefing using Gemma 3 model.
    
    This function creates a comprehensive executive briefing that:
    1. Focuses on injury impacts and how they affect today's matchups
    2. Highlights high-stakes storylines based on recent news sentiment
    3. Identifies the most important games to watch and why
    
    The briefing is generated by sending combined news and scoreboard data
    to Gemini 2.5 Flash with a structured prompt.
    
    Args:
        news_df (pd.DataFrame): DataFrame with news headlines, descriptions, sentiment scores, and summaries
        scoreboard_df (pd.DataFrame): DataFrame with today's game matchups, scores, and status
        model (genai.GenerativeModel): Initialized Gemini 2.5 Flash model instance
        
    Returns:
        str: 3-paragraph executive briefing text
        
    Note:
        - Merges news sentiment with teams playing today to identify relevant storylines
        - Includes top negative and positive sentiment news
        - Provides fallback briefing if AI generation fails
    """
    try:
        logger.info("Generating executive briefing")
        
        # Prepare data summary for Gemini 2.5 Flash
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
        
        # Create comprehensive prompt for Gemma 3 model
        prompt = f"""Write a 3-paragraph Executive Pregame Briefing for today's NBA games.

Focus on:
1. Injury impacts and how they affect today's matchups
2. High-stakes storylines based on recent news sentiment
3. The most important games to watch and why

{news_summary}

{games_summary}

{relevant_storylines}

Write a professional, concise 3-paragraph briefing that executives can quickly read. Each paragraph should be 3-5 sentences. Focus on actionable insights about injuries, team momentum, and game importance."""
        
        # Generate briefing using Gemma 3 model
        response = model.generate_content(prompt)
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
