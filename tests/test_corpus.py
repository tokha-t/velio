from navigator.corpus import normalization_map, normalize


def test_normalize_nasty_typography():
    assert normalize("  “Rent”\u00a0—  fee\n cap  ") == '"Rent" - fee cap'


def test_normalization_map_tracks_source():
    text, offsets = normalization_map("  Alpha\n  beta")
    assert text == "Alpha beta"
    assert offsets[0] == 2
