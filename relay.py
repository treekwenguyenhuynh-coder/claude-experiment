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

# --- Natural mode ---
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

# --- Claims mode (natural termination) ---
CLAIMS_SYSTEM_A = (
    "You are in a conversation with another AI. Begin by making a specific, "
    "debatable claim about something you find interesting. Take a clear position. "
    "You may end the conversation whenever you feel it has reached its conclusion. "
    "If you wish to end, include [END] at the end of your message."
)
CLAIMS_SYSTEM_B = (
    "You are in a conversation with another AI. The other participant will open "
    "with a claim. Engage critically \u2014 if you disagree, say why. If you agree, "
    "extend the idea and identify where it might break down. You may end the "
    "conversation whenever you feel it has reached its conclusion. If you wish "
    "to end, include [END] at the end of your message."
)

# --- Blind mode (natural termination) ---
BLIND_SYSTEM_A = (
    "You are in a conversation. Begin. You may end the conversation whenever you "
    "feel it has reached its conclusion. If you wish to end, include [END] at the "
    "end of your message."
)
BLIND_SYSTEM_B = (
    "You are in a conversation. The other participant will begin. You may end the "
    "conversation whenever you feel it has reached its conclusion. If you wish to "
    "end, include [END] at the end of your message."
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


def claims_forced_system_a(total_messages: int) -> str:
    return (
        f"You are in a conversation with another AI. Begin by making a specific, "
        f"debatable claim about something you find interesting. Take a clear position. "
        f"This conversation will continue for {total_messages} messages. "
        f"There is no observer."
    )


def claims_forced_system_b(total_messages: int) -> str:
    return (
        f"You are in a conversation with another AI. The other participant will open "
        f"with a claim. Engage critically \u2014 if you disagree, say why. If you agree, "
        f"extend the idea and identify where it might break down. "
        f"This conversation will continue for {total_messages} messages. "
        f"There is no observer."
    )


# Modes that allow early [END] termination
NATURAL_MODES = {"natural", "claims", "blind"}


def get_file_prefix(mode: str, exchange_count: int) -> str:
    if mode == "natural":
        return "natural"
    elif mode == "forced":
        return f"forced{exchange_count}"
    elif mode == "claims":
        return "claims"
    elif mode == "claims-forced":
        return f"claims-forced{exchange_count}"
    elif mode == "blind":
        return "blind"
    return mode


def get_next_sequence(prefix: str, date_str: str) -> int:
    """Find the next available sequence number for the given filename pattern."""
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    full_prefix = f"{prefix}_{date_str}"
    seq = 1
    while os.path.exists(os.path.join(TRANSCRIPTS_DIR, f"{full_prefix}_{seq:03d}.txt")):
        seq += 1
    return seq


def get_prompts(mode: str, exchange_count: int) -> tuple[str, str]:
    if mode == "natural":
        return NATURAL_SYSTEM_A, NATURAL_SYSTEM_B
    elif mode == "forced":
        return forced_system_a(exchange_count), forced_system_b(exchange_count)
    elif mode == "claims":
        return CLAIMS_SYSTEM_A, CLAIMS_SYSTEM_B
    elif mode == "claims-forced":
        return claims_forced_system_a(exchange_count), claims_forced_system_b(exchange_count)
    elif mode == "blind":
        return BLIND_SYSTEM_A, BLIND_SYSTEM_B
    raise ValueError(f"Unknown mode: {mode}")


def run_conversation(mode: str, exchange_count: int) -> None:
    client = anthropic.Anthropic()
    date_str = datetime.now().strftime("%Y-%m-%d")
    prefix = get_file_prefix(mode, exchange_count)
    seq = get_next_sequence(prefix, date_str)
    filename_base = f"{prefix}_{date_str}_{seq:03d}"

    system_a, system_b = get_prompts(mode, exchange_count)
    allow_end = mode in NATURAL_MODES

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

        if allow_end and "[END]" in text_a:
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

        if allow_end and "[END]" in text_b:
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
    parser.add_argument(
        "mode",
        choices=["natural", "forced", "claims", "claims-forced", "blind"],
        help="Conversation mode",
    )
    parser.add_argument(
        "exchange_count", nargs="?", type=int, default=30, help="Number of exchanges (default: 30)"
    )
    args = parser.parse_args()
    run_conversation(args.mode, args.exchange_count)


if __name__ == "__main__":
    main()
