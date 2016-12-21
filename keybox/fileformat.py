# format, parse
# (keybox file format)
#

import io

from keybox.record import Record, COLUMNS


def format_header(columns=COLUMNS) -> str:
    """Format header as tab-delimited column names."""
    return '\t'.join(columns) + '\n'


def format_record(record: Record, columns=COLUMNS) -> str:
    """Format record as tab-delimited column values."""
    return '\t'.join(record[key] for key in columns) + '\n'


def write_file(stream, records, columns=COLUMNS):
    """Write header and records into text stream."""
    stream.write(format_header(columns))
    for record in records:
        stream.write(format_record(record, columns))


def format_file(records, columns=COLUMNS) -> str:
    """Format whole file (header and records) into string."""
    stream = io.StringIO()
    write_file(stream, records, columns)
    return stream.getvalue()


def parse_header(data: str) -> tuple:
    """Parse header, return column names."""
    return tuple(data.rstrip('\n').split('\t'))


def parse_record(data: str, columns: tuple) -> Record:
    """Parse record, return column values."""
    values = data.rstrip('\n').split('\t')
    return Record(zip(columns, values))


def read_file(stream) -> tuple:
    """Read header and records from text stream."""
    line = stream.readline()
    columns = parse_header(line)
    records = [parse_record(line, columns) for line in stream]
    return records, columns


def parse_file(data: str) -> tuple:
    """Parse whole file (header and records) from string."""
    stream = io.StringIO(data)
    return read_file(stream)
