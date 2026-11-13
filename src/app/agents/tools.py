from langchain_core.tools import tool

from app.agents.mock_bank import get_device_status, get_transactions, get_user_profile

profile_tool = tool(
    description="Look up a customer profile by user id: name, plan, machine model and account status. Returns null when the user does not exist.",
)(get_user_profile)

transactions_tool = tool(
    description="List a customer's recent card sales with gross/net amounts, sale dates and settlement dates (when the money is deposited). Returns an empty list for unknown users.",
)(get_transactions)

device_tool = tool(
    description="Check the customer's card machine status: model, connectivity, last sync time and last error.",
)(get_device_status)

SUPPORT_TOOLS = [profile_tool, transactions_tool, device_tool]
