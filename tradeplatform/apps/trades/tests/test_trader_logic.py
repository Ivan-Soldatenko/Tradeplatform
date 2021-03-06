from apps.trades.models import Inventory, Offer, Trade
from apps.trades.services.db_interaction import (get_available_quantity_stocks,
                                                 get_offer_by_id)
from apps.trades.services.trader_logic import (
    _change_user_balance_by_offer_id, _change_user_inventory_by_offer_id,
    _check_offer_quantity, _confirm_trade, _create_trade, _delete_empty_offer,
    _make_trades, _prepare_for_trade,
    _stocks_quantity_for_trade_by_given_offers, create_trades_between_users)


def test_change_user_balance_by_offer_id(offer_sell_instance):
    """Ensure that function correctly change user balance by the given offer's id and change quantity"""

    current_quantity = offer_sell_instance.user.balance.get().quantity
    change_quantity = 110

    offer_id = offer_sell_instance.id
    _change_user_balance_by_offer_id(offer_id=offer_id, money_quantity=change_quantity)

    user_balance = offer_sell_instance.user.balance.get()

    assert user_balance.quantity == current_quantity + change_quantity


def test_change_user_inventory_by_offer_id_with_not_exist_inventory(
    offer_purchase_instance,
):
    """
    Ensure that function correctly create and change user's inventory, related to offer's item
    With not exist inventory related to the given user and item
    """

    change_quantity = 100

    offer_id = offer_purchase_instance.id
    _change_user_inventory_by_offer_id(offer_id=offer_id, quantity=change_quantity)

    offer = get_offer_by_id(offer_id=offer_id)
    user_inventory = offer.user.inventory.get(item_id=offer.item.id)

    assert user_inventory.quantity == 1000 + change_quantity


def test_change_user_inventory_by_offer_id_with_exist_inventory(
    offer_purchase_instance,
):
    """
    Ensure that function correctly create and change user's inventory, related to offer's item
    With exist inventory related to the given user and item
    """

    current_quantity = 214
    change_quantity = 100

    offer_id = offer_purchase_instance.id
    Inventory.objects.create(
        user=offer_purchase_instance.user,
        item=offer_purchase_instance.item,
        quantity=current_quantity,
    )

    _change_user_inventory_by_offer_id(offer_id=offer_id, quantity=change_quantity)

    user_inventory = offer_purchase_instance.user.inventory.get(
        item_id=offer_purchase_instance.item.id
    )

    assert user_inventory.quantity == current_quantity + change_quantity


def test_stocks_quantity_for_trade_by_given_offers_with_greatest_purchase_quantity(
    offer_instances,
):
    """
    Ensure that function return correct stocks quantity for trade.
    Since purchase offer has more quantity of stocks than sell offer.
    Function has to return sell offer quantity of stocks.
    """

    purchase_offer = offer_instances[0]
    sell_offer = offer_instances[4]

    final_quantity = _stocks_quantity_for_trade_by_given_offers(
        sell_offer_id=sell_offer.id, purchase_offer_id=purchase_offer.id
    )

    assert final_quantity == get_available_quantity_stocks(offer_id=sell_offer.id)


def test_stocks_quantity_for_trade_by_given_offers_with_equal_quantity(offer_instances):
    """
    Ensure that function return correct stocks quantity for trade.
    Since purchase offer and sell offers have equal quantity of stocks,
    Function has to return sell offer and purchase offer quantity of stocks.
    """

    purchase_offer = offer_instances[0]
    sell_offer = offer_instances[6]

    final_quantity = _stocks_quantity_for_trade_by_given_offers(
        sell_offer_id=sell_offer.id, purchase_offer_id=purchase_offer.id
    )

    assert final_quantity == get_available_quantity_stocks(offer_id=sell_offer.id)
    assert final_quantity == get_available_quantity_stocks(offer_id=purchase_offer.id)


def test_stocks_quantity_for_trade_by_given_offers_with_greatest_sell_quantity(
    offer_instances,
):
    """
    Ensure that function return correct stocks quantity for trade.
    Since sell offer has more quantity of stocks than purchase offer.
    Function has to return purchase offer quantity of stocks.
    """

    purchase_offer_id = offer_instances[0].id
    sell_offer_id = offer_instances[5].id

    final_quantity = _stocks_quantity_for_trade_by_given_offers(
        sell_offer_id=sell_offer_id, purchase_offer_id=purchase_offer_id
    )

    assert final_quantity == get_available_quantity_stocks(offer_id=purchase_offer_id)


def test_prepare_for_trade(offer_purchase_instance):
    """Ensure that function correctly change user's and offer's attributes"""

    user = offer_purchase_instance.user
    current_money_quantity = user.balance.get().quantity
    current_offer_quantity = offer_purchase_instance.quantity
    money_quantity = 5443
    quantity = 3141

    offer_id = offer_purchase_instance.id

    _prepare_for_trade(
        offer_id=offer_id, money_quantity=money_quantity, quantity=quantity
    )

    user = offer_purchase_instance.user
    user_balance = user.balance.get()
    user_inventory = user.inventory.get(item_id=offer_purchase_instance.item)

    assert user_balance.quantity == current_money_quantity + money_quantity
    assert user_inventory.quantity == 1000 + quantity
    assert Offer.objects.get().quantity == current_offer_quantity + quantity


def test_check_offer_quantity_with_remaining_stocks(offer_sell_instance):
    """
    Ensure that function return right boolean response
    Since offer has the remaining stocks, function has to return False
    """

    result = _check_offer_quantity(offer_id=offer_sell_instance.id)

    assert result == False


def test_check_offer_quantity_without_remaining_stocks(offer_sell_instance):
    """
    Ensure that function return right boolean response
    Since offer hasn't the remaining stocks, function has to return True
    """

    offer_sell_instance.quantity = offer_sell_instance.entry_quantity
    offer_sell_instance.save()

    result = _check_offer_quantity(offer_id=offer_sell_instance.id)

    assert result == True


def test_delete_empty_offer_with_remaining_stocks(offer_purchase_instance):
    """
    Ensure that function return right boolean response and delete offer in right situations
    Since offer has the remaining stocks, function has to return False and hasn't to delete offer
    """

    result = _delete_empty_offer(offer_id=offer_purchase_instance.id)

    assert result == False
    assert Offer.objects.get().is_active == True


def test_delete_empty_offer_without_remaining_stocks(offer_purchase_instance):
    """
    Ensure that function return right boolean response and delete offer in right situations
    Since offer hasn't the remaining stocks, function has to return True and has to delete offer
    """

    offer_purchase_instance.quantity = offer_purchase_instance.entry_quantity
    offer_purchase_instance.save()

    result = _delete_empty_offer(offer_id=offer_purchase_instance.id)

    assert result == True
    assert Offer.objects.get().is_active == False


def test_create_trade_with_equal_quantity_stocks(offer_instances):
    """
    Ensure that function correctly create Trade instance by the given offers
    """

    purchase_offer = offer_instances[0]
    sell_offer = offer_instances[6]

    buyer = purchase_offer.user
    seller = sell_offer.user

    original_buyer_balance = buyer.balance.get().quantity
    original_seller_balance = seller.balance.get().quantity

    correct_quantity = get_available_quantity_stocks(offer_id=sell_offer.id)

    _create_trade(sell_offer_id=sell_offer.id, purchase_offer_id=purchase_offer.id)

    trade = Trade.objects.get()

    buyer_balance = buyer.balance.get().quantity
    buyer_inventory = buyer.inventory.get(item_id=purchase_offer.item).quantity

    seller_balance = seller.balance.get().quantity
    seller_inventory = seller.inventory.get(item_id=purchase_offer.item).quantity

    assert trade.item == purchase_offer.item
    assert trade.item == sell_offer.item
    assert trade.seller == sell_offer.user
    assert trade.buyer == purchase_offer.user
    assert trade.quantity == correct_quantity
    assert trade.unit_price == sell_offer.price
    assert (
        trade.description
        == f"Trade between {sell_offer.user.username} and {purchase_offer.user.username}"
    )
    assert trade.seller_offer == sell_offer
    assert trade.buyer_offer == purchase_offer
    assert buyer_balance == original_buyer_balance - (trade.unit_price * trade.quantity)
    assert seller_balance == original_seller_balance + (
        trade.unit_price * trade.quantity
    )
    assert buyer_inventory == 1000 - trade.quantity
    assert seller_inventory == 1000 + trade.quantity


def test_confirm_trade_with_equal_stocks_quantity(offer_instances):
    """
    Ensure that function create correct trade instance and delete right offer instances
    Since offers has equal quantity of stocks, function has to delete both offers
    """

    purchase_offer = offer_instances[0]
    sell_offer = offer_instances[6]

    buyer = purchase_offer.user
    seller = sell_offer.user

    correct_quantity = get_available_quantity_stocks(offer_id=sell_offer.id)

    original_buyer_balance = buyer.balance.get().quantity
    original_seller_balance = seller.balance.get().quantity

    _confirm_trade(sell_offer_id=sell_offer.id, purchase_offer_id=purchase_offer.id)

    buyer_balance = buyer.balance.get().quantity
    buyer_inventory = buyer.inventory.get(item_id=purchase_offer.item).quantity

    seller_balance = seller.balance.get().quantity
    seller_inventory = seller.inventory.get(item_id=purchase_offer.item).quantity

    trade = Trade.objects.get()

    assert Trade.objects.count() == 1
    assert Offer.objects.get(id=purchase_offer.id).is_active == False
    assert Offer.objects.get(id=sell_offer.id).is_active == False

    assert trade.item == purchase_offer.item
    assert trade.item == sell_offer.item
    assert trade.seller == sell_offer.user
    assert trade.buyer == purchase_offer.user
    assert trade.quantity == correct_quantity
    assert trade.unit_price == sell_offer.price
    assert (
        trade.description
        == f"Trade between {sell_offer.user.username} and {purchase_offer.user.username}"
    )
    assert trade.seller_offer == sell_offer
    assert trade.buyer_offer == purchase_offer
    assert buyer_balance == original_buyer_balance - (trade.unit_price * trade.quantity)
    assert seller_balance == original_seller_balance + (
        trade.unit_price * trade.quantity
    )
    assert buyer_inventory == 1000 - trade.quantity
    assert seller_inventory == 1000 + trade.quantity


def test_confirm_trade_with_greatest_sell_stocks_quantity(offer_instances):
    """
    Ensure that function create correct trade instance and delete right offer instances
    Since sell offer has more quantity of stocks than purchase offer, function has to delete purchase offer
    """

    purchase_offer = offer_instances[0]
    sell_offer = offer_instances[5]

    buyer = purchase_offer.user
    seller = sell_offer.user

    correct_quantity = get_available_quantity_stocks(offer_id=purchase_offer.id)

    original_buyer_balance = buyer.balance.get().quantity
    original_seller_balance = seller.balance.get().quantity

    _confirm_trade(sell_offer_id=sell_offer.id, purchase_offer_id=purchase_offer.id)

    buyer_balance = buyer.balance.get().quantity
    buyer_inventory = buyer.inventory.get(item_id=purchase_offer.item).quantity

    seller_balance = seller.balance.get().quantity
    seller_inventory = seller.inventory.get(item_id=purchase_offer.item).quantity

    trade = Trade.objects.get()

    assert Trade.objects.count() == 1
    assert Offer.objects.get(id=purchase_offer.id).is_active == False
    assert Offer.objects.get(id=sell_offer.id).is_active == True

    assert trade.item == purchase_offer.item
    assert trade.item == sell_offer.item
    assert trade.seller == sell_offer.user
    assert trade.buyer == purchase_offer.user
    assert trade.quantity == correct_quantity
    assert trade.unit_price == sell_offer.price
    assert (
        trade.description
        == f"Trade between {sell_offer.user.username} and {purchase_offer.user.username}"
    )
    assert trade.seller_offer == sell_offer
    assert trade.buyer_offer == purchase_offer
    assert buyer_balance == original_buyer_balance - (trade.unit_price * trade.quantity)
    assert seller_balance == original_seller_balance + (
        trade.unit_price * trade.quantity
    )
    assert buyer_inventory == 1000 - trade.quantity
    assert seller_inventory == 1000 + trade.quantity


def test_confirm_trade_with_greatest_purchase_stocks_quantity(offer_instances):
    """
    Ensure that function create correct trade instance and delete right offer instances
    Since purchase offer has more quantity of stocks than sell offer, function has to delete sell offer
    """

    purchase_offer = offer_instances[0]
    sell_offer = offer_instances[3]

    buyer = purchase_offer.user
    seller = sell_offer.user

    correct_quantity = get_available_quantity_stocks(offer_id=sell_offer.id)

    original_buyer_balance = buyer.balance.get().quantity
    original_seller_balance = seller.balance.get().quantity

    _confirm_trade(sell_offer_id=sell_offer.id, purchase_offer_id=purchase_offer.id)

    buyer_balance = buyer.balance.get().quantity
    buyer_inventory = buyer.inventory.get(item_id=purchase_offer.item).quantity

    seller_balance = seller.balance.get().quantity
    seller_inventory = seller.inventory.get(item_id=purchase_offer.item).quantity

    trade = Trade.objects.get()

    assert Trade.objects.count() == 1
    assert Offer.objects.get(id=purchase_offer.id).is_active == True
    assert Offer.objects.get(id=sell_offer.id).is_active == False

    assert trade.item == purchase_offer.item
    assert trade.item == sell_offer.item
    assert trade.seller == sell_offer.user
    assert trade.buyer == purchase_offer.user
    assert trade.quantity == correct_quantity
    assert trade.unit_price == sell_offer.price
    assert (
        trade.description
        == f"Trade between {sell_offer.user.username} and {purchase_offer.user.username}"
    )
    assert trade.seller_offer == sell_offer
    assert trade.buyer_offer == purchase_offer
    assert buyer_balance == original_buyer_balance - (trade.unit_price * trade.quantity)
    assert seller_balance == original_seller_balance + (
        trade.unit_price * trade.quantity
    )
    assert buyer_inventory == 1000 - trade.quantity
    assert seller_inventory == 1000 + trade.quantity


def test_make_trades_with_greatest_purchase_stocks(offer_instances):
    """
    Ensure that function create right trade instances
    Since purchase offer has more quantity of stocks than one sell offer
    Function has to create 2 trade instances with different sell offer instances
    And delete purchase offer and first sell offer
    """

    purchase_offer = offer_instances[0]
    sell_offer_1 = offer_instances[3]
    sell_offer_2 = offer_instances[5]

    current_purchase_quantity = get_available_quantity_stocks(
        offer_id=purchase_offer.id
    )
    current_sell_quantity_1 = get_available_quantity_stocks(offer_id=sell_offer_1.id)
    current_sell_quantity_2 = get_available_quantity_stocks(offer_id=sell_offer_2.id)

    correct_quantity_1 = current_sell_quantity_1
    correct_quantity_2 = current_purchase_quantity - correct_quantity_1

    _make_trades(offer_id=purchase_offer.id)

    trade_1 = Trade.objects.first()
    trade_2 = Trade.objects.last()

    assert Trade.objects.count() == 2
    assert Offer.objects.get(id=purchase_offer.id).is_active == False
    assert Offer.objects.get(id=sell_offer_1.id).is_active == False
    assert Offer.objects.get(id=sell_offer_2.id).is_active == True

    assert trade_1.seller_offer == sell_offer_1
    assert trade_1.buyer_offer == purchase_offer
    assert trade_1.quantity == correct_quantity_1
    assert trade_1.unit_price == sell_offer_1.price
    assert get_available_quantity_stocks(offer_id=sell_offer_1.id) == 0

    assert trade_2.seller_offer == sell_offer_2
    assert trade_2.buyer_offer == purchase_offer
    assert trade_2.quantity == correct_quantity_2
    assert trade_2.unit_price == sell_offer_2.price
    assert (
        get_available_quantity_stocks(offer_id=sell_offer_2.id)
        == current_sell_quantity_2 - trade_2.quantity
    )
    assert get_available_quantity_stocks(offer_id=purchase_offer.id) == 0


def test_make_trades_with_equal_stocks(offer_instances):
    """
    Ensure that function create right trade instance
    Since purchase offer and sell offer have equal quantity of stocks
    Function has to create trade instance and delete both offers
    """

    purchase_offer = offer_instances[0]
    sell_offer = offer_instances[3]
    sell_offer.quantity = purchase_offer.quantity
    sell_offer.entry_quantity = purchase_offer.entry_quantity
    sell_offer.save()

    correct_quantity = get_available_quantity_stocks(offer_id=purchase_offer.id)

    _make_trades(offer_id=purchase_offer.id)

    trade = Trade.objects.get()

    assert Trade.objects.count() == 1
    assert Offer.objects.get(id=purchase_offer.id).is_active == False
    assert Offer.objects.get(id=sell_offer.id).is_active == False

    assert trade.seller_offer == sell_offer
    assert trade.buyer_offer == purchase_offer
    assert trade.quantity == correct_quantity
    assert trade.unit_price == sell_offer.price

    assert get_available_quantity_stocks(offer_id=sell_offer.id) == 0
    assert get_available_quantity_stocks(offer_id=purchase_offer.id) == 0


def test_make_trades_with_greatest_sell_stocks(offer_instances):
    """
    Ensure that function create right trade instance
    Since sell offer has more quantity of stocks than purchase offer
    Function has to create trade instance and delete purchase offer
    """

    purchase_offer = offer_instances[0]
    sell_offer = offer_instances[3]
    sell_offer.quantity = purchase_offer.quantity
    sell_offer.entry_quantity = purchase_offer.entry_quantity + 70
    sell_offer.save()

    correct_available_quantity = get_available_quantity_stocks(
        offer_id=sell_offer.id
    ) - get_available_quantity_stocks(offer_id=purchase_offer.id)
    correct_quantity = get_available_quantity_stocks(offer_id=purchase_offer.id)

    _make_trades(offer_id=purchase_offer.id)

    trade = Trade.objects.get()

    assert Trade.objects.count() == 1
    assert Offer.objects.get(id=purchase_offer.id).is_active == False
    assert Offer.objects.get(id=sell_offer.id).is_active == True

    assert trade.seller_offer == sell_offer
    assert trade.buyer_offer == purchase_offer
    assert trade.quantity == correct_quantity
    assert trade.unit_price == sell_offer.price

    assert get_available_quantity_stocks(offer_id=purchase_offer.id) == 0
    assert (
        get_available_quantity_stocks(offer_id=sell_offer.id)
        == correct_available_quantity
    )


def test_create_trades_between_users(offer_instances):
    """Ensure that function find suitable offers and create right trade instances between them"""

    purchase_offer_1 = offer_instances[0]
    purchase_offer_2 = offer_instances[7]

    sell_offer_1 = offer_instances[3]
    sell_offer_2 = offer_instances[5]
    sell_offer_3 = offer_instances[8]

    create_trades_between_users()

    trades_purchase_1 = Trade.objects.all().filter(buyer_offer__id=purchase_offer_1.id)
    trades_purchase_2 = Trade.objects.all().filter(buyer_offer__id=purchase_offer_2.id)

    assert trades_purchase_1.count() == 2
    assert trades_purchase_2.count() == 2

    assert trades_purchase_1[0].seller_offer == sell_offer_1
    assert trades_purchase_1[1].seller_offer == sell_offer_2
    assert Offer.objects.get(id=sell_offer_1.id).is_active == False
    assert Offer.objects.get(id=sell_offer_2.id).is_active == True
    assert Offer.objects.get(id=purchase_offer_1.id).is_active == False

    assert trades_purchase_2[0].seller_offer == sell_offer_3
    assert trades_purchase_2[1].seller_offer == sell_offer_2
    assert Offer.objects.get(id=sell_offer_3.id).is_active == False
    assert Offer.objects.get(id=sell_offer_2.id).is_active == True
    assert Offer.objects.get(id=purchase_offer_2.id).is_active == False


def test_create_trades_between_users_with_greatest_purchase_quantity(
    offer_purchase_instance, offer_sell_instance, user_instances
):
    """
    Ensure that function create right trade instances and correctly delete offer instance
    Since purchase offer has more quantity than sell offer
    Function has to create 1 trade instance and delete sell offer instance
    """

    offer_sell_instance.user = user_instances[1]
    offer_sell_instance.item = offer_purchase_instance.item
    offer_sell_instance.price = offer_purchase_instance.price - 2
    offer_sell_instance.save()

    create_trades_between_users()

    trade = Trade.objects.get()

    assert Trade.objects.count() == 1
    assert trade.buyer_offer == offer_purchase_instance
    assert trade.seller_offer == offer_sell_instance
    assert Offer.objects.get(id=offer_purchase_instance.id).is_active == True
    assert Offer.objects.get(id=offer_sell_instance.id).is_active == False


def test_create_trades_between_users_with_greatest_sell_quantity(
    offer_purchase_instance, offer_sell_instance, user_instances
):
    """
    Ensure that function create right trade instances and correctly delete offer instance
    Since sell offer has more quantity than purchase offer
    Function has to create 1 trade instance and delete purchase offer instance
    """

    offer_sell_instance.user = user_instances[1]
    offer_sell_instance.entry_quantity = 150
    offer_sell_instance.item = offer_purchase_instance.item
    offer_sell_instance.price = offer_purchase_instance.price - 2
    offer_sell_instance.save()

    create_trades_between_users()

    trade = Trade.objects.get()

    assert Trade.objects.count() == 1
    assert trade.buyer_offer == offer_purchase_instance
    assert trade.seller_offer == offer_sell_instance
    assert Offer.objects.get(id=offer_purchase_instance.id).is_active == False
    assert Offer.objects.get(id=offer_sell_instance.id).is_active == True
