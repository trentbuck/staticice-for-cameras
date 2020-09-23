#!/usr/bin/python3
import argparse
import logging
import pathlib
import sqlite3

import xlsxwriter

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('sqlite_path', type=pathlib.Path)
    parser.add_argument('xlsx_path', type=pathlib.Path, nargs='?', help='By default, based on sqlite path')
    parser.add_argument('-t', '--tables', nargs='*', help='By default, all tables are converted')
    parser.add_argument('-q', '--queries', nargs='*', help='Convert SELECT results (not tables)')
    args = parser.parse_args()
    xlsx_path = args.xlsx_path or args.sqlite_path.with_suffix('.xlsx')
    with sqlite3.connect(
            args.sqlite_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES) as conn:
        conn.row_factory = sqlite3.Row
        with xlsxwriter.Workbook(xlsx_path) as workbook:
            if not args.tables and not args.queries:  # if you don't ask for anything, do ALL tables.
                worksheet_queries = [q for q, in conn.execute("SELECT printf('select * from %s;', quote(name)) FROM sqlite_schema WHERE type = 'table';").fetchall()]
            else:
                worksheet_queries = [q
                                     for t in args.tables or []  # FIXME: use "WHERE name IN ?" for a single query.
                                     for q, in conn.execute("SELECT printf('select * from %s;', quote(?))", (t,)).fetchall()]
            worksheet_queries += args.queries or []
            for worksheet_query in worksheet_queries:
                logging.info('Creating worksheet for %s', worksheet_query)
                worksheet = workbook.add_worksheet()
                rows = conn.execute(worksheet_query).fetchall()
                if rows:
                    worksheet.write_row(f'A1', rows[0].keys())
                for i, row in enumerate(rows):
                    worksheet.write_row(f'A{2+i}', row)


if __name__ == '__main__':
    main()
