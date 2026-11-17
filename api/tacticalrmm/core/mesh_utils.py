import asyncio
import json
import re
import secrets
import string
import traceback
from typing import TYPE_CHECKING, Any

import websockets

from accounts.utils import is_superuser
from tacticalrmm.constants import TRMM_WS_MAX_SIZE
from tacticalrmm.logger import logger

if TYPE_CHECKING:
    from accounts.models import User


def build_mesh_display_name(
    *, first_name: str | None, last_name: str | None, company_name: str | None
) -> str:
    ret = ""
    if first_name:
        ret += first_name

    if last_name:
        ret += f" {last_name}"

    if ret and company_name:
        ret += f" - {company_name}"
    elif company_name:
        ret += company_name

    return ret


def has_mesh_perms(*, user: "User") -> bool:
    if user.is_superuser or is_superuser(user):
        return True

    return user.role and getattr(user.role, "can_use_mesh")


def make_mesh_password() -> str:
    alpha = string.ascii_letters + string.digits
    nonalpha = "!@#$"
    passwd = [secrets.choice(alpha) for _ in range(29)] + [secrets.choice(nonalpha)]
    secrets.SystemRandom().shuffle(passwd)
    return "".join(passwd)


def transform_trmm(obj):
    ret = []
    try:
        for node in obj:
            node_id = node["node_id"]
            user_ids = [link["_id"] for link in node["links"]]
            ret.append({"node_id": node_id, "user_ids": user_ids})
    except Exception:
        logger.debug(traceback.format_exc)
    return ret


def transform_mesh(obj):
    pattern = re.compile(r".*___\d+")
    ret = []
    try:
        for _, nodes in obj.items():
            for node in nodes:
                node_id = node["_id"]
                try:
                    user_ids = [
                        user_id
                        for user_id in node["links"].keys()
                        if pattern.match(user_id)
                    ]
                except KeyError:
                    # will trigger on initial sync cuz no mesh users yet
                    # also triggers for invalid agents after sync
                    pass
                else:
                    ret.append({"node_id": node_id, "user_ids": user_ids})

    except Exception:
        logger.debug(traceback.format_exc)
    return ret


class MeshSync:
    def __init__(self, uri: str):
        self.uri = uri
        self.mesh_users = self.get_trmm_mesh_users()  # full list

    def mesh_action(
        self, *, payload: dict[str, Any], wait=True
    ) -> dict[str, Any]:
        async def _do(payload) -> dict[str, Any]:
            last_err = None
            for attempt in range(3):
                try:
                    async with websockets.connect(
                        self.uri,
                        max_size=TRMM_WS_MAX_SIZE,
                        ping_interval=20,
                        ping_timeout=20,
                        close_timeout=10,
                        open_timeout=15,
                    ) as ws:
                        await ws.send(json.dumps(payload))
                        if wait:
                            while True:
                                try:
                                    message = await asyncio.wait_for(ws.recv(), 90)
                                    r = json.loads(message)
                                    if isinstance(r, dict) and r.get("action") == payload.get("action"):
                                        return r
                                except asyncio.TimeoutError:
                                    logger.error(f"MeshCentral WebSocket timeout waiting for action={payload.get('action')}")
                                    break
                        else:
                            return {"status": "sent", "users": [], "nodes": {}}
                except Exception as exc:
                    last_err = exc
                    if attempt < 2:
                        await asyncio.sleep(0.6 * (attempt + 1))
            if last_err:
                logger.debug(f"MeshSync WebSocket action {payload.get('action')} failed after retries: {last_err}")
            return {"users": [], "nodes": {}}

        payload["responseid"] = "meshctrl"
        logger.debug(payload)

        return asyncio.run(_do(payload))

    def get_unique_mesh_users(
        self, trmm_agents_list: list[dict[str, Any]]
    ) -> list[str]:
        userids = [i["links"] for i in trmm_agents_list]
        all_ids = [item["_id"] for sublist in userids for item in sublist]
        return list(set(all_ids))

    def get_trmm_mesh_users(self):
        payload = {"action": "users"}
        res = self.mesh_action(payload=payload, wait=True)
        users_list = res.get("users") or [] if isinstance(res, dict) else []
        ret = {
            i["_id"]: i
            for i in users_list
            if isinstance(i, dict) and "_id" in i and re.search(r".*___\d+", i["_id"])
        }
        return ret

    def add_users_to_node(self, *, node_id: str, user_ids: list[str]):

        payload = {
            "action": "adddeviceuser",
            "nodeid": node_id,
            "usernames": [s.replace("user//", "") for s in user_ids],
            "rights": 4088024,
            "remove": False,
        }
        self.mesh_action(payload=payload, wait=False)

    def delete_users_from_node(self, *, node_id: str, user_ids: list[str]):
        payload = {
            "action": "adddeviceuser",
            "nodeid": node_id,
            "userids": user_ids,
            "rights": 0,
            "remove": True,
        }
        self.mesh_action(payload=payload, wait=False)

    def update_mesh_displayname(self, *, user_info: dict[str, Any]) -> None:
        payload = {
            "action": "edituser",
            "id": user_info["_id"],
            "realname": user_info["full_name"],
        }
        self.mesh_action(payload=payload, wait=False)

    def add_user_to_mesh(self, *, user_info: dict[str, Any]) -> None:
        payload = {
            "action": "adduser",
            "username": user_info["username"],
            "email": user_info["email"],
            "pass": make_mesh_password(),
            "resetNextLogin": False,
            "randomPassword": False,
            "removeEvents": False,
            "emailVerified": True,
        }
        self.mesh_action(payload=payload, wait=False)
        if user_info["full_name"]:
            self.update_mesh_displayname(user_info=user_info)

    def delete_user_from_mesh(self, *, mesh_user_id: str) -> None:
        payload = {
            "action": "deleteuser",
            "userid": mesh_user_id,
        }
        self.mesh_action(payload=payload, wait=False)


async def _ws_recv_action(ws, expected_action: str, timeout_s: float = 5.0) -> dict[str, Any]:
    """Read messages from an open MeshCentral WebSocket until expected_action arrives."""
    deadline = asyncio.get_running_loop().time() + timeout_s
    while True:
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            return {}
        raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        data = json.loads(raw)
        if isinstance(data, dict) and data.get("action") == expected_action:
            return data


def _find_node_in_nodes_map(nodes_map: Any, target_node_id: str) -> dict[str, Any] | None:
    if not isinstance(nodes_map, dict):
        return None
    for _, node_list in nodes_map.items():
        if not isinstance(node_list, list):
            continue
        for node in node_list:
            if isinstance(node, dict) and node.get("_id") == target_node_id:
                return node
    return None


async def a_get_mesh_node_live_state(
    uri: str,
    hex_node_id: str,
    *,
    mesh_user_id: str | None = None,
    mesh_username: str | None = None,
    mesh_display_name: str | None = None,
    mesh_email: str | None = None,
    sync_user: bool = False,
    open_timeout: float = 2.5,
) -> dict[str, Any]:
    """
    Query MeshCentral over a single fast WebSocket for node registration, live agent
    connectivity (`conn`), and optional synchronous user permission grant.
    """
    state: dict[str, Any] = {
        "mesh_reachable": False,
        "node_found": False,
        "mesh_connected": False,
        "conn": 0,
        "user_linked": False,
        "rights_synced": False,
    }
    if not hex_node_id or hex_node_id == "error":
        return state

    target_node_id = (
        hex_node_id if hex_node_id.startswith("node//") else f"node//{hex_node_id}"
    )

    try:
        async with websockets.connect(
            uri,
            max_size=TRMM_WS_MAX_SIZE,
            open_timeout=open_timeout,
            close_timeout=2,
            ping_interval=20,
        ) as ws:
            state["mesh_reachable"] = True
            await ws.send(json.dumps({"action": "nodes", "responseid": "meshctrl"}))
            nodes_resp = await _ws_recv_action(ws, "nodes", timeout_s=4.5)
            node = _find_node_in_nodes_map(nodes_resp.get("nodes"), target_node_id)
            if not node:
                return state

            state["node_found"] = True
            try:
                conn_val = int(node.get("conn") or 0)
            except (TypeError, ValueError):
                conn_val = 0
            state["conn"] = conn_val
            state["mesh_connected"] = bool(conn_val & 1)

            links = node.get("links") if isinstance(node.get("links"), dict) else {}
            if mesh_user_id:
                state["user_linked"] = mesh_user_id in links

            if sync_user and mesh_user_id and mesh_username and not state["user_linked"]:
                try:
                    await ws.send(
                        json.dumps({"action": "users", "responseid": "meshctrl"})
                    )
                    users_resp = await _ws_recv_action(ws, "users", timeout_s=4.0)
                    existing_users = {
                        u.get("_id")
                        for u in (users_resp.get("users") or [])
                        if isinstance(u, dict) and u.get("_id")
                    }
                    if mesh_user_id not in existing_users and mesh_email:
                        await ws.send(
                            json.dumps(
                                {
                                    "action": "adduser",
                                    "username": mesh_username,
                                    "email": mesh_email,
                                    "pass": make_mesh_password(),
                                    "resetNextLogin": False,
                                    "randomPassword": False,
                                    "removeEvents": False,
                                    "emailVerified": True,
                                    "responseid": "meshctrl",
                                }
                            )
                        )
                        if mesh_display_name:
                            await ws.send(
                                json.dumps(
                                    {
                                        "action": "edituser",
                                        "id": mesh_user_id,
                                        "realname": mesh_display_name,
                                        "responseid": "meshctrl",
                                    }
                                )
                            )
                        await asyncio.sleep(0.15)

                    await ws.send(
                        json.dumps(
                            {
                                "action": "adddeviceuser",
                                "nodeid": target_node_id,
                                "usernames": [mesh_username],
                                "rights": 4088024,
                                "remove": False,
                                "responseid": "meshctrl",
                            }
                        )
                    )
                    await asyncio.sleep(0.15)
                    state["rights_synced"] = True
                    state["user_linked"] = True
                except Exception as exc:
                    logger.debug(
                        f"Synchronous Mesh permission grant skipped for {target_node_id}: {exc}"
                    )

            return state
    except Exception as exc:
        logger.debug(f"Live Mesh state query failed for {target_node_id}: {exc}")
        return state


def get_mesh_node_live_state(
    uri: str,
    hex_node_id: str,
    *,
    mesh_user_id: str | None = None,
    mesh_username: str | None = None,
    mesh_display_name: str | None = None,
    mesh_email: str | None = None,
    sync_user: bool = False,
) -> dict[str, Any]:
    return asyncio.run(
        a_get_mesh_node_live_state(
            uri,
            hex_node_id,
            mesh_user_id=mesh_user_id,
            mesh_username=mesh_username,
            mesh_display_name=mesh_display_name,
            mesh_email=mesh_email,
            sync_user=sync_user,
        )
    )


async def a_poll_mesh_node_connected(
    uri: str,
    hex_node_id: str,
    *,
    mesh_user_id: str | None = None,
    mesh_username: str | None = None,
    mesh_display_name: str | None = None,
    mesh_email: str | None = None,
    sync_user: bool = False,
    max_wait_s: float = 7.0,
    poll_interval_s: float = 0.85,
) -> dict[str, Any]:
    """Poll MeshCentral until the agent connects or max_wait_s elapses."""
    deadline = asyncio.get_running_loop().time() + max_wait_s
    last_state: dict[str, Any] = {
        "mesh_reachable": False,
        "node_found": False,
        "mesh_connected": False,
        "conn": 0,
        "user_linked": False,
        "rights_synced": False,
    }
    first = True
    while True:
        last_state = await a_get_mesh_node_live_state(
            uri,
            hex_node_id,
            mesh_user_id=mesh_user_id,
            mesh_username=mesh_username,
            mesh_display_name=mesh_display_name,
            mesh_email=mesh_email,
            sync_user=sync_user if (first or last_state.get("rights_synced") is False) else False,
        )
        first = False
        if not last_state["mesh_reachable"]:
            return last_state
        if last_state["node_found"] and last_state["mesh_connected"]:
            return last_state
        if asyncio.get_running_loop().time() >= deadline:
            return last_state
        await asyncio.sleep(poll_interval_s)


def poll_mesh_node_connected(
    uri: str,
    hex_node_id: str,
    *,
    mesh_user_id: str | None = None,
    mesh_username: str | None = None,
    mesh_display_name: str | None = None,
    mesh_email: str | None = None,
    sync_user: bool = False,
    max_wait_s: float = 7.0,
    poll_interval_s: float = 0.85,
) -> dict[str, Any]:
    return asyncio.run(
        a_poll_mesh_node_connected(
            uri,
            hex_node_id,
            mesh_user_id=mesh_user_id,
            mesh_username=mesh_username,
            mesh_display_name=mesh_display_name,
            mesh_email=mesh_email,
            sync_user=sync_user,
            max_wait_s=max_wait_s,
            poll_interval_s=poll_interval_s,
        )
    )
