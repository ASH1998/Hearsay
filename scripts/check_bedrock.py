from __future__ import annotations

import argparse
from collections.abc import Callable
from time import perf_counter
from typing import Any

from hearsay_api.config import Settings
from hearsay_api.inference import (
    AutonomousActionRequest,
    BedrockInferenceProvider,
    DialogueRequest,
    ProviderCall,
    RumorRetellingRequest,
)

PROBES: dict[str, Callable[[BedrockInferenceProvider], ProviderCall[Any]]] = {
    "rumor": lambda provider: provider.retell_rumor(
        RumorRetellingRequest(
            original_claim="The newcomer challenged Bram's shipment price in market row.",
            speaker_id="bram",
            listener_id="pip",
            trust=0.6,
            context="A public dispute in Greyhaven.",
        )
    ),
    "dialogue": lambda provider: provider.generate_dialogue(
        DialogueRequest(
            npc_id="talia",
            player_message="What did Pip tell you about Bram?",
            recalled_memories=[
                "Pip said the newcomer challenged Bram's shipment price.",
            ],
            current_mood="guarded",
        )
    ),
    "autonomous": lambda provider: provider.choose_autonomous_action(
        AutonomousActionRequest(
            agent_id="pip",
            location_id="market",
            nearby_agent_ids=["talia"],
            recalled_memories=[
                "Bram resents the newcomer challenging his shipment price.",
            ],
            allowed_actions=["talk", "share_rumor", "wait"],
        )
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run one to three explicit Bedrock structured-output calls, once, with "
            "no retries, fallback, loop, or persistent server."
        )
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Acknowledge that the selected Bedrock calls may incur AWS charges.",
    )
    parser.add_argument(
        "operations",
        nargs="*",
        default=[],
        help="Bounded operations to call once each (maximum three).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = Settings()
    region = settings.aws_region
    model_id = settings.bedrock_model
    missing = [
        name
        for name, value in (
            ("AWS_REGION", region),
            ("HEARSAY_BEDROCK_MODEL", model_id),
        )
        if not value
    ]
    if missing:
        print(
            "Bedrock proof is not configured; missing "
            + ", ".join(missing)
            + ". No AWS request was made."
        )
        return 1 if args.execute else 0
    if settings.llm_provider != "bedrock":
        print(
            "Bedrock proof is disabled because HEARSAY_LLM_PROVIDER is not "
            "'bedrock'. No AWS request was made."
        )
        return 1 if args.execute else 0
    if not args.execute:
        print(
            "Bedrock configuration is present. No AWS request was made. Pass "
            "--execute and one or more operations to authorize bounded paid calls."
        )
        return 0
    if not args.operations:
        print("Choose at least one of: rumor, dialogue, autonomous.")
        return 2
    invalid_operations = set(args.operations) - set(PROBES)
    if invalid_operations:
        print("Unknown Bedrock proof operation(s): " + ", ".join(sorted(invalid_operations)) + ".")
        return 2
    if len(args.operations) != len(set(args.operations)):
        print("Each Bedrock proof operation may be selected at most once.")
        return 2
    assert region is not None
    assert model_id is not None
    if "anthropic" not in model_id.lower() and "claude" not in model_id.lower():
        print("Configured Bedrock model is not identifiable as Claude. No AWS request was made.")
        return 2

    provider = BedrockInferenceProvider(
        region=region,
        model_id=model_id,
        timeout_seconds=min(settings.inference_timeout_seconds, 45),
    )
    print(
        f"Starting {len(args.operations)} one-shot Bedrock call(s); retries=0, "
        "fallback=off, persistent_server=off."
    )
    for operation in args.operations:
        started = perf_counter()
        try:
            result = PROBES[operation](provider)
        except Exception as error:
            print(
                f"{operation}: failed safely with {type(error).__name__}; no retry was attempted."
            )
            return 1
        latency_ms = (perf_counter() - started) * 1000
        print(
            f"{operation}: structured_output=true, provider=bedrock, "
            f"model={model_id}, input_tokens={result.input_tokens}, "
            f"output_tokens={result.output_tokens}, latency_ms={latency_ms:.1f}."
        )
    print("Bounded Bedrock proof completed; the process is exiting.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
