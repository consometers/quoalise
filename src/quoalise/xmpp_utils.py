from typing import Any

import slixmpp
import asyncio

from .errors import (
    ConnectionFailed,
)


async def _wait_for_session_start(xmpp_client: slixmpp.ClientXMPP) -> None:
    """
    Intended to be called right after xmpp_client.connect().
    Wait for a session_start event, raise an exception when not received, or
    when another unexpected event happens.

    Return nothing on success, raise a ConnectionFailed exception on failure.
    """

    session_state: asyncio.Future[bool] = asyncio.Future()
    error = None

    def session_start_waiter(event_data: Any) -> None:
        if not session_state.done():
            session_state.set_result(True)

    def session_end_handler(event_data: Any) -> None:
        if not session_state.done():
            nonlocal error
            error = ConnectionFailed("XMPP server ended the session")
            session_state.set_result(False)

    def connection_failed_handler(event_data: Any) -> None:
        if not session_state.done():
            nonlocal error
            error = ConnectionFailed(f"XMPP server is not reachable, {event_data}")
            session_state.set_result(False)

    def failed_auth_handler(event_data: Any) -> None:
        if not session_state.done():
            nonlocal error
            error = ConnectionFailed("Invalid username or password")
            session_state.set_result(False)

    handlers = {
        "session_start": session_start_waiter,
        "session_end": session_end_handler,
        "connection_failed": connection_failed_handler,
        "failed_auth": failed_auth_handler,
    }

    try:
        for event_name, pointer in handlers.items():
            xmpp_client.add_event_handler(
                event_name,
                pointer,
                disposable=True,
            )

        await asyncio.wait_for(session_state, 10)

        if error:
            raise error

    finally:
        for event_name, pointer in handlers.items():
            xmpp_client.del_event_handler(
                event_name,
                pointer,
            )
