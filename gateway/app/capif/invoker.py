import asyncio
import logging
import os
from contextlib import asynccontextmanager

import opencapif_sdk
from fastapi import FastAPI

from app.capif import CAPIF_SDK_CONFIG_PATH

class CapifInvoker:

    def __init__(self, config_path: str)-> None:
        self.config_path: str = config_path
        self.invoker: opencapif_sdk.capif_invoker_connector | None = None
        self.service_discoverer: opencapif_sdk.service_discoverer | None = None

    def startup(self)-> None:
        logging.info("Onboarding new invoker if not onboarded")
        self.invoker = opencapif_sdk.capif_invoker_connector(config_file=self.config_path)

        if not self.__is_onboarded():
            self.invoker.onboard_invoker()
            self.service_discoverer = opencapif_sdk.service_discoverer(config_file=self.config_path)
            api_invoker_id = self.service_discoverer.invoker_capif_details.get("api_invoker_id")
            logging.info(f"New Invoker Onboarded with id {api_invoker_id}")
        else:
            self.service_discoverer = opencapif_sdk.service_discoverer(config_file=self.config_path)

        self.service_discoverer.discover()
        self.service_discoverer.get_tokens()

    def shutdown(self)-> None:
        if not self.invoker:
            logging.warning("Shutdown called but invoker was never initialized")
            return

        if not self.service_discoverer:
            logging.warning("Shutdown called but service discoverer is unavailable; skipping offboarding")
            return

        api_invoker_id = self.service_discoverer.invoker_capif_details.get("api_invoker_id")
        logging.info(f"Offboarding invoker with id {api_invoker_id}")
        self.invoker.offboard_invoker()

    def __is_onboarded(self) -> bool:
        """
        The invoker is onboarded if the capif detail file exists, and you can successfully discover the service APIs
        """
        try:
            capif_detils_path = os.path.join(
                self.invoker.invoker_folder,
                self.invoker.invoker_capif_details_filename
            )
            if not os.path.exists(capif_detils_path):
                logging.info("Capif Details file not found. Invoker not onboarded")
                return False

            self.service_discoverer.discover()
            api_invoker_id = self.service_discoverer.invoker_capif_details.get("api_invoker_id")
            logging.info(f"Invoker already onboarded (id={api_invoker_id})")
            return True
        except Exception as e:
            logging.warning(f"Error during Service Discovery (for checking onboarding). {e}; Invoker may not be onboarded yet.")
            return False

    def get_base_url(self) -> str:
        """
        Get the base URL (host + port) from the CAPIF security context.
        From https://192.168.0.180:443/nef/api/v1/3gpp-monitoring-event/v1/...
        Returns e.g. https://192.168.0.180:443/nef/api/v1/
        """
        contexts = self.service_discoverer.invoker_capif_details["registered_security_contexes"]
        interface = contexts[0]["aef_profiles"][0]["interface_descriptions"][0]
        ip = interface["ipv4_addr"]
        port = interface["port"]

        # Find any URI and extract the common prefix up to the 3gpp- part
        resources = contexts[0]["aef_profiles"][0]["versions"][0]["resources"]
        any_uri = resources[0]["uri"]  # e.g. /nef/api/v1/3gpp-monitoring-event/...
        base_path = any_uri.split("/3gpp-")[0]  # e.g. /nef/api/v1

        return f"https://{ip}:{port}{base_path}"

    def get_service_relative_url(self, *, resource_name: str, api_name_filter: str, operation: str) -> str | None:
        """
        Get the relative URL (path) for a given resource name, optionally filtering by API name.
        From https://192.168.0.180:443/nef/api/v1/3gpp-monitoring-event/v1/...
        Returns e.g. /3gpp-monitoring-event/v1/...
        """
        contexts = self.service_discoverer.invoker_capif_details["registered_security_contexes"]
        resources = contexts[0]["aef_profiles"][0]["versions"][0]["resources"]

        matches = [
            r["uri"] for r in resources
            if r["resource_name"] == resource_name
            and api_name_filter in r["uri"]
            and operation in r["operations"]
        ]
        if not matches:
            logging.warning(f"No resource found with name '{resource_name}', filter '{api_name_filter}', operation '{operation}'")
            return None

        uri = matches[0]
        marker = "/3gpp-"
        idx = uri.find(marker)
        if idx != -1:
            uri = uri[idx:]

        return uri


capif_invoker = CapifInvoker(CAPIF_SDK_CONFIG_PATH)
