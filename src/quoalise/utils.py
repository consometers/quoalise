import datetime as dt
from .data import Record


def parse_iso_date(date_str):
    return dt.datetime.strptime(date_str, "%Y-%m-%d").date()


def format_iso_date(date):
    return date.strftime("%Y-%m-%d")


def serialize(obj):
    if isinstance(obj, (dt.datetime, dt.date)):
        return obj.isoformat()
    if isinstance(obj, Record):
        return obj.__dict__
    return str(obj)
