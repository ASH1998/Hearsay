from __future__ import annotations

from database_setup import configured_environment
from hearsay_api.inference import (
    DeterministicInferenceProvider,
    ModalInferenceProvider,
    RumorRetellingRequest,
)


def main() -> int:
    environment = configured_environment()
    modal_url = environment.get("MODAL_PROXY_URL")
    token_id = environment.get("MODAL_PROXY_TOKEN_ID")
    token_secret = environment.get("MODAL_PROXY_TOKEN_SECRET")
    model_id = environment.get(
        "HEARSAY_MODAL_MODEL",
        "thinkingmachines/Inkling-NVFP4",
    )
    request = RumorRetellingRequest(
        original_claim="The newcomer challenged Bram's shipment price in market row.",
        speaker_id="bram",
        listener_id="pip",
        trust=0.6,
        context="A public dispute in Greyhaven.",
    )

    if modal_url and token_id and token_secret:
        provider = ModalInferenceProvider(
            base_url=modal_url,
            token_id=token_id,
            token_secret=token_secret,
            model_id=model_id,
            timeout_seconds=45,
        )
        result = provider.retell_rumor(request)
        if not result.retold_claim.strip() or not result.semantic_position.model_dump(
            exclude_none=True
        ):
            raise RuntimeError("Modal returned an incomplete structured rumor.")
        print(
            "Modal structured-output probe passed "
            f"with provider '{provider.provider_id}' and model '{provider.model_id}'."
        )
        return 0

    provider = DeterministicInferenceProvider()
    result = provider.retell_rumor(request)
    if not result.retold_claim.strip() or not result.semantic_position.model_dump(
        exclude_none=True
    ):
        raise RuntimeError("Deterministic structured-output fixture is incomplete.")
    print("Modal is not configured; deterministic structured-output fixture passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
