# NBA Intelligence Dispatcher

A Python-based system that scrapes ESPN NBA headlines, analyzes sentiment using Gemini 1.5 Flash, and generates executive pregame briefings delivered via email.

## Features

- **Web Scraping**: Scrapes top 10 NBA headlines and descriptions from ESPN
- **Scoreboard Integration**: Fetches today's NBA games using nba_api
- **AI-Powered Analysis**: Uses Gemini 1.5 Flash for sentiment analysis (-1.0 to 1.0)
- **Executive Briefings**: Generates 3-paragraph briefings focusing on injuries and high-stakes storylines
- **Professional Email**: Sends dark-themed HTML emails with color-coded sentiment indicators

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Google Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Gmail Configuration (requires 2FA and App Password)
GMAIL_EMAIL=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password_here

# Email Recipient
EMAIL_RECIPIENT=recipient@example.com
```

### 3. Get Your API Keys

- **Gemini API Key**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
- **Gmail App Password**: 
  1. Enable 2-Factor Authentication on your Gmail account
  2. Go to Google Account Settings → Security → App Passwords
  3. Generate an app password for "Mail"
  4. Use this 16-character password (not your regular Gmail password)

## Usage

Run the main script:

```bash
python main.py
```

The script will:
1. Scrape ESPN headlines
2. Fetch today's NBA scoreboard
3. Analyze sentiment for each headline
4. Generate an executive briefing
5. Send an HTML email with all results

## Project Structure

```
.
├── main.py              # Main orchestrator
├── scraper.py           # ESPN scraping and NBA API integration
├── engine.py            # Gemini AI integration and analysis
├── notifier.py          # Email sending functionality
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (create this)
└── README.md           # This file
```

## Error Handling

The system is designed to be robust:
- Continues processing if ESPN is down
- Handles missing headlines gracefully
- Works even if no games are scheduled
- Provides fallback briefings if AI generation fails
- Validates all environment variables before execution

## Email Template

The email includes:
- **Executive Briefing**: 3-paragraph analysis focusing on injuries and storylines
- **News Headlines Table**: Color-coded sentiment (Green = positive, Red = negative)
- **Today's Games**: Matchups, scores, and status
- **Dark Theme**: Professional styling optimized for readability

## Requirements

- Python 3.8+
- Internet connection
- Valid Gemini API key
- Gmail account with 2FA enabled
- App Password for Gmail

## Troubleshooting

- **Import errors**: Make sure all dependencies are installed via `pip install -r requirements.txt`
- **API errors**: Verify your Gemini API key is correct and has quota remaining
- **Email errors**: Ensure 2FA is enabled and you're using an App Password (not your regular password)
- **Scraping errors**: ESPN's structure may change; the scraper includes fallback selectors

## License

This project is for personal/educational use.
