import sys
import os
import argparse
import logging
import datetime as dt
import zoneinfo
from typing import Iterable
from xml.dom import minidom
import xml.etree.ElementTree as ET

from .client import Client
from .errors import NotAuthorized, ServiceUnavailable, ConnectionFailed
from .data import Data


def cli() -> int:

    parser = argparse.ArgumentParser(description="Access a Quoalise API.")

    parser.add_argument("--debug", action="store_true", help="Show xmpp debug logs")

    parser.add_argument(
        "--format",
        choices={"quoalise", "json", "csv"},
        default="json",
        help="default: %(default)s",
    )

    parser.add_argument(
        "--tz", help="timezone descriptor, ie. Europe/Paris, local time by default"
    )

    subparsers = parser.add_subparsers(help="command", dest="command")

    parser_client = subparsers.add_parser("get-history", help="Get history")
    parser_client.add_argument(
        "server_jid",
        help="full jid of the server providing the API, "
        + "i.e. sge-proxy@provider.tld/proxy",
    )
    parser_client.add_argument(
        "data_id", help="data identifier, i.e. urn:dev:ow:10e2073a0108006_voltage"
    )
    parser_client.add_argument("--start-time", metavar="YYYY-MM-DDTHH:MM:SSZ")
    parser_client.add_argument("--end-time", metavar="YYYY-MM-DDTHH:MM:SSZ")

    subparsers.add_parser("listen", help="Listen for incoming messages")

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    if args.tz is not None:
        args.tz = zoneinfo.ZoneInfo(args.tz)

    quoalise_user = os.environ.get("QUOALISE_USER")
    quoalise_password = os.environ.get("QUOALISE_PASSWORD")
    if quoalise_user is None or quoalise_password is None:
        sys.exit(
            "Client credentials not found in environment variables:\n"
            + "QUOALISE_USER should be set to your xmpp bare jid\n"
            + "QUOALISE_PASSWORD should be set to your xmpp password"
        )

    # Negative priority prevents to receive messages that are not explicitely
    # addressed to this resource. Use a positive value when waiting for
    # subscription records, use a negative value when polling records.
    if args.command == "get-history":
        priority = -1
    else:
        priority = 1

    client = Client.connect(quoalise_user, quoalise_password, priority=priority)

    try:
        if args.command == "get-history":

            if args.start_time is not None:
                args.start_time = dt.datetime.fromisoformat(args.start_time)
                args.start_time = args.start_time.astimezone(tz=args.tz)

            if args.end_time is not None:
                args.end_time = dt.datetime.fromisoformat(args.end_time)
                args.end_time = args.end_time.astimezone(tz=args.tz)

            data_stream: Iterable[Data] = [
                client.get_history(
                    args.server_jid, args.data_id, args.start_time, args.end_time
                )
            ]
        elif args.command == "listen":
            data_stream = client.listen()
        else:
            raise ValueError(f"Unexpected command {args.command}")

        for data in data_stream:
            if args.format == "quoalise":
                print(
                    minidom.parseString(ET.tostring(data.to_xml())).toprettyxml(
                        indent="  "
                    )
                )
            elif args.format == "json":
                print(data.to_json(indent=2, tz=args.tz))
            else:
                raise ValueError(f"Unexpected format {args.format}")

    except NotAuthorized as e:
        print(f"You are not authorized to access the resource: {e}", file=sys.stderr)

    except ServiceUnavailable as e:
        print(f"{args.server_jid} is not available: {e}", file=sys.stderr)

    except ConnectionFailed as e:
        print(f"XMPP user {quoalise_user} is not able to connect: {e}", file=sys.stderr)

    except Exception as e:
        if args.debug:
            raise e
        else:
            print(f"{type(e).__name__}: {e}", file=sys.stderr)

    return -1


if __name__ == "__main__":
    sys.exit(cli())
