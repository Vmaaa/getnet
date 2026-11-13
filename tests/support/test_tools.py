from datetime import date, timedelta

from app.agents.mock_bank import get_device_status, get_transactions, get_user_profile

TODAY = date.today()


def test_unknown_user_profile_is_none():
    assert get_user_profile("ghost_user") is None


def test_known_user_profile():
    profile = get_user_profile("cliente1988")
    assert profile["name"] == "Ana Souza"
    assert profile["plan"] == "get_plus"
    assert profile["account_status"] == "active"


def test_transactions_have_settlement_dates():
    transactions = get_transactions("cliente1988")
    assert transactions
    for t in transactions:
        assert t["settlement_date"]
        assert t["sale_date"]
        assert t["net_amount_brl"] < t["gross_amount_brl"]


def test_settlement_follows_plan_rules():
    transactions = get_transactions("cliente1988")
    for t in transactions:
        sale = date.fromisoformat(t["sale_date"])
        settlement = date.fromisoformat(t["settlement_date"])
        assert (settlement - sale).days == 1
    classic = get_transactions("maria_loja")
    for t in classic:
        sale = date.fromisoformat(t["sale_date"])
        settlement = date.fromisoformat(t["settlement_date"])
        assert (settlement - sale).days == 2


def test_yesterday_sales_settlement_today_on_get_plus():
    transactions = get_transactions("cliente1988")
    yesterday_sales = [t for t in transactions if t["sale_date"] == (TODAY - timedelta(days=1)).isoformat()]
    assert yesterday_sales
    assert all(t["settlement_date"] == TODAY.isoformat() for t in yesterday_sales)
    assert all(t["status"] == "settled" for t in yesterday_sales)


def test_device_status_offline_for_cliente1988():
    device = get_device_status("cliente1988")
    assert device["connectivity"] == "offline"
    assert device["last_error"]


def test_transactions_empty_for_unknown_user():
    assert get_transactions("ghost_user") == []
    assert get_device_status("ghost_user") is None
