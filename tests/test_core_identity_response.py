from core.modules.identity.service import build_identity_response


def test_core_identity_response_public_api_is_available():
    result = build_identity_response("identity")

    assert result["agent"] == "identity_module"
    assert result["identity_kind"] == "identity_short"
    assert result["response"].strip()
