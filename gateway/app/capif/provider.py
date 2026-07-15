import logging
import os

import opencapif_sdk
import yaml
from fastapi import FastAPI
from requests import RequestException

from app.capif import CAPIF_SDK_CONFIG_PATH
from app.settings import settings


class CapifProvider:

    def __init__(self, config_path: str):
        self.config_path: str = config_path
        self.capif_cert_pem_path: str | None = None
        self.provider: opencapif_sdk.capif_provider_connector | None = None
        self.logging_feature: opencapif_sdk.capif_logging_feature | None = None
        self.api_name = "gsma-open-gateway"
        # api_name is extracted using translator.build() from the base url (<host>:<port>/<apiName>/v<version>)
        # It cannot be changed without changing the url
        self.base_url = f"{str(settings.gateway_public_url).rstrip('/')}/{self.api_name}/v1"

    def startup(self, gateway_app: FastAPI) -> None:
        logging.info("Starting CAPIF provider")
        self.provider = opencapif_sdk.capif_provider_connector(config_file=self.config_path)
        is_onboarded = self.__is_onboarded()

        logging.info(f"CAPIF provider is onboarded: {is_onboarded}")
        if not is_onboarded:
            self.provider.onboard_provider()
            logging.info("CAPIF provider onboarded.")

        self.capif_cert_pem_path = os.path.join(self.provider.provider_folder, "capif_cert_server.pem")

        # Onboarding and service publishing are two separate steps that can succeed
        # independently (e.g. a crash between the two) - so publishing must be
        # checked and (re)attempted on its own, not skipped just because the
        # provider itself is already onboarded.
        if self.__is_published():
            logging.info("Skipping CAPIF service publishing; already published.")
        else:
            # Get the gateway OpenAPI schema and translate it to CAPIF format
            openapi_schema_name = "gateway_openapi"
            openapi_schema_spec = gateway_app.openapi()
            with open(f"{openapi_schema_name}.yaml", "w") as f:
                yaml.dump(openapi_schema_spec, f, allow_unicode=True, sort_keys=False)
            translator = opencapif_sdk.api_schema_translator(f"./{openapi_schema_name}.yaml")
            translator.build(
                url=self.base_url,
                supported_features="0", api_supp_features="0"
            )
            self.provider.api_description_path = f"./{self.api_name}.json"
            self.__publish_services()

        # capif_logging_feature requires the service to already be published
        # (it reads provider_service_ids.json), so it must be constructed last.
        self.logging_feature = opencapif_sdk.capif_logging_feature(config_file=self.config_path)

    def shutdown(self) -> None:
        logging.info("Shutting down CAPIF provider...")

        if settings.capif_sdk.cleanup_on_shutdown and self.provider and self.__is_onboarded():
            logging.info("Offboarding CAPIF provider and unpublishing services...")
            self.provider.publish_req['service_api_id'] = self.provider.provider_service_ids[self.api_name]
            self.provider.publish_req['publisher_apf_id'] = self.provider.provider_capif_ids['APF-1']
            self.provider.publish_req['publisher_aefs_ids'] = [self.provider.provider_capif_ids['AEF-1']]
            self.provider.unpublish_service()
            self.provider.offboard_provider()
            logging.info("CAPIF provider offboarded.")

    def __publish_services(self) -> None:
        logging.info("Publishing gateway services to CAPIF...")
        APF1 = self.provider.provider_capif_ids['APF-1']
        AEF1 = self.provider.provider_capif_ids['AEF-1']
        self.provider.publish_req['publisher_apf_id'] = APF1
        self.provider.publish_req['publisher_aefs_ids'] = [AEF1]
        try:
            self.provider.publish_services()
        except RequestException as e:
            logging.warning(f"SDK Request to CAPIF failed: {e} - Response: {e.response.text}")
            details = e.response.json()
            if details.get("status") != 403 or details.get("detail") != "Already registered service with same api name":
                logging.error("Unexpected error during service publication. Terminating...")
                raise

    def __is_onboarded(self) -> bool:
        return bool(self.provider is not None and self.provider.provider_capif_ids)

    def __is_published(self) -> bool:
        return os.path.exists(os.path.join(self.provider.provider_folder, "provider_service_ids.json"))


capif_provider = CapifProvider(config_path=CAPIF_SDK_CONFIG_PATH)
