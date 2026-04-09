from typing import Any

from pydantic import BaseModel, Field


class KeeneticAuthRequest(BaseModel):
    base_url: str = Field(..., examples=["http://192.168.1.1"])
    login: str = Field(..., examples=["admin"])
    password: str = Field(..., examples=["admin_password"])


class ShowInterfacesRequest(KeeneticAuthRequest):
    pass


class RawRciPostRequest(KeeneticAuthRequest):
    path: str = Field(..., examples=["/rci/..."])
    payload: Any = Field(default_factory=dict)


class RenameInterfaceRequest(KeeneticAuthRequest):
    interface_id: str = Field(..., examples=["Wireguard0"])
    new_name: str = Field(..., examples=["test1"])
    path: str | None = Field(default=None, examples=["/rci/confirmed/rename/path"])
    payload: Any | None = Field(default=None)


class DeleteInterfaceRequest(KeeneticAuthRequest):
    interface_id: str = Field(..., examples=["Wireguard2"])
    path: str | None = Field(default=None, examples=["/rci/"])
    payload: Any | None = Field(default=None)
