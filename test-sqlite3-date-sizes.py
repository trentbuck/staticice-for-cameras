# GOAL: demonstrate that using in sqlite3,
#       INTEGER Rata Die is BY FAR THE MOST EFFICIENT storage format for dates (but not timestamps).
#
# OUTPUT:
#
#       Size BEFORE transparent ZFS compression:
#             14M     size-test-date-integer.db  # WINNER!
#             16M     size-test-date-real.db
#             18M     size-test-date-text.db
#             18M     size-test-datetime-integer.db  # WINNER!
#             20M     size-test-datetime-real.db
#             18M     size-test-datetime-text-unixepoch.db
#             26M     size-test-datetime-text.db
#             8.7M    size-test-time-integer.db  # WINNER!
#             11M     size-test-time-real.db
#             16M     size-test-time-text.db
#
#       Size AFTER transparent ZFS compression:  # with compression=lz4
#             4.3M    size-test-date-integer.db
#             4.4M    size-test-date-real.db
#             4.4M    size-test-date-text.db
#             4.4M    size-test-datetime-integer.db
#             4.3M    size-test-datetime-real.db
#             4.4M    size-test-datetime-text-unixepoch.db
#             5.8M    size-test-datetime-text.db
#             4.1M    size-test-time-integer.db
#             4.3M    size-test-time-real.db
#             4.4M    size-test-time-text.db
#
#       Size AFTER transparent ZFS compression:  # with compression=gzip-9
#             2.6M    size-test-date-integer.db
#             2.9M    size-test-date-real.db
#             2.8M    size-test-date-text.db
#             2.8M    size-test-datetime-integer.db
#             3.0M    size-test-datetime-real.db
#             2.8M    size-test-datetime-text-unixepoch.db
#             3.3M    size-test-datetime-text.db
#             2.4M    size-test-time-integer.db
#             2.4M    size-test-time-real.db
#             2.9M    size-test-time-text.db


import pprint
import os
import time
import pathlib
import sqlite3
import datetime
import subprocess
import glob                     # BAD BAD BAD; USE Path.glob!

def do_test(query_name, value):
    path = pathlib.Path(f'size-test-{query_name}.db')
    path.unlink() if path.exists() else None
    with sqlite3.connect(path) as conn:
        conn.execute('PRAGMA journal_mode = WAL;')
        conn.execute('CREATE TABLE xs (x TEXT NOT NULL);')
        conn.executemany('INSERT INTO xs (x) VALUES (?)',
                         ((value,) for _ in range(1_000_000)))
        (db_value,), = conn.execute('SELECT DISTINCT x FROM xs').fetchall()

# NOTE: we truncate to the nearest second to make the comparison a little fairer.
#       Otherwise REAL would get a boost.
now = datetime.datetime.utcnow().replace(microsecond=0)
# UPDATE: actually let's set a deterministic date (that also compresses well)
now = datetime.datetime(year=2020, month=1, day=1)

# DATE
do_test('date-text',    str(now.date()))
do_test('date-real',    float(now.toordinal()))
do_test('date-integer', int(now.toordinal()))  # rata die

# TIME
do_test('time-text',    str(now.time()))
do_test('time-real',    float(now.hour * 3600 + now.minute * 60 + now.second))
do_test('time-integer', int(now.hour * 3600 + now.minute * 60 + now.second))

# DATETIME
do_test('datetime-text', str(now))
do_test('datetime-text-unixepoch', str(now.strftime('%s')))
do_test('datetime-real', float(now.strftime('%s')))
do_test('datetime-integer', int(now.strftime('%s')))

print('Size BEFORE transparent ZFS compression:', flush=True)
subprocess.check_call(['du', '-h', *sorted(glob.glob('size-test-*.db')), '--apparent-size'])
time.sleep(60)  # wait "long enough" for ZFS to hit the disks... we hope?
print('Size AFTER transparent ZFS compression:', flush=True)
subprocess.check_call(['du', '-h', *sorted(glob.glob('size-test-*.db'))])
