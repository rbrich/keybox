# format, parse
# (locker file format)
#

from pwlockr.record import Record, COLUMNS
import io


def format_header(columns=COLUMNS):
    return '\t'.join(columns) + '\n'


def format_record(record: Record, columns=COLUMNS):
    return '\t'.join(record.get(key, '') for key in columns) + '\n'


def format_file(records: list, columns=COLUMNS):
    stream = io.BytesIO()
    stream.write(format_header(columns).encode())
    for record in records:
        stream.write(format_record(record, columns).encode())
    return stream.getvalue()


def parse_header(data: str) -> tuple:
    return tuple(data.rstrip('\n').split('\t'))


def parse_record(data: str, columns: tuple) -> Record:
    values = data.rstrip('\n').split('\t')
    return Record(zip(columns, values))


def parse_file(data: io.IOBase or bytes) -> list:
    if isinstance(data, bytes):
        stream = io.BytesIO(data)
    else:
        stream = data
    line = stream.readline()
    columns = parse_header(line.decode())
    records = []
    for line in stream:
        record = parse_record(line.decode(), columns)
        records.append(record)
    return records, columns
