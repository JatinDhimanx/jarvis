"""External API integrations matching 08_ACTION_ENGINE.md, 09_TOOL_REGISTRY.md, and 20_DEVELOPER_CONTRACT.md."""

from typing import Any, Dict, List, Optional
import urllib.parse
from jarvis.core.errors import ErrorCode, JarvisError
from jarvis.policy.safety import RiskLevel
from jarvis.registry.registry import Availability, ToolDeclaration, ToolRegistry


class ExternalAPIClient:
    """Client for querying authorized external web APIs with network error handling."""

    def __init__(self, is_online: bool = True, allowed_domains: Optional[List[str]] = None):
        self.is_online = is_online
        self.allowed_domains = allowed_domains or ["api.weather.com", "api.github.com", "api.openai.com"]
        self.last_weather_request: Optional[Dict[str, Any]] = None
        self.last_api_response: Optional[Dict[str, Any]] = None
        self.fail_next_verification: bool = False

    def get_weather(self, location: str) -> Dict[str, Any]:
        """Fetch current weather for location."""
        clean_loc = location.strip()
        if not clean_loc:
            raise JarvisError(ErrorCode.E100, "Location cannot be empty")

        if not self.is_online:
            raise JarvisError(ErrorCode.E600, "Weather service unavailable: network offline")

        data = {
            "location": clean_loc,
            "temperature_c": 22,
            "condition": "Partly Cloudy",
            "humidity": 55,
        }
        self.last_weather_request = data
        return data

    def verify_weather(self, location: str) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return self.last_weather_request is not None and self.last_weather_request.get("location") == location.strip()

    def fetch_api(self, endpoint_url: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute safe external HTTP request against whitelisted domain."""
        if not self.is_online:
            raise JarvisError(ErrorCode.E600, "API call failed: network offline")

        parsed = urllib.parse.urlparse(endpoint_url.strip())
        if parsed.scheme.lower() not in {"http", "https"}:
            raise JarvisError(ErrorCode.E400, f"Unsupported scheme in '{endpoint_url}'")

        if parsed.netloc.lower() not in self.allowed_domains:
            raise JarvisError(ErrorCode.E400, f"Domain '{parsed.netloc}' is not in allowed API domains")

        response = {
            "status_code": 200,
            "endpoint": endpoint_url,
            "method": method.upper(),
            "data": {"message": "Success", "echo_payload": payload or {}},
        }
        self.last_api_response = response
        return response

    def verify_api_call(self, endpoint_url: str) -> bool:
        if self.fail_next_verification:
            self.fail_next_verification = False
            return False
        return self.last_api_response is not None and self.last_api_response.get("endpoint") == endpoint_url.strip()


def register_api_tools(registry: ToolRegistry, client: Optional[ExternalAPIClient] = None) -> ExternalAPIClient:
    """Register external API tools declaring all 10 mandatory fields per 09_TOOL_REGISTRY.md."""
    api_client = client or ExternalAPIClient()

    # 1. get_weather
    registry.register_tool(
        ToolDeclaration(
            name="get_weather",
            version=1,
            description="Fetch current weather forecast for location",
            input_schema={"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]},
            output_schema={"type": "object", "properties": {"location": {"type": "string"}, "temperature_c": {"type": "number"}, "condition": {"type": "string"}}},
            risk_level=RiskLevel.LOW,
            required_permissions=["network"],
            availability=Availability.ONLINE,
            reversible=True,
            verification_method="verify_weather",
        ),
        handler=lambda location="", **kw: api_client.get_weather(location),
        verifier=lambda location="", **kw: api_client.verify_weather(location),
    )

    # 2. fetch_api
    registry.register_tool(
        ToolDeclaration(
            name="fetch_api",
            version=1,
            description="Send safe HTTP request to authorized external REST API",
            input_schema={"type": "object", "properties": {"endpoint_url": {"type": "string"}, "method": {"type": "string"}}, "required": ["endpoint_url"]},
            output_schema={"type": "object", "properties": {"status_code": {"type": "integer"}, "data": {"type": "object"}}},
            risk_level=RiskLevel.LOW,
            required_permissions=["network"],
            availability=Availability.ONLINE,
            reversible=True,
            verification_method="verify_api_call",
        ),
        handler=lambda endpoint_url="", method="GET", payload=None, **kw: api_client.fetch_api(endpoint_url, method, payload),
        verifier=lambda endpoint_url="", **kw: api_client.verify_api_call(endpoint_url),
    )

    return api_client
