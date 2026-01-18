"""
NBA Intelligence Dispatcher - Scraper Module

This module handles web scraping of ESPN NBA headlines and fetching
today's NBA game scoreboard using the nba_api library.
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from nba_api.live.nba.endpoints import ScoreBoard
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NBA team name mapping for normalization
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

# Common team name variations for extraction
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
    
    Args:
        article_url (str): URL of the article to scrape
        headers (dict): HTTP headers to use for the request
        
    Returns:
        str: Full article text content, or empty string if scraping fails
    """
    try:
        logger.debug(f"Scraping article content from: {article_url}")
        response = requests.get(article_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Find article content - ESPN uses various selectors
        article_text = ""
        
        # Try common ESPN article content selectors
        content_selectors = [
            '.article-body',
            '[data-module="ArticleBody"]',
            '.StoryBody',
            'article p',
            '.article-content p',
            '.article p'
        ]
        
        for selector in content_selectors:
            content_elements = soup.select(selector)
            if content_elements:
                # Combine all paragraph text
                paragraphs = [elem.get_text(strip=True) for elem in content_elements if elem.get_text(strip=True)]
                article_text = ' '.join(paragraphs)
                if len(article_text) > 100:  # Make sure we got substantial content
                    break
        
        # If no content found, try to get all paragraph text from main content area
        if not article_text or len(article_text) < 100:
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|article|story', re.I))
            if main_content:
                paragraphs = main_content.find_all('p')
                article_text = ' '.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        
        # Clean up the text
        if article_text:
            # Remove extra whitespace
            article_text = ' '.join(article_text.split())
            # Limit to reasonable length (first 2000 chars should be enough for summary)
            if len(article_text) > 2000:
                article_text = article_text[:2000] + "..."
        
        logger.debug(f"Scraped {len(article_text)} characters of article content")
        return article_text
        
    except Exception as e:
        logger.warning(f"Error scraping article content from {article_url}: {e}")
        return ""


def extract_team_name(text):
    """
    Extract NBA team name from headline or description text.
    
    Args:
        text (str): Text to search for team names
        
    Returns:
        str: Team name if found, None otherwise
    """
    if not text:
        return None
    
    text_lower = text.lower()
    for keyword, team_name in TEAM_KEYWORDS.items():
        if keyword in text_lower:
            return team_name
    return None


def scrape_espn_headlines(limit=5):
    """
    Scrape the top NBA headlines and descriptions from ESPN NBA news page.
    
    Args:
        limit (int): Maximum number of headlines to scrape (default: 5)
        
    Returns:
        pd.DataFrame: DataFrame with columns: headline, description, link, date, team
                     Returns empty DataFrame if scraping fails
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
        # Try multiple selectors to find headlines
        headline_selectors = [
            'a[data-clamp="2"]',  # Common ESPN headline selector
            '.headlineStack__list a',
            'a[data-module="Article"]',
            'h2 a',
            'h3 a',
            '.contentItem__title a'
        ]
        
        headlines_found = []
        for selector in headline_selectors:
            elements = soup.select(selector)
            if elements:
                headlines_found = elements
                break
        
        # If no headlines found with selectors, try finding by text content
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
                    # Look for description in nearby elements
                    desc_elements = parent.find_all(['p', 'span', 'div'], class_=re.compile(r'description|summary|excerpt', re.I))
                    if desc_elements:
                        description = desc_elements[0].get_text(strip=True)
                    else:
                        # Try next sibling
                        next_sibling = element.find_next_sibling(['p', 'span', 'div'])
                        if next_sibling:
                            description = next_sibling.get_text(strip=True)
                
                # Extract team name if possible
                team = extract_team_name(headline_text + " " + description)
                
                # Only add if we have a headline
                if headline_text:
                    # Scrape full article content
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
    Fetch today's NBA game scoreboard using nba_api.
    
    Returns:
        pd.DataFrame: DataFrame with columns: home_team, away_team, home_score, 
                     away_score, status, game_id, game_date
                     Returns empty DataFrame if no games or API fails
    """
    try:
        logger.info("Fetching today's NBA scoreboard")
        today = datetime.now()
        
        # Get scoreboard for today (ScoreBoard automatically gets today's games)
        scoreboard = ScoreBoard()
        
        # Extract game data from games list
        games_list = scoreboard.games.get_dict()
        
        if not games_list:
            logger.info("No games scheduled for today")
            return pd.DataFrame(columns=['home_team', 'away_team', 'home_score', 
                                        'away_score', 'status', 'game_id', 'game_date'])
        
        games_data = []
        
        for game in games_list:
            try:
                game_id = game.get('gameId', '')
                
                # Get team names and scores
                home_team_data = game.get('homeTeam', {})
                away_team_data = game.get('awayTeam', {})
                
                home_team_name = home_team_data.get('teamName', 'Unknown')
                away_team_name = away_team_data.get('teamName', 'Unknown')
                
                # Get scores (may be None if game hasn't started)
                home_score = home_team_data.get('score', 0)
                away_score = away_team_data.get('score', 0)
                
                home_score_val = int(home_score) if home_score is not None else 0
                away_score_val = int(away_score) if away_score is not None else 0
                
                # Get game status
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
