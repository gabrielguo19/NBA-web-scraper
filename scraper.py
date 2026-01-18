"""
NBA Intelligence Dispatcher - Scraper Module

This module handles web scraping of ESPN NBA headlines and fetching
today's NBA game scoreboard using the nba_api library.

Functions:
    - scrape_article_content(): Scrapes full article text from ESPN article pages
    - extract_team_name(): Extracts NBA team names from text
    - scrape_espn_headlines(): Scrapes top NBA headlines and full article content
    - get_todays_scoreboard(): Fetches today's NBA games using nba_api
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from nba_api.live.nba.endpoints import ScoreBoard
import re
import logging

# Configure logging for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NBA team name mapping for normalization - all 30 NBA teams
NBA_TEAMS = {
    'Atlanta Hawks', 'Boston Celtics', 'Brooklyn Nets', 'Charlotte Hornets',
    'Chicago Bulls', 'Cleveland Cavaliers', 'Dallas Mavericks', 'Denver Nuggets',
    'Detroit Pistons', 'Golden State Warriors', 'Houston Rockets', 'Indiana Pacers',
    'LA Clippers', 'Los Angeles Lakers', 'Memphis Grizzlies', 'Miami Heat',
    'Milwaukee Bucks', 'Minnesota Timberwolves', 'New Orleans Pelicans', 'New York Knicks',
    'Oklahoma City Thunder', 'Orlando Magic', 'Philadelphia 76ers', 'Phoenix Suns',
    'Portland Trail Blazers', 'Sacramento Kings', 'San Antonio Spurs', 'Toronto Raptors',
    'Utah Jazz', 'Washington Wizards'
}

# Common team name variations for extraction from headlines/descriptions
# Maps keywords to full team names for better matching
TEAM_KEYWORDS = {
    'hawks': 'Atlanta Hawks', 'celtics': 'Boston Celtics', 'nets': 'Brooklyn Nets',
    'hornets': 'Charlotte Hornets', 'bulls': 'Chicago Bulls', 'cavaliers': 'Cleveland Cavaliers',
    'cavs': 'Cleveland Cavaliers', 'mavericks': 'Dallas Mavericks', 'mavs': 'Dallas Mavericks',
    'nuggets': 'Denver Nuggets', 'pistons': 'Detroit Pistons', 'warriors': 'Golden State Warriors',
    'rockets': 'Houston Rockets', 'pacers': 'Indiana Pacers', 'clippers': 'LA Clippers',
    'lakers': 'Los Angeles Lakers', 'grizzlies': 'Memphis Grizzlies', 'heat': 'Miami Heat',
    'bucks': 'Milwaukee Bucks', 'timberwolves': 'Minnesota Timberwolves', 'wolves': 'Minnesota Timberwolves',
    'pelicans': 'New Orleans Pelicans', 'knicks': 'New York Knicks', 'thunder': 'Oklahoma City Thunder',
    'magic': 'Orlando Magic', '76ers': 'Philadelphia 76ers', 'sixers': 'Philadelphia 76ers',
    'suns': 'Phoenix Suns', 'trail blazers': 'Portland Trail Blazers', 'blazers': 'Portland Trail Blazers',
    'kings': 'Sacramento Kings', 'spurs': 'San Antonio Spurs', 'raptors': 'Toronto Raptors',
    'jazz': 'Utah Jazz', 'wizards': 'Washington Wizards'
}


def scrape_article_content(article_url, headers):
    """
    Scrape the full article content from an ESPN article page.
    
    This function visits each article URL and extracts the main article text
    to provide more context for AI analysis. It tries multiple CSS selectors
    to find article content, as ESPN's structure may vary.
    
    Args:
        article_url (str): Full URL of the ESPN article to scrape
        headers (dict): HTTP headers dictionary for the request (includes User-Agent)
        
    Returns:
        str: Full article text content (up to 2000 characters), or empty string if scraping fails
        
    Note:
        - Limits content to 2000 characters to stay within API token limits
        - Gracefully handles failures and returns empty string
    """
    try:
        logger.debug(f"Scraping article content from: {article_url}")
        response = requests.get(article_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Find article content - ESPN uses various selectors depending on article type
        article_text = ""
        
        # Try common ESPN article content selectors in order of preference
        content_selectors = [
            '.article-body',              # Standard article body class
            '[data-module="ArticleBody"]', # Data attribute selector
            '.StoryBody',                  # Story body class
            'article p',                   # Paragraphs within article tag
            '.article-content p',          # Article content paragraphs
            '.article p'                   # Generic article paragraphs
        ]
        
        # Try each selector until we find substantial content (>100 chars)
        for selector in content_selectors:
            content_elements = soup.select(selector)
            if content_elements:
                # Combine all paragraph text into single string
                paragraphs = [elem.get_text(strip=True) for elem in content_elements if elem.get_text(strip=True)]
                article_text = ' '.join(paragraphs)
                if len(article_text) > 100:  # Make sure we got substantial content
                    break
        
        # Fallback: If no content found with selectors, try to get all paragraph text from main content area
        if not article_text or len(article_text) < 100:
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|article|story', re.I))
            if main_content:
                paragraphs = main_content.find_all('p')
                article_text = ' '.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        
        # Clean up the text
        if article_text:
            # Remove extra whitespace and normalize
            article_text = ' '.join(article_text.split())
            # Limit to reasonable length (first 2000 chars should be enough for AI summary)
            # This helps stay within API token limits while providing sufficient context
            if len(article_text) > 2000:
                article_text = article_text[:2000] + "..."
        
        logger.debug(f"Scraped {len(article_text)} characters of article content")
        return article_text
        
    except Exception as e:
        logger.warning(f"Error scraping article content from {article_url}: {e}")
        return ""


def extract_team_name(text):
    """
    Extract NBA team name from headline or description text using keyword matching.
    
    Searches for team name keywords in the provided text and returns the
    corresponding full team name if found.
    
    Args:
        text (str): Text to search for team names (headline, description, etc.)
        
    Returns:
        str: Full team name if found (e.g., "Los Angeles Lakers"), None otherwise
        
    Example:
        >>> extract_team_name("Lakers beat Warriors in overtime")
        "Los Angeles Lakers"
    """
    if not text:
        return None
    
    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # Search for team keywords in the text
    for keyword, team_name in TEAM_KEYWORDS.items():
        if keyword in text_lower:
            return team_name
    
    return None


def scrape_espn_headlines(limit=5):
    """
    Scrape the top NBA headlines and full article content from ESPN NBA news page.
    
    This function:
    1. Scrapes the ESPN NBA homepage for headlines
    2. Extracts headline text, descriptions, and links
    3. Visits each article URL to scrape full article content
    4. Extracts team names when possible
    5. Returns everything as a Pandas DataFrame
    
    Args:
        limit (int): Maximum number of headlines to scrape (default: 5)
                     Limited to 5 to stay within Gemini API free tier rate limits (5 RPM)
        
    Returns:
        pd.DataFrame: DataFrame with columns:
            - headline: Article headline text
            - description: Short description from homepage (if available)
            - link: Full URL to the article
            - date: Scrape date (YYYY-MM-DD format)
            - team: Extracted team name (if found, None otherwise)
            - article_content: Full article text content (up to 2000 chars)
        
        Returns empty DataFrame if scraping fails.
        
    Note:
        - Uses multiple CSS selectors as fallbacks since ESPN's structure may change
        - Scrapes full article content for better AI analysis
        - Handles network errors gracefully
    """
    url = "https://www.espn.com/nba/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    headlines_data = []
    
    try:
        logger.info(f"Scraping ESPN NBA headlines from {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Find headline elements - ESPN uses various selectors
        # Try multiple selectors to find headlines (ESPN structure may vary)
        headline_selectors = [
            'a[data-clamp="2"]',      # Common ESPN headline selector with data attribute
            '.headlineStack__list a', # Headline stack list items
            'a[data-module="Article"]', # Article module links
            'h2 a',                    # Headings level 2 with links
            'h3 a',                    # Headings level 3 with links
            '.contentItem__title a'    # Content item titles
        ]
        
        headlines_found = []
        # Try each selector until we find headlines
        for selector in headline_selectors:
            elements = soup.select(selector)
            if elements:
                headlines_found = elements
                break
        
        # Fallback: If no headlines found with selectors, try finding by text content
        if not headlines_found:
            all_links = soup.find_all('a', href=True)
            headlines_found = [link for link in all_links 
                             if '/nba/' in link.get('href', '') 
                             and link.get_text(strip=True)]
        
        count = 0
        for element in headlines_found:
            if count >= limit:
                break
                
            try:
                headline_text = element.get_text(strip=True)
                link = element.get('href', '')
                
                # Make link absolute if relative
                if link.startswith('/'):
                    link = f"https://www.espn.com{link}"
                elif not link.startswith('http'):
                    link = f"https://www.espn.com/{link}"
                
                # Try to find description - look for sibling or parent elements
                description = ""
                parent = element.parent
                if parent:
                    # Look for description in nearby elements with description/summary/excerpt classes
                    desc_elements = parent.find_all(['p', 'span', 'div'], class_=re.compile(r'description|summary|excerpt', re.I))
                    if desc_elements:
                        description = desc_elements[0].get_text(strip=True)
                    else:
                        # Try next sibling element
                        next_sibling = element.find_next_sibling(['p', 'span', 'div'])
                        if next_sibling:
                            description = next_sibling.get_text(strip=True)
                
                # Extract team name if possible (for matching with games)
                team = extract_team_name(headline_text + " " + description)
                
                # Only add if we have a headline
                if headline_text:
                    # Scrape full article content for better AI analysis
                    article_content = scrape_article_content(link, headers)
                    
                    headlines_data.append({
                        'headline': headline_text,
                        'description': description if description else "No description available",
                        'link': link,
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'team': team,
                        'article_content': article_content
                    })
                    count += 1
                    
            except Exception as e:
                logger.warning(f"Error processing headline element: {e}")
                continue
        
        if not headlines_data:
            logger.warning("No headlines found. ESPN page structure may have changed.")
            return pd.DataFrame(columns=['headline', 'description', 'link', 'date', 'team', 'article_content'])
        
        df = pd.DataFrame(headlines_data)
        logger.info(f"Successfully scraped {len(df)} headlines")
        return df
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while scraping ESPN: {e}")
        return pd.DataFrame(columns=['headline', 'description', 'link', 'date', 'team', 'article_content'])
    except Exception as e:
        logger.error(f"Unexpected error while scraping ESPN: {e}")
        return pd.DataFrame(columns=['headline', 'description', 'link', 'date', 'team', 'article_content'])


def get_todays_scoreboard():
    """
    Fetch today's NBA game scoreboard using nba_api library.
    
    Uses the ScoreBoard endpoint from nba_api to get all games scheduled
    for today, including scores (if games are in progress or finished) and
    game status.
    
    Returns:
        pd.DataFrame: DataFrame with columns:
            - home_team: Home team name
            - away_team: Away team name
            - home_score: Home team score (0 if game hasn't started)
            - away_score: Away team score (0 if game hasn't started)
            - status: Game status (e.g., "Final", "7:00 pm ET", "Scheduled")
            - game_id: Unique game identifier
            - game_date: Date of the game (YYYY-MM-DD format)
        
        Returns empty DataFrame if no games scheduled or API fails.
        
    Note:
        - ScoreBoard() automatically gets today's games (no date parameter needed)
        - Handles cases where games haven't started (scores will be 0)
        - Gracefully handles API failures
    """
    try:
        logger.info("Fetching today's NBA scoreboard")
        today = datetime.now()
        
        # Get scoreboard for today (ScoreBoard automatically gets today's games)
        scoreboard = ScoreBoard()
        
        # Extract game data from games list (returns list of dictionaries)
        games_list = scoreboard.games.get_dict()
        
        if not games_list:
            logger.info("No games scheduled for today")
            return pd.DataFrame(columns=['home_team', 'away_team', 'home_score', 
                                        'away_score', 'status', 'game_id', 'game_date'])
        
        games_data = []
        
        # Process each game in the scoreboard
        for game in games_list:
            try:
                game_id = game.get('gameId', '')
                
                # Get team names and scores from game data
                home_team_data = game.get('homeTeam', {})
                away_team_data = game.get('awayTeam', {})
                
                home_team_name = home_team_data.get('teamName', 'Unknown')
                away_team_name = away_team_data.get('teamName', 'Unknown')
                
                # Get scores (may be None if game hasn't started)
                home_score = home_team_data.get('score', 0)
                away_score = away_team_data.get('score', 0)
                
                # Convert to integers, defaulting to 0 if None
                home_score_val = int(home_score) if home_score is not None else 0
                away_score_val = int(away_score) if away_score is not None else 0
                
                # Get game status (e.g., "Final", "7:00 pm ET", "Scheduled")
                status = game.get('gameStatusText', 'Scheduled')
                
                games_data.append({
                    'home_team': home_team_name,
                    'away_team': away_team_name,
                    'home_score': home_score_val,
                    'away_score': away_score_val,
                    'status': status,
                    'game_id': game_id,
                    'game_date': today.strftime('%Y-%m-%d')
                })
                
            except Exception as e:
                logger.warning(f"Error processing game {game.get('gameId', 'unknown')}: {e}")
                continue
        
        if not games_data:
            logger.info("No valid games found in scoreboard")
            return pd.DataFrame(columns=['home_team', 'away_team', 'home_score', 
                                        'away_score', 'status', 'game_id', 'game_date'])
        
        df = pd.DataFrame(games_data)
        logger.info(f"Successfully fetched {len(df)} games")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching NBA scoreboard: {e}")
        return pd.DataFrame(columns=['home_team', 'away_team', 'home_score', 
                                    'away_score', 'status', 'game_id', 'game_date'])
