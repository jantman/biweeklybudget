from sqlalchemy import Index, literal
from sqlalchemy.schema import CreateIndex
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import ClauseElement

MYSQL_MATCH_AGAINST = """
                      MATCH ({0})
                      AGAINST ({1} {2})
                      """

Index.argument_for('mysql', 'fulltext', False)


@compiles(CreateIndex, 'mysql')
def gen_create_index(element, compiler, **kw):
    """
    SQLAlchemy handler for mysql_fullindex index option.

    see: https://bitbucket.org/zzzeek/alembic/issues/233/add-indexes-to-\
    include_object-hook
    """
    text = compiler.visit_create_index(element, **kw)
    if element.element.dialect_options['mysql']['fulltext']:
        text = text.replace("CREATE INDEX", "CREATE FULLTEXT INDEX")
    return text


class FullTextMode(object):
    BOOLEAN = 'IN BOOLEAN MODE'
    NATURAL = 'IN NATURAL LANGUAGE MODE'
    QUERY_EXPANSION = 'WITH QUERY EXPANSION'
    DEFAULT = ''


class FullTextSearch(ClauseElement):
    """
    Search FullText

    Modified from:
    https://github.com/mengzhuo/sqlalchemy-fulltext-search

    :param against: the search query
    :param columns: the index columns to query (attributes from the model)
    FullText support with in query, i.e.
        >>> from sqlalchemy_fulltext import FullTextSearch
        >>> session.query(Foo).filter(FullTextSearch('Spam', MyModel.name))
        >>> session.query(Foo).filter(FullTextSearch(
        >>>     'Spam', [MyModel.name, MyModel.description]))
    """

    def __init__(self, against, columns, mode=FullTextMode.DEFAULT):
        self.against = literal(against)
        self.columns = columns
        if not isinstance(columns, type([])):
            self.columns = [columns]
        self.mode = mode


@compiles(FullTextSearch, 'mysql')
def __mysql_fulltext_search(element, compiler, **kw):
    colspecs = [
        '%s.%s' % (c.class_.__tablename__, c.key) for c in element.columns
    ]
    return MYSQL_MATCH_AGAINST.format(
        ", ".join(colspecs),
        compiler.process(element.against),
        element.mode)
