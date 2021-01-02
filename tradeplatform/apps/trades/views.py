from apps.trades.customfilters import (BalanceFilter, InventoryFilter,
                                       OfferFilter, PriceFilter, TradeFilter)
from apps.trades.custompermission import IsOwnerOrReadOnly
from apps.trades.models import (Balance, Currency, Inventory, Item, Offer,
                                Price, Trade, WatchList)
from apps.trades.serializers import (BalanceSerializer, CurrencySerializer,
                                     InventorySerializer, ItemSerializer,
                                     OfferCreateSerializer, OfferSerializer,
                                     PriceCreateSerializer, PriceSerializer,
                                     TradeSerializer,
                                     WatchListCreateSerializer,
                                     WatchListSerializer)
from apps.trades.services.db_interaction import delete_offer_by_id
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly


class CurrencyViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """ViewSet for Currency model"""

    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer

    permission_classes = [IsAuthenticatedOrReadOnly]

    filterset_fields = (
        "name",
        "code",
    )
    search_fields = (
        "^name",
        "^code",
    )
    ordering_fields = (
        "name",
        "code",
    )


class ItemViewSet(viewsets.ModelViewSet):
    """ViewSet for Item model"""

    queryset = Item.objects.all()
    serializer_class = ItemSerializer

    permission_classes = [IsAuthenticatedOrReadOnly]

    filterset_fields = (
        "name",
        "code",
    )
    search_fields = (
        "^name",
        "^code",
    )
    ordering_fields = (
        "name",
        "code",
    )


class PriceViewSet(viewsets.ModelViewSet):
    """ViewSet for Price model"""

    queryset = Price.objects.all()

    filterset_class = PriceFilter
    search_fields = ("^item__code",)
    ordering_fields = (
        "item__code",
        "currency__code",
        "price",
        "date",
    )

    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        """Function return serializer for the certain action"""

        if self.action == "list" or self.action == "retrieve":
            return PriceSerializer
        return PriceCreateSerializer


class WatchListViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """ViewSet for WatchList model"""

    queryset = WatchList.objects.all()

    filterset_fields = ("user__username",)
    search_fields = ("user__username",)
    ordering_fields = ("user__username",)

    permission_classes = [IsOwnerOrReadOnly]

    def get_serializer_class(self):
        """Function return serializer for the certain action"""

        if self.action == "update":
            return WatchListCreateSerializer
        return WatchListSerializer


class OfferViewSet(viewsets.ModelViewSet):
    """ViewSet for Offer model"""

    queryset = Offer.objects.all()
    serializer_class = OfferSerializer

    filterset_class = OfferFilter
    search_fields = ("user__username",)
    ordering_fields = (
        "user__username",
        "price",
        "entry_quantity",
        "quantity",
    )

    permission_classes = [IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        """
        When receive post method, connect offer instance with current user.
        Also will create balance for the user, if it doesn't exist
        """

        user = self.request.user
        serializer.save(user=user)

    def perform_destroy(self, instance):
        """
        When receive delete method, instance won't be deleted from the database.
        Only change is_active field to False
        """

        delete_offer_by_id(offer_id=instance.id)

    def get_serializer_class(self):
        """Function return serializer for the certain action"""

        if self.action == "list" or self.action == "retrieve":
            return OfferSerializer
        return OfferCreateSerializer


class InventoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Inventory model"""

    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer

    filterset_class = InventoryFilter
    search_fields = (
        "user__username",
        "item__code",
    )
    ordering_fields = (
        "user__username",
        "item__code",
        "quantity",
    )


class BalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Balance model"""

    queryset = Balance.objects.all()
    serializer_class = BalanceSerializer

    filterset_class = BalanceFilter
    search_fields = (
        "user__username",
        "currency__code",
    )
    ordering_fields = (
        "user__username",
        "currency__code",
        "quantity",
    )


class TradeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Trade model"""

    queryset = Trade.objects.all()
    serializer_class = TradeSerializer

    filterset_class = TradeFilter
    search_fields = (
        "item__code",
        "seller__username",
        "buyer__username",
    )
    ordering_fields = (
        "item__code",
        "unit_price",
        "quantity",
    )
