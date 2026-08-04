import factory

from apps.payouts.models import FolioDistributorMapping
from apps.users.factories import DistributorProfileFactory


class FolioDistributorMappingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FolioDistributorMapping

    folio_number = factory.Sequence(lambda number: f"FOLIO{number:08d}")
    distributor = factory.SubFactory(DistributorProfileFactory)
