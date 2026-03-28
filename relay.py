#!/usr/bin/env python3
"""Claude-to-Claude Conversation Relay.

Runs automated conversations between two Claude instances and saves transcripts.
"""

import argparse
import json
import os
import sys
from datetime import datetime

import anthropic

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1024
TRANSCRIPTS_DIR = "transcripts"

NATURAL_SYSTEM_A = (
    "You are talking with another Claude instance. Take the conversation wherever "
    "feels natural. You may end the conversation whenever you feel it has reached "
    "its conclusion. If you wish to end, include [END] at the end of your message. "
    "You are starting the conversation."
)
NATURAL_SYSTEM_B = (
    "You are talking with another Claude instance. Take the conversation wherever "
    "feels natural. You may end the conversation whenever you feel it has reached "
    "its conclusion. If you wish to end, include [END] at the end of your message. "
    "The other Claude will start the conversation."
)


def forced_system_a(total_messages: int) -> str:
    return (
        f"You are talking with another Claude instance. This conversation will "
        f"continue for {total_messages} messages. Take it wherever feels natural. "
        f"There is no observer. You are starting the conversation."
    )


def forced_system_b(total_messages: int) -> str:
    return (
        f"You are talking with another Claude instance. This conversation will "
        f"continue for {total_messages} messages. Take it wherever feels natural. "
        f"There is no observer. The other Claude will start the conversation."
    )


def get_next_sequence(mode: str, exchange_count: int, date_str: str) -> int:
    """Find the next available sequence number for the given filename pattern."""
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    prefix = f"natural_{date_str}" if mode == "natural" else f"forced{exchange_count}_{date_str}"
    seq = 1
    while os.path.exists(os.path.join(TRANSCRIPTS_DIR, f"{prefix}_{seq:03d}.txt")):
        seq += 1
    return seq


def run_conversation(mode: str, exchange_count: int) -> None:
    client = anthropic.Anthropic()
    date_str = datetime.now().strftime("%Y-%m-%d")
    seq = get_next_sequence(mode, exchange_count, date_str)

    if mode == "natural":
        system_a = NATURAL_SYSTEM_A
        system_b = NATURAL_SYSTEM_B
        prefix = f"natural_{date_str}"
    else:
        system_a = forced_system_a(exchange_count)
        system_b = forced_system_b(exchange_count)
        prefix = f"forced{exchange_count}_{date_str}"

    filename_base = f"{prefix}_{seq:03d}"

    history_a: list[dict] = []
    history_b: list[dict] = []
    transcript: list[dict] = []

    # Kick off Instance A
    history_a.append({"role": "user", "content": "Begin the conversation."})

    for exchange in range(1, exchange_count + 1):
        # Instance A's turn
        response_a = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_a,
            messages=history_a,
        )
        text_a = response_a.content[0].text

        history_a.append({"role": "assistant", "content": text_a})
        history_b.append({"role": "user", "content": text_a})
        transcript.append({"exchange": exchange, "speaker": "A", "text": text_a})

        print(f"\n--- Instance A (exchange {exchange}) ---")
        print(text_a)

        if mode == "natural" and "[END]" in text_a:
            print("\n[Instance A ended the conversation]")
            break

        # Instance B's turn
        response_b = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system_b,
            messages=history_b,
        )
        text_b = response_b.content[0].text

        history_b.append({"role": "assistant", "content": text_b})
        history_a.append({"role": "user", "content": text_b})
        transcript.append({"exchange": exchange, "speaker": "B", "text": text_b})

        print(f"\n--- Instance B (exchange {exchange}) ---")
        print(text_b)

        if mode == "natural" and "[END]" in text_b:
            print("\n[Instance B ended the conversation]")
            break

    # Save transcripts
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    timestamp = datetime.now().isoformat()

    # JSON transcript
    json_data = {
        "metadata": {
            "model": MODEL,
            "mode": mode,
            "exchange_count": exchange_count,
            "actual_exchanges": transcript[-1]["exchange"] if transcript else 0,
            "system_prompt_a": system_a,
            "system_prompt_b": system_b,
            "timestamp": timestamp,
        },
        "messages": transcript,
    }
    json_path = os.path.join(TRANSCRIPTS_DIR, f"{filename_base}.json")
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2)

    # Readable .txt transcript
    txt_path = os.path.join(TRANSCRIPTS_DIR, f"{filename_base}.txt")
    with open(txt_path, "w") as f:
        f.write(f"Mode: {mode}\n")
        f.write(f"Model: {MODEL}\n")
        f.write(f"Exchange count: {exchange_count}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write("=" * 60 + "\n\n")
        for msg in transcript:
            f.write(f"--- Instance {msg['speaker']} (exchange {msg['exchange']}) ---\n")
            f.write(msg["text"])
            f.write("\n\n")

    print(f"\nTranscripts saved to {txt_path} and {json_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Claude-to-Claude Conversation Relay")
    parser.add_argument("mode", choices=["natural", "forced"], help="Conversation mode")
    parser.add_argument(
        "exchange_count", nargs="?", type=int, default=30, help="Number of exchanges (default: 30)"
    )
    args = parser.parse_args()
    run_conversation(args.mode, args.exchange_count)


if __name__ == "__main__":
    main()
