from .schemas import AsrRequest, AsrResponse


def transcribe_audio(request: AsrRequest) -> AsrResponse:
    """Mock ASR entrypoint; replace with iFlytek integration later."""
    if request.mock_text:
        return AsrResponse(
            success=True,
            text=request.mock_text,
            confidence=1.0,
            provider="mock",
            message="ASR mock_text returned.",
        )
    return AsrResponse(
        success=False,
        text="",
        confidence=0.0,
        provider="mock",
        message="No mock_text provided. Real ASR provider is not configured in MVP.",
    )
