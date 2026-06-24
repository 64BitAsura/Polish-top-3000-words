"""
Scrape the top 3000 Polish words from Wiktionary and generate a CSV file.

Data source:
  - Word list: https://en.wiktionary.org/wiki/Wiktionary:Frequency_lists/Polish_wordlist
    (based on OpenSubtitles corpus)
  - Definitions: English Wiktionary API (batch queries, 50 words per request)

Output columns:
  rank, word, part_of_speech, meaning,
  sentence_example_polish, english_translation, source_reference
"""

import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request

WIKTIONARY_API = "https://en.wiktionary.org/w/api.php"
USER_AGENT = "Polish-top-3000-words/1.0 (https://github.com/64BitAsura/Polish-top-3000-words)"
BATCH_SIZE = 50
OUTPUT_FILE = "polish_top_3000_words.csv"
TARGET_COUNT = 3000
# Pause between batches to respect Wiktionary rate limits (max 200 req/s for bots,
# but we stay polite with a small delay).
BATCH_DELAY = 0.5  # seconds


def api_get(params: dict) -> dict:
    """Make a GET request to the Wiktionary API and return parsed JSON."""
    params["format"] = "json"
    url = WIKTIONARY_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_frequency_list() -> list[str]:
    """Return the top TARGET_COUNT Polish words from the Wiktionary frequency list."""
    print("Fetching Polish frequency list from Wiktionary…", flush=True)
    data = api_get(
        {
            "action": "parse",
            "page": "Wiktionary:Frequency_lists/Polish_wordlist",
            "prop": "wikitext",
        }
    )
    wikitext = data["parse"]["wikitext"]["*"]

    # Each entry looks like:
    #   # <span lang="pl">[[word#Polish|word]]</span> 123456
    # We capture the link target (before #Polish).
    pattern = re.compile(r"#\s*<span[^>]*>\[\[([^#\]|]+)#Polish\|")
    words: list[str] = []
    for m in pattern.finditer(wikitext):
        word = m.group(1).strip()
        if word and word not in words:
            words.append(word)
        if len(words) >= TARGET_COUNT:
            break

    print(f"  Found {len(words)} words.", flush=True)
    return words


def clean_wikitext(text: str) -> str:
    """Strip wikitext markup from a definition string."""
    # Remove template calls: {{...}}
    # Handle nested braces iteratively
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    # Resolve piped links: [[target|display]] → display; [[target]] → target
    text = re.sub(r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]", r"\1", text)
    # Remove bold/italic markup
    text = re.sub(r"'{2,3}", "", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


# Part-of-speech headers recognised in Wiktionary wikitext
_POS_LABELS = (
    "Noun",
    "Verb",
    "Adjective",
    "Adverb",
    "Pronoun",
    "Preposition",
    "Conjunction",
    "Interjection",
    "Particle",
    "Numeral",
    "Determiner",
    "Article",
    "Phrase",
    "Suffix",
    "Prefix",
)
_POS_PATTERN = re.compile(
    r"={2,4}\s*(" + "|".join(_POS_LABELS) + r")\s*={2,4}"
)


def parse_polish_entry(wikitext: str) -> tuple[str, str]:
    """
    Extract the first part of speech and first English definition from
    the ==Polish== section of a Wiktionary wikitext page.

    Returns (part_of_speech, meaning).  Either may be an empty string if
    no Polish section or definition was found.
    """
    # Isolate the ==Polish== language section
    # A new top-level section (== ... ==) marks the end.
    m = re.search(r"==Polish==\s*\n(.+?)(?:\n==[A-Z][^=\n]|\Z)", wikitext, re.DOTALL)
    if not m:
        return "", ""

    section = m.group(1)

    # First POS heading inside this section
    pos_match = _POS_PATTERN.search(section)
    pos = pos_match.group(1).lower() if pos_match else ""

    # First definition line (starts with "# " but not "#:" which is an example)
    def_match = re.search(r"^#(?!:)\s*(.+)", section, re.MULTILINE)
    meaning = clean_wikitext(def_match.group(1)) if def_match else ""

    return pos, meaning


def fetch_word_batch(words: list[str]) -> dict[str, tuple[str, str]]:
    """
    Fetch Wiktionary wikitext for a batch of words and return a dict
    mapping each word → (part_of_speech, meaning).
    """
    titles = "|".join(urllib.parse.quote(w) for w in words)
    data = api_get(
        {
            "action": "query",
            "titles": titles,
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
        }
    )

    results: dict[str, tuple[str, str]] = {}
    for page in data["query"]["pages"].values():
        title = page.get("title", "")
        if "revisions" not in page:
            results[title] = ("", "")
            continue
        rev = page["revisions"][0]
        # Content may be in slots/main/* (newer API) or directly in rev['*']
        content = (
            rev.get("slots", {}).get("main", {}).get("*")
            or rev.get("*", "")
        )
        results[title] = parse_polish_entry(content)

    return results


def main() -> None:
    words = fetch_frequency_list()

    rows: list[dict] = []
    total_batches = (len(words) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_num, start in enumerate(range(0, len(words), BATCH_SIZE), 1):
        batch = words[start : start + BATCH_SIZE]
        print(
            f"  Batch {batch_num}/{total_batches}: words {start + 1}–{start + len(batch)}…",
            end=" ",
            flush=True,
        )
        try:
            info = fetch_word_batch(batch)
        except Exception as exc:
            print(f"ERROR ({exc}); using empty values.")
            info = {w: ("", "") for w in batch}
        else:
            print("OK", flush=True)

        for rank, word in enumerate(batch, start=start + 1):
            pos, meaning = info.get(word, ("", ""))
            rows.append(
                {
                    "rank": rank,
                    "word": word,
                    "part_of_speech": pos,
                    "meaning": meaning,
                    "sentence_example_polish": "",
                    "english_translation": "",
                    "source_reference": "https://en.wiktionary.org/wiki/"
                    + urllib.parse.quote(word),
                }
            )

        if batch_num < total_batches:
            time.sleep(BATCH_DELAY)

    fieldnames = [
        "rank",
        "word",
        "part_of_speech",
        "meaning",
        "sentence_example_polish",
        "english_translation",
        "source_reference",
    ]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone! Wrote {len(rows)} rows to {OUTPUT_FILE}.")


if __name__ == "__main__":
    main()
