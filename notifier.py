"""
NBA Intelligence Dispatcher - Email Notifier Module

This module handles sending HTML emails with the executive briefing,
news headlines with summaries, and game scoreboard using smtplib and email.mime.

Functions:
    - create_html_email(): Creates dark-themed HTML email template
    - send_email(): Sends email via Gmail SMTP using App Password authentication
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
import logging
import re

# Configure logging for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def markdown_to_html(text):
    """
    Convert basic markdown formatting to HTML.
    
    Currently supports:
    - **text** -> <strong>text</strong> (bold)
    
    Args:
        text (str): Text with markdown formatting
        
    Returns:
        str: Text with HTML formatting
    """
    # Convert markdown bold (**text**) to HTML bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    return text


def create_html_email(briefing, news_df, scoreboard_df):
    """
    Create a professional dark-themed HTML email template.
    
    This function formats the executive briefing, news headlines with summaries,
    and game scoreboard into a beautiful dark-themed HTML email. The template
    includes color-coded sentiment indicators (green for positive, red for negative).
    
    Args:
        briefing (str): Executive briefing text (3 paragraphs)
        news_df (pd.DataFrame): DataFrame with headlines, summaries, and sentiment scores
        scoreboard_df (pd.DataFrame): DataFrame with game matchups, scores, and status
        
    Returns:
        str: Complete HTML email content with inline CSS styling
        
    Note:
        - Dark theme: background #1a1a1a, text #e0e0e0
        - Sentiment colors: Green (#4CAF50) for positive, Red (#F44336) for negative
        - Responsive design with max-width 800px
        - Includes both HTML and plain text versions
    """
    # Format briefing paragraphs with proper HTML paragraph tags
    # Convert markdown formatting (like **bold**) to HTML
    briefing_paragraphs = briefing.split('\n\n')
    briefing_html = ""
    for para in briefing_paragraphs:
        if para.strip():
            # Convert markdown to HTML (e.g., **text** -> <strong>text</strong>)
            para_html = markdown_to_html(para.strip())
            # Escape HTML special characters, but preserve our <strong> tags
            # First, temporarily replace our HTML tags with placeholders
            para_html = para_html.replace('<strong>', '___STRONG_OPEN___').replace('</strong>', '___STRONG_CLOSE___')
            # Escape HTML special characters
            para_html = para_html.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            # Restore our <strong> tags
            para_html = para_html.replace('___STRONG_OPEN___', '<strong>').replace('___STRONG_CLOSE___', '</strong>')
            briefing_html += f"<p style='margin: 0 0 15px 0; line-height: 1.6;'>{para_html}</p>\n"
    
    # Create headlines table with color-coded sentiment
    headlines_html = ""
    if not news_df.empty:
        headlines_html = """
        <table style='width: 100%; border-collapse: collapse; margin: 20px 0;'>
            <thead>
                <tr style='background-color: #2a2a2a;'>
                    <th style='padding: 12px; text-align: left; border-bottom: 2px solid #444; color: #e0e0e0;'>Headline</th>
                    <th style='padding: 12px; text-align: left; border-bottom: 2px solid #444; color: #e0e0e0;'>Summary</th>
                    <th style='padding: 12px; text-align: center; border-bottom: 2px solid #444; color: #e0e0e0; width: 100px;'>Sentiment</th>
                </tr>
            </thead>
            <tbody>
"""
        # Add each headline as a table row
        for _, row in news_df.iterrows():
            sentiment = row.get('sentiment', 0.0)
            
            # Color code: Green for positive (>= 0), Red for negative (< 0)
            if sentiment >= 0:
                sentiment_color = '#4CAF50'  # Green
                sentiment_text = f"+{sentiment:.2f}"
            else:
                sentiment_color = '#F44336'  # Red
                sentiment_text = f"{sentiment:.2f}"
            
            # Escape HTML special characters in headline
            headline = str(row.get('headline', 'N/A')).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            # Use AI-generated summary (5 sentences from Gemini 2.5 Flash)
            summary = str(row.get('summary', ''))
            if not summary or summary == "No summary available" or summary == "":
                summary = str(row.get('description', 'No description available'))
            
            # Escape HTML and limit length
            summary = summary[:500].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            if len(summary) > 500:
                summary += "..."
            
            headlines_html += f"""
                <tr style='border-bottom: 1px solid #333;'>
                    <td style='padding: 10px; color: #e0e0e0; font-weight: 500;'>{headline}</td>
                    <td style='padding: 10px; color: #b0b0b0; font-size: 0.9em; line-height: 1.6;'>{summary}</td>
                    <td style='padding: 10px; text-align: center; background-color: {sentiment_color}; color: white; font-weight: bold; border-radius: 4px;'>{sentiment_text}</td>
                </tr>
"""
        headlines_html += """
            </tbody>
        </table>
"""
    else:
        headlines_html = "<p style='color: #b0b0b0; font-style: italic;'>No headlines available.</p>"
    
    # Create games table
    games_html = ""
    if not scoreboard_df.empty:
        games_html = """
        <table style='width: 100%; border-collapse: collapse; margin: 20px 0;'>
            <thead>
                <tr style='background-color: #2a2a2a;'>
                    <th style='padding: 12px; text-align: left; border-bottom: 2px solid #444; color: #e0e0e0;'>Away Team</th>
                    <th style='padding: 12px; text-align: left; border-bottom: 2px solid #444; color: #e0e0e0;'>Home Team</th>
                    <th style='padding: 12px; text-align: center; border-bottom: 2px solid #444; color: #e0e0e0;'>Score</th>
                    <th style='padding: 12px; text-align: center; border-bottom: 2px solid #444; color: #e0e0e0;'>Status</th>
                </tr>
            </thead>
            <tbody>
"""
        # Add each game as a table row
        for _, game in scoreboard_df.iterrows():
            away_team = str(game.get('away_team', 'N/A'))
            home_team = str(game.get('home_team', 'N/A'))
            away_score = game.get('away_score', 0)
            home_score = game.get('home_score', 0)
            status = str(game.get('status', 'Scheduled'))
            
            # Display score if game has started, otherwise show "TBD"
            score_display = f"{away_score} - {home_score}" if (away_score > 0 or home_score > 0) else "TBD"
            
            games_html += f"""
                <tr style='border-bottom: 1px solid #333;'>
                    <td style='padding: 10px; color: #e0e0e0;'>{away_team}</td>
                    <td style='padding: 10px; color: #e0e0e0;'>{home_team}</td>
                    <td style='padding: 10px; text-align: center; color: #e0e0e0; font-weight: bold;'>{score_display}</td>
                    <td style='padding: 10px; text-align: center; color: #b0b0b0;'>{status}</td>
                </tr>
"""
        games_html += """
            </tbody>
        </table>
"""
    else:
        games_html = "<p style='color: #b0b0b0; font-style: italic;'>No games scheduled for today.</p>"
    
    # Complete HTML template with dark theme styling
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NBA Executive Pregame Briefing</title>
</head>
<body style="margin: 0; padding: 0; background-color: #1a1a1a; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
    <div style="max-width: 800px; margin: 0 auto; padding: 20px; background-color: #1a1a1a;">
        <!-- Header with gradient background -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 8px 8px 0 0; margin-bottom: 20px;">
            <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 600;">NBA Intelligence Dispatch</h1>
            <p style="margin: 10px 0 0 0; color: #e0e0e0; font-size: 14px;">Executive Pregame Briefing</p>
        </div>
        
        <!-- Main Content -->
        <div style="background-color: #242424; padding: 30px; border-radius: 0 0 8px 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
            <!-- Executive Briefing Section -->
            <div style="margin-bottom: 30px;">
                <h2 style="color: #e0e0e0; font-size: 22px; margin-bottom: 15px; border-bottom: 2px solid #444; padding-bottom: 10px;">Executive Briefing</h2>
                <div style="color: #e0e0e0; line-height: 1.8;">
                    {briefing_html}
                </div>
            </div>
            
            <!-- News Headlines Section -->
            <div style="margin-bottom: 30px;">
                <h2 style="color: #e0e0e0; font-size: 22px; margin-bottom: 15px; border-bottom: 2px solid #444; padding-bottom: 10px;">Top News Headlines</h2>
                {headlines_html}
            </div>
            
            <!-- Today's Games Section -->
            <div>
                <h2 style="color: #e0e0e0; font-size: 22px; margin-bottom: 15px; border-bottom: 2px solid #444; padding-bottom: 10px;">Today's Games</h2>
                {games_html}
            </div>
        </div>
        
        <!-- Footer -->
        <div style="text-align: center; margin-top: 20px; padding: 20px; color: #b0b0b0; font-size: 12px;">
            <p style="margin: 0;">NBA Intelligence Dispatcher | Generated automatically</p>
            <p style="margin: 5px 0 0 0;">This is an automated briefing. Data sourced from ESPN and NBA API.</p>
        </div>
    </div>
</body>
</html>
"""
    return html_content


def send_email(briefing, news_df, scoreboard_df, sender_email, app_password, recipient_email):
    """
    Send HTML email with executive briefing, news, and scoreboard data.
    
    Uses Gmail SMTP with App Password authentication (requires 2FA enabled).
    Sends both HTML and plain text versions for maximum compatibility.
    
    Args:
        briefing (str): Executive briefing text (3 paragraphs)
        news_df (pd.DataFrame): DataFrame with headlines, summaries, and sentiment scores
        scoreboard_df (pd.DataFrame): DataFrame with game matchups, scores, and status
        sender_email (str): Gmail sender email address
        app_password (str): Gmail App Password (16-character password, not regular password)
        recipient_email (str): Recipient email address
        
    Returns:
        bool: True if email sent successfully, False otherwise
        
    Raises:
        ValueError: If email credentials are missing
        smtplib.SMTPAuthenticationError: If Gmail authentication fails
        smtplib.SMTPException: If SMTP error occurs
        
    Note:
        - Requires Gmail account with 2FA enabled
        - Uses App Password (not regular Gmail password)
        - Sends via smtp.gmail.com on port 587 with TLS
        - Includes both HTML and plain text versions
    """
    try:
        logger.info(f"Preparing email to {recipient_email}")
        
        # Validate inputs
        if not sender_email or not app_password or not recipient_email:
            raise ValueError("Email credentials are missing")
        
        # Create HTML content
        html_content = create_html_email(briefing, news_df, scoreboard_df)
        
        # Create multipart message (supports both HTML and plain text)
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "NBA Executive Pregame Briefing"
        msg['From'] = sender_email
        msg['To'] = recipient_email
        
        # Create plain text version as fallback for email clients that don't support HTML
        text_content = f"""
NBA Executive Pregame Briefing

{briefing}

Top News Headlines:
"""
        if not news_df.empty:
            for _, row in news_df.iterrows():
                text_content += f"\n- {row.get('headline', 'N/A')} (Sentiment: {row.get('sentiment', 0.0):.2f})\n"
        else:
            text_content += "\nNo headlines available.\n"
        
        text_content += "\nToday's Games:\n"
        if not scoreboard_df.empty:
            for _, game in scoreboard_df.iterrows():
                text_content += f"\n{game.get('away_team', 'N/A')} @ {game.get('home_team', 'N/A')} - {game.get('status', 'Scheduled')}\n"
        else:
            text_content += "\nNo games scheduled for today.\n"
        
        # Attach both plain text and HTML versions
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email via Gmail SMTP
        logger.info("Connecting to Gmail SMTP server")
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()  # Enable TLS encryption
            server.login(sender_email, app_password)
            server.send_message(msg)
        
        logger.info(f"Email sent successfully to {recipient_email}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"Gmail authentication failed: {e}")
        logger.error("Please verify your Gmail App Password is correct and 2FA is enabled")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error while sending email: {e}")
        return False
    except ValueError as e:
        logger.error(f"Invalid email configuration: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending email: {e}")
        return False
