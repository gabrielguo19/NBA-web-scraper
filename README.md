# NBA Intelligence Dispatcher

A Python-based system that scrapes ESPN NBA headlines, analyzes sentiment using **Gemini text-out models** via Google GenAI SDK (automatically selects best available), and generates executive pregame briefings delivered via email.

**Note**: Uses the new `google-genai` package (not the deprecated `google-generativeai`). Only uses Gemini text-out models.

## Features

- **Web Scraping**: Scrapes top 5 NBA headlines and full article content from ESPN
- **Scoreboard Integration**: Fetches today's NBA games using nba_api
- **AI-Powered Analysis**: Uses **Gemini text-out models** (currently gemini-2.5-flash-lite) for sentiment analysis (-1.0 to 1.0) and 5-sentence summaries
- **Executive Briefings**: Generates 3-paragraph briefings focusing on injuries and high-stakes storylines
- **Professional Email**: Sends dark-themed HTML emails with color-coded sentiment indicators

## 🚀 Quick Setup Guide

**Follow these steps to get started in 5 minutes:**

1. **Install Python dependencies** → See Step 1 below
2. **Get your Gemini API key** → Go to [Google AI Studio](https://aistudio.google.com/app/apikey) (Step 2)
3. **Set up Gmail App Password** → See Step 3 below
4. **Create `.env` file** → See Step 4 below
5. **Run the script** → `python main.py`

---

## Setup

### Prerequisites

- Python 3.8 or higher
- Internet connection
- Gmail account with 2-Factor Authentication (2FA) enabled
- Google Gemini API key (free tier available)

### Step 1: Install Dependencies

First, make sure you have Python installed. Then install all required packages:

```bash
pip install -r requirements.txt
```

This will install:
- `google-genai` - For Google GenAI SDK (new SDK, replaces google-generativeai)
- `pandas` - For data manipulation
- `requests` - For HTTP requests
- `beautifulsoup4` - For HTML parsing
- `lxml` - HTML parser for BeautifulSoup
- `nba_api` - For NBA scoreboard data
- `python-dotenv` - For environment variable management

### Step 2: Get Your Gemini API Key

**📍 Go to Google AI Studio to get your API key:**

1. **Visit [Google AI Studio](https://aistudio.google.com/app/apikey)** (or go to [aistudio.google.com](https://aistudio.google.com) and click "Get API Key")
2. Sign in with your Google account
3. Click **"Create API Key"** or **"Get API Key"**
4. Copy your API key (starts with `AIza...`)
5. **Save it** - you'll need it for the `.env` file in Step 4

**Important Notes:**
- The API key is **free** for the tier we're using
- Keep your API key **secret** - don't share it publicly
- The script automatically selects the best available Gemini text-out model
- **gemini-2.5-flash-lite**: 10 requests per minute (RPM) and 20 requests per day (RPD) - **Currently in use**
- Other Gemini Flash models: 5 RPM and 20 RPD
- Only text-out models are used (required for text generation)

### Step 3: Set Up Gmail App Password

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

### Step 4: Configure Environment Variables

Create a `.env` file in the project root directory with the following content:

```env
# Google Gemini API Configuration
# Get your API key from: https://aistudio.google.com/app/apikey
# Or visit: https://aistudio.google.com and click "Get API Key"
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

**Sample `.env` file** (what it should look like with real values):

```env
# Google Gemini API Configuration
GEMINI_API_KEY=AIzaSyB1234567890abcdefghijklmnopqrstuvwxyz

# Gmail Configuration
GMAIL_EMAIL=john.doe@gmail.com
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop

# Email Recipient
EMAIL_RECIPIENT=john.doe@gmail.com
```

**Important Notes**:
- Replace all placeholder values with your actual credentials
- The `.env` file should be in the same directory as `main.py`
- Never commit the `.env` file to version control (it's already in `.gitignore`)
- Make sure there are **no spaces** around the `=` sign
- Don't use quotes around the values (e.g., use `AIza...` not `"AIza..."`)
- The Gmail App Password may have spaces (like `abcd efgh ijkl mnop`) - that's fine, keep them as-is
- Your `EMAIL_RECIPIENT` can be the same as `GMAIL_EMAIL` if you want to send to yourself

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

**Current Model: gemini-2.5-flash-lite** (automatically selected):
- 10 requests per minute (RPM)
- 20 requests per day (RPD)

**Other Available Gemini Text-Out Models**:
- gemini-3-flash: 5 RPM, 20 RPD
- gemini-2.5-flash: 5 RPM, 20 RPD

The script is configured to:
- Automatically detect and use the best available Gemini text-out model
- Scrape 5 headlines
- Make 5 sentiment/summary requests (can be done immediately with 10 RPM limit)
- Make 1 briefing request
- **Total**: 6 API calls per run (within 20 RPD daily limit)

**Note**: The script will automatically try to use Gemini models with better rate limits if available. Only text-out models are used.

## Requirements

- **Python**: 3.8 or higher
- **Internet Connection**: Required for scraping and API calls
- **Valid Gemini API Key**: Get from [Google AI Studio](https://aistudio.google.com/app/apikey) or visit [aistudio.google.com](https://aistudio.google.com)
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
- **"Quota exceeded"**: You've hit the daily limit (20 requests). Wait 24 hours or the script will automatically try other available models.
- **"Model not found"**: The preferred model may be temporarily unavailable. The script will automatically try fallback models.
- **Import errors with google-genai**: Make sure you've installed the new package: `pip install -U -q "google-genai"`

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


## Sample output

<img width="346" height="737" alt="image" src="https://github.com/user-attachments/assets/16ccbc98-ee1a-4587-b7bc-5ff005ad06e2" />
