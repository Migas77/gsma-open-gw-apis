import uuid

from pydantic import TypeAdapter, ValidationError

from app import dev_patches # noqa: F401
from typing import Any
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Depends
from fastapi.openapi.utils import get_openapi
from fastapi.requests import Request
from fastapi.responses import Response

from app import drivers, endpoints, probes
from app.exception_handlers import install_exception_handlers
from app.exceptions import BadRequest
from app.schemas.common import XCorrelator


app = FastAPI(
    separate_input_output_schemas=False
)

app.include_router(probes.router)
app.include_router(endpoints.router)
app.include_router(drivers.router, include_in_schema=False)

install_exception_handlers(app)


_x_correlator_type_adapter = TypeAdapter(XCorrelator)


@app.middleware("http")
async def add_correlation_header(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    x_correlator_header = request.headers.get("x-correlator")

    try:
        x_correlator = _x_correlator_type_adapter.validate_python(
            x_correlator_header if x_correlator_header is not None else str(uuid.uuid4())
        )
    except ValidationError:
        raise BadRequest(message="Invalid X-Correlator header")

    request.state.x_correlator = x_correlator

    response = await call_next(request)
    response.headers["x-correlator"] = x_correlator

    return response


# Add the x-correlator header to all operations and responses
def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="GSMA Open Gateway",
        version="0.1.0",
        routes=app.routes,
        separate_input_output_schemas=app.separate_input_output_schemas,
    )

    x_correlator_schema = _x_correlator_type_adapter.json_schema()
    x_correlator_description = x_correlator_schema.get("description", "")

    components = openapi_schema.setdefault("components", {})
    c_parameters = components.setdefault("parameters", {})
    c_parameters["x-correlator"] = {
        "name": "x-correlator",
        "in": "header",
        "description": x_correlator_description,
        "required": False,
        "schema": x_correlator_schema,
    }
    c_headers = components.setdefault("headers", {})
    c_headers["x-correlator"] = {
        "description": x_correlator_description,
        "schema": x_correlator_schema,
    }

    for _, path_schema in openapi_schema["paths"].items():
        for method in ["get", "put", "post", "delete"]:
            operation = path_schema.get(method)
            if operation is None:
                continue

            parameters = operation.setdefault("parameters", [])
            parameters.append({"$ref": "#/components/parameters/x-correlator"})

            responses = operation.setdefault("responses", {})

            if responses.get("422") is not None:
                del responses["422"]

            for _, response in responses.items():
                headers = response.setdefault("headers", {})
                headers["x-correlator"] = {"$ref": "#/components/headers/x-correlator"}

    app.openapi_schema = openapi_schema
    return app.openapi_schema


# This is needed as mypy isn't happy when assigning to a method
# mypy: ignore-errors
app.openapi = custom_openapi
