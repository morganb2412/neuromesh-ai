import pytest
from defusedxml.common import EntitiesForbidden

from neuromesh_api.ingestion import normalize_arxiv_feed, normalize_pubmed_xml


ARXIV_FEED = b'''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
<entry><id>http://arxiv.org/abs/2501.01234v2</id><title>Continual Learning Methods</title>
<published>2025-01-03T12:00:00Z</published><updated>2025-01-04T12:00:00Z</updated>
<summary>Research abstract.</summary><author><name>Sample Author</name></author>
<category term="cs.LG"/><arxiv:doi>10.5555/arxivtest</arxiv:doi></entry></feed>'''

PUBMED_XML = b'''<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>12345678</PMID>
<Article><ArticleTitle>Temporal Memory in Neuroscience</ArticleTitle><ArticleDate>
<Year>2025</Year><Month>02</Month><Day>14</Day></ArticleDate>
<AuthorList><Author><ForeName>Sample</ForeName><LastName>Researcher</LastName>
<AffiliationInfo><Affiliation>Test University</Affiliation></AffiliationInfo></Author></AuthorList>
<Abstract><AbstractText>Published abstract.</AbstractText></Abstract></Article>
<MeshHeadingList><MeshHeading><DescriptorName UI="D012345">Memory</DescriptorName></MeshHeading></MeshHeadingList>
</MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi">10.5555/pubmedtest</ArticleId></ArticleIdList></PubmedData>
</PubmedArticle></PubmedArticleSet>'''


def test_arxiv_atom_keeps_stable_id_and_record_scoped_byline():
    record = normalize_arxiv_feed(ARXIV_FEED)[0]
    assert record['id'] == 'arxiv:2501.01234'
    assert record['url'] == 'https://arxiv.org/abs/2501.01234'
    assert record['scholarly']['arxiv_id'] == '2501.01234'
    assert record['scholarly']['authors'][0]['identity_scope'] == 'source_record'
    assert record['scholarly']['topics'][0]['name'] == 'cs.LG'
    assert '2501.01234v2' in record['payload']['raw_xml']


def test_pubmed_xml_keeps_pmid_date_abstract_and_mesh_source():
    record = normalize_pubmed_xml(PUBMED_XML)[0]
    assert record['id'] == 'pubmed:12345678'
    assert record['date'] == '2025-02-14'
    assert record['scholarly']['pmid'] == '12345678'
    assert record['scholarly']['authors'][0]['affiliations_raw'] == ['Test University']
    assert record['scholarly']['topics'][0]['id'] == 'mesh:D012345'
    assert record['payload']['abstract'] == 'Published abstract.'


def test_external_xml_entities_are_rejected():
    attack = b'<!DOCTYPE feed [<!ENTITY x SYSTEM "file:///etc/passwd">]><feed>&x;</feed>'
    with pytest.raises(EntitiesForbidden):
        normalize_arxiv_feed(attack)
