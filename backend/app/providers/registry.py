from typing import Dict, List, Optional
from app.providers.base import CloudProviderBase, GPUInstanceInfo
from app.providers.aws_provider import AWSProvider
from app.providers.gcp_provider import GCPProvider
from app.providers.azure_provider import AzureProvider
from app.config import settings


class ProviderRegistry:
    """Manages all cloud provider instances."""

    def __init__(self):
        self._providers: Dict[str, CloudProviderBase] = {}

    def initialize(self) -> None:
        if settings.AWS_ENABLED:
            self._providers["aws"] = AWSProvider(regions=settings.AWS_REGIONS)
        if settings.GCP_ENABLED:
            self._providers["gcp"] = GCPProvider(regions=settings.GCP_REGIONS)
        if settings.AZURE_ENABLED:
            self._providers["azure"] = AzureProvider(regions=settings.AZURE_REGIONS)

    def get(self, provider_name: str) -> Optional[CloudProviderBase]:
        return self._providers.get(provider_name)

    def all(self) -> List[CloudProviderBase]:
        return list(self._providers.values())

    def names(self) -> List[str]:
        return list(self._providers.keys())

    async def list_all_instances(self) -> List[GPUInstanceInfo]:
        all_instances: List[GPUInstanceInfo] = []
        for provider in self._providers.values():
            try:
                instances = await provider.list_available_instances()
                all_instances.extend(instances)
            except Exception:
                pass
        return all_instances

    async def health_check(self) -> Dict[str, bool]:
        results: Dict[str, bool] = {}
        for name, provider in self._providers.items():
            results[name] = await provider.health_check()
        return results


# Singleton registry
provider_registry = ProviderRegistry()
