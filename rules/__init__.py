from .article import article_rule
from .decimal import decimal_rule
from .capstopic import capstopic_rule
from .section import section_rule
from .annex import annex_rule
from .table import table_rule

PLUGINS = [
    article_rule,
    decimal_rule,
    section_rule,
    annex_rule,
    capstopic_rule,
    table_rule,
]

__all__ = [
    "article_rule",
    "decimal_rule",
    "section_rule",
    "annex_rule",
    "capstopic_rule",
    "table_rule",
    "PLUGINS",
]
