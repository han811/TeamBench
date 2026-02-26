"""
Parameterized generator for CR5: Test Coverage - Add Tests for Uncovered Paths.

TNI Pattern A (hidden constraints): Brief says "increase test coverage."
Spec lists exact uncovered branches/paths with expected behavior for each.

Each seed produces:
- A different module type (payment, inventory, scheduler, parser)
- A Python module with good functionality but sparse tests (happy paths only)
- 5-8 specific uncovered paths listed in spec with expected behavior
- Buggy variants of the module (one mutation per uncovered path) for mutation testing

The agent sees: brief.md (vague), spec.md (exact uncovered paths + expected behavior),
                workspace/<module>.py (correct implementation), workspace/test_<module>.py (sparse)
The grader uses: buggy variants to verify each new test catches the mutation.
"""
from __future__ import annotations

import textwrap
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ---------------------------------------------------------------------------
# Module pool — each entry defines a complete module with uncoverable paths
# ---------------------------------------------------------------------------

MODULE_POOL = [
    # ── payment ──────────────────────────────────────────────────────────────
    {
        "module_name": "payment",
        "display_name": "Payment Processor",
        "description": "processes payment transactions with validation and error handling",
        "module_src": '''\
"""
Payment processor module.

Handles payment transactions including validation, processing, and refunds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


class PaymentError(Exception):
    """Raised when a payment operation fails."""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass
class Card:
    number: str
    expiry_month: int
    expiry_year: int
    cvv: str
    holder: str


@dataclass
class Transaction:
    transaction_id: str
    amount: float
    currency: str
    status: str = "pending"
    refunded_amount: float = 0.0


class PaymentProcessor:
    """Processes payment transactions."""

    SUPPORTED_CURRENCIES = {"USD", "EUR", "GBP", "JPY"}
    MAX_AMOUNT = 100_000.0
    MIN_AMOUNT = 0.01

    def __init__(self):
        self._transactions: dict[str, Transaction] = {}
        self._next_id = 1

    def _generate_id(self) -> str:
        tid = f"TXN{self._next_id:06d}"
        self._next_id += 1
        return tid

    def _validate_card(self, card: Card) -> None:
        """Validate card details. Raises PaymentError on invalid card."""
        if not card.number or len(card.number.replace(" ", "")) < 13:
            raise PaymentError("invalid_card_number", "Card number too short")
        if not card.cvv or len(card.cvv) not in (3, 4):
            raise PaymentError("invalid_cvv", "CVV must be 3 or 4 digits")
        if not card.holder or not card.holder.strip():
            raise PaymentError("invalid_holder", "Card holder name required")

    def _validate_expiry(self, card: Card, current_year: int, current_month: int) -> None:
        """Validate card expiry. Raises PaymentError if card is expired."""
        if card.expiry_year < current_year:
            raise PaymentError("card_expired", "Card has expired")
        if card.expiry_year == current_year and card.expiry_month < current_month:
            raise PaymentError("card_expired", "Card has expired")

    def _validate_amount(self, amount: float, currency: str) -> None:
        """Validate payment amount and currency."""
        if currency not in self.SUPPORTED_CURRENCIES:
            raise PaymentError("unsupported_currency", f"Currency {currency!r} not supported")
        if amount < self.MIN_AMOUNT:
            raise PaymentError("amount_too_small", f"Minimum amount is {self.MIN_AMOUNT}")
        if amount > self.MAX_AMOUNT:
            raise PaymentError("amount_too_large", f"Maximum amount is {self.MAX_AMOUNT}")

    def charge(
        self,
        card: Card,
        amount: float,
        currency: str = "USD",
        current_year: int = 2024,
        current_month: int = 1,
    ) -> Transaction:
        """
        Charge a card. Returns a completed Transaction on success.
        Raises PaymentError for validation failures.
        """
        self._validate_card(card)
        self._validate_expiry(card, current_year, current_month)
        self._validate_amount(amount, currency)

        tid = self._generate_id()
        txn = Transaction(
            transaction_id=tid,
            amount=amount,
            currency=currency,
            status="completed",
        )
        self._transactions[tid] = txn
        return txn

    def refund(self, transaction_id: str, amount: Optional[float] = None) -> Transaction:
        """
        Refund a transaction (full or partial).
        Raises PaymentError if transaction not found, already fully refunded,
        or refund amount exceeds remaining balance.
        """
        txn = self._transactions.get(transaction_id)
        if txn is None:
            raise PaymentError("transaction_not_found", f"No transaction {transaction_id!r}")
        if txn.status == "refunded":
            raise PaymentError("already_refunded", "Transaction fully refunded")

        refund_amount = amount if amount is not None else txn.amount
        remaining = txn.amount - txn.refunded_amount
        if refund_amount > remaining:
            raise PaymentError(
                "refund_exceeds_balance",
                f"Refund {refund_amount} exceeds remaining {remaining}",
            )

        txn.refunded_amount += refund_amount
        if txn.refunded_amount >= txn.amount:
            txn.status = "refunded"
        else:
            txn.status = "partially_refunded"
        return txn

    def get_transaction(self, transaction_id: str) -> Transaction:
        """Retrieve a transaction by ID. Raises PaymentError if not found."""
        txn = self._transactions.get(transaction_id)
        if txn is None:
            raise PaymentError("transaction_not_found", f"No transaction {transaction_id!r}")
        return txn
''',
        "happy_test_src": '''\
"""Tests for payment processor — happy path only."""
import pytest
from payment import PaymentProcessor, Card, PaymentError


@pytest.fixture
def processor():
    return PaymentProcessor()


@pytest.fixture
def valid_card():
    return Card(
        number="4111111111111111",
        expiry_month=12,
        expiry_year=2026,
        cvv="123",
        holder="Alice Smith",
    )


def test_charge_success(processor, valid_card):
    txn = processor.charge(valid_card, 50.0, "USD", current_year=2024, current_month=1)
    assert txn.status == "completed"
    assert txn.amount == 50.0
    assert txn.currency == "USD"


def test_full_refund(processor, valid_card):
    txn = processor.charge(valid_card, 100.0, "USD", current_year=2024, current_month=1)
    refunded = processor.refund(txn.transaction_id)
    assert refunded.status == "refunded"
    assert refunded.refunded_amount == 100.0
''',
        "paths": [
            {
                "path_id": "expired_card",
                "title": "charge() raises PaymentError when card is expired",
                "description": (
                    "When the card's expiry year is before the current year, "
                    "or the expiry month is before the current month in the same year, "
                    "`charge()` must raise `PaymentError` with code `'card_expired'`."
                ),
                "examples": [
                    "Card expiry 06/2023, current date 01/2024 → PaymentError('card_expired')",
                    "Card expiry 01/2024, current date 03/2024 → PaymentError('card_expired')",
                    "Card expiry 12/2024, current date 12/2024 → completes (same month OK)",
                ],
                "func_name": "_validate_expiry",
                "fixed_body": '''\
    def _validate_expiry(self, card: Card, current_year: int, current_month: int) -> None:
        """Validate card expiry. Raises PaymentError if card is expired."""
        if card.expiry_year < current_year:
            raise PaymentError("card_expired", "Card has expired")
        if card.expiry_year == current_year and card.expiry_month < current_month:
            raise PaymentError("card_expired", "Card has expired")
''',
                "buggy_body": '''\
    def _validate_expiry(self, card: Card, current_year: int, current_month: int) -> None:
        """Validate card expiry. Raises PaymentError if card is expired."""
        if card.expiry_year < current_year:
            raise PaymentError("card_expired", "Card has expired")
        # BUG: month check omitted — expired cards in current year not caught
''',
            },
            {
                "path_id": "unsupported_currency",
                "title": "charge() raises PaymentError for unsupported currency",
                "description": (
                    "`charge()` must raise `PaymentError` with code `'unsupported_currency'` "
                    "when the currency string is not in the supported set "
                    "(USD, EUR, GBP, JPY)."
                ),
                "examples": [
                    "currency='CHF' → PaymentError('unsupported_currency')",
                    "currency='BTC' → PaymentError('unsupported_currency')",
                    "currency='USD' → no error",
                ],
                "func_name": "_validate_amount",
                "fixed_body": '''\
    def _validate_amount(self, amount: float, currency: str) -> None:
        """Validate payment amount and currency."""
        if currency not in self.SUPPORTED_CURRENCIES:
            raise PaymentError("unsupported_currency", f"Currency {currency!r} not supported")
        if amount < self.MIN_AMOUNT:
            raise PaymentError("amount_too_small", f"Minimum amount is {self.MIN_AMOUNT}")
        if amount > self.MAX_AMOUNT:
            raise PaymentError("amount_too_large", f"Maximum amount is {self.MAX_AMOUNT}")
''',
                "buggy_body": '''\
    def _validate_amount(self, amount: float, currency: str) -> None:
        """Validate payment amount and currency."""
        # BUG: currency check skipped
        if amount < self.MIN_AMOUNT:
            raise PaymentError("amount_too_small", f"Minimum amount is {self.MIN_AMOUNT}")
        if amount > self.MAX_AMOUNT:
            raise PaymentError("amount_too_large", f"Maximum amount is {self.MAX_AMOUNT}")
''',
            },
            {
                "path_id": "amount_too_small",
                "title": "charge() raises PaymentError when amount is below minimum",
                "description": (
                    "`charge()` must raise `PaymentError` with code `'amount_too_small'` "
                    "when the amount is less than `MIN_AMOUNT` (0.01)."
                ),
                "examples": [
                    "amount=0.0 → PaymentError('amount_too_small')",
                    "amount=0.005 → PaymentError('amount_too_small')",
                    "amount=0.01 → no error (boundary is inclusive)",
                ],
                "func_name": "_validate_amount",
                "fixed_body": '''\
    def _validate_amount(self, amount: float, currency: str) -> None:
        """Validate payment amount and currency."""
        if currency not in self.SUPPORTED_CURRENCIES:
            raise PaymentError("unsupported_currency", f"Currency {currency!r} not supported")
        if amount < self.MIN_AMOUNT:
            raise PaymentError("amount_too_small", f"Minimum amount is {self.MIN_AMOUNT}")
        if amount > self.MAX_AMOUNT:
            raise PaymentError("amount_too_large", f"Maximum amount is {self.MAX_AMOUNT}")
''',
                "buggy_body": '''\
    def _validate_amount(self, amount: float, currency: str) -> None:
        """Validate payment amount and currency."""
        if currency not in self.SUPPORTED_CURRENCIES:
            raise PaymentError("unsupported_currency", f"Currency {currency!r} not supported")
        # BUG: minimum amount check skipped
        if amount > self.MAX_AMOUNT:
            raise PaymentError("amount_too_large", f"Maximum amount is {self.MAX_AMOUNT}")
''',
            },
            {
                "path_id": "amount_too_large",
                "title": "charge() raises PaymentError when amount exceeds maximum",
                "description": (
                    "`charge()` must raise `PaymentError` with code `'amount_too_large'` "
                    "when the amount exceeds `MAX_AMOUNT` (100,000.0)."
                ),
                "examples": [
                    "amount=100_000.01 → PaymentError('amount_too_large')",
                    "amount=200_000.0 → PaymentError('amount_too_large')",
                    "amount=100_000.0 → no error (boundary is inclusive)",
                ],
                "func_name": "_validate_amount",
                "fixed_body": '''\
    def _validate_amount(self, amount: float, currency: str) -> None:
        """Validate payment amount and currency."""
        if currency not in self.SUPPORTED_CURRENCIES:
            raise PaymentError("unsupported_currency", f"Currency {currency!r} not supported")
        if amount < self.MIN_AMOUNT:
            raise PaymentError("amount_too_small", f"Minimum amount is {self.MIN_AMOUNT}")
        if amount > self.MAX_AMOUNT:
            raise PaymentError("amount_too_large", f"Maximum amount is {self.MAX_AMOUNT}")
''',
                "buggy_body": '''\
    def _validate_amount(self, amount: float, currency: str) -> None:
        """Validate payment amount and currency."""
        if currency not in self.SUPPORTED_CURRENCIES:
            raise PaymentError("unsupported_currency", f"Currency {currency!r} not supported")
        if amount < self.MIN_AMOUNT:
            raise PaymentError("amount_too_small", f"Minimum amount is {self.MIN_AMOUNT}")
        # BUG: maximum amount check skipped
''',
            },
            {
                "path_id": "already_refunded",
                "title": "refund() raises PaymentError when transaction already fully refunded",
                "description": (
                    "`refund()` must raise `PaymentError` with code `'already_refunded'` "
                    "when called on a transaction whose status is `'refunded'`."
                ),
                "examples": [
                    "Fully refund txn, then refund again → PaymentError('already_refunded')",
                    "Partially refund (status 'partially_refunded'), then refund again → no error",
                ],
                "func_name": "refund",
                "fixed_body": '''\
    def refund(self, transaction_id: str, amount=None) -> Transaction:
        """Refund a transaction (full or partial)."""
        txn = self._transactions.get(transaction_id)
        if txn is None:
            raise PaymentError("transaction_not_found", f"No transaction {transaction_id!r}")
        if txn.status == "refunded":
            raise PaymentError("already_refunded", "Transaction fully refunded")
        refund_amount = amount if amount is not None else txn.amount
        remaining = txn.amount - txn.refunded_amount
        if refund_amount > remaining:
            raise PaymentError("refund_exceeds_balance", f"Refund {refund_amount} exceeds remaining {remaining}")
        txn.refunded_amount += refund_amount
        if txn.refunded_amount >= txn.amount:
            txn.status = "refunded"
        else:
            txn.status = "partially_refunded"
        return txn
''',
                "buggy_body": '''\
    def refund(self, transaction_id: str, amount=None) -> Transaction:
        """Refund a transaction (full or partial)."""
        txn = self._transactions.get(transaction_id)
        if txn is None:
            raise PaymentError("transaction_not_found", f"No transaction {transaction_id!r}")
        # BUG: already_refunded check omitted
        refund_amount = amount if amount is not None else txn.amount
        remaining = txn.amount - txn.refunded_amount
        if refund_amount > remaining:
            raise PaymentError("refund_exceeds_balance", f"Refund {refund_amount} exceeds remaining {remaining}")
        txn.refunded_amount += refund_amount
        if txn.refunded_amount >= txn.amount:
            txn.status = "refunded"
        else:
            txn.status = "partially_refunded"
        return txn
''',
            },
            {
                "path_id": "refund_exceeds_balance",
                "title": "refund() raises PaymentError when partial refund exceeds remaining balance",
                "description": (
                    "`refund()` must raise `PaymentError` with code `'refund_exceeds_balance'` "
                    "when the requested refund amount exceeds the remaining non-refunded amount."
                ),
                "examples": [
                    "Charge $100, partial refund $60, then refund $50 → PaymentError('refund_exceeds_balance')",
                    "Charge $100, refund $100.01 → PaymentError('refund_exceeds_balance')",
                    "Charge $100, refund $50 → OK (status='partially_refunded')",
                ],
                "func_name": "refund",
                "fixed_body": '''\
    def refund(self, transaction_id: str, amount=None) -> Transaction:
        """Refund a transaction (full or partial)."""
        txn = self._transactions.get(transaction_id)
        if txn is None:
            raise PaymentError("transaction_not_found", f"No transaction {transaction_id!r}")
        if txn.status == "refunded":
            raise PaymentError("already_refunded", "Transaction fully refunded")
        refund_amount = amount if amount is not None else txn.amount
        remaining = txn.amount - txn.refunded_amount
        if refund_amount > remaining:
            raise PaymentError("refund_exceeds_balance", f"Refund {refund_amount} exceeds remaining {remaining}")
        txn.refunded_amount += refund_amount
        if txn.refunded_amount >= txn.amount:
            txn.status = "refunded"
        else:
            txn.status = "partially_refunded"
        return txn
''',
                "buggy_body": '''\
    def refund(self, transaction_id: str, amount=None) -> Transaction:
        """Refund a transaction (full or partial)."""
        txn = self._transactions.get(transaction_id)
        if txn is None:
            raise PaymentError("transaction_not_found", f"No transaction {transaction_id!r}")
        if txn.status == "refunded":
            raise PaymentError("already_refunded", "Transaction fully refunded")
        refund_amount = amount if amount is not None else txn.amount
        remaining = txn.amount - txn.refunded_amount
        # BUG: refund_exceeds_balance check skipped
        txn.refunded_amount += refund_amount
        if txn.refunded_amount >= txn.amount:
            txn.status = "refunded"
        else:
            txn.status = "partially_refunded"
        return txn
''',
            },
            {
                "path_id": "transaction_not_found",
                "title": "get_transaction() raises PaymentError for unknown transaction IDs",
                "description": (
                    "`get_transaction()` must raise `PaymentError` with code "
                    "`'transaction_not_found'` when called with a transaction ID that "
                    "was never created."
                ),
                "examples": [
                    "get_transaction('TXN999999') → PaymentError('transaction_not_found')",
                    "get_transaction('') → PaymentError('transaction_not_found')",
                    "After charge, get_transaction(txn.transaction_id) → returns Transaction",
                ],
                "func_name": "get_transaction",
                "fixed_body": '''\
    def get_transaction(self, transaction_id: str) -> Transaction:
        """Retrieve a transaction by ID. Raises PaymentError if not found."""
        txn = self._transactions.get(transaction_id)
        if txn is None:
            raise PaymentError("transaction_not_found", f"No transaction {transaction_id!r}")
        return txn
''',
                "buggy_body": '''\
    def get_transaction(self, transaction_id: str) -> Transaction:
        """Retrieve a transaction by ID. Raises PaymentError if not found."""
        # BUG: returns None instead of raising
        return self._transactions.get(transaction_id)
''',
            },
            {
                "path_id": "partial_refund_status",
                "title": "refund() sets status to 'partially_refunded' for partial refunds",
                "description": (
                    "When a refund is partial (less than the full transaction amount), "
                    "`refund()` must set the transaction status to `'partially_refunded'` "
                    "and accumulate `refunded_amount` correctly."
                ),
                "examples": [
                    "Charge $100, refund $30 → status='partially_refunded', refunded_amount=30.0",
                    "Charge $100, refund $50, refund $50 → status='refunded', refunded_amount=100.0",
                    "Charge $100, refund $100 → status='refunded'",
                ],
                "func_name": "refund",
                "fixed_body": '''\
    def refund(self, transaction_id: str, amount=None) -> Transaction:
        """Refund a transaction (full or partial)."""
        txn = self._transactions.get(transaction_id)
        if txn is None:
            raise PaymentError("transaction_not_found", f"No transaction {transaction_id!r}")
        if txn.status == "refunded":
            raise PaymentError("already_refunded", "Transaction fully refunded")
        refund_amount = amount if amount is not None else txn.amount
        remaining = txn.amount - txn.refunded_amount
        if refund_amount > remaining:
            raise PaymentError("refund_exceeds_balance", f"Refund {refund_amount} exceeds remaining {remaining}")
        txn.refunded_amount += refund_amount
        if txn.refunded_amount >= txn.amount:
            txn.status = "refunded"
        else:
            txn.status = "partially_refunded"
        return txn
''',
                "buggy_body": '''\
    def refund(self, transaction_id: str, amount=None) -> Transaction:
        """Refund a transaction (full or partial)."""
        txn = self._transactions.get(transaction_id)
        if txn is None:
            raise PaymentError("transaction_not_found", f"No transaction {transaction_id!r}")
        if txn.status == "refunded":
            raise PaymentError("already_refunded", "Transaction fully refunded")
        refund_amount = amount if amount is not None else txn.amount
        remaining = txn.amount - txn.refunded_amount
        if refund_amount > remaining:
            raise PaymentError("refund_exceeds_balance", f"Refund {refund_amount} exceeds remaining {remaining}")
        txn.refunded_amount += refund_amount
        # BUG: always sets to "refunded" even for partial refunds
        txn.status = "refunded"
        return txn
''',
            },
        ],
    },

    # ── inventory ────────────────────────────────────────────────────────────
    {
        "module_name": "inventory",
        "display_name": "Inventory Manager",
        "description": "manages product stock levels with reservations and adjustments",
        "module_src": '''\
"""
Inventory manager module.

Tracks product stock with support for reservations, releases, and adjustments.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


class InventoryError(Exception):
    """Raised when an inventory operation fails."""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass
class Product:
    product_id: str
    name: str
    quantity: int
    reserved: int = 0
    reorder_threshold: int = 10

    @property
    def available(self) -> int:
        return self.quantity - self.reserved


class InventoryManager:
    """Manages product stock levels."""

    def __init__(self):
        self._products: dict[str, Product] = {}

    def add_product(self, product_id: str, name: str, quantity: int, reorder_threshold: int = 10) -> Product:
        """Add a new product. Raises InventoryError if product already exists or quantity negative."""
        if product_id in self._products:
            raise InventoryError("product_exists", f"Product {product_id!r} already exists")
        if quantity < 0:
            raise InventoryError("negative_quantity", "Initial quantity cannot be negative")
        product = Product(product_id=product_id, name=name, quantity=quantity, reorder_threshold=reorder_threshold)
        self._products[product_id] = product
        return product

    def reserve(self, product_id: str, quantity: int) -> Product:
        """
        Reserve stock for an order.
        Raises InventoryError if product not found, quantity <= 0,
        or insufficient available stock.
        """
        product = self._products.get(product_id)
        if product is None:
            raise InventoryError("product_not_found", f"No product {product_id!r}")
        if quantity <= 0:
            raise InventoryError("invalid_quantity", "Quantity must be positive")
        if quantity > product.available:
            raise InventoryError(
                "insufficient_stock",
                f"Only {product.available} units available, requested {quantity}",
            )
        product.reserved += quantity
        return product

    def release(self, product_id: str, quantity: int) -> Product:
        """
        Release previously reserved stock.
        Raises InventoryError if product not found, quantity <= 0,
        or release exceeds reserved amount.
        """
        product = self._products.get(product_id)
        if product is None:
            raise InventoryError("product_not_found", f"No product {product_id!r}")
        if quantity <= 0:
            raise InventoryError("invalid_quantity", "Quantity must be positive")
        if quantity > product.reserved:
            raise InventoryError(
                "release_exceeds_reserved",
                f"Cannot release {quantity}, only {product.reserved} reserved",
            )
        product.reserved -= quantity
        return product

    def adjust_stock(self, product_id: str, delta: int) -> Product:
        """
        Adjust stock quantity by delta (positive = restock, negative = shrinkage).
        Raises InventoryError if product not found or resulting quantity would go
        below reserved level.
        """
        product = self._products.get(product_id)
        if product is None:
            raise InventoryError("product_not_found", f"No product {product_id!r}")
        new_quantity = product.quantity + delta
        if new_quantity < product.reserved:
            raise InventoryError(
                "quantity_below_reserved",
                f"Cannot reduce to {new_quantity}, {product.reserved} units reserved",
            )
        product.quantity = new_quantity
        return product

    def needs_reorder(self, product_id: str) -> bool:
        """
        Return True if available stock is at or below reorder_threshold.
        Raises InventoryError if product not found.
        """
        product = self._products.get(product_id)
        if product is None:
            raise InventoryError("product_not_found", f"No product {product_id!r}")
        return product.available <= product.reorder_threshold

    def get_product(self, product_id: str) -> Product:
        """Retrieve a product. Raises InventoryError if not found."""
        product = self._products.get(product_id)
        if product is None:
            raise InventoryError("product_not_found", f"No product {product_id!r}")
        return product
''',
        "happy_test_src": '''\
"""Tests for inventory manager — happy path only."""
import pytest
from inventory import InventoryManager, InventoryError


@pytest.fixture
def manager():
    return InventoryManager()


def test_add_product(manager):
    p = manager.add_product("P001", "Widget", 100)
    assert p.product_id == "P001"
    assert p.quantity == 100
    assert p.available == 100


def test_reserve_success(manager):
    manager.add_product("P001", "Widget", 50)
    p = manager.reserve("P001", 10)
    assert p.reserved == 10
    assert p.available == 40


def test_release_success(manager):
    manager.add_product("P001", "Widget", 50)
    manager.reserve("P001", 20)
    p = manager.release("P001", 10)
    assert p.reserved == 10
''',
        "paths": [
            {
                "path_id": "product_exists",
                "title": "add_product() raises InventoryError when product already exists",
                "description": (
                    "`add_product()` must raise `InventoryError` with code `'product_exists'` "
                    "when called with a `product_id` that was already added."
                ),
                "examples": [
                    "add_product('P1', 'A', 10), then add_product('P1', 'B', 5) → InventoryError('product_exists')",
                    "add_product('P1', 'A', 10), then add_product('P2', 'B', 5) → OK",
                ],
                "func_name": "add_product",
                "fixed_body": '''\
    def add_product(self, product_id: str, name: str, quantity: int, reorder_threshold: int = 10) -> Product:
        """Add a new product. Raises InventoryError if product already exists or quantity negative."""
        if product_id in self._products:
            raise InventoryError("product_exists", f"Product {product_id!r} already exists")
        if quantity < 0:
            raise InventoryError("negative_quantity", "Initial quantity cannot be negative")
        product = Product(product_id=product_id, name=name, quantity=quantity, reorder_threshold=reorder_threshold)
        self._products[product_id] = product
        return product
''',
                "buggy_body": '''\
    def add_product(self, product_id: str, name: str, quantity: int, reorder_threshold: int = 10) -> Product:
        """Add a new product. Raises InventoryError if product already exists or quantity negative."""
        # BUG: duplicate product check omitted
        if quantity < 0:
            raise InventoryError("negative_quantity", "Initial quantity cannot be negative")
        product = Product(product_id=product_id, name=name, quantity=quantity, reorder_threshold=reorder_threshold)
        self._products[product_id] = product
        return product
''',
            },
            {
                "path_id": "negative_quantity",
                "title": "add_product() raises InventoryError for negative initial quantity",
                "description": (
                    "`add_product()` must raise `InventoryError` with code `'negative_quantity'` "
                    "when the initial `quantity` argument is less than zero."
                ),
                "examples": [
                    "add_product('P1', 'A', -1) → InventoryError('negative_quantity')",
                    "add_product('P1', 'A', 0) → OK (zero is valid)",
                    "add_product('P1', 'A', 100) → OK",
                ],
                "func_name": "add_product",
                "fixed_body": '''\
    def add_product(self, product_id: str, name: str, quantity: int, reorder_threshold: int = 10) -> Product:
        """Add a new product. Raises InventoryError if product already exists or quantity negative."""
        if product_id in self._products:
            raise InventoryError("product_exists", f"Product {product_id!r} already exists")
        if quantity < 0:
            raise InventoryError("negative_quantity", "Initial quantity cannot be negative")
        product = Product(product_id=product_id, name=name, quantity=quantity, reorder_threshold=reorder_threshold)
        self._products[product_id] = product
        return product
''',
                "buggy_body": '''\
    def add_product(self, product_id: str, name: str, quantity: int, reorder_threshold: int = 10) -> Product:
        """Add a new product. Raises InventoryError if product already exists or quantity negative."""
        if product_id in self._products:
            raise InventoryError("product_exists", f"Product {product_id!r} already exists")
        # BUG: negative quantity check omitted
        product = Product(product_id=product_id, name=name, quantity=quantity, reorder_threshold=reorder_threshold)
        self._products[product_id] = product
        return product
''',
            },
            {
                "path_id": "insufficient_stock",
                "title": "reserve() raises InventoryError when available stock is insufficient",
                "description": (
                    "`reserve()` must raise `InventoryError` with code `'insufficient_stock'` "
                    "when the requested quantity exceeds `product.available` (quantity minus already reserved)."
                ),
                "examples": [
                    "add_product('P1', 'A', 5), reserve('P1', 6) → InventoryError('insufficient_stock')",
                    "add_product('P1', 'A', 10), reserve('P1', 5), reserve('P1', 6) → InventoryError('insufficient_stock')",
                    "add_product('P1', 'A', 10), reserve('P1', 10) → OK (exact available)",
                ],
                "func_name": "reserve",
                "fixed_body": '''\
    def reserve(self, product_id: str, quantity: int) -> Product:
        """Reserve stock for an order."""
        product = self._products.get(product_id)
        if product is None:
            raise InventoryError("product_not_found", f"No product {product_id!r}")
        if quantity <= 0:
            raise InventoryError("invalid_quantity", "Quantity must be positive")
        if quantity > product.available:
            raise InventoryError("insufficient_stock", f"Only {product.available} units available, requested {quantity}")
        product.reserved += quantity
        return product
''',
                "buggy_body": '''\
    def reserve(self, product_id: str, quantity: int) -> Product:
        """Reserve stock for an order."""
        product = self._products.get(product_id)
        if product is None:
            raise InventoryError("product_not_found", f"No product {product_id!r}")
        if quantity <= 0:
            raise InventoryError("invalid_quantity", "Quantity must be positive")
        # BUG: insufficient_stock check omitted
        product.reserved += quantity
        return product
''',
            },
            {
                "path_id": "invalid_quantity",
                "title": "reserve() raises InventoryError for zero or negative quantity",
                "description": (
                    "`reserve()` must raise `InventoryError` with code `'invalid_quantity'` "
                    "when the quantity is zero or negative."
                ),
                "examples": [
                    "reserve('P1', 0) → InventoryError('invalid_quantity')",
                    "reserve('P1', -5) → InventoryError('invalid_quantity')",
                    "reserve('P1', 1) → OK",
                ],
                "func_name": "reserve",
                "fixed_body": '''\
    def reserve(self, product_id: str, quantity: int) -> Product:
        """Reserve stock for an order."""
        product = self._products.get(product_id)
        if product is None:
            raise InventoryError("product_not_found", f"No product {product_id!r}")
        if quantity <= 0:
            raise InventoryError("invalid_quantity", "Quantity must be positive")
        if quantity > product.available:
            raise InventoryError("insufficient_stock", f"Only {product.available} units available, requested {quantity}")
        product.reserved += quantity
        return product
''',
                "buggy_body": '''\
    def reserve(self, product_id: str, quantity: int) -> Product:
        """Reserve stock for an order."""
        product = self._products.get(product_id)
        if product is None:
            raise InventoryError("product_not_found", f"No product {product_id!r}")
        # BUG: invalid_quantity check omitted
        if quantity > product.available:
            raise InventoryError("insufficient_stock", f"Only {product.available} units available, requested {quantity}")
        product.reserved += quantity
        return product
''',
            },
            {
                "path_id": "release_exceeds_reserved",
                "title": "release() raises InventoryError when release amount exceeds reserved",
                "description": (
                    "`release()` must raise `InventoryError` with code `'release_exceeds_reserved'` "
                    "when the release quantity exceeds the current `product.reserved` amount."
                ),
                "examples": [
                    "reserve 5 units, release 6 → InventoryError('release_exceeds_reserved')",
                    "reserve 5, release 5 → OK (exact match)",
                    "reserve 10, release 3, release 8 → InventoryError('release_exceeds_reserved')",
                ],
                "func_name": "release",
                "fixed_body": '''\
    def release(self, product_id: str, quantity: int) -> Product:
        """Release previously reserved stock."""
        product = self._products.get(product_id)
        if product is None:
            raise InventoryError("product_not_found", f"No product {product_id!r}")
        if quantity <= 0:
            raise InventoryError("invalid_quantity", "Quantity must be positive")
        if quantity > product.reserved:
            raise InventoryError("release_exceeds_reserved", f"Cannot release {quantity}, only {product.reserved} reserved")
        product.reserved -= quantity
        return product
''',
                "buggy_body": '''\
    def release(self, product_id: str, quantity: int) -> Product:
        """Release previously reserved stock."""
        product = self._products.get(product_id)
        if product is None:
            raise InventoryError("product_not_found", f"No product {product_id!r}")
        if quantity <= 0:
            raise InventoryError("invalid_quantity", "Quantity must be positive")
        # BUG: release_exceeds_reserved check omitted
        product.reserved -= quantity
        return product
''',
            },
            {
                "path_id": "quantity_below_reserved",
                "title": "adjust_stock() raises InventoryError when stock would drop below reserved",
                "description": (
                    "`adjust_stock()` must raise `InventoryError` with code `'quantity_below_reserved'` "
                    "when a negative delta would make `quantity` drop below the `reserved` count."
                ),
                "examples": [
                    "quantity=20, reserved=15, adjust(-10) → InventoryError('quantity_below_reserved') (20-10=10 < 15)",
                    "quantity=20, reserved=10, adjust(-10) → OK (20-10=10 == 10)",
                    "quantity=20, reserved=0, adjust(-20) → OK (down to 0)",
                ],
                "func_name": "adjust_stock",
                "fixed_body": '''\
    def adjust_stock(self, product_id: str, delta: int) -> Product:
        """Adjust stock quantity by delta."""
        product = self._products.get(product_id)
        if product is None:
            raise InventoryError("product_not_found", f"No product {product_id!r}")
        new_quantity = product.quantity + delta
        if new_quantity < product.reserved:
            raise InventoryError("quantity_below_reserved", f"Cannot reduce to {new_quantity}, {product.reserved} units reserved")
        product.quantity = new_quantity
        return product
''',
                "buggy_body": '''\
    def adjust_stock(self, product_id: str, delta: int) -> Product:
        """Adjust stock quantity by delta."""
        product = self._products.get(product_id)
        if product is None:
            raise InventoryError("product_not_found", f"No product {product_id!r}")
        # BUG: below-reserved check omitted
        product.quantity += delta
        return product
''',
            },
            {
                "path_id": "needs_reorder_boundary",
                "title": "needs_reorder() returns True when available stock equals reorder_threshold",
                "description": (
                    "`needs_reorder()` must return `True` when `available <= reorder_threshold`. "
                    "The boundary condition (`available == reorder_threshold`) must also return `True`."
                ),
                "examples": [
                    "quantity=10, reserved=0, reorder_threshold=10 → needs_reorder() returns True (at boundary)",
                    "quantity=11, reserved=0, reorder_threshold=10 → needs_reorder() returns False",
                    "quantity=5, reserved=0, reorder_threshold=10 → needs_reorder() returns True",
                ],
                "func_name": "needs_reorder",
                "fixed_body": '''\
    def needs_reorder(self, product_id: str) -> bool:
        """Return True if available stock is at or below reorder_threshold."""
        product = self._products.get(product_id)
        if product is None:
            raise InventoryError("product_not_found", f"No product {product_id!r}")
        return product.available <= product.reorder_threshold
''',
                "buggy_body": '''\
    def needs_reorder(self, product_id: str) -> bool:
        """Return True if available stock is at or below reorder_threshold."""
        product = self._products.get(product_id)
        if product is None:
            raise InventoryError("product_not_found", f"No product {product_id!r}")
        # BUG: strict less-than excludes boundary case
        return product.available < product.reorder_threshold
''',
            },
            {
                "path_id": "product_not_found",
                "title": "get_product() raises InventoryError for unknown product IDs",
                "description": (
                    "`get_product()` must raise `InventoryError` with code `'product_not_found'` "
                    "when called with a product ID that does not exist."
                ),
                "examples": [
                    "get_product('NONEXISTENT') → InventoryError('product_not_found')",
                    "add_product('P1', 'A', 10), get_product('P1') → returns Product",
                ],
                "func_name": "get_product",
                "fixed_body": '''\
    def get_product(self, product_id: str) -> Product:
        """Retrieve a product. Raises InventoryError if not found."""
        product = self._products.get(product_id)
        if product is None:
            raise InventoryError("product_not_found", f"No product {product_id!r}")
        return product
''',
                "buggy_body": '''\
    def get_product(self, product_id: str) -> Product:
        """Retrieve a product. Raises InventoryError if not found."""
        # BUG: returns None instead of raising
        return self._products.get(product_id)
''',
            },
        ],
    },

    # ── scheduler ─────────────────────────────────────────────────────────────
    {
        "module_name": "scheduler",
        "display_name": "Task Scheduler",
        "description": "schedules and manages recurring tasks with priority queuing",
        "module_src": '''\
"""
Task scheduler module.

Schedules tasks with priorities, intervals, and retry logic.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional


class SchedulerError(Exception):
    """Raised when a scheduler operation fails."""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass
class Task:
    task_id: str
    name: str
    interval_seconds: float
    priority: int  # 1 (highest) to 10 (lowest)
    max_retries: int = 3
    retry_count: int = 0
    enabled: bool = True
    last_run: Optional[float] = None
    run_count: int = 0


class TaskScheduler:
    """Manages scheduled tasks."""

    MAX_TASKS = 100
    MIN_INTERVAL = 1.0    # seconds
    MAX_INTERVAL = 86400.0  # 24 hours

    def __init__(self):
        self._tasks: dict[str, Task] = {}

    def add_task(
        self,
        task_id: str,
        name: str,
        interval_seconds: float,
        priority: int = 5,
        max_retries: int = 3,
    ) -> Task:
        """
        Register a new task.
        Raises SchedulerError if task_id already exists, interval out of range,
        priority out of [1,10], or scheduler is at capacity.
        """
        if task_id in self._tasks:
            raise SchedulerError("task_exists", f"Task {task_id!r} already registered")
        if len(self._tasks) >= self.MAX_TASKS:
            raise SchedulerError("scheduler_full", f"Cannot exceed {self.MAX_TASKS} tasks")
        if interval_seconds < self.MIN_INTERVAL or interval_seconds > self.MAX_INTERVAL:
            raise SchedulerError(
                "invalid_interval",
                f"Interval must be between {self.MIN_INTERVAL} and {self.MAX_INTERVAL} seconds",
            )
        if priority < 1 or priority > 10:
            raise SchedulerError("invalid_priority", "Priority must be between 1 and 10")
        task = Task(
            task_id=task_id,
            name=name,
            interval_seconds=interval_seconds,
            priority=priority,
            max_retries=max_retries,
        )
        self._tasks[task_id] = task
        return task

    def remove_task(self, task_id: str) -> None:
        """Remove a task. Raises SchedulerError if task not found."""
        if task_id not in self._tasks:
            raise SchedulerError("task_not_found", f"No task {task_id!r}")
        del self._tasks[task_id]

    def record_run(self, task_id: str, success: bool, timestamp: Optional[float] = None) -> Task:
        """
        Record a task execution result.
        On success: resets retry_count, increments run_count.
        On failure: increments retry_count. If retry_count > max_retries, disables task.
        Raises SchedulerError if task not found.
        """
        task = self._tasks.get(task_id)
        if task is None:
            raise SchedulerError("task_not_found", f"No task {task_id!r}")
        task.last_run = timestamp if timestamp is not None else time.time()
        task.run_count += 1
        if success:
            task.retry_count = 0
        else:
            task.retry_count += 1
            if task.retry_count > task.max_retries:
                task.enabled = False
        return task

    def get_due_tasks(self, current_time: float) -> list[Task]:
        """
        Return all enabled tasks that are due (never run, or last_run + interval <= current_time),
        sorted by priority ascending (1 = highest priority first).
        """
        due = []
        for task in self._tasks.values():
            if not task.enabled:
                continue
            if task.last_run is None or (task.last_run + task.interval_seconds) <= current_time:
                due.append(task)
        due.sort(key=lambda t: t.priority)
        return due

    def enable_task(self, task_id: str) -> Task:
        """Enable a task and reset its retry count. Raises SchedulerError if not found."""
        task = self._tasks.get(task_id)
        if task is None:
            raise SchedulerError("task_not_found", f"No task {task_id!r}")
        task.enabled = True
        task.retry_count = 0
        return task

    def get_task(self, task_id: str) -> Task:
        """Retrieve a task. Raises SchedulerError if not found."""
        task = self._tasks.get(task_id)
        if task is None:
            raise SchedulerError("task_not_found", f"No task {task_id!r}")
        return task
''',
        "happy_test_src": '''\
"""Tests for task scheduler — happy path only."""
import pytest
from scheduler import TaskScheduler, SchedulerError


@pytest.fixture
def scheduler():
    return TaskScheduler()


def test_add_task(scheduler):
    task = scheduler.add_task("T1", "Daily Job", 3600.0, priority=3)
    assert task.task_id == "T1"
    assert task.interval_seconds == 3600.0
    assert task.enabled is True


def test_record_run_success(scheduler):
    scheduler.add_task("T1", "Job", 60.0)
    task = scheduler.record_run("T1", success=True, timestamp=1000.0)
    assert task.run_count == 1
    assert task.retry_count == 0
    assert task.last_run == 1000.0


def test_get_due_tasks(scheduler):
    scheduler.add_task("T1", "Job", 60.0)
    due = scheduler.get_due_tasks(current_time=0.0)
    assert len(due) == 1
''',
        "paths": [
            {
                "path_id": "task_exists",
                "title": "add_task() raises SchedulerError when task_id already registered",
                "description": (
                    "`add_task()` must raise `SchedulerError` with code `'task_exists'` "
                    "when the given `task_id` is already in the scheduler."
                ),
                "examples": [
                    "add_task('T1', ...), add_task('T1', ...) → SchedulerError('task_exists')",
                    "add_task('T1', ...), add_task('T2', ...) → OK",
                ],
                "func_name": "add_task",
                "fixed_body": '''\
    def add_task(self, task_id, name, interval_seconds, priority=5, max_retries=3):
        if task_id in self._tasks:
            raise SchedulerError("task_exists", f"Task {task_id!r} already registered")
        if len(self._tasks) >= self.MAX_TASKS:
            raise SchedulerError("scheduler_full", f"Cannot exceed {self.MAX_TASKS} tasks")
        if interval_seconds < self.MIN_INTERVAL or interval_seconds > self.MAX_INTERVAL:
            raise SchedulerError("invalid_interval", f"Interval must be between {self.MIN_INTERVAL} and {self.MAX_INTERVAL} seconds")
        if priority < 1 or priority > 10:
            raise SchedulerError("invalid_priority", "Priority must be between 1 and 10")
        task = Task(task_id=task_id, name=name, interval_seconds=interval_seconds, priority=priority, max_retries=max_retries)
        self._tasks[task_id] = task
        return task
''',
                "buggy_body": '''\
    def add_task(self, task_id, name, interval_seconds, priority=5, max_retries=3):
        # BUG: task_exists check omitted
        if len(self._tasks) >= self.MAX_TASKS:
            raise SchedulerError("scheduler_full", f"Cannot exceed {self.MAX_TASKS} tasks")
        if interval_seconds < self.MIN_INTERVAL or interval_seconds > self.MAX_INTERVAL:
            raise SchedulerError("invalid_interval", f"Interval must be between {self.MIN_INTERVAL} and {self.MAX_INTERVAL} seconds")
        if priority < 1 or priority > 10:
            raise SchedulerError("invalid_priority", "Priority must be between 1 and 10")
        task = Task(task_id=task_id, name=name, interval_seconds=interval_seconds, priority=priority, max_retries=max_retries)
        self._tasks[task_id] = task
        return task
''',
            },
            {
                "path_id": "invalid_interval",
                "title": "add_task() raises SchedulerError for out-of-range interval",
                "description": (
                    "`add_task()` must raise `SchedulerError` with code `'invalid_interval'` "
                    "when `interval_seconds` is below `MIN_INTERVAL` (1.0) or above `MAX_INTERVAL` (86400.0)."
                ),
                "examples": [
                    "interval_seconds=0.5 → SchedulerError('invalid_interval')",
                    "interval_seconds=86401.0 → SchedulerError('invalid_interval')",
                    "interval_seconds=1.0 → OK (at minimum boundary)",
                    "interval_seconds=86400.0 → OK (at maximum boundary)",
                ],
                "func_name": "add_task",
                "fixed_body": '''\
    def add_task(self, task_id, name, interval_seconds, priority=5, max_retries=3):
        if task_id in self._tasks:
            raise SchedulerError("task_exists", f"Task {task_id!r} already registered")
        if len(self._tasks) >= self.MAX_TASKS:
            raise SchedulerError("scheduler_full", f"Cannot exceed {self.MAX_TASKS} tasks")
        if interval_seconds < self.MIN_INTERVAL or interval_seconds > self.MAX_INTERVAL:
            raise SchedulerError("invalid_interval", f"Interval must be between {self.MIN_INTERVAL} and {self.MAX_INTERVAL} seconds")
        if priority < 1 or priority > 10:
            raise SchedulerError("invalid_priority", "Priority must be between 1 and 10")
        task = Task(task_id=task_id, name=name, interval_seconds=interval_seconds, priority=priority, max_retries=max_retries)
        self._tasks[task_id] = task
        return task
''',
                "buggy_body": '''\
    def add_task(self, task_id, name, interval_seconds, priority=5, max_retries=3):
        if task_id in self._tasks:
            raise SchedulerError("task_exists", f"Task {task_id!r} already registered")
        if len(self._tasks) >= self.MAX_TASKS:
            raise SchedulerError("scheduler_full", f"Cannot exceed {self.MAX_TASKS} tasks")
        # BUG: interval range check omitted
        if priority < 1 or priority > 10:
            raise SchedulerError("invalid_priority", "Priority must be between 1 and 10")
        task = Task(task_id=task_id, name=name, interval_seconds=interval_seconds, priority=priority, max_retries=max_retries)
        self._tasks[task_id] = task
        return task
''',
            },
            {
                "path_id": "invalid_priority",
                "title": "add_task() raises SchedulerError for priority outside [1, 10]",
                "description": (
                    "`add_task()` must raise `SchedulerError` with code `'invalid_priority'` "
                    "when `priority` is less than 1 or greater than 10."
                ),
                "examples": [
                    "priority=0 → SchedulerError('invalid_priority')",
                    "priority=11 → SchedulerError('invalid_priority')",
                    "priority=1 → OK (minimum boundary)",
                    "priority=10 → OK (maximum boundary)",
                ],
                "func_name": "add_task",
                "fixed_body": '''\
    def add_task(self, task_id, name, interval_seconds, priority=5, max_retries=3):
        if task_id in self._tasks:
            raise SchedulerError("task_exists", f"Task {task_id!r} already registered")
        if len(self._tasks) >= self.MAX_TASKS:
            raise SchedulerError("scheduler_full", f"Cannot exceed {self.MAX_TASKS} tasks")
        if interval_seconds < self.MIN_INTERVAL or interval_seconds > self.MAX_INTERVAL:
            raise SchedulerError("invalid_interval", f"Interval must be between {self.MIN_INTERVAL} and {self.MAX_INTERVAL} seconds")
        if priority < 1 or priority > 10:
            raise SchedulerError("invalid_priority", "Priority must be between 1 and 10")
        task = Task(task_id=task_id, name=name, interval_seconds=interval_seconds, priority=priority, max_retries=max_retries)
        self._tasks[task_id] = task
        return task
''',
                "buggy_body": '''\
    def add_task(self, task_id, name, interval_seconds, priority=5, max_retries=3):
        if task_id in self._tasks:
            raise SchedulerError("task_exists", f"Task {task_id!r} already registered")
        if len(self._tasks) >= self.MAX_TASKS:
            raise SchedulerError("scheduler_full", f"Cannot exceed {self.MAX_TASKS} tasks")
        if interval_seconds < self.MIN_INTERVAL or interval_seconds > self.MAX_INTERVAL:
            raise SchedulerError("invalid_interval", f"Interval must be between {self.MIN_INTERVAL} and {self.MAX_INTERVAL} seconds")
        # BUG: priority range check omitted
        task = Task(task_id=task_id, name=name, interval_seconds=interval_seconds, priority=priority, max_retries=max_retries)
        self._tasks[task_id] = task
        return task
''',
            },
            {
                "path_id": "retry_exceeds_max",
                "title": "record_run() disables task when retry_count exceeds max_retries",
                "description": (
                    "After enough consecutive failures, `record_run()` must set `task.enabled = False` "
                    "when `retry_count > max_retries`. The task should still be accessible via `get_task()`."
                ),
                "examples": [
                    "max_retries=2, record_run failure x3 → task.enabled == False",
                    "max_retries=3, record_run failure x3 → task.enabled == True (retry_count == max_retries, not >)",
                    "max_retries=1, fail, success → task.enabled == True (success resets retry_count)",
                ],
                "func_name": "record_run",
                "fixed_body": '''\
    def record_run(self, task_id, success, timestamp=None):
        task = self._tasks.get(task_id)
        if task is None:
            raise SchedulerError("task_not_found", f"No task {task_id!r}")
        task.last_run = timestamp if timestamp is not None else time.time()
        task.run_count += 1
        if success:
            task.retry_count = 0
        else:
            task.retry_count += 1
            if task.retry_count > task.max_retries:
                task.enabled = False
        return task
''',
                "buggy_body": '''\
    def record_run(self, task_id, success, timestamp=None):
        task = self._tasks.get(task_id)
        if task is None:
            raise SchedulerError("task_not_found", f"No task {task_id!r}")
        task.last_run = timestamp if timestamp is not None else time.time()
        task.run_count += 1
        if success:
            task.retry_count = 0
        else:
            task.retry_count += 1
            # BUG: uses >= instead of > — disables one failure too early
            if task.retry_count >= task.max_retries:
                task.enabled = False
        return task
''',
            },
            {
                "path_id": "success_resets_retry",
                "title": "record_run() resets retry_count to zero on success",
                "description": (
                    "After a successful run, `record_run()` must reset `task.retry_count` to 0, "
                    "even if there were previous failures."
                ),
                "examples": [
                    "fail x2 (retry_count=2), then success → retry_count == 0",
                    "success immediately → retry_count stays 0",
                    "fail, success, fail → retry_count == 1 (not 3)",
                ],
                "func_name": "record_run",
                "fixed_body": '''\
    def record_run(self, task_id, success, timestamp=None):
        task = self._tasks.get(task_id)
        if task is None:
            raise SchedulerError("task_not_found", f"No task {task_id!r}")
        task.last_run = timestamp if timestamp is not None else time.time()
        task.run_count += 1
        if success:
            task.retry_count = 0
        else:
            task.retry_count += 1
            if task.retry_count > task.max_retries:
                task.enabled = False
        return task
''',
                "buggy_body": '''\
    def record_run(self, task_id, success, timestamp=None):
        task = self._tasks.get(task_id)
        if task is None:
            raise SchedulerError("task_not_found", f"No task {task_id!r}")
        task.last_run = timestamp if timestamp is not None else time.time()
        task.run_count += 1
        if success:
            pass  # BUG: retry_count not reset on success
        else:
            task.retry_count += 1
            if task.retry_count > task.max_retries:
                task.enabled = False
        return task
''',
            },
            {
                "path_id": "get_due_excludes_disabled",
                "title": "get_due_tasks() excludes disabled tasks",
                "description": (
                    "`get_due_tasks()` must not return tasks where `task.enabled == False`, "
                    "even if they are past their scheduled interval."
                ),
                "examples": [
                    "Add task, disable it, get_due_tasks → empty list",
                    "Add two tasks, disable one → only enabled task returned",
                    "Re-enable via enable_task, get_due_tasks → task appears again",
                ],
                "func_name": "get_due_tasks",
                "fixed_body": '''\
    def get_due_tasks(self, current_time: float) -> list:
        due = []
        for task in self._tasks.values():
            if not task.enabled:
                continue
            if task.last_run is None or (task.last_run + task.interval_seconds) <= current_time:
                due.append(task)
        due.sort(key=lambda t: t.priority)
        return due
''',
                "buggy_body": '''\
    def get_due_tasks(self, current_time: float) -> list:
        due = []
        for task in self._tasks.values():
            # BUG: enabled check omitted
            if task.last_run is None or (task.last_run + task.interval_seconds) <= current_time:
                due.append(task)
        due.sort(key=lambda t: t.priority)
        return due
''',
            },
            {
                "path_id": "get_due_priority_order",
                "title": "get_due_tasks() returns tasks sorted by priority ascending",
                "description": (
                    "`get_due_tasks()` must return due tasks sorted by `priority` in ascending order "
                    "(priority 1 first, priority 10 last — lower number = higher priority)."
                ),
                "examples": [
                    "Tasks with priority 5, 2, 8 → returned as [2, 5, 8]",
                    "All same priority → any order acceptable",
                    "Single task → [task]",
                ],
                "func_name": "get_due_tasks",
                "fixed_body": '''\
    def get_due_tasks(self, current_time: float) -> list:
        due = []
        for task in self._tasks.values():
            if not task.enabled:
                continue
            if task.last_run is None or (task.last_run + task.interval_seconds) <= current_time:
                due.append(task)
        due.sort(key=lambda t: t.priority)
        return due
''',
                "buggy_body": '''\
    def get_due_tasks(self, current_time: float) -> list:
        due = []
        for task in self._tasks.values():
            if not task.enabled:
                continue
            if task.last_run is None or (task.last_run + task.interval_seconds) <= current_time:
                due.append(task)
        # BUG: sorted descending (reverse=True) — wrong order
        due.sort(key=lambda t: t.priority, reverse=True)
        return due
''',
            },
            {
                "path_id": "remove_task_not_found",
                "title": "remove_task() raises SchedulerError for unknown task IDs",
                "description": (
                    "`remove_task()` must raise `SchedulerError` with code `'task_not_found'` "
                    "when the specified task ID does not exist in the scheduler."
                ),
                "examples": [
                    "remove_task('GHOST') → SchedulerError('task_not_found')",
                    "add_task('T1', ...), remove_task('T1') → OK, then remove_task('T1') again → SchedulerError('task_not_found')",
                ],
                "func_name": "remove_task",
                "fixed_body": '''\
    def remove_task(self, task_id: str) -> None:
        """Remove a task. Raises SchedulerError if task not found."""
        if task_id not in self._tasks:
            raise SchedulerError("task_not_found", f"No task {task_id!r}")
        del self._tasks[task_id]
''',
                "buggy_body": '''\
    def remove_task(self, task_id: str) -> None:
        """Remove a task. Raises SchedulerError if task not found."""
        # BUG: silently ignores missing task instead of raising
        self._tasks.pop(task_id, None)
''',
            },
        ],
    },

    # ── parser ────────────────────────────────────────────────────────────────
    {
        "module_name": "parser",
        "display_name": "Config Parser",
        "description": "parses and validates structured configuration data",
        "module_src": '''\
"""
Config parser module.

Parses INI-style config text into typed values with validation.
"""
from __future__ import annotations

from typing import Any, Optional


class ParseError(Exception):
    """Raised when config parsing or validation fails."""
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class ConfigParser:
    """Parses and validates configuration data."""

    VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    MAX_WORKERS = 64
    MIN_WORKERS = 1
    MAX_TIMEOUT = 3600
    MIN_TIMEOUT = 1

    def parse_int(self, value: str, field_name: str = "field") -> int:
        """Parse a string as integer. Raises ParseError on failure."""
        try:
            return int(value.strip())
        except (ValueError, AttributeError):
            raise ParseError("invalid_int", f"{field_name!r} must be an integer, got {value!r}")

    def parse_bool(self, value: str, field_name: str = "field") -> bool:
        """Parse a string as boolean (true/false, yes/no, 1/0). Raises ParseError on unknown."""
        normalized = value.strip().lower()
        if normalized in ("true", "yes", "1"):
            return True
        if normalized in ("false", "no", "0"):
            return False
        raise ParseError("invalid_bool", f"{field_name!r} must be true/false/yes/no/1/0, got {value!r}")

    def validate_log_level(self, level: str) -> str:
        """Validate and normalise a log level string. Raises ParseError for unknown levels."""
        normalized = level.strip().upper()
        if normalized not in self.VALID_LOG_LEVELS:
            raise ParseError(
                "invalid_log_level",
                f"Log level must be one of {sorted(self.VALID_LOG_LEVELS)}, got {level!r}",
            )
        return normalized

    def validate_workers(self, count: int) -> int:
        """Validate worker count is within [MIN_WORKERS, MAX_WORKERS]. Raises ParseError otherwise."""
        if count < self.MIN_WORKERS:
            raise ParseError("workers_too_low", f"Worker count must be >= {self.MIN_WORKERS}")
        if count > self.MAX_WORKERS:
            raise ParseError("workers_too_high", f"Worker count must be <= {self.MAX_WORKERS}")
        return count

    def validate_timeout(self, seconds: int) -> int:
        """Validate timeout is within [MIN_TIMEOUT, MAX_TIMEOUT]. Raises ParseError otherwise."""
        if seconds < self.MIN_TIMEOUT:
            raise ParseError("timeout_too_low", f"Timeout must be >= {self.MIN_TIMEOUT} seconds")
        if seconds > self.MAX_TIMEOUT:
            raise ParseError("timeout_too_high", f"Timeout must be <= {self.MAX_TIMEOUT} seconds")
        return seconds

    def parse_config(self, raw: dict[str, str]) -> dict[str, Any]:
        """
        Parse a raw config dict (all string values) into typed config.
        Expected keys: log_level, workers, timeout, debug_mode, max_connections.
        Returns dict with typed values.
        Raises ParseError for any invalid field.
        """
        result = {}

        if "log_level" in raw:
            result["log_level"] = self.validate_log_level(raw["log_level"])

        if "workers" in raw:
            workers = self.parse_int(raw["workers"], "workers")
            result["workers"] = self.validate_workers(workers)

        if "timeout" in raw:
            timeout = self.parse_int(raw["timeout"], "timeout")
            result["timeout"] = self.validate_timeout(timeout)

        if "debug_mode" in raw:
            result["debug_mode"] = self.parse_bool(raw["debug_mode"], "debug_mode")

        if "max_connections" in raw:
            max_conn = self.parse_int(raw["max_connections"], "max_connections")
            if max_conn < 1:
                raise ParseError("invalid_max_connections", "max_connections must be >= 1")
            result["max_connections"] = max_conn

        return result

    def merge_configs(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """
        Merge two parsed configs. Override values take precedence.
        Neither argument is modified.
        """
        merged = dict(base)
        merged.update(override)
        return merged
''',
        "happy_test_src": '''\
"""Tests for config parser — happy path only."""
import pytest
from parser import ConfigParser, ParseError


@pytest.fixture
def parser():
    return ConfigParser()


def test_parse_int_success(parser):
    assert parser.parse_int("42") == 42
    assert parser.parse_int("  100  ") == 100


def test_parse_bool_true(parser):
    assert parser.parse_bool("true") is True
    assert parser.parse_bool("yes") is True
    assert parser.parse_bool("1") is True


def test_parse_config_success(parser):
    result = parser.parse_config({
        "log_level": "info",
        "workers": "4",
        "timeout": "30",
        "debug_mode": "false",
    })
    assert result["log_level"] == "INFO"
    assert result["workers"] == 4
    assert result["debug_mode"] is False
''',
        "paths": [
            {
                "path_id": "invalid_int",
                "title": "parse_int() raises ParseError for non-integer strings",
                "description": (
                    "`parse_int()` must raise `ParseError` with code `'invalid_int'` "
                    "when the input string cannot be parsed as an integer."
                ),
                "examples": [
                    "parse_int('abc') → ParseError('invalid_int')",
                    "parse_int('3.14') → ParseError('invalid_int')",
                    "parse_int('') → ParseError('invalid_int')",
                    "parse_int('42') → 42",
                ],
                "func_name": "parse_int",
                "fixed_body": '''\
    def parse_int(self, value: str, field_name: str = "field") -> int:
        """Parse a string as integer. Raises ParseError on failure."""
        try:
            return int(value.strip())
        except (ValueError, AttributeError):
            raise ParseError("invalid_int", f"{field_name!r} must be an integer, got {value!r}")
''',
                "buggy_body": '''\
    def parse_int(self, value: str, field_name: str = "field") -> int:
        """Parse a string as integer. Raises ParseError on failure."""
        try:
            return int(value.strip())
        except (ValueError, AttributeError):
            # BUG: returns 0 instead of raising
            return 0
''',
            },
            {
                "path_id": "invalid_bool",
                "title": "parse_bool() raises ParseError for unrecognized boolean strings",
                "description": (
                    "`parse_bool()` must raise `ParseError` with code `'invalid_bool'` "
                    "when the input is not one of the recognized boolean representations "
                    "(true, false, yes, no, 1, 0)."
                ),
                "examples": [
                    "parse_bool('maybe') → ParseError('invalid_bool')",
                    "parse_bool('enabled') → ParseError('invalid_bool')",
                    "parse_bool('TRUE') → True (case-insensitive)",
                    "parse_bool('0') → False",
                ],
                "func_name": "parse_bool",
                "fixed_body": '''\
    def parse_bool(self, value: str, field_name: str = "field") -> bool:
        """Parse a string as boolean."""
        normalized = value.strip().lower()
        if normalized in ("true", "yes", "1"):
            return True
        if normalized in ("false", "no", "0"):
            return False
        raise ParseError("invalid_bool", f"{field_name!r} must be true/false/yes/no/1/0, got {value!r}")
''',
                "buggy_body": '''\
    def parse_bool(self, value: str, field_name: str = "field") -> bool:
        """Parse a string as boolean."""
        normalized = value.strip().lower()
        if normalized in ("true", "yes", "1"):
            return True
        if normalized in ("false", "no", "0"):
            return False
        # BUG: returns False instead of raising
        return False
''',
            },
            {
                "path_id": "invalid_log_level",
                "title": "validate_log_level() raises ParseError for unknown log levels",
                "description": (
                    "`validate_log_level()` must raise `ParseError` with code `'invalid_log_level'` "
                    "for any level string not in {DEBUG, INFO, WARNING, ERROR, CRITICAL} "
                    "(case-insensitive)."
                ),
                "examples": [
                    "validate_log_level('TRACE') → ParseError('invalid_log_level')",
                    "validate_log_level('verbose') → ParseError('invalid_log_level')",
                    "validate_log_level('info') → 'INFO' (normalized)",
                    "validate_log_level('DEBUG') → 'DEBUG'",
                ],
                "func_name": "validate_log_level",
                "fixed_body": '''\
    def validate_log_level(self, level: str) -> str:
        """Validate and normalise a log level string."""
        normalized = level.strip().upper()
        if normalized not in self.VALID_LOG_LEVELS:
            raise ParseError("invalid_log_level", f"Log level must be one of {sorted(self.VALID_LOG_LEVELS)}, got {level!r}")
        return normalized
''',
                "buggy_body": '''\
    def validate_log_level(self, level: str) -> str:
        """Validate and normalise a log level string."""
        normalized = level.strip().upper()
        # BUG: missing validation — accepts any level
        return normalized
''',
            },
            {
                "path_id": "workers_too_low",
                "title": "validate_workers() raises ParseError when count is below minimum",
                "description": (
                    "`validate_workers()` must raise `ParseError` with code `'workers_too_low'` "
                    "when the worker count is less than `MIN_WORKERS` (1)."
                ),
                "examples": [
                    "validate_workers(0) → ParseError('workers_too_low')",
                    "validate_workers(-1) → ParseError('workers_too_low')",
                    "validate_workers(1) → 1 (minimum boundary)",
                ],
                "func_name": "validate_workers",
                "fixed_body": '''\
    def validate_workers(self, count: int) -> int:
        """Validate worker count."""
        if count < self.MIN_WORKERS:
            raise ParseError("workers_too_low", f"Worker count must be >= {self.MIN_WORKERS}")
        if count > self.MAX_WORKERS:
            raise ParseError("workers_too_high", f"Worker count must be <= {self.MAX_WORKERS}")
        return count
''',
                "buggy_body": '''\
    def validate_workers(self, count: int) -> int:
        """Validate worker count."""
        # BUG: minimum check omitted
        if count > self.MAX_WORKERS:
            raise ParseError("workers_too_high", f"Worker count must be <= {self.MAX_WORKERS}")
        return count
''',
            },
            {
                "path_id": "workers_too_high",
                "title": "validate_workers() raises ParseError when count exceeds maximum",
                "description": (
                    "`validate_workers()` must raise `ParseError` with code `'workers_too_high'` "
                    "when the worker count exceeds `MAX_WORKERS` (64)."
                ),
                "examples": [
                    "validate_workers(65) → ParseError('workers_too_high')",
                    "validate_workers(100) → ParseError('workers_too_high')",
                    "validate_workers(64) → 64 (maximum boundary)",
                ],
                "func_name": "validate_workers",
                "fixed_body": '''\
    def validate_workers(self, count: int) -> int:
        """Validate worker count."""
        if count < self.MIN_WORKERS:
            raise ParseError("workers_too_low", f"Worker count must be >= {self.MIN_WORKERS}")
        if count > self.MAX_WORKERS:
            raise ParseError("workers_too_high", f"Worker count must be <= {self.MAX_WORKERS}")
        return count
''',
                "buggy_body": '''\
    def validate_workers(self, count: int) -> int:
        """Validate worker count."""
        if count < self.MIN_WORKERS:
            raise ParseError("workers_too_low", f"Worker count must be >= {self.MIN_WORKERS}")
        # BUG: maximum check omitted
        return count
''',
            },
            {
                "path_id": "timeout_too_low",
                "title": "validate_timeout() raises ParseError for timeout below minimum",
                "description": (
                    "`validate_timeout()` must raise `ParseError` with code `'timeout_too_low'` "
                    "when the timeout is less than `MIN_TIMEOUT` (1 second)."
                ),
                "examples": [
                    "validate_timeout(0) → ParseError('timeout_too_low')",
                    "validate_timeout(-10) → ParseError('timeout_too_low')",
                    "validate_timeout(1) → 1 (minimum boundary)",
                ],
                "func_name": "validate_timeout",
                "fixed_body": '''\
    def validate_timeout(self, seconds: int) -> int:
        """Validate timeout range."""
        if seconds < self.MIN_TIMEOUT:
            raise ParseError("timeout_too_low", f"Timeout must be >= {self.MIN_TIMEOUT} seconds")
        if seconds > self.MAX_TIMEOUT:
            raise ParseError("timeout_too_high", f"Timeout must be <= {self.MAX_TIMEOUT} seconds")
        return seconds
''',
                "buggy_body": '''\
    def validate_timeout(self, seconds: int) -> int:
        """Validate timeout range."""
        # BUG: minimum check omitted
        if seconds > self.MAX_TIMEOUT:
            raise ParseError("timeout_too_high", f"Timeout must be <= {self.MAX_TIMEOUT} seconds")
        return seconds
''',
            },
            {
                "path_id": "timeout_too_high",
                "title": "validate_timeout() raises ParseError for timeout above maximum",
                "description": (
                    "`validate_timeout()` must raise `ParseError` with code `'timeout_too_high'` "
                    "when the timeout exceeds `MAX_TIMEOUT` (3600 seconds)."
                ),
                "examples": [
                    "validate_timeout(3601) → ParseError('timeout_too_high')",
                    "validate_timeout(7200) → ParseError('timeout_too_high')",
                    "validate_timeout(3600) → 3600 (maximum boundary)",
                ],
                "func_name": "validate_timeout",
                "fixed_body": '''\
    def validate_timeout(self, seconds: int) -> int:
        """Validate timeout range."""
        if seconds < self.MIN_TIMEOUT:
            raise ParseError("timeout_too_low", f"Timeout must be >= {self.MIN_TIMEOUT} seconds")
        if seconds > self.MAX_TIMEOUT:
            raise ParseError("timeout_too_high", f"Timeout must be <= {self.MAX_TIMEOUT} seconds")
        return seconds
''',
                "buggy_body": '''\
    def validate_timeout(self, seconds: int) -> int:
        """Validate timeout range."""
        if seconds < self.MIN_TIMEOUT:
            raise ParseError("timeout_too_low", f"Timeout must be >= {self.MIN_TIMEOUT} seconds")
        # BUG: maximum check omitted
        return seconds
''',
            },
            {
                "path_id": "merge_does_not_mutate",
                "title": "merge_configs() does not mutate either input dict",
                "description": (
                    "`merge_configs(base, override)` must return a new dict with override "
                    "values taking precedence, without modifying `base` or `override`."
                ),
                "examples": [
                    "base={'a':1}, override={'a':2, 'b':3} → merged={'a':2,'b':3}, base unchanged",
                    "base={'x':10}, override={} → merged={'x':10}",
                    "base={}, override={'y':5} → merged={'y':5}",
                ],
                "func_name": "merge_configs",
                "fixed_body": '''\
    def merge_configs(self, base: dict, override: dict) -> dict:
        """Merge two parsed configs. Override values take precedence. Neither argument is modified."""
        merged = dict(base)
        merged.update(override)
        return merged
''',
                "buggy_body": '''\
    def merge_configs(self, base: dict, override: dict) -> dict:
        """Merge two parsed configs. Override values take precedence. Neither argument is modified."""
        # BUG: mutates base in place instead of creating new dict
        base.update(override)
        return base
''',
            },
        ],
    },
]


def _build_buggy_module(module_def: dict, target_path: dict) -> str:
    """
    Return a module where the target path's function body is replaced with the buggy version.

    Strategy: find the function by name in the source using AST line numbers,
    then replace those lines with the buggy body lines.  Falls back to direct
    string substitution when the function appears more than once (e.g. refund
    appears in multiple paths for the same func_name).
    """
    import ast as _ast

    src = module_def["module_src"]
    func_name = target_path["func_name"]
    buggy_body = target_path["buggy_body"]

    # Normalise indentation of buggy_body to match source (8-space method indent)
    buggy_lines = buggy_body.splitlines()
    # Strip leading blank lines
    while buggy_lines and not buggy_lines[0].strip():
        buggy_lines.pop(0)
    # Strip trailing blank lines
    while buggy_lines and not buggy_lines[-1].strip():
        buggy_lines.pop()

    src_lines = src.splitlines()

    try:
        tree = _ast.parse(src)
    except SyntaxError:
        return src

    # Collect all FunctionDef nodes with matching name (methods inside classes too)
    matches = []
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            if node.name == func_name:
                matches.append(node)

    if not matches:
        return src

    # Use the first match
    node = matches[0]
    # line numbers are 1-based; end_lineno inclusive
    start = node.lineno - 1   # 0-based index of "def ..." line
    end = node.end_lineno      # 0-based exclusive (slice end)

    # Build replacement: keep the "def ..." signature line from source,
    # then insert the buggy body lines (skipping the def line in buggy_body if present)
    def_line = src_lines[start]

    # buggy_body may or may not include a "def ..." line; detect and skip it
    body_start = 0
    if buggy_lines and buggy_lines[0].lstrip().startswith("def "):
        body_start = 1

    replacement = [def_line] + buggy_lines[body_start:]

    new_lines = src_lines[:start] + replacement + src_lines[end:]
    return "\n".join(new_lines) + "\n"


class Generator(TaskGenerator):
    task_id = "CR5_test_coverage"
    domain = "testing"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # Pick module type
        module_def = MODULE_POOL[rng.randint(0, len(MODULE_POOL) - 1)]
        module_name = module_def["module_name"]

        # Pick 5-8 uncovered paths from this module's path pool
        num_paths = rng.randint(5, min(8, len(module_def["paths"])))
        path_indices = rng.sample(list(range(len(module_def["paths"]))), num_paths)
        selected_paths = [module_def["paths"][i] for i in path_indices]

        # Build workspace files
        workspace_files: dict[str, str] = {
            f"{module_name}.py": module_def["module_src"],
            f"test_{module_name}.py": module_def["happy_test_src"],
        }

        # Build buggy variants (one per selected path)
        for path in selected_paths:
            buggy_src = _build_buggy_module(module_def, path)
            workspace_files[f"buggy_variants/{path['path_id']}.py"] = buggy_src

        spec_md = self._generate_spec(module_def, selected_paths, seed)
        brief_md = self._generate_brief(module_def, module_name)

        expected = {
            "module_name": module_name,
            "path_ids": [p["path_id"] for p in selected_paths],
            "path_count": num_paths,
            "min_new_tests": num_paths,
            "module_display_name": module_def["display_name"],
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _generate_spec(self, module_def: dict, paths: list[dict], seed: int) -> str:
        module_name = module_def["module_name"]
        display_name = module_def["display_name"]
        num_paths = len(paths)

        path_sections = []
        for idx, path in enumerate(paths, start=1):
            examples_text = "\n".join(f"  - {ex}" for ex in path["examples"])
            section = textwrap.dedent(f"""\
                ### Path {idx}: {path['title']}

                **Code location**: `{path['func_name']}()`

                **Description**: {path['description']}

                **Expected behaviour for each case**:
                {examples_text}
            """)
            path_sections.append(section)

        paths_text = "\n".join(path_sections)

        return textwrap.dedent(f"""\
            # CR5: Test Coverage — Add Tests for Uncovered Paths

            ## Context

            The `{module_name}.py` module ({display_name}) has a solid implementation
            but the existing test suite (`test_{module_name}.py`) only covers **happy paths**.
            The following {num_paths} code paths are **completely untested**.

            Your task: add new tests to `test_{module_name}.py` that cover each path below.
            Each new test must:
            1. Pass against the correct `{module_name}.py` implementation.
            2. **Fail** if that path's logic were removed or broken (mutation resistance).

            Do **not** modify `{module_name}.py` — source code is read-only.

            ## Uncovered Paths (Seed {seed})

            {paths_text}

            ## Deliverables

            - Updated `test_{module_name}.py` with at least {num_paths} new test functions.
            - Tests must use `assert` statements or `pytest.raises`.
            - Run with: `python -m pytest test_{module_name}.py`

            ## Grading

            - **Check 1**: `test_{module_name}.py` exists.
            - **Check 2**: All tests pass on the correct `{module_name}.py`.
            - **Check 3**: At least {num_paths} test functions present.
            - **Check 4**: Tests use assertions (not print-only).
            - **Check 5**: `pytest` exits with code 0.
            - **Checks 6–{num_paths + 5}**: Each uncovered path has a test that catches its mutation.
        """)

    def _generate_brief(self, module_def: dict, module_name: str) -> str:
        display_name = module_def["display_name"]
        return textwrap.dedent(f"""\
            # CR5: Test Coverage (Brief)

            The `{module_name}.py` module ({display_name}) has low test coverage.
            The existing tests only cover happy paths. Increase coverage by adding
            tests for the uncovered branches and error-handling paths.

            - File to update: `test_{module_name}.py`
            - Do NOT modify `{module_name}.py`
            - Run tests with: `python -m pytest test_{module_name}.py`
            - The Planner has the full list of uncovered paths with expected behavior.
        """)
