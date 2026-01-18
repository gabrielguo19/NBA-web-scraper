"""
NBA Intelligence Dispatcher - AI Engine Module

This module handles Gemini 2.5 Flash initialization, sentiment analysis,
and executive briefing generation.
"""

import google.generativeai as genai
import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def initialize_gemini(api_key):
    """
    Initialize Google Generative AI client using Gemini 2.5 Flash.
    
    Args:
        api_key (str): Google Gemini API key
        
    Returns:
        genai.GenerativeModel: Configured Gemini 2.5 Flash model instance
        
    Raises:
        ValueError: If API key is invalid or missing
        Exception: If initialization fails
    """
    try:
        if not api_key or api_key.strip() == "":
            raise ValueError("GEMINI_API_KEY is missing or empty")
        
        logger.info("Initializing Gemini 2.5 Flash model")
        genai.configure(api_key=api_key)
        
        # Use Gemini 2.5 Flash as primary model
        model_name = 'gemini-2.5-flash'
        try:
            model = genai.GenerativeModel(model_name)
            # Test the model with a simple prompt to verify it works
            test_response = model.generate_content("Say 'OK' if you're ready.")
            logger.info(f"Successfully initialized {model_name}")
        except Exception as e:
            # Fallback: try other available Flash models
            logger.warning(f"{model_name} not available, trying alternatives: {e}")
            fallback_models = ['gemini-2.0-flash-exp', 'gemini-2.0-flash', 'gemini-1.5-flash']
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
                # Last resort: try to list available models
                try:
                    available_models = genai.list_models()
                    flash_models = [m.name for m in available_models if 'flash' in m.name.lower()]
                    if flash_models:
                        model_name = flash_models[0]
                        logger.info(f"Using available model: {model_name}")
                        model = genai.GenerativeModel(model_name)
                    else:
                        raise ValueError("No Flash models available. Please check your API key and model availability.")
                except Exception as list_error:
                    raise ValueError(f"Could not find an available Gemini Flash model: {list_error}")
        
        return model
        
    except ValueError as e:
        logger.error(f"Invalid API key: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize Gemini: {e}")
        raise


def analyze_sentiment(headlines_df, model):
    """
    Analyze sentiment and generate summary for each headline using Gemini 2.5 Flash.
    
    Scores range from -1.0 (bad news/injuries) to 1.0 (good news/hype).
    Also generates a short summary for each headline.
    
    Args:
        headlines_df (pd.DataFrame): DataFrame with columns: headline, description, link, date, team
        model (genai.GenerativeModel): Initialized Gemini model instance
        
    Returns:
        pd.DataFrame: Original DataFrame with added 'sentiment' and 'summary' columns
    """
    if headlines_df.empty:
        logger.warning("Empty headlines DataFrame provided for sentiment analysis")
        headlines_df['sentiment'] = 0.0
        headlines_df['summary'] = ""
        return headlines_df
    
    logger.info(f"Analyzing sentiment and generating summaries for {len(headlines_df)} headlines")
    
    sentiments = []
    summaries = []
    
    for idx, row in headlines_df.iterrows():
        try:
            headline = str(row.get('headline', ''))
            description = str(row.get('description', ''))
            
            if not headline:
                logger.warning(f"Empty headline at index {idx}, assigning neutral sentiment")
                sentiments.append(0.0)
                summaries.append("No summary available")
                continue
            
            # Get article content if available
            article_content = str(row.get('article_content', ''))
            
            # Create prompt for sentiment analysis AND summary generation
            # Use full article content if available, otherwise use description
            content_to_analyze = article_content if article_content and len(article_content) > 50 else description
            
            prompt = f"""Analyze this NBA news article and provide:
1. A sentiment score from -1.0 (bad news/injuries) to 1.0 (good news/hype) as a float
2. A detailed 5-sentence summary of what this news is about, including key details, context, and implications

Headline: {headline}
Article Content: {content_to_analyze}

Format your response exactly as:
SENTIMENT: [score]
SUMMARY: [5-sentence summary covering key details, context, and implications]"""
            
            # Call Gemini API (5 requests per minute limit - can do all 5 immediately)
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Parse sentiment and summary from response
            sentiment_score = 0.0
            summary = "No summary available"
            
            try:
                import re
                # Extract sentiment
                sentiment_match = re.search(r'SENTIMENT:\s*(-?\d+\.?\d*)', response_text, re.IGNORECASE)
                if sentiment_match:
                    sentiment_score = float(sentiment_match.group(1))
                    sentiment_score = max(-1.0, min(1.0, sentiment_score))
                else:
                    # Fallback: try to find any number
                    numbers = re.findall(r'-?\d+\.?\d*', response_text)
                    if numbers:
                        sentiment_score = float(numbers[0])
                        sentiment_score = max(-1.0, min(1.0, sentiment_score))
                
                # Extract summary
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
                        # Last resort: use first sentence after any numbers
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
    Generate a 3-paragraph Executive Pregame Briefing using Gemini 2.5 Flash.
    
    Focuses on injury impacts and high-stakes storylines based on news sentiment
    and game data.
    
    Args:
        news_df (pd.DataFrame): DataFrame with news headlines, descriptions, and sentiment scores
        scoreboard_df (pd.DataFrame): DataFrame with today's game matchups and scores
        model (genai.GenerativeModel): Initialized Gemini model instance
        
    Returns:
        str: 3-paragraph executive briefing text
    """
    try:
        logger.info("Generating executive briefing")
        
        # Prepare data summary for Gemini
        news_summary = ""
        if not news_df.empty:
            # Get top headlines with sentiment
            top_negative = news_df.nsmallest(3, 'sentiment') if len(news_df) >= 3 else news_df.nsmallest(len(news_df), 'sentiment')
            top_positive = news_df.nlargest(3, 'sentiment') if len(news_df) >= 3 else news_df.nlargest(len(news_df), 'sentiment')
            
            news_summary = "Top News Headlines:\n"
            news_summary += "\nNegative Sentiment News:\n"
            for _, row in top_negative.iterrows():
                news_summary += f"- {row['headline']} (Sentiment: {row['sentiment']:.2f}, Team: {row.get('team', 'N/A')})\n"
            
            news_summary += "\nPositive Sentiment News:\n"
            for _, row in top_positive.iterrows():
                news_summary += f"- {row['headline']} (Sentiment: {row['sentiment']:.2f}, Team: {row.get('team', 'N/A')})\n"
        
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
            
            matching_news = news_df[news_df['team'].isin(teams_playing)]
            if not matching_news.empty:
                for _, row in matching_news.iterrows():
                    relevant_storylines += f"- {row['headline']} (Team: {row['team']}, Sentiment: {row['sentiment']:.2f})\n"
            else:
                relevant_storylines += "- No direct news matches for teams playing today.\n"
        
        # Create comprehensive prompt
        prompt = f"""Write a 3-paragraph Executive Pregame Briefing for today's NBA games.

Focus on:
1. Injury impacts and how they affect today's matchups
2. High-stakes storylines based on recent news sentiment
3. The most important games to watch and why

{news_summary}

{games_summary}

{relevant_storylines}

Write a professional, concise 3-paragraph briefing that executives can quickly read. Each paragraph should be 3-5 sentences. Focus on actionable insights about injuries, team momentum, and game importance."""
        
        # Generate briefing
        response = model.generate_content(prompt)
        briefing = response.text.strip()
        
        # Ensure it's roughly 3 paragraphs (split by double newlines or periods)
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
        # Return a fallback briefing
        fallback = """Today's NBA schedule presents several key matchups worth monitoring. Recent news sentiment and injury reports will significantly impact game outcomes and team performance.

The most critical games today feature teams dealing with various challenges, from injury concerns to momentum shifts based on recent performance. Teams with negative news sentiment may face additional pressure, while those with positive momentum could capitalize on their current form.

Executives should pay close attention to games involving teams with significant injury reports or recent roster changes, as these factors often determine game outcomes more than historical matchups."""
        return fallback
