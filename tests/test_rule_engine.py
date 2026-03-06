import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)

import rule_engine as re


def test_article_rule_match():
    block = re.Block(type="title", text="Art. 10 Admissions and Fees")
    rule = re.ArticleRule()
    ctx = re.ClassifyContext()
    h = rule.match(block, 0, ctx)
    assert h is not None
    assert h.kind == "article"
    assert h.key == "ART:10"
    assert "Art." in h.title or "10" in h.title


def test_decimal_rule_match_and_numbering():
    block = re.Block(type="title", text="2.1 Admission requirements")
    rule = re.DecimalRule()
    ctx = re.ClassifyContext()
    h = rule.match(block, 1, ctx)
    assert h is not None
    assert h.kind == "subsection"
    assert h.key.startswith("NUM:2.1")
    assert h.numbering == (2, 1)


def test_decimal_rule_respects_current_article():
    block = re.Block(type="title", text="3.1 Something else")
    rule = re.DecimalRule()
    ctx = re.ClassifyContext(current_article_num=2)
    h = rule.match(block, 2, ctx)
    assert h is None


def test_caps_topic_rule_match():
    block = re.Block(type="title", text="ADMISSIONS")
    rule = re.CapsTopicRule()
    ctx = re.ClassifyContext()
    h = rule.match(block, 3, ctx)
    assert h is not None
    assert h.kind == "topic"


def test_classifier_integration():
    blocks = [
        re.Block(type="header", text="SECTION I GENERAL"),
        re.Block(type="title", text="Art. 2 Eligibility"),
        re.Block(type="title", text="2.1 Eligible candidates"),
        re.Block(type="title", text="APPLICATIONS"),
    ]
    clf = re.make_classifier()
    out = clf.classify(blocks)
    # should produce 4 headings
    assert len(out) == 4
    assert out[0].kind == "section"
    assert out[1].kind == "article"
    assert out[2].kind == "subsection"
    assert out[3].kind in ("topic", "unknown")
