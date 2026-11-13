from datetime import date, timedelta

SETTLEMENT_DAYS = {"get_plus": 1, "classic": 2}
FEE_RATE = 0.0299
FIXED_FEE = 0.39

_ACCOUNTS = {
    "cliente1988": {
        "name": "Ana Souza",
        "plan": "get_plus",
        "machine_model": "Get Smart 2",
        "account_status": "active",
    },
    "maria_loja": {
        "name": "Maria Oliveira",
        "plan": "classic",
        "machine_model": "Get Clássica 2",
        "account_status": "active",
    },
    "joao_food": {
        "name": "João Pereira",
        "plan": "classic",
        "machine_model": "Get Tap",
        "account_status": "suspended",
    },
}

_SALES = {
    "cliente1988": [(1, 189.90), (1, 75.00), (3, 320.45), (10, 1299.99)],
    "maria_loja": [(1, 540.10), (2, 96.30), (7, 2100.00)],
    "joao_food": [(1, 88.50), (5, 412.75)],
}

_DEVICES = {
    "cliente1988": {
        "device_model": "Get Smart 2",
        "connectivity": "offline",
        "last_sync_hours_ago": 14,
        "last_error": "WifiAuthenticationError: wrong password",
    },
    "maria_loja": {
        "device_model": "Get Clássica 2",
        "connectivity": "online",
        "last_sync_hours_ago": 1,
        "last_error": None,
    },
    "joao_food": {
        "device_model": "Get Tap",
        "connectivity": "online",
        "last_sync_hours_ago": 3,
        "last_error": None,
    },
}


def get_user_profile(user_id: str) -> dict | None:
    account = _ACCOUNTS.get(user_id)
    if account is None:
        return None
    return dict(account)


def get_transactions(user_id: str) -> list[dict]:
    account = _ACCOUNTS.get(user_id)
    if account is None:
        return []
    settlement_days = SETTLEMENT_DAYS[account["plan"]]
    today = date.today()
    transactions = []
    for i, (days_ago, gross) in enumerate(_SALES[user_id], start=1):
        sale = today - timedelta(days=days_ago)
        settlement = sale + timedelta(days=settlement_days)
        fee = round(gross * FEE_RATE + FIXED_FEE, 2)
        transactions.append(
            {
                "id": f"{user_id}-tx{i:03d}",
                "gross_amount_brl": gross,
                "fee_brl": fee,
                "net_amount_brl": round(gross - fee, 2),
                "sale_date": sale.isoformat(),
                "settlement_date": settlement.isoformat(),
                "status": "settled" if settlement <= today else "pending",
            }
        )
    return transactions


def get_device_status(user_id: str) -> dict | None:
    device = _DEVICES.get(user_id)
    if device is None:
        return None
    out = dict(device)
    out["last_sync_at"] = (date.today() - timedelta(days=1)).isoformat()
    return out
