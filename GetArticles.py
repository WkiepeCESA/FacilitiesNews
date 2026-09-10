import datetime
import random
import time
import urllib.parse
from pathlib import Path
import feedparser
import pandas as pd

# Directory setup
SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_CSV = SCRIPT_DIR / "private_schools_list.csv"
OUTPUT_CSV = SCRIPT_DIR / "renovation_matches.csv"

LOOKBACK_HOURS = 24*7
KEYWORDS = '(renovation OR construction OR expansion OR groundbreaking OR "building project")'

# Override default feedparser header to mimic a standard Chrome browser
feedparser.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def check_school_news(school_name: str) -> list[dict]:
    """Queries Google News RSS for a single school and returns articles from the last N hours."""
    query = f'"{school_name}" AND {KEYWORDS}'
    encoded_query = urllib.parse.quote(query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    feed = feedparser.parse(rss_url)
    matches = []
    now = datetime.datetime.now(datetime.timezone.utc)

    for entry in feed.entries:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            pub_dt = datetime.datetime(
                *entry.published_parsed[:6], tzinfo=datetime.timezone.utc
            )
            hours_old = (now - pub_dt).total_seconds() / 3600

            if hours_old <= LOOKBACK_HOURS:
                matches.append(
                    {
                        "school": school_name,
                        "title": entry.title,
                        "link": entry.link,
                        "published": entry.published,
                    }
                )

    return matches


def main():
    df_schools = pd.read_csv(INPUT_CSV)
    df_schools["School and City"] = df_schools["School Name"] + " " + df_schools["City"]
    if "School and City" not in df_schools.columns:
        print("Error: Column 'School and City' column not found in the CSV.")
        return
    schools = (
        df_schools["School and City"].dropna().astype(str).str.strip().unique().tolist()
    )

    print(f"Scanning {len(schools)} schools individually...")
    results = []

    for idx, school in enumerate(schools, 1):
        if idx <= 10: #limit to 10 schools for testing
            print(f"[{idx}/{len(schools)}] Checking: {school}")
            matches = check_school_news(school)

            if matches:
                results.extend(matches)
                print(f"  --> Found {len(matches)} matching article(s)!")

                # Randomized delay (2.0 to 4.0s) to prevent request pattern detection
            time.sleep(random.uniform(2.0, 4.0))

    if results:
        df_new = pd.DataFrame(results)
        df_new = df_new[["school", "title", "link", "published"]]

        file_exists = OUTPUT_CSV.exists()
        df_new.to_csv(
            OUTPUT_CSV, mode="a", index=False, header=not file_exists
        )
        print(
            f"\nFinished! Appended {len(df_new)} article(s) to:\n{OUTPUT_CSV}"
        )
    else:
        now = datetime.datetime.now(datetime.timezone.utc)
        formatted_date = now.strftime("%m/%d/%Y")
        data = {
            "school": ["No schools found"],
            "title": ["No articles found"],
            "link": ["N/A"],
            "published": [formatted_date],
        }
        df_new = pd.DataFrame(data)
        file_exists = OUTPUT_CSV.exists()
        df_new.to_csv(
            OUTPUT_CSV, mode="a", index=False, header=not file_exists
        )
        print("\nFinished! No renovation articles found today.")



if __name__ == "__main__":
    main()
