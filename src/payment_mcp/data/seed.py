"""Seed data for custom-payment-mcp."""

from payment_mcp.models.customer import Customer, CustomerStatus
from payment_mcp.models.payment import Payment, PaymentStatus

SEED_CUSTOMERS: list[Customer] = [
    Customer(
        customer_id="CUS-001",
        name="John Tan",
        country="SG",
        status=CustomerStatus.ACTIVE,
    ),
    Customer(
        customer_id="CUS-002",
        name="Mary Lim",
        country="SG",
        status=CustomerStatus.ACTIVE,
    ),
]

SEED_PAYMENTS: list[Payment] = [
    Payment(
        payment_id="PAY-1001",
        customer_id="CUS-001",
        amount=250.00,
        currency="SGD",
        status=PaymentStatus.DECLINED,
        merchant="APPLE",
        decline_code="05",
    ),
    Payment(
        payment_id="PAY-1002",
        customer_id="CUS-002",
        amount=50.00,
        currency="SGD",
        status=PaymentStatus.SETTLED,
        merchant="NETFLIX",
        decline_code=None,
    ),
    Payment(
        payment_id="PAY-1003",
        customer_id="CUS-001",
        amount=1200.00,
        currency="SGD",
        status=PaymentStatus.DECLINED,
        merchant="ELECTRONICS STORE",
        decline_code="51",
    ),
]

DECLINE_CODE_POLICIES: dict[str, str] = {
    "05": (
        "Do not honor - The issuing bank has declined the transaction without specific reason. "
        "Direct customer to contact card issuer."
    ),
    "51": (
        "Insufficient funds - The cardholder account does not have sufficient available balance "
        "or credit line."
    ),
    "14": (
        "Invalid card number - The primary account number fails Luhn validation or does not exist "
        "at issuing bank."
    ),
    "54": (
        "Expired card - The payment card expiration date has passed or was transmitted incorrectly."
    ),
    "57": (
        "Transaction not permitted - The cardholder or issuing bank prohibits this transaction "
        "type, merchant category, or international processing."
    ),
}

DECLINE_CODE_POLICY_DOCUMENT = """PAYMENT DECLINE CODE POLICIES & RESOLUTION GUIDELINES

05 - Do not honor
Issuer general decline. Direct customer to contact card issuer for authorization.

51 - Insufficient funds
Customer account lacks funds or credit limit. Advise alternative payment or balance reload.

14 - Invalid card number
Card number failed checksum or routing. Customer should re-enter card details.

54 - Expired card
Card is expired. Customer must update expiration date or provide a valid card.

57 - Transaction not permitted
Issuer restrictions apply (cross-border, online, or MCC restriction). Cardholder must contact bank.
"""
