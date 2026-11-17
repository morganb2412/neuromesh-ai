from neuromesh_api.research import answer_uses_catalog_urls


def test_generated_answer_must_cite_only_current_retrieved_urls():
    evidence = [{'url': 'https://openalex.org/W123'}]
    assert answer_uses_catalog_urls('The source is [this work](https://openalex.org/W123).', evidence)
    assert not answer_uses_catalog_urls('A claim with no citation.', evidence)
    assert not answer_uses_catalog_urls('See https://example.com/invented.', evidence)
    assert not answer_uses_catalog_urls('See https://openalex.org/W123 and https://example.com/other.', evidence)
