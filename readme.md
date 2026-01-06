# 🤖 LinkedIn AI Auto Poster

Automatically generates and posts trending Android content to your LinkedIn profile.

## 🔄 How It Works

```
┌─────────────────────────┐
│  1. DuckDuckGo Search   │  → Find 5 trending Android topics
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│  2. Groq AI (LLaMA 70B) │  → Pick best topic + Generate post
└───────────┬─────────────┘
            ↓
┌─────────────────────────┐
│  3. LinkedIn API        │  → Post to your profile
└─────────────────────────┘
```

## 📋 Prerequisites

1. **LinkedIn tokens** - Run `linkedin_post.py` first to authenticate
2. **Groq API key** - Free at https://console.groq.com
3. **Python 3.8+**

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Test without posting (dry run)
python linkedin_ai_poster.py --dry-run

# Actually post to LinkedIn
python linkedin_ai_poster.py
```

## ⚙️ Configuration

Edit the script to customize:

```python
# Search queries for trending topics
SEARCH_QUERIES = [
    "Android development trends 2025",
    "Kotlin new features latest",
    "Jetpack Compose updates",
]

# AI Model
GROQ_MODEL = "llama-3.3-70b-versatile"
```

## 📅 Weekly Automation (GitHub Actions)

Create `.github/workflows/weekly-post.yml`:

```yaml
name: Weekly LinkedIn Post

on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday 9 AM UTC
  workflow_dispatch:  # Manual trigger

jobs:
  post:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run poster
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          LINKEDIN_ACCESS_TOKEN: ${{ secrets.LINKEDIN_ACCESS_TOKEN }}
          LINKEDIN_PERSON_URN: ${{ secrets.LINKEDIN_PERSON_URN }}
        run: python linkedin_ai_poster.py
```

## 🧪 Dry Run Mode

Test without posting:

```bash
python linkedin_ai_poster.py --dry-run
# or
python linkedin_ai_poster.py -d
```

This will:
- Search trending topics ✅
- Pick best topic with AI ✅
- Generate post content ✅
- Show preview ✅
- NOT post to LinkedIn ❌

## 📁 Files

```
linkedin_ai_poster/
├── linkedin_ai_poster.py   # Main script
├── linkedin_tokens.json    # LinkedIn auth tokens
├── post_history.json       # History of posted content
├── requirements.txt        # Dependencies
└── README.md              # This file
```

## 🎯 Customizing the Prompt

The `SYSTEM_PROMPT` in the script defines your LinkedIn persona. Customize it for your niche:

- Change expertise areas
- Update your background
- Modify tone and style
- Add/remove hashtags

## ⚠️ Notes

- LinkedIn tokens expire in ~60 days
- Don't post too frequently (1-2x per week is ideal)
- Review AI content before posting in production
- Groq free tier has rate limits

## 🐛 Troubleshooting

**"No LinkedIn tokens found"**
→ Run `linkedin_post.py` first to authenticate

**"Groq API error"**
→ Check your API key is valid

**"Search error"**
→ DuckDuckGo might be rate-limited, try again later

---

Made with ❤️ for building LinkedIn presence on autopilot!