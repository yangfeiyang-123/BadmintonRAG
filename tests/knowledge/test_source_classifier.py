from rag_project.knowledge.source_classifier import classify_source


def test_classifies_official_manual():
    result = classify_source("BWF_COACHES", "official", "downloaded_html_and_supplemental_pdf", "BWF Coach Manual")
    assert result == "official_manual"


def test_classifies_book_preview():
    result = classify_source("BOOK_GRICE", "book", "downloaded_html", "Badminton: Steps to Success")
    assert result == "book_preview_or_product_page"


def test_classifies_pubmed_as_metadata_when_only_html():
    result = classify_source("REV_PHOMSOUPHA_LAFFAYE", "review", "downloaded_html", "PubMed record")
    assert result == "abstract_or_metadata_only"


def test_classifies_pmc_html_as_full_text():
    result = classify_source("REV_LAM_LUNGE", "review", "downloaded_html", "PMC open access article")
    assert result == "full_text_html"
