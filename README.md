# Polish top 3000 words

A dataset of the 3 000 most frequently used Polish words, with part of speech and English meanings sourced from Wiktionary.

## Dataset

**File:** `polish_top_3000_words.csv`

**Source:** Frequency rankings are taken from the [Wiktionary Polish frequency list](https://en.wiktionary.org/wiki/Wiktionary:Frequency_lists/Polish_wordlist), which is derived from the [OpenSubtitles](https://www.opensubtitles.org/) corpus. Part of speech and meaning data are fetched from the [English Wiktionary API](https://en.wiktionary.org/w/api.php).

### Columns

| Column | Description |
|---|---|
| `rank` | Frequency rank (1 = most common) |
| `word` | Polish word in lowercase |
| `part_of_speech` | Grammatical category (noun, verb, adjective, adverb, etc.) |
| `meaning` | First English definition from Wiktionary |
| `sentence_example_polish` | *(empty — fill in a Polish example sentence)* |
| `english_translation` | *(empty — fill in the English translation of the example)* |
| `source_reference` | URL of the word's Wiktionary page |

### Notes

* Some high-frequency words (e.g. inflected forms, particles) may lack a dedicated Wiktionary entry; those rows have empty `part_of_speech` and `meaning` fields.
* The list is based on movie subtitles and skews towards conversational/informal language.

## Generating / updating the dataset

Requires Python 3.9+ and no third-party libraries:

```bash
python3 scrape_polish_words.py
```

The script fetches the frequency list and then queries the Wiktionary API in batches of 50 words, writing results to `polish_top_3000_words.csv`.

## License

See [LICENSE](LICENSE).