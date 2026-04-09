import hashlib
from typing import Any

import httpx


class KeeneticClient:
    def __init__(self, base_url: str, login: str, password: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.login = login
        self.password = password
        self._authed = False
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            follow_redirects=True,
            trust_env=False,
        )

    async def __aenter__(self) -> "KeeneticClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    async def auth(self) -> None:
        if self._authed:
            return

        response = await self._client.get("/auth")
        challenge = response.headers.get("X-NDM-Challenge")
        realm = response.headers.get("X-NDM-Realm")

        if not challenge or not realm:
            raise RuntimeError("Keenetic auth challenge headers were not returned by GET /auth")

        md5_part = hashlib.md5(f"{self.login}:{realm}:{self.password}".encode("utf-8")).hexdigest()
        sha_part = hashlib.sha256(f"{challenge}{md5_part}".encode("utf-8")).hexdigest()

        auth_response = await self._client.post(
            "/auth",
            json={"login": self.login, "password": sha_part},
        )
        auth_response.raise_for_status()
        self._authed = True

    async def show_interfaces(self) -> Any:
        await self.auth()
        response = await self._client.get("/rci/show/interface")
        response.raise_for_status()
        return response.json()

    async def list_interfaces(self) -> list[dict[str, Any]]:
        data = await self.show_interfaces()
        return self._normalize_interfaces(data)

    async def list_wireguard_interfaces(self) -> dict[str, Any]:
        interfaces = await self.list_interfaces()
        wireguard_interfaces = []
        for item in interfaces:
            if self._infer_interface_kind(item["interface_id"]) != "wireguard":
                continue
            wireguard_interfaces.append(
                {
                    **item,
                    "display_name": item["name"] or item["interface_id"],
                    "has_name": item["name"] is not None,
                    "kind": "wireguard",
                }
            )

        return {
            "kind": "wireguard",
            "total": len(wireguard_interfaces),
            "named_total": sum(1 for item in wireguard_interfaces if item["name"] is not None),
            "unnamed_total": sum(1 for item in wireguard_interfaces if item["name"] is None),
            "interfaces": wireguard_interfaces,
        }

    async def raw_rci_post(self, path: str, payload: Any) -> Any:
        await self.auth()
        normalized_path = path if path.startswith("/") else f"/{path}"
        response = await self._client.post(normalized_path, json=payload)
        response.raise_for_status()
        return self._decode_response(response)

    async def rename_interface(
        self,
        interface_id: str,
        new_name: str,
        path: str | None = None,
        payload: Any | None = None,
    ) -> Any:
        if path and payload is not None:
            result = await self.raw_rci_post(path=path, payload=payload)
            return self._format_rename_result(interface_id=interface_id, new_name=new_name, result=result)

        inferred_payload = [
            {
                "interface": {
                    "description": new_name,
                    "name": interface_id,
                }
            },
            {
                "system": {
                    "configuration": {
                        "save": {}
                    }
                }
            },
        ]
        result = await self.raw_rci_post(path="/rci/", payload=inferred_payload)
        return self._format_rename_result(interface_id=interface_id, new_name=new_name, result=result)

    async def delete_interface(
        self,
        interface_id: str,
        path: str | None = None,
        payload: Any | None = None,
    ) -> Any:
        if path and payload is not None:
            result = await self.raw_rci_post(path=path, payload=payload)
            return self._format_delete_result(interface_id=interface_id, result=result)

        inferred_payload = [
            {
                "interface": {
                    "name": interface_id,
                    "no": True,
                }
            },
            {
                "system": {
                    "configuration": {
                        "save": {}
                    }
                }
            },
        ]
        result = await self.raw_rci_post(path="/rci/", payload=inferred_payload)
        return self._format_delete_result(interface_id=interface_id, result=result)

    async def create_interface(
        self,
        config_base64: str,
        filename: str,
        name: str = "",
        path: str | None = None,
        payload: Any | None = None,
    ) -> Any:
        if path and payload is not None:
            result = await self.raw_rci_post(path=path, payload=payload)
            return self._format_create_result(filename=filename, result=result)

        inferred_payload = [
            {
                "interface": {
                    "wireguard": {
                        "import": {
                            "import": config_base64,
                            "name": name,
                            "filename": filename,
                        }
                    }
                }
            }
        ]
        result = await self.raw_rci_post(path="/rci/", payload=inferred_payload)
        return self._format_create_result(filename=filename, result=result)

    @staticmethod
    def _decode_response(response: httpx.Response) -> Any:
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        try:
            return response.json()
        except ValueError:
            return {"status_code": response.status_code, "text": response.text}

    @staticmethod
    def _normalize_interfaces(data: Any) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []

        if isinstance(data, list):
            candidates = [item for item in data if isinstance(item, dict)]
        elif isinstance(data, dict):
            nested = data.get("interface") or data.get("interfaces")
            if isinstance(nested, list):
                candidates = [item for item in nested if isinstance(item, dict)]
            elif isinstance(nested, dict):
                candidates = KeeneticClient._dict_values_to_candidates(nested)
            else:
                candidates = KeeneticClient._dict_values_to_candidates(data)

        normalized: list[dict[str, Any]] = []
        for item in candidates:
            interface_id = (
                item.get("id")
                or item.get("interface_id")
                or item.get("interface")
                or item.get("ifname")
                or item.get("_key")
            )
            name = (
                item.get("name")
                or item.get("description")
                or item.get("display_name")
                or item.get("alias")
                or item.get("comment")
            )
            if interface_id:
                normalized.append(
                    {
                        "interface_id": str(interface_id),
                        "name": str(name) if name is not None else None,
                    }
                )

        normalized.sort(key=lambda item: item["interface_id"])
        return normalized

    @staticmethod
    def _dict_values_to_candidates(data: dict[str, Any]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for key, value in data.items():
            if isinstance(value, dict):
                candidate = dict(value)
                candidate.setdefault("_key", key)
                candidates.append(candidate)
        return candidates

    @staticmethod
    def _infer_interface_kind(interface_id: str) -> str:
        if interface_id.startswith("Wireguard"):
            return "wireguard"
        if interface_id.startswith("Bridge"):
            return "bridge"
        if interface_id.startswith("FastEthernet"):
            return "ethernet"
        if interface_id.startswith("WifiMaster"):
            return "wifi"
        return "other"

    @classmethod
    def _format_rename_result(cls, interface_id: str, new_name: str, result: Any) -> dict[str, Any]:
        statuses = cls._extract_statuses(result)
        return {
            "ok": True,
            "action": "rename_interface",
            "interface_id": interface_id,
            "new_name": new_name,
            "saved": cls._has_saved_status(statuses),
            "message": f"Interface {interface_id} renamed to {new_name}.",
            "router_messages": cls._extract_messages(statuses),
        }

    @classmethod
    def _format_delete_result(cls, interface_id: str, result: Any) -> dict[str, Any]:
        statuses = cls._extract_statuses(result)
        return {
            "ok": True,
            "action": "delete_interface",
            "interface_id": interface_id,
            "deleted": True,
            "saved": cls._has_saved_status(statuses),
            "message": f"Interface {interface_id} deleted.",
            "router_messages": cls._extract_messages(statuses),
        }

    @classmethod
    def _format_create_result(cls, filename: str, result: Any) -> dict[str, Any]:
        statuses = cls._extract_statuses(result)
        created_interface_id = cls._find_first_value(result, "created")
        intersects = cls._find_first_value(result, "intersects")
        message = (
            f"Interface {created_interface_id} created from {filename}."
            if created_interface_id
            else f"Interface imported from {filename}."
        )
        return {
            "ok": True,
            "action": "create_interface",
            "filename": filename,
            "interface_id": created_interface_id,
            "intersects": intersects,
            "message": message,
            "router_messages": cls._extract_messages(statuses),
        }

    @classmethod
    def _extract_statuses(cls, data: Any) -> list[dict[str, Any]]:
        statuses: list[dict[str, Any]] = []
        cls._walk_statuses(data, statuses)
        return statuses

    @classmethod
    def _walk_statuses(cls, node: Any, statuses: list[dict[str, Any]]) -> None:
        if isinstance(node, list):
            for item in node:
                cls._walk_statuses(item, statuses)
            return

        if not isinstance(node, dict):
            return

        maybe_status = node.get("status")
        if isinstance(maybe_status, list):
            for item in maybe_status:
                if isinstance(item, dict):
                    statuses.append(
                        {
                            "status": item.get("status"),
                            "code": item.get("code"),
                            "ident": item.get("ident"),
                            "message": item.get("message"),
                        }
                    )

        for value in node.values():
            cls._walk_statuses(value, statuses)

    @staticmethod
    def _extract_messages(statuses: list[dict[str, Any]]) -> list[str]:
        return [item["message"] for item in statuses if item.get("message")]

    @staticmethod
    def _has_saved_status(statuses: list[dict[str, Any]]) -> bool:
        for item in statuses:
            message = str(item.get("message") or "").lower()
            if "saving (http/rci)" in message:
                return True
        return False

    @classmethod
    def _find_first_value(cls, node: Any, key: str) -> Any:
        if isinstance(node, dict):
            if key in node:
                return node[key]
            for value in node.values():
                found = cls._find_first_value(value, key)
                if found is not None:
                    return found
            return None

        if isinstance(node, list):
            for item in node:
                found = cls._find_first_value(item, key)
                if found is not None:
                    return found

        return None
