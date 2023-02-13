from typing import (
    Tuple,
    Optional,
    Type,
    Literal,
)
from types import TracebackType
from abc import ABC, abstractmethod
import slixmpp
from slixmpp.jid import JID
from slixmpp.plugins.xep_0004.stanza import Form
from slixmpp.exceptions import XMPPError
import datetime as dt
import pytz

from .xmpp_utils import _wait_for_session_start


class ErrorToXmppConverter:
    """
    Convert raised exceptions to XMPP errors.
    """

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        ex_type: Optional[Type[BaseException]],
        ex_val: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> Literal[False]:
        if ex_type == PermissionError:
            raise XMPPError(condition="not-authorized", text=str(ex_val))
        if ex_type == ValueError:
            raise XMPPError(
                condition="bad-request",
                etype="modify",
                text=str(ex_val),
            )
        # Raise exception as-is if not handled above
        return False


class CommandHandler(ABC):
    def __init__(self, node: str, name: str):
        self.node = node
        self.name = name

    def handle_request(self, iq, session):

        if iq["command"].xml:  # has subelements
            return self.handle_submit(session["payload"], session)

        form = self.xmpp_client["xep_0004"].make_form(ftype="form", title=self.name)

        with ErrorToXmppConverter():
            self.fill_form(form)

        session["payload"] = form
        session["next"] = self.handle_submit

        return session

    def handle_submit(self, payload, session):

        result_form = self.xmpp_client["xep_0004"].make_form(
            ftype="result", title="Get history"
        )

        with ErrorToXmppConverter():
            result_data = self.execute(
                session["from"],
                payload,
                result_form,
            )

        session["next"] = None
        session["payload"] = [result_form, result_data]

        return session

    @abstractmethod
    def fill_form(self, client_form: Form):
        pass

    @abstractmethod
    def execute(self, client: JID, payload, result_form: Form):
        pass


class ServerAsync:
    def __init__(self, xmpp_client: slixmpp.ClientXMPP):
        self.xmpp_client = xmpp_client

    @classmethod
    async def connect(
        cls,
        full_jid: str,
        password: str,
        address: Optional[Tuple[str, str]] = None,
    ) -> "ServerAsync":
        xmpp_client = slixmpp.ClientXMPP(full_jid, password)

        # XEP-0004 Data Forms
        xmpp_client.register_plugin("xep_0004")
        # XEP-0050 Ad-Hoc Commands
        xmpp_client.register_plugin("xep_0050")
        # XEP-0199 XMPP Ping
        # Given that XMPP is based on TCP connections, it is possible for the
        # underlying connection to be terminated without the application’s
        # awareness. Ping stanzas provide an alternative to whitespace based
        # keepalive methods for detecting lost connections.
        # TODO check frequency
        xmpp_client.register_plugin("xep_0199", {"keepalive": True, "frequency": 15})

        xmpp_client.connect(address=address)
        await _wait_for_session_start(xmpp_client)
        xmpp_client.send_presence()

        return cls(xmpp_client)

    def add_handler(self, handler: CommandHandler) -> None:
        handler.xmpp_client = self.xmpp_client
        self.xmpp_client["xep_0050"].add_command(
            node=handler.node,
            name=handler.name,
            handler=handler.handle_request,
        )


class GetHistoryHandler(CommandHandler):
    def __init__(self):
        super().__init__(
            node="get_history",
            name="Get history",
        )

    def fill_form(self, client_form: Form):

        client_form.addField(
            var="identifier",
            ftype="text-single",
            label="Identifier",
            required=True,
            value=self.default_identifier(),
        )

        end_time = dt.datetime.now(pytz.timezone("Europe/Paris")).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        start_time = end_time - dt.timedelta(days=1)

        client_form.addField(
            var="start_time",
            ftype="text-single",
            label="Start date",
            desc="Au format ISO 8601",
            required=True,
            value=start_time.isoformat(),
        )

        client_form.addField(
            var="end_time",
            ftype="text-single",
            label="End date",
            desc="Au format ISO 8601",
            required=True,
            value=end_time.isoformat(),
        )

    def execute(self, client: JID, payload, result_form: Form):

        identifier = payload["values"]["identifier"]
        start_time = dt.datetime.fromisoformat(payload["values"]["start_time"])
        end_time = dt.datetime.fromisoformat(payload["values"]["end_time"])

        data = self.get_history(client, identifier, start_time, end_time)

        result_form.addField(
            var="result", ftype="fixed", label=f"Get {identifier}", value="Success"
        )

        return data

    @abstractmethod
    def default_identifier(self) -> str:
        pass

    @abstractmethod
    def get_history(self, client, identifier, start_time, end_time):
        pass


class Subscribe:
    def __init__(self):
        super().__init__(
            node="subscribe",
            name="Subscribe",
        )

    def fill_form(self, client_form: Form):

        client_form.addField(
            var="identifier",
            ftype="text-single",
            label="Identifier",
            required=True,
            value=self.default_identifier,
        )

    def execute(self, client: JID, payload, result_form: Form):

        identifier = payload["values"]["identifier"]

        self.subscribe(client, identifier)

        result_form.addField(
            var="result",
            ftype="fixed",
            label=f"Subscribe to {identifier}",
            value="Success",
        )

        return None

    @abstractmethod
    def default_identifier(self) -> str:
        pass

    @abstractmethod
    def subscribe(self, client, identifier):
        pass


class Unsubscribe:
    def __init__(self):
        super().__init__(
            node="unsubscribe",
            name="Unsubscribe",
        )

    def fill_form(self, client_form: Form):

        client_form.addField(
            var="identifier",
            ftype="text-single",
            label="Identifier",
            required=True,
            value=self.default_identifier,
        )

    def execute(self, client: JID, payload, result_form: Form):

        identifier = payload["values"]["identifier"]

        self.unsubscribe(client, identifier)

        result_form.addField(
            var="result",
            ftype="fixed",
            label=f"Subscribe to {identifier}",
            value="Success",
        )

        return None

    @abstractmethod
    def default_identifier(self) -> str:
        pass

    @abstractmethod
    def unsubscribe(self, client, identifier):
        pass
