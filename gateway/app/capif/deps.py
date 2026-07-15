import logging

import jwt
from fastapi import Request
from OpenSSL import crypto

from app.capif.invoker import capif_invoker
from app.capif.provider import capif_provider
from app.exceptions import InternalServerError, Unauthorized


def _extract_public_key(cert_path: str) -> bytes:
    with open(cert_path, "r") as f:
        cert = f.read()

    crt_obj = crypto.load_certificate(crypto.FILETYPE_PEM, cert)
    pub_key_obj = crt_obj.get_pubkey()
    return crypto.dump_publickey(crypto.FILETYPE_PEM, pub_key_obj)


def verify_capif_invoker_token(request: Request) -> None:
    """
    Dependency function that verifies incoming requests to the CAMARA (GSMA Open Gateway)
    APIs carry a valid access token issued by CAPIF for an onboarded API invoker.
    """
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ") if auth_header.startswith("Bearer ") else None
    if token is None:
        raise Unauthorized()

    if capif_provider.capif_cert_pem_path is None:
        logging.error("Internal error: CAPIF provider is not initialized")
        raise InternalServerError()

    try:
        jwt.decode(
            token,
            _extract_public_key(capif_provider.capif_cert_pem_path),
            algorithms=["RS256"],
        )
    except jwt.PyJWTError:
        raise Unauthorized()


def get_nef_capif_token(force_refresh: bool = False) -> str:
    """
    Dependency function to get the CAPIF token
    needed to perform the related background NEF operations
    """

    service_discoverer = capif_invoker.service_discoverer
    if not service_discoverer:
        logging.info("Internal error: no service discoverer => no CAPIF token found")
        raise InternalServerError()

    token = service_discoverer.token
    if not force_refresh and token:
        try:
            jwt.decode(token, options={"verify_signature": False, "verify_exp": True})
            return str(service_discoverer.token)
        except jwt.ExpiredSignatureError:
            logging.warning("Internal error: CAPIF token is expired")
        except jwt.InvalidTokenError:
            logging.error("Internal error: invalid CAPIF token")
            raise InternalServerError()
        except jwt.PyJWTError:
            logging.error("Internal error: invalid CAPIF token (unknown error)")
            raise InternalServerError()

    service_discoverer.get_tokens()
    return str(service_discoverer.token)
