from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException

from keenetic_client import KeeneticClient
from schemas import DeleteInterfaceRequest, RawRciPostRequest, RenameInterfaceRequest, ShowInterfacesRequest


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="Keenetic WireGuard Rename MVP", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/show-interfaces")
async def show_interfaces(request: ShowInterfacesRequest):
    try:
        async with KeeneticClient(
            base_url=request.base_url,
            login=request.login,
            password=request.password,
        ) as client:
            return await client.show_interfaces()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=_httpx_error_detail(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/interfaces")
async def list_interfaces(request: ShowInterfacesRequest):
    try:
        async with KeeneticClient(
            base_url=request.base_url,
            login=request.login,
            password=request.password,
        ) as client:
            return await client.list_wireguard_interfaces()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=_httpx_error_detail(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/raw-rci-post")
async def raw_rci_post(request: RawRciPostRequest):
    try:
        async with KeeneticClient(
            base_url=request.base_url,
            login=request.login,
            password=request.password,
        ) as client:
            return await client.raw_rci_post(path=request.path, payload=request.payload)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=_httpx_error_detail(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/rename-interface")
async def rename_interface(request: RenameInterfaceRequest):
    try:
        async with KeeneticClient(
            base_url=request.base_url,
            login=request.login,
            password=request.password,
        ) as client:
            return await client.rename_interface(
                interface_id=request.interface_id,
                new_name=request.new_name,
                path=request.path,
                payload=request.payload,
            )
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=_httpx_error_detail(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/delete-interface")
async def delete_interface(request: DeleteInterfaceRequest):
    try:
        async with KeeneticClient(
            base_url=request.base_url,
            login=request.login,
            password=request.password,
        ) as client:
            return await client.delete_interface(
                interface_id=request.interface_id,
                path=request.path,
                payload=request.payload,
            )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=_httpx_error_detail(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _httpx_error_detail(exc: httpx.HTTPStatusError) -> dict[str, str | int]:
    return {
        "message": str(exc),
        "status_code": exc.response.status_code,
        "response_text": exc.response.text,
    }
