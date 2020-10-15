# GOAL: port spaceanal.tcl (sqlite3_analyzer) to Python.
#
# sqlite3_analyzer is just spaceanal.tcl bundled with tclsh and libsqlite3.
# But Debian doesn't ship those, and it DOES ship python and it's
# usually already there (unlike tclsh).
#
# So fuck it, let's just do this directly in Python.
#
# This is based on
# https://sqlite.org/src/file/tool/spaceanal.tcl
# https://sqlite.org/src/raw/a95036b36622e25cffd65a55b22d6af53dfbbff0de02d45dd0059bb3c9978609?at=spaceanal.tcl

import argparse
import sqlite3
import os
import pathlib
import textwrap


def is_without_rowid_f(tname):
    t = quote(tname)
    row = db.execute(f"PRAGMA index_list = '{t}'").fetchone()
    if row and row['origin'] == 'pk':
        count, = db.execute('SELECT count(*) FROM sqlite_schema WHERE name = :name', {'name': row['name']}).fetchone()
        if count == 0:
            return True
    return False


def tclsh():
    raise NotImplementedError()

def usage():
    raise NotImplementedError()


parser = argparse.ArgumentParser(
    description=
        """
        Analyze the SQLite3 database file specified by the "database-filename"
        argument and output a report detailing size and storage efficiency
        information for the database and its constituent tables and indexes.
        """)
mutex = parser.add_mutually_exclusive_group()
mutex.add_argument(
    '--pageinfo',
    action='store_true',
    help='Show how each page of the database-file is used')
mutex.add_argument(
    '--stats',
    action='store_true',
    help=('Output SQL text that creates a new database containing'
          'statistics about the database that was analyzed'))
parser.add_argument(
    '--tclsh',
    action='store_true',
    help='Run the built-in TCL interpreter interactively (for debugging)')
mutex.add_argument(
    '--version',
    action='store_true',
    help='Show the version number of SQLite')
parser.add_argument('database_filename', type=pathlib.Path)
parser.add_argument('--debug', action='store_true')  # SECRET ARGUMENT!
args = parser.parse_args()

if args.version:
    mem = sqlite3.connect(':memory:')
    print(*mem.execute("SELECT sqlite_version()||' '||sqlite_source_id()").fetchone())
    exit(os.EX_OK)

# Raise an error if the file does not exist, or is not readable.
# We need this because sqlite3.connect() will otherwise CREATE a database.
with args.database_filename.open('rb') as _:
    pass

if args.database_filename.stat().st_size < 512:
    print('Empty or malformed database:', args.database_filename, file=sys.stderr, flush=True)
    exit(os.EX_ERR)

# Compute the total file size assuming test_multiplexor is being used.
# Assume that SQLITE_ENABLE_8_3_NAMES might be enabled
# FIXME: skipped because fuck DOS.

# Open the database
db = sqlite3.connect(args.database_filename)
db.row_factory = sqlite3.Row
if args.debug:
    # FIXME: some kind of "print every SQL query/result to stder" happens here.
    raise NotImplementedError()

# Make sure all required compile-time options are available
if not db.execute(
        """SELECT 1 FROM pragma_compile_options
        WHERE compile_options='ENABLE_DBSTAT_VTAB'""").fetchone():
    print(
        'The SQLite database engine linked with this application'
        'lacks required capabilities. Recompile using the'
        '-DSQLITE_ENABLE_DBSTAT_VTAB compile-time option to fix'
        'this problem.',
        file=sys.stderr,
        flush=True)
    exit(os.EX_ERR)
db.execute('SELECT count(*) FROM sqlite_schema')  # FIXME: ???
page_size, = db.execute('PRAGMA page_size').fetchone()

if args.pageinfo:
    db.execute('CREATE VIRTUAL TABLE temp.stat USING dbstat')
    row = db.execute('SELECT pageno, name, path FROM temp.stat ORDER BY pageno').fetchone()
    print(*row)
    exit(os.EX_OK)

if args.stats:
    db.execute('CREATE VIRTUAL TABLE temp.stat USING dbstat')
    print(textwrap.dedent(
        """
        BEGIN;
        CREATE TABLE stats(
          name       STRING,           /* Name of table or index */
          path       INTEGER,          /* Path to page from root */
          pageno     INTEGER,          /* Page number */
          pagetype   STRING,           /* 'internal', 'leaf' or 'overflow' */
          ncell      INTEGER,          /* Cells on page (0 for overflow) */
          payload    INTEGER,          /* Bytes of payload on this page */
          unused     INTEGER,          /* Bytes of unused space on this page */
          mx_payload INTEGER,          /* Largest payload size of all cells */
          pgoffset   INTEGER,          /* Offset of page in file */
          pgsize     INTEGER           /* Size of the page */
        );
        """))
    for x, in db.execute(
            """
            SELECT quote(name) || ',' ||
                   quote(path) || ',' ||
                   quote(pageno) || ',' ||
                   quote(pagetype) || ',' ||
                   quote(ncell) || ',' ||
                   quote(payload) || ',' ||
                   quote(unused) || ',' ||
                   quote(mx_payload) || ',' ||
                   quote(pgoffset) || ',' ||
                   quote(pgsize) AS x FROM stat
            """):
        print(f'INSERT INTO stats VALUES({x});')
    print(f'COMMIT;')
    exit(os.EX_OK)

# In-memory database for collecting statistics. This script loops through
# the tables and indices in the database being analyzed, adding a row for each
# to an in-memory database (for which the schema is shown below). It then
# queries the in-memory db to produce the space-analysis report.
mem = sqlite3.connect(':memory:')
if args.debug:
    # FIXME: some kind of "print every SQL query/result to stder" happens here.
    raise NotImplementedError()
mem.execute(
    """
    CREATE TABLE space_used(
       name clob,        -- Name of a table or index in the database file
       tblname clob,     -- Name of associated table
       is_index boolean, -- TRUE if it is an index, false for a table
       is_without_rowid boolean, -- TRUE if WITHOUT ROWID table
       nentry int,       -- Number of entries in the BTree
       leaf_entries int, -- Number of leaf entries
       depth int,        -- Depth of the b-tree
       payload int,      -- Total amount of data stored in this table or index
       ovfl_payload int, -- Total amount of data stored on overflow pages
       ovfl_cnt int,     -- Number of entries that use overflow
       mx_payload int,   -- Maximum payload size
       int_pages int,    -- Number of interior pages used
       leaf_pages int,   -- Number of leaf pages used
       ovfl_pages int,   -- Number of overflow pages used
       int_unused int,   -- Number of unused bytes on interior pages
       leaf_unused int,  -- Number of unused bytes on primary pages
       ovfl_unused int,  -- Number of unused bytes on overflow pages
       gap_cnt int,      -- Number of gaps in the page layout
       compressed_size int  -- Total bytes stored on disk
    );
    """)

# Create a temporary "dbstat" virtual table.
db.execute('CREATE VIRTUAL TABLE temp.stat USING dbstat')
db.execute('CREATE TEMP TABLE dbstat AS SELECT * FROM temp.stat ORDER BY name, path')
db.execute('DROP TABLE temp.stat')

is_compressed = False
compress_overhead = 0
depth = 0
for name, tbl_name in db.execute('SELECT name, tbl_name FROM sqlite_schema WHERE rootpage>0').fetchall():
    is_index = name != tbl_name
    is_without_rowid = is_without_rowid_f(name)
    row = db.execute(
        """
        SELECT
          sum(ncell)                            AS nentry,
          sum((pagetype=='leaf')*ncell)         AS leaf_entries,
          sum(payload)                          AS payload,
          sum((pagetype=='overflow') * payload) AS ovfl_payload,
          sum(path LIKE '%+000000')             AS ovfl_cnt,
          max(mx_payload)                       AS mx_payload,
          sum(pagetype=='internal')             AS int_pages,
          sum(pagetype=='leaf')                 AS leaf_pages,
          sum(pagetype=='overflow')             AS ovfl_pages,
          sum((pagetype=='internal') * unused)  AS int_unused,
          sum((pagetype=='leaf') * unused)      AS leaf_unused,
          sum((pagetype=='overflow') * unused)  AS ovfl_unused,
          sum(pgsize)                           AS compressed_size,

          -- This was being done in TCL, but fuck it, just do it in sqlite?
          sum(pagetype in ('internal', 'leaf', 'overflow')) * :page_size AS storage,

          max((length(CASE WHEN path LIKE '%+%' THEN '' ELSE path END)+3)/4)
                                                AS depth
        FROM temp.dbstat WHERE name = :name
        """,
        {'name': name,
         'page_size': page_size}).fetchone()
    # FIXME: WTF is up with the "break" in the .tcl here?
    if not is_compressed and row['storage'] > row['compressed_size']:
        is_compressed = True
        compress_overhead = 14   # ????

    # Column 'gap_cnt' is set to the number of non-contiguous entries in the
    # list of pages visited if the b-tree structure is traversed in a top-down
    # fashion (each node visited before its child-tree is passed). Any overflow
    # chains present are traversed from start to finish before any child-tree
    # is.
    gap_cnt = 0
    prev = 0
    for pageno, pagetype in db.execute(
        """
        SELECT pageno, pagetype FROM temp.dbstat
         WHERE name = :name
         ORDER BY pageno
        """, {'name': name}):
        if prev > 0 and pagetype == 'leaf' and pageno != prev + 1:
            gap_cnt += 1
        prev = pageno

    mem.execute(
        'INSERT INTO space_used VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (name,
         tbl_name,
         is_index,
         is_without_rowid,
         row['nentry'],
         row['leaf_entries'],
         row['depth'],
         row['payload'],
         row['ovfl_payload'],
         row['ovfl_cnt'],
         row['mx_payload'],
         row['int_pages'],
         row['leaf_pages'],
         row['ovfl_pages'],
         row['int_unused'],
         row['leaf_unused'],
         row['ovfl_unused'],
         gap_cnt,
         row['compressed_size']))

def integerify(real):
    raise NotImplementedError()


# Quote a string for use in an SQL query. Examples:
#
# quote("hello world")  == "hello world"
# quote("hello world's" == "hello world''s"
def quote(txt):
    return txt.replace("'", "''")

# Output a title line
def titleline(title):
    if title == '':
        print('*' * 79)
    else:
        stars = '*' * (79 - len(title) - 5)
        print('***', title, stars)

# Generate a single line of output in the statistics section of the
# report.
def statline(title, value, extra=''):
    # This isn't identical to the original, but
    # it's close enough. --twb, Oct 2020x
    dots = '.' * 50 - len(title)
    print(title, '.' * 50 - len(title), value, extra)

def percent(num, denom, of=None):
    raise NotImplementedError()

def divide(num, denom):
    raise NotImplementedError()

# Generate a subreport that covers some subset of the database.
# the $where clause determines which subset to analyze.
def subreport(title, where, showFrag):
    global page_size, file_pgcnt, compress_overhead
    ## FIXME: injection attack
    mem.execute(
        f"""
        SELECT
          int(sum(
            CASE WHEN (is_without_rowid OR is_index) THEN nentry
                 ELSE leaf_entries
            END))                   AS nentry,
          int(sum(payload))         AS payload,
          int(sum(ovfl_payload))    AS ovfl_payload,
          max(mx_payload)           AS mx_payload,
          int(sum(ovfl_cnt))        as ovfl_cnt,
          int(sum(leaf_pages))      AS leaf_pages,
          int(sum(int_pages))       AS int_pages,
          int(sum(ovfl_pages))      AS ovfl_pages,
          int(sum(leaf_unused))     AS leaf_unused,
          int(sum(int_unused))      AS int_unused,
          int(sum(ovfl_unused))     AS ovfl_unused,
          int(sum(gap_cnt))         AS gap_cnt,
          int(sum(compressed_size)) AS compressed_size,
          int(max(depth))           AS depth,
          count(*)                  AS cnt
        FROM space_used WHERE $where" {} {}
        """)

    # Output the sub-report title, nicely decorated with * characters.
    #x
    print()
    print(titleline(title))
    print()
