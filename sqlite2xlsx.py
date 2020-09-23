#!/usr/bin/python3
import argparse
import pathlib
import sqlite3

import xlsxwriter

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('sqlite_path', type=pathlib.Path)
    parser.add_argument('xlsx_path', type=pathlib.Path, nargs='?')
    parser.add_argument('--tables', nargs='*', help='By default, all tables are converted')
    parser.add_argument('--queries', nargs='*', help='Convert SELECT results (not tables)')
    args = parser.parse_args()

    xlsx_path = args.xlsx_path or args.sqlite_path.with_suffix('.xlsx')

    with sqlite3.connect(
            args.sqlite_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            # row_factory=sqlite3.Row
    ) as conn:
        with xlsxwriter.Workbook(xlsx_path) as workbook:
            for query in args.queries:
                worksheet = workbook.add_worksheet()
                cursor = conn.execute(query)
                # FIXME: pull headings
                for i, row in enumerate(cursor):
                    worksheet.write_row(f'A{2+i}', row)
            # else:
            #     raise NotImplementedError()


if __name__ == '__main__':
    main()
