#!/usr/bin/env python3

import os
import sys
import argparse
import csv
import datetime as dt
import zoneinfo

import quoalise

# import logging
# logging.basicConfig(level=logging.DEBUG)

parser = argparse.ArgumentParser(
    description="Get records from previous week in a csv file"
)

parser.add_argument(
    "server_jid",
    help="full jid of the server providing the API, "
    + "i.e., sge-proxy@provider.tld/proxy",
)
parser.add_argument(
    "data_id", help="data identifier, i.e., urn:dev:ow:10e2073a0108006_voltage"
)

args = parser.parse_args()

quoalise_user = os.environ.get("QUOALISE_USER")
quoalise_password = os.environ.get("QUOALISE_PASSWORD")
if quoalise_user is None or quoalise_password is None:
    sys.exit(
        "Client credentials not found in environment variables:\n"
        + "QUOALISE_USER should be set to your xmpp bare jid\n"
        + "QUOALISE_PASSWORD should be set to your xmpp password"
    )

# Last available record from history is yesterday at midnight, french time
paris_tz = zoneinfo.ZoneInfo("Europe/Paris")
end_time = dt.datetime.now(paris_tz).replace(hour=0, minute=0, second=0, microsecond=0)

start_time = end_time - dt.timedelta(days=7)

client = quoalise.Client.connect(quoalise_user, quoalise_password)
data = client.get_history(args.server_jid, args.data_id, start_time, end_time)

writer = csv.writer(sys.stdout)

for record in data.records:
    # Quoalise use UTC time internally, convert it back to french time
    time = (
        record.time.astimezone(paris_tz).isoformat()
        if record.time is not None
        else None
    )
    writer.writerow([time, record.value])
