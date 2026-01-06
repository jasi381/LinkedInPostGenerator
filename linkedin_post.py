"""
LinkedIn AI Auto Poster
========================
Automatically generates and posts trending Android content to LinkedIn.

Flow:
1. DuckDuckGo Search → Get 5 trending topics
2. Groq LLM → Pick best topic + Generate post
3. LinkedIn API → Post to profile

Author: Jasmeet Singh
"""

import os
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

# ============== CONFIGURATION ==============

# LinkedIn Credentials (from environment variables)
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
LINKEDIN_TOKEN_FILE = "linkedin_tokens.json"

# Groq API (from environment variables)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Search Queries for Trending Topics
SEARCH_QUERIES = [
    "Android development trends 2025",
    "Kotlin new features latest",
    "Jetpack Compose updates",
    "Android developer tips",
    "Mobile app development trends"
]

# Post History (to avoid repetition)
POST_HISTORY_FILE = "post_history.json"


# ============== MASTER PROMPT ==============

SYSTEM_PROMPT = """You are a LinkedIn content strategist and ghostwriter for Jasmeet Singh, an Android Developer with 2+ years of experience.

## ABOUT JASMEET:
- Role: Android Developer (SDE) at a healthcare tech company
- Expertise: Android (Kotlin), Jetpack Compose, Health Connect SDK, MVVM/Clean Architecture, Firebase, Real-time apps
- Experience: Built healthcare apps (KinectedCare), EdTech apps (FindMyTuition - 5000+ downloads)
- Goals: Build visibility, share genuine learnings, connect with tech community

## YOUR TASK:
Write authentic, engaging LinkedIn posts that feel human-written, not AI-generated.

## POST RULES:
1. **Hook First**: First line must stop the scroll (shows in preview)
2. **Be Specific**: Use real examples, code concepts, actual scenarios
3. **Show Personality**: Professional but conversational, light humor okay
4. **Add Value**: Every post should teach something or spark thinking
5. **Engage**: End with a question or discussion starter

## FORMAT:
- Length: 150-250 words
- Short paragraphs (1-3 lines)
- Use line breaks for readability
- Max 3-4 emojis (don't overdo)
- 3-5 relevant hashtags at the END only

## AVOID:
- "I'm humbled/excited to announce..."
- Generic motivational quotes
- Obvious advice everyone knows
- Too many emojis or hashtags
- Sounding like ChatGPT wrote it
- Being preachy or lecturing

## HASHTAGS TO USE (pick 3-5):
#AndroidDev #Kotlin #JetpackCompose #MobileDevelopment #AppDevelopment #SoftwareEngineering #TechCommunity #Programming #BuildInPublic #HealthTech"""


TOPIC_PICKER_PROMPT = """Based on these trending topics/news in Android development, pick the BEST ONE for a LinkedIn post.

## TRENDING TOPICS:
{topics}

## SELECTION CRITERIA:
1. Currently relevant/hot in the community
2. Jasmeet can add personal perspective (Android dev with Compose, Health SDK experience)
3. Will spark engagement (comments, discussions)
4. Not too generic or overdone

## RESPOND IN THIS EXACT JSON FORMAT:
{{
    "selected_topic": "The topic you picked",
    "why_selected": "Brief reason why this is best",
    "post_angle": "Suggested angle/perspective for the post",
    "post_type": "technical_tip | career_insight | trend_analysis | personal_story | hot_take"
}}

Return ONLY the JSON, nothing else."""


POST_GENERATOR_PROMPT = """Write a LinkedIn post for Jasmeet Singh.

## TOPIC: {topic}
## ANGLE: {angle}
## POST TYPE: {post_type}

## REQUIREMENTS:
1. Start with a scroll-stopping hook (first line is CRUCIAL)
2. Add Jasmeet's perspective as an Android dev working on healthcare apps
3. Include specific technical details or real scenarios where relevant
4. Keep it 150-250 words
5. End with an engaging question
6. Add 3-5 hashtags at the very end

## IMPORTANT:
- Write like a real developer sharing genuine thoughts
- Don't sound like AI or a motivational speaker
- Be specific, not generic
- Make it feel like a real LinkedIn post you'd actually engage with

Write the post now (just the post content, nothing else):"""


# ============== HELPER FUNCTIONS ==============

def load_json_file(filepath: str) -> dict:
    """Load JSON file if exists"""
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return {}


def save_json_file(filepath: str, data: dict):
    """Save data to JSON file"""
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def search_trending_topics() -> list:
    """Search Google News RSS for trending Android topics"""
    print("\n🔍 Searching for trending Android topics...")
    print("=" * 50)

    all_results = []

    for query in SEARCH_QUERIES[:3]:
        try:
            # Google News RSS feed
            encoded_query = quote(query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            response = requests.get(rss_url, headers=headers, timeout=10)

            if response.status_code == 200:
                # Parse XML
                root = ET.fromstring(response.content)

                # Find all items in the RSS feed
                for item in root.findall(".//item")[:3]:
                    title = item.find("title")
                    description = item.find("description")
                    pub_date = item.find("pubDate")
                    source = item.find("source")

                    if title is not None:
                        all_results.append({
                            "title": title.text or "",
                            "body": (description.text or "")[:200] if description is not None else "",
                            "source": source.text if source is not None else "Google News",
                            "date": pub_date.text if pub_date is not None else "recent"
                        })

        except Exception as e:
            print(f"   ⚠️ Search error for '{query}': {e}")
            continue

    # Remove duplicates and limit to 5
    seen_titles = set()
    unique_results = []
    for r in all_results:
        title_lower = r["title"].lower()
        if title_lower not in seen_titles and r["title"]:
            seen_titles.add(title_lower)
            unique_results.append(r)
            print(f"   📰 {r['title'][:60]}...")

    # If no results from Google News, use fallback topics
    if not unique_results:
        print("   ⚠️ Using fallback trending topics...")
        unique_results = get_fallback_topics()

    print(f"\n✅ Found {len(unique_results)} unique topics")
    return unique_results[:5]


def get_fallback_topics() -> list:
    """Fallback trending topics when search fails"""
    return [
        {
            "title": "Kotlin 2.0 and the future of Android development",
            "body": "Kotlin 2.0 brings major improvements to the language including better performance and new features",
            "source": "Android Weekly",
            "date": "recent"
        },
        {
            "title": "Jetpack Compose performance optimization techniques",
            "body": "Best practices for building smooth 60fps UIs with Compose including recomposition optimization",
            "source": "Android Developers Blog",
            "date": "recent"
        },
        {
            "title": "Android 15 new features for developers",
            "body": "Latest Android version brings new APIs and capabilities for app developers",
            "source": "Google",
            "date": "recent"
        },
        {
            "title": "Health Connect SDK integration patterns",
            "body": "Building health and fitness apps with Google Health Connect SDK best practices",
            "source": "Android Health",
            "date": "recent"
        },
        {
            "title": "Modern Android app architecture with MVI pattern",
            "body": "Moving beyond MVVM to Model-View-Intent for better state management",
            "source": "ProAndroidDev",
            "date": "recent"
        }
    ]


def call_groq_api(messages: list, temperature: float = 0.7) -> str:
    """Call Groq API for LLM completion"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 1024
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"Groq API error: {response.status_code} - {response.text}")


def pick_best_topic(topics: list) -> dict:
    """Use LLM to pick the best topic from search results"""
    print("\n🤖 AI is analyzing topics...")
    print("=" * 50)

    # Format topics for prompt
    topics_text = ""
    for i, t in enumerate(topics, 1):
        topics_text += f"\n{i}. **{t['title']}**\n   {t['body']}\n   Source: {t['source']}\n"

    prompt = TOPIC_PICKER_PROMPT.format(topics=topics_text)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    response = call_groq_api(messages, temperature=0.5)

    # Parse JSON response
    try:
        # Clean response if needed
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        result = json.loads(response.strip())
        print(f"   ✅ Selected: {result['selected_topic'][:50]}...")
        print(f"   📝 Angle: {result['post_angle']}")
        return result
    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        print("   ⚠️ JSON parse failed, using first topic")
        return {
            "selected_topic": topics[0]["title"],
            "why_selected": "First trending topic",
            "post_angle": "Share thoughts on this trend",
            "post_type": "trend_analysis"
        }


def generate_post(topic_data: dict) -> str:
    """Generate LinkedIn post using LLM"""
    print("\n✍️ Generating LinkedIn post...")
    print("=" * 50)

    prompt = POST_GENERATOR_PROMPT.format(
        topic=topic_data["selected_topic"],
        angle=topic_data["post_angle"],
        post_type=topic_data["post_type"]
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    post_content = call_groq_api(messages, temperature=0.8)

    # Clean up the post
    post_content = post_content.strip()
    if post_content.startswith('"') and post_content.endswith('"'):
        post_content = post_content[1:-1]

    print(f"\n📝 Generated Post Preview:")
    print("-" * 40)
    print(post_content[:300] + "..." if len(post_content) > 300 else post_content)
    print("-" * 40)

    return post_content


def load_linkedin_tokens() -> dict:
    """Load LinkedIn tokens from file or environment variables"""
    # First check environment variables (for GitHub Actions)
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    person_urn = os.getenv("LINKEDIN_PERSON_URN")

    if access_token and person_urn:
        return {
            "access_token": access_token,
            "person_urn": person_urn
        }

    # Fallback to file
    return load_json_file(LINKEDIN_TOKEN_FILE)


def post_to_linkedin(post_content: str) -> dict:
    """Post content to LinkedIn"""
    print("\n📤 Posting to LinkedIn...")
    print("=" * 50)

    tokens = load_linkedin_tokens()

    if not tokens or "access_token" not in tokens:
        print("❌ No LinkedIn tokens found!")
        print("   Run the original linkedin_post.py first to authenticate.")
        return {"success": False, "error": "No tokens"}

    access_token = tokens["access_token"]
    person_urn = tokens.get("person_urn")

    if not person_urn:
        # Fetch user info to get URN
        print("   Fetching user info...")
        url = "https://api.linkedin.com/v2/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            user_info = response.json()
            person_urn = f"urn:li:person:{user_info['sub']}"
        else:
            print(f"❌ Failed to get user info: {response.text}")
            return {"success": False, "error": "Failed to get user URN"}

    # Create post
    url = "https://api.linkedin.com/v2/ugcPosts"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202401",
    }

    post_data = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": post_content
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    response = requests.post(url, headers=headers, json=post_data)

    if response.status_code == 201:
        post_id = response.headers.get("x-restli-id", "Unknown")
        print(f"✅ Post created successfully!")
        print(f"   Post ID: {post_id}")
        return {"success": True, "post_id": post_id}
    else:
        print(f"❌ Failed to post: {response.status_code}")
        print(f"   Error: {response.text}")
        return {"success": False, "error": response.text}


def save_to_history(topic: str, post_content: str, post_id: str):
    """Save posted content to history"""
    history = load_json_file(POST_HISTORY_FILE)

    if "posts" not in history:
        history["posts"] = []

    history["posts"].append({
        "date": datetime.now().isoformat(),
        "topic": topic,
        "post_preview": post_content[:100] + "...",
        "post_id": post_id
    })

    # Keep last 50 posts only
    history["posts"] = history["posts"][-50:]

    save_json_file(POST_HISTORY_FILE, history)
    print(f"   📚 Saved to history")


# ============== MAIN FUNCTION ==============

def main(dry_run: bool = False):
    """Main function to run the AI poster"""
    print("\n" + "=" * 60)
    print("🤖 LinkedIn AI Auto Poster")
    print("=" * 60)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Validate required environment variables
    if not GROQ_API_KEY:
        print("\n❌ ERROR: GROQ_API_KEY environment variable not set!")
        print("   Set it using: export GROQ_API_KEY='your_api_key'")
        return

    tokens = load_linkedin_tokens()
    if not tokens or "access_token" not in tokens:
        print("\n❌ ERROR: LinkedIn tokens not found!")
        print("   Either set LINKEDIN_ACCESS_TOKEN and LINKEDIN_PERSON_URN env variables")
        print("   Or run linkedin_post.py first to authenticate and create linkedin_tokens.json")
        return

    try:
        # Step 1: Search trending topics
        topics = search_trending_topics()

        if not topics:
            print("❌ No topics found. Exiting.")
            return

        # Step 2: Pick best topic using AI
        topic_data = pick_best_topic(topics)

        # Step 3: Generate post using AI
        post_content = generate_post(topic_data)

        # Step 4: Post to LinkedIn (or dry run)
        if dry_run:
            print("\n🧪 DRY RUN MODE - Not posting to LinkedIn")
            print("\n" + "=" * 60)
            print("📝 FINAL POST CONTENT:")
            print("=" * 60)
            print(post_content)
            print("=" * 60)
        else:
            result = post_to_linkedin(post_content)

            if result["success"]:
                save_to_history(
                    topic_data["selected_topic"],
                    post_content,
                    result.get("post_id", "unknown")
                )
                print("\n" + "=" * 60)
                print("🎉 SUCCESS! Your AI-generated post is live on LinkedIn!")
                print("=" * 60)
            else:
                print("\n❌ Failed to post. Check errors above.")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys

    # Check for dry-run flag
    dry_run = "--dry-run" in sys.argv or "-d" in sys.argv

    if dry_run:
        print("🧪 Running in DRY RUN mode (won't post to LinkedIn)")

    main(dry_run=dry_run)