"""
Analyze quotes.json and produce a single comprehensive PDF report (report.pdf) covering:
  1. Quote leaderboard (quotes per person)
  2. Word/phrase frequency
  3. "Risky" quote breakdown
  4. Quote length distribution
  5. Per-person signature words
  6. Sequence/clustering of contributors by id order

Usage:
    python analyze_quotes.py [path/to/quotes.json]

Requires matplotlib (pip install matplotlib).
"""

import json
import re
import sys
import statistics
import textwrap
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "is",
    "it", "i", "you", "we", "they", "he", "she", "that", "this", "for",
    "with", "are", "was", "were", "be", "been", "have", "has", "had",
    "do", "does", "did", "not", "no", "so", "if", "my", "your", "their",
    "his", "her", "our", "its", "what", "who", "whats", "thats", "im",
    "its", "at", "as", "by", "up", "out", "just", "like", "get", "got",
    "all", "me", "us", "them", "us", "than", "then", "when", "where",
    "why", "how", "can", "will", "would", "could", "should", "let",
    "lets", "youre", "dont", "didnt", "isnt", "ive", "theyre", "one",
    "ill", "youll", "okay", "yeah", "oh", "well", "really", "very",
}

PAGE_SIZE = (8.5, 11)


def load_quotes(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["quotes"]


def tokenize(text: str):
    return re.findall(r"[a-z']+", text.lower())


def add_title_page(pdf, quotes):
    fig = plt.figure(figsize=PAGE_SIZE)
    fig.text(0.5, 0.65, "Composition Crew Quotes", ha="center", fontsize=28, weight="bold")
    fig.text(0.5, 0.58, "Analysis Report", ha="center", fontsize=18)
    fig.text(
        0.5, 0.45,
        f"{len(quotes)} quotes from {len(set(q['saidBy'] for q in quotes))} contributors",
        ha="center", fontsize=12, color="gray",
    )
    plt.axis("off")
    pdf.savefig(fig)
    plt.close(fig)


def add_text_page(pdf, title, body_lines, font_size=10, font_family="monospace"):
    fig = plt.figure(figsize=PAGE_SIZE)
    fig.text(0.06, 0.95, title, fontsize=16, weight="bold", va="top")
    body = "\n".join(body_lines)
    fig.text(0.06, 0.90, body, fontsize=font_size, va="top", family=font_family)
    plt.axis("off")
    pdf.savefig(fig)
    plt.close(fig)


def add_table_pages(pdf, title, headers, rows, col_widths, rows_per_page=28):
    chunks = [rows[i:i + rows_per_page] for i in range(0, len(rows), rows_per_page)] or [[]]
    for idx, chunk in enumerate(chunks):
        fig = plt.figure(figsize=PAGE_SIZE)
        page_title = title if len(chunks) == 1 else f"{title} (page {idx + 1}/{len(chunks)})"
        fig.text(0.06, 0.96, page_title, fontsize=16, weight="bold", va="top")
        ax = fig.add_axes([0.05, 0.05, 0.9, 0.85])
        ax.axis("off")
        table = ax.table(cellText=chunk, colLabels=headers, loc="upper left", cellLoc="left",
                          colWidths=col_widths)
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.4)
        pdf.savefig(fig)
        plt.close(fig)


def analyze_leaderboard(quotes):
    return Counter(q["saidBy"] for q in quotes)


def chart_leaderboard(pdf, counts):
    ranked = counts.most_common()
    names, values = zip(*ranked)
    fig, ax = plt.subplots(figsize=PAGE_SIZE)
    ax.barh(names[::-1], values[::-1], color="#4C72B0")
    ax.set_title("1. Quote Leaderboard — quotes per person", fontsize=14, weight="bold")
    ax.set_xlabel("number of quotes")
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def analyze_word_frequency(quotes):
    words = Counter()
    for q in quotes:
        for w in tokenize(q["quote"]):
            if w not in STOPWORDS and len(w) > 2:
                words[w] += 1
    return words


def chart_word_frequency(pdf, words):
    top = words.most_common(25)
    labels, values = zip(*top)
    fig, ax = plt.subplots(figsize=PAGE_SIZE)
    ax.barh(labels[::-1], values[::-1], color="#55A868")
    ax.set_title("2. Word Frequency — top 25 (stopwords removed)", fontsize=14, weight="bold")
    ax.set_xlabel("occurrences")
    fig.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)


def add_risky_section(pdf, quotes):
    risky = [q for q in quotes if q.get("risky")]
    by_person = Counter(q["saidBy"] for q in risky)
    lines = [
        f"{len(risky)} of {len(quotes)} quotes are flagged risky: true.",
        "",
        "By person: " + (", ".join(f"{n} ({c})" for n, c in by_person.most_common()) or "n/a"),
        "",
    ]
    headers = ["id", "saidBy", "quote"]
    rows = [[q["id"], q["saidBy"], textwrap.fill(q["quote"], 60)] for q in risky]
    add_text_page(pdf, "3. Risky Quote Breakdown", lines, font_size=11)
    if rows:
        add_table_pages(pdf, "3. Risky Quotes (detail)", headers, rows, col_widths=[0.1, 0.2, 0.7])


def add_length_section(pdf, quotes):
    lengths = [len(q["quote"]) for q in quotes]
    buckets = Counter((l // 10) * 10 for l in lengths)

    fig, axes = plt.subplots(2, 1, figsize=PAGE_SIZE, gridspec_kw={"height_ratios": [1, 1]})
    axes[0].hist(lengths, bins=20, color="#C44E52")
    axes[0].set_title("4. Quote Length Distribution (characters)", fontsize=14, weight="bold")
    axes[0].set_xlabel("characters")
    axes[0].set_ylabel("count")

    by_person_lengths = defaultdict(list)
    for q in quotes:
        by_person_lengths[q["saidBy"]].append(len(q["quote"]))
    top_people = [p for p, _ in Counter(q["saidBy"] for q in quotes).most_common(10)]
    avgs = [statistics.mean(by_person_lengths[p]) for p in top_people]
    axes[1].barh(top_people[::-1], avgs[::-1], color="#8172B2")
    axes[1].set_xlabel("average quote length (characters)")
    axes[1].set_title("Average quote length, top 10 contributors", fontsize=11)

    fig.text(
        0.06, 0.02,
        f"mean={statistics.mean(lengths):.1f}  median={statistics.median(lengths)}  "
        f"min={min(lengths)}  max={max(lengths)}",
        fontsize=9, color="gray",
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    pdf.savefig(fig)
    plt.close(fig)


def add_signature_section(pdf, quotes, global_word_counts):
    by_person_words = defaultdict(Counter)
    for q in quotes:
        for w in tokenize(q["quote"]):
            if w not in STOPWORDS and len(w) > 2:
                by_person_words[q["saidBy"]][w] += 1

    total_words = sum(global_word_counts.values())
    top_people = [p for p, _ in Counter(q["saidBy"] for q in quotes).most_common(8)]

    lines = [
        "Words each top contributor uses disproportionately more than the group",
        "average (relative-frequency score, minimum 2 uses).",
        "",
    ]
    for person in top_people:
        wc = by_person_words[person]
        person_total = sum(wc.values())
        if person_total == 0:
            continue
        scored = []
        for word, count in wc.items():
            if count < 2:
                continue
            person_freq = count / person_total
            global_freq = global_word_counts[word] / total_words
            score = person_freq / global_freq if global_freq else 0
            scored.append((score, word, count))
        scored.sort(reverse=True)
        top_words = ", ".join(f"{w} ({c})" for _, w, c in scored[:6])
        lines.append(f"{person:<14} {top_words or '(not enough repeated words)'}")
    add_text_page(pdf, "5. Per-Person Signature Words", lines, font_size=10)


def add_sequence_section(pdf, quotes):
    runs = []
    current_person, current_len, start_id = None, 0, None
    for q in quotes:
        if q["saidBy"] == current_person:
            current_len += 1
        else:
            if current_person and current_len >= 3:
                runs.append((start_id, current_person, current_len))
            current_person, current_len, start_id = q["saidBy"], 1, q["id"]
    if current_person and current_len >= 3:
        runs.append((start_id, current_person, current_len))
    runs.sort(key=lambda r: -r[2])

    intro = [
        "Quotes are ordered by id, which likely reflects when they were logged.",
        "This groups consecutive runs by the same speaker (3+ in a row) - possible",
        "indicators of a specific hangout/session dominated by one voice.",
        "",
    ]
    add_text_page(pdf, "6. Sequence Clustering by Quote ID", intro, font_size=11)
    if runs:
        headers = ["starting id", "person", "consecutive quotes"]
        rows = [[r[0], r[1], str(r[2])] for r in runs]
        add_table_pages(pdf, "6. Consecutive-Run Detail", headers, rows, col_widths=[0.3, 0.4, 0.3])


def main():
    quotes_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("quotes.json")
    quotes = load_quotes(quotes_path)

    leaderboard_counts = analyze_leaderboard(quotes)
    word_counts = analyze_word_frequency(quotes)

    out_path = Path("report.pdf")
    with PdfPages(out_path) as pdf:
        add_title_page(pdf, quotes)
        chart_leaderboard(pdf, leaderboard_counts)
        chart_word_frequency(pdf, word_counts)
        add_risky_section(pdf, quotes)
        add_length_section(pdf, quotes)
        add_signature_section(pdf, quotes, word_counts)
        add_sequence_section(pdf, quotes)

    print(f"Report written to {out_path}")


if __name__ == "__main__":
    main()
