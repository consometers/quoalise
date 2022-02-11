import sys
import os
import argparse
import json
import datetime as dt
from xml.dom import minidom
import xml.etree.ElementTree as ET

from .client import Client
from .utils import parse_iso_date, serialize
from .errors import NotAuthorized, ServiceUnavailable


def cli():

    parser = argparse.ArgumentParser(description="Access a Quoalise API.")
    subparsers = parser.add_subparsers(help="sub-command")

    parser_client = subparsers.add_parser("get-records", help="Get records")
    parser_client.add_argument(
        "server_jid",
        help="full jid of the server providing the API, "
        + "i.e., sge-proxy@provider.tld/proxy",
    )
    parser_client.add_argument(
        "data_id", help="data identifier, i.e., urn:dev:ow:10e2073a0108006_voltage"
    )
    parser_client.add_argument("--start-date", metavar="YYYY-MM-DD")
    parser_client.add_argument("--end-date", metavar="YYYY-MM-DD")
    parser_client.add_argument(
        "--format",
        choices={"quoalise", "json", "csv"},
        default="json",
        help="default: %(default)s",
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

    if args.start_date is not None:
        args.start_date = parse_iso_date(args.start_date)

    if args.end_date is not None:
        args.end_date = parse_iso_date(args.end_date)

    try:
        return get_records(
            quoalise_user,
            quoalise_password,
            args.server_jid,
            args.data_id,
            start_date=args.start_date,
            end_date=args.end_date,
            format=args.format,
        )
    except NotAuthorized as e:
        print(f"You are not authorized to access the resource: {e}", file=sys.stderr)

    except ServiceUnavailable as e:
        print(f"{args.server_jid} is not available: {e}", file=sys.stderr)

    except Exception as e:
        print(str(e), file=sys.stderr)

    return -1


def get_records(
    client_jid,
    client_pass,
    server_full_jid,
    data_id,
    start_date=None,
    end_date=None,
    format="json",
):

    client = Client.connect(client_jid, client_pass, server_full_jid)
    data = client.get_records(data_id, start_date, end_date)

    if format == "quoalise":
        print(minidom.parseString(ET.tostring(data.xml)).toprettyxml(indent="  "))

    elif format == "json":

        print(
            json.dumps(
                {"meta": data.meta, "records": data.records},
                indent=2,
                default=serialize,
            )
        )

    else:
        raise ValueError(f"Unexpected format: {format}")

    return 0


if __name__ == "__main__":
    sys.exit(cli())
