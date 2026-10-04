from navigator.verify import verify_quote


def test_normalized_exact_curly_quotes_and_whitespace():
    raw = "Before. The landlord “shall not”\u00a0charge  that fee. After."
    result = verify_quote('The landlord "shall not" charge that fee.', raw)
    assert result is not None
    assert result.method == "normalized_exact"
    assert "landlord" in result.text


def test_rejects_unrelated_quote():
    assert verify_quote("This fabricated requirement is definitely nowhere in the source.", "A very different source document with enough text.") is None
