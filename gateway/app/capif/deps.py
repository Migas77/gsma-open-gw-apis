import logging

import jwt

from app.capif.invoker import capif_invoker
from app.exceptions import InternalServerError


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
