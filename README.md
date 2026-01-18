# NBA Intelligence Dispatcher

A Python-based system that scrapes ESPN NBA headlines, analyzes sentiment using **Gemma 3 model** (with better rate limits), and generates executive pregame briefings delivered via email.

## Features

- **Web Scraping**: Scrapes top 5 NBA headlines and full article content from ESPN
- **Scoreboard Integration**: Fetches today's NBA games using nba_api
- **AI-Powered Analysis**: Uses **Gemma 3 model** for sentiment analysis (-1.0 to 1.0) and 5-sentence summaries (14.4K RPD vs 20 RPD)
- **Executive Briefings**: Generates 3-paragraph briefings focusing on injuries and high-stakes storylines
- **Professional Email**: Sends dark-themed HTML emails with color-coded sentiment indicators

## Setup

### Prerequisites

- Python 3.8 or higher
- Internet connection
- Gmail account with 2-Factor Authentication (2FA) enabled
- Google Gemini API key (free tier available)

### 1. Install Dependencies

First, make sure you have Python installed. Then install all required packages:

```bash
pip install -r requirements.txt
```

This will install:
- `google-generativeai` - For Gemini 2.5 Flash AI integration
- `pandas` - For data manipulation
- `requests` - For HTTP requests
- `beautifulsoup4` - For HTML parsing
- `lxml` - HTML parser for BeautifulSoup
- `nba_api` - For NBA scoreboard data
- `python-dotenv` - For environment variable management

### 2. Get Your API Keys

#### Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy your API key (you'll need this for the .env file)

**Note**: 
- **Gemma 3 models**: 30 requests per minute (RPM) and 14,400 requests per day (RPD) - **RECOMMENDED**
- Gemini 2.5 Flash: 5 requests per minute (RPM) and 20 requests per day (RPD) - limited

#### Gmail App Password

1. Enable 2-Factor Authentication (2FA) on your Gmail account:
   - Go to [Google Account Settings](https://myaccount.google.com/)
   - Navigate to Security → 2-Step Verification
   - Follow the prompts to enable 2FA

2. Generate an App Password:
   - Go to Google Account Settings → Security
   - Under "2-Step Verification", click "App passwords"
   - Select "Mail" as the app and "Other" as the device
   - Name it "NBA Dispatcher" (or any name you prefer)
   - Copy the 16-character password (you'll need this for the .env file)

**Important**: Use the App Password, NOT your regular Gmail password.

### 3. Configure Environment Variables

Create a `.env` file in the project root directory with the following content:

```env
# Google Gemini API Configuration
# Get your API key from: https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Gmail Configuration (requires 2FA and App Password)
# Use your Gmail address (the one with 2FA enabled)
GMAIL_EMAIL=your_email@gmail.com
# Use the 16-character App Password (NOT your regular password)
GMAIL_APP_PASSWORD=your_16_character_app_password_here

# Email Recipient
# Where to send the executive briefing
EMAIL_RECIPIENT=recipient@example.com
```

**Important Notes**:
- Replace all placeholder values with your actual credentials
- The `.env` file should be in the same directory as `main.py`
- Never commit the `.env` file to version control (it's already in `.gitignore`)

## Usage

### Running the Script

Simply run the main script:

```bash
python main.py
```

### What Happens

The script will:

1. **Scrape ESPN Headlines** (~10-15 seconds)
   - Scrapes 5 top NBA headlines from ESPN
   - Visits each article URL to get full article content
   - Extracts team names when possible

2. **Fetch Today's Scoreboard** (~2-3 seconds)
   - Gets all NBA games scheduled for today
   - Includes scores if games are in progress or finished

3. **Analyze Sentiment & Generate Summaries** (~30-60 seconds)
   - Uses Gemini 2.5 Flash to analyze each headline
   - Generates sentiment scores (-1.0 to 1.0)
   - Creates 5-sentence summaries for each article
   - All 5 requests can be made immediately (within 5 RPM limit)

4. **Generate Executive Briefing** (~10-15 seconds)
   - Uses Gemini 2.5 Flash to create a 3-paragraph briefing
   - Focuses on injuries and high-stakes storylines
   - Highlights most important games to watch

5. **Send Email** (~5 seconds)
   - Sends professional HTML email with all results
   - Includes dark-themed template with color-coded sentiment

**Total Runtime**: Approximately 1-2 minutes

### Testing Components

You can test individual components without running the full workflow:

```bash
python test_components.py
```

This will test:
- Environment variable configuration
- Gemini 2.5 Flash initialization
- ESPN headline scraping
- NBA scoreboard fetching

## Project Structure

```
.
├── main.py              # Main orchestrator - entry point
├── scraper.py           # ESPN scraping and NBA API integration
├── engine.py            # Gemini 2.5 Flash integration and analysis
├── notifier.py          # Email sending functionality
├── test_components.py  # Component testing script
├── requirements.txt    # Python dependencies
├── .env                 # Environment variables (create this)
├── .gitignore          # Git ignore file
└── README.md           # This file
```

## Error Handling

The system is designed to be robust:

- **ESPN Down**: Continues with empty headlines DataFrame
- **No Games Today**: Continues with empty scoreboard DataFrame
- **API Failures**: Provides fallback briefings and neutral sentiment scores
- **Email Failures**: Logs error but doesn't crash
- **Missing Headlines**: Gracefully handles empty data
- **Environment Validation**: Checks all required variables before execution

## Email Template

The email includes:

- **Executive Briefing**: 3-paragraph analysis focusing on injuries and storylines
- **News Headlines Table**: 
  - Headline text
  - 5-sentence AI-generated summary
  - Color-coded sentiment (Green = positive, Red = negative)
- **Today's Games**: Matchups, scores, and status
- **Dark Theme**: Professional styling optimized for readability

## Rate Limits

**Gemma 3 Models (Primary - Recommended)**:
- 30 requests per minute (RPM)
- 14,400 requests per day (RPD) - **Much better than Gemini's 20 RPD!**

**Gemini 2.5 Flash (Fallback)**:
- 5 requests per minute (RPM)
- 20 requests per day (RPD) - Very limited

The script is configured to:
- Use Gemma 3-12B as primary model (14.4K RPD limit)
- Scrape 5 headlines
- Make 5 sentiment/summary requests (can be done immediately)
- Make 1 briefing request
- **Total**: 6 API calls per run (well within Gemma's 14.4K daily limit)

## Requirements

- **Python**: 3.8 or higher
- **Internet Connection**: Required for scraping and API calls
- **Valid Gemini API Key**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
- **Gmail Account**: With 2FA enabled
- **Gmail App Password**: 16-character password (not regular password)

## Troubleshooting

### Import Errors

```bash
# Make sure all dependencies are installed
pip install -r requirements.txt
```

### API Errors

- **"API key invalid"**: Check your `GEMINI_API_KEY` in `.env`
- **"Quota exceeded"**: 
  - If using Gemma 3: You've hit the daily limit (14,400 requests) - very unlikely
  - If using Gemini: You've hit the daily limit (20 requests). The script will try Gemma models as fallback.
- **"Model not found"**: Gemma 3 may be temporarily unavailable. The script will try fallback models (other Gemma variants or Gemini models).

### Email Errors

- **"Authentication failed"**: 
  - Verify 2FA is enabled on your Gmail account
  - Make sure you're using the App Password (16 characters), not your regular password
  - Check that the App Password is correct in `.env`

- **"SMTP error"**: 
  - Check your internet connection
  - Verify Gmail SMTP settings (should be smtp.gmail.com:587)

### Scraping Errors

- **"No headlines found"**: ESPN's page structure may have changed. The scraper includes multiple fallback selectors.
- **"Network error"**: Check your internet connection or ESPN may be down.

### Environment Variable Errors

- **"Missing required environment variables"**: Check your `.env` file exists and all variables are set
- **"Placeholder detected"**: Make sure you've replaced placeholder values with actual credentials

## License

This project is for personal/educational use.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify all environment variables are set correctly
3. Run `python test_components.py` to test individual components
4. Check the logs for detailed error messages
