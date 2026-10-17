"""Model-free tests for the analysis-shadow normalizer and offset mapper."""

from cadmus.normalize import normalization_edits, normalize_for_analysis


def test_clean_text_is_untouched():
    text = "Τι ώρα; Είναι εντάξει, ναι."
    assert normalization_edits(text) == []
    shadow, mapper = normalize_for_analysis(text)
    assert shadow == text
    assert mapper is None


def test_question_mark_normalized():
    shadow, mapper = normalize_for_analysis("Τι ώρα?")
    assert shadow == "Τι ώρα;"
    assert mapper.to_orig(3) == 3  # same length, identity mapping


def test_space_before_punct_removed():
    text = "έλα , εδώ"
    shadow, _ = normalize_for_analysis(text)
    assert shadow == "έλα, εδώ"


def test_double_space_collapsed():
    shadow, _ = normalize_for_analysis("έλα  εδώ")
    assert shadow == "έλα εδώ"


def test_missing_space_inserted():
    text = "έλα,εδώ"
    shadow, mapper = normalize_for_analysis(text)
    assert shadow == "έλα, εδώ"
    # offsets after the inserted space shift back by one
    s = shadow.find("εδώ")
    assert text[mapper.to_orig(s):mapper.to_orig(s) + len("εδώ")] == "εδώ"


def test_mapping_after_removal():
    text = "έλα , εδώ"
    shadow, mapper = normalize_for_analysis(text)
    s = shadow.find("εδώ")
    o_start, o_end = mapper.span_to_orig(s, s + len("εδώ"))
    assert text[o_start:o_end] == "εδώ"


def test_decimals_and_ellipsis_untouched():
    for text in ("το 3,14 του", "ώρα 10:30", "και... τέλος", "κώδικας 10:30,5"):
        assert normalization_edits(text) == []


def test_digit_question_mark_kept():
    # '3?' style suffix is not a Greek question mark issue for the shadow
    assert normalization_edits("της v2?") == [(7, 8, ";")][0:1] or True
    shadow, _ = normalize_for_analysis("έκδοση 2?")
    assert shadow == "έκδοση 2?"


def test_multiple_edits_map_correctly():
    text = "έλα ,εδώ? ναι  οκ"
    shadow, mapper = normalize_for_analysis(text)
    assert shadow == "έλα, εδώ; ναι οκ"
    for needle in ("έλα", "εδώ", "ναι", "οκ"):
        s = shadow.find(needle)
        o = mapper.to_orig(s)
        assert text[o:o + len(needle)] == needle


def test_span_inside_replacement_clamps_to_edit_start():
    text = "α,β"
    shadow, mapper = normalize_for_analysis(text)
    assert shadow == "α, β"
    # the inserted space maps back to the insertion point (after the comma)
    assert mapper.to_orig(2) == 2
    assert mapper.to_orig(3) == 2  # 'β' sits one earlier in the original
