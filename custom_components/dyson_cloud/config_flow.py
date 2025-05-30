"""Config flow for Dyson Cloud integration."""

import logging

from libdyson.cloud import REGIONS, DysonAccount
from libdyson.cloud.account import DysonAccountCN
from libdyson.exceptions import (
    DysonInvalidAccountStatus,
    DysonLoginFailure,
    DysonNetworkError,
    DysonOTPTooFrequently,
)
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from .const import CONF_AUTH, CONF_REGION, DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_MOBILE = "mobile"
CONF_OTP = "otp"

DISCOVERY_TIMEOUT = 10


class DysonCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Dyson cloud config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._region = None
        self._mobile = None
        self._email = None
        self._verify = None

    async def async_step_user(self, user_input: dict | None):
        """Handle step initialized by user."""
        if user_input is not None:
            self._region = user_input[CONF_REGION]
            if self._region == "CN":
                return await self.async_step_mobile()
            return await self.async_step_email()

        region_names = {code: f"{name} ({code})" for code, name in REGIONS.items()}
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_REGION): vol.In(region_names)}),
        )

    async def async_step_email(self, info: dict | None = None):
        """Handle step to set email."""
        errors = {}
        if info is not None:
            email = info[CONF_EMAIL]
            unique_id = f"global_{email}"
            for entry in self._async_current_entries():
                if entry.unique_id == unique_id:
                    return self.async_abort(reason="already_configured")
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            account = DysonAccount()
            try:
                self._verify = await self.hass.async_add_executor_job(
                    account.login_email_otp, email, self._region
                )
            except DysonNetworkError:
                errors["base"] = "cannot_connect"
            except DysonInvalidAccountStatus:
                errors["base"] = "email_not_registered"
            else:
                self._email = email
                return await self.async_step_email_otp()

        info = info or {}
        return self.async_show_form(
            step_id="email",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL, default=info.get(CONF_EMAIL, "")): str,
                }
            ),
            errors=errors,
        )

    async def async_step_email_otp(self, info: dict | None = None):
        """Handle step to enter email OTP code."""
        errors = {}
        if info is not None:
            try:
                auth_info = await self.hass.async_add_executor_job(
                    self._verify, info[CONF_OTP], info[CONF_PASSWORD]
                )
            except DysonLoginFailure:
                errors["base"] = "invalid_auth"
            else:
                return self.async_create_entry(
                    title=f"{self._email} ({self._region})",
                    data={
                        CONF_REGION: self._region,
                        CONF_AUTH: auth_info,
                    },
                )

        return self.async_show_form(
            step_id="email_otp",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(CONF_OTP): str,
                }
            ),
            errors=errors,
        )

    async def async_step_mobile(self, info: dict | None = None):
        """Handle step to set mobile number."""
        errors = {}
        if info is not None:
            account = DysonAccountCN()
            mobile = info[CONF_MOBILE]
            if not mobile.startswith("+"):
                mobile = f"+86{mobile}"
            try:
                self._verify = await self.hass.async_add_executor_job(
                    account.login_mobile_otp, mobile
                )
            except DysonOTPTooFrequently:
                errors["base"] = "otp_too_frequent"
            else:
                self._mobile = mobile
                return await self.async_step_mobile_otp()

        info = info or {}
        return self.async_show_form(
            step_id="mobile",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MOBILE, default=info.get(CONF_MOBILE, "")): str,
                }
            ),
            errors=errors,
        )

    async def async_step_mobile_otp(self, info: dict | None = None):
        """Handle step to enter mobile OTP code."""
        errors = {}
        if info is not None:
            try:
                auth_info = await self.hass.async_add_executor_job(
                    self._verify, info[CONF_OTP]
                )
            except DysonLoginFailure:
                errors["base"] = "invalid_otp"
            else:
                return self.async_create_entry(
                    title=f"{self._mobile} ({self._region})",
                    data={
                        CONF_REGION: self._region,
                        CONF_AUTH: auth_info,
                    },
                )

        return self.async_show_form(
            step_id="mobile_otp",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_OTP): str,
                }
            ),
            errors=errors,
        )
