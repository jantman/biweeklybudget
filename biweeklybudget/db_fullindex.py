from sqlalchemy import Index
from sqlalchemy.schema import CreateIndex
from sqlalchemy.ext.compiler import compiles

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
