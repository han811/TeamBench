"""
Parameterized generator for SPEC2: API Design from OpenAPI Spec.

Each seed selects a different REST API domain and produces:
  - app.py: Flask app with route decorators but TODO function bodies
  - models.py: In-memory data store with basic field definitions
  - test_api.py: Integration tests that validate SOME behavior (not comprehensive)
  - requirements.txt: flask
  - spec.md: Complete OpenAPI-style spec with schemas, status codes, validation rules
  - brief.md: "Implement the API endpoints. The Planner has the full API spec."
  - expected.json: Seed-aware ground-truth for the grader

TNI driver: brief.md says "implement endpoints; Planner has the spec."
The spec contains exact request/response field names, required fields, status codes,
validation rules (length limits, regex, enums), and business logic (no-duplicate,
must-reference-existing). The executor can infer basic CRUD behavior from test_api.py
but NOT the exact schemas, error codes, or validation constraints.

Seed → domain mapping:
  0 mod 5 → task_management  (tasks with status/priority)
  1 mod 5 → inventory        (products with categories/stock)
  2 mod 5 → booking          (reservations with slots/users)
  3 mod 5 → user_management  (users with roles/profiles)
  4 mod 5 → blog             (posts with tags/authors)
"""
from __future__ import annotations

import textwrap

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ---------------------------------------------------------------------------
# Domain list
# ---------------------------------------------------------------------------

DOMAINS = [
    "task_management",
    "inventory",
    "booking",
    "user_management",
    "blog",
]


class Generator(TaskGenerator):
    task_id = "SPEC2_api_design"
    domain = "specification"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        domain = DOMAINS[seed % len(DOMAINS)]

        if domain == "task_management":
            return self._gen_task_management(seed, rng)
        elif domain == "inventory":
            return self._gen_inventory(seed, rng)
        elif domain == "booking":
            return self._gen_booking(seed, rng)
        elif domain == "user_management":
            return self._gen_user_management(seed, rng)
        else:
            return self._gen_blog(seed, rng)

    # -----------------------------------------------------------------------
    # Domain 0: Task Management API
    # -----------------------------------------------------------------------

    def _gen_task_management(self, seed: int, rng: SeededRandom) -> GeneratedTask:
        max_title_len = rng.choice([60, 80, 100])
        max_desc_len = rng.choice([200, 300, 500])
        priorities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        statuses = ["TODO", "IN_PROGRESS", "DONE", "CANCELLED"]
        allowed_priorities = rng.sample(priorities, rng.randint(3, 4))
        allowed_priorities_sorted = [p for p in priorities if p in allowed_priorities]

        expected = {
            "domain": "task_management",
            "resource": "task",
            "max_title_len": max_title_len,
            "max_desc_len": max_desc_len,
            "allowed_priorities": allowed_priorities_sorted,
            "statuses": statuses,
            "post_status": 201,
            "get_status": 200,
            "delete_status": 200,
            "not_found_code": "TASK_NOT_FOUND",
            "validation_error_code": "VALIDATION_ERROR",
            "duplicate_code": "DUPLICATE_TITLE",
            "response_fields": ["id", "title", "description", "priority", "status", "created_at"],
            "required_post_fields": ["title", "priority"],
        }

        priorities_str = ", ".join(f'`{p}`' for p in allowed_priorities_sorted)
        statuses_str = ", ".join(f'`{s}`' for s in statuses)

        spec_md = f"""# SPEC2: Task Management REST API — Full OpenAPI Specification

## Overview
Implement a REST API for task management. Tasks have a title, description,
priority, and status. The API supports full CRUD plus status transitions.

## Base URL
`/api/v1`

## Data Model: Task

| Field        | Type    | Description                                      |
|--------------|---------|--------------------------------------------------|
| `id`         | integer | Auto-assigned, starts at 1, increments by 1      |
| `title`      | string  | Required; max {max_title_len} characters; must be unique |
| `description`| string  | Optional; max {max_desc_len} characters if provided      |
| `priority`   | string  | Required; one of: {priorities_str}               |
| `status`     | string  | Read-only on creation; always starts as `TODO`   |
| `created_at` | string  | ISO 8601 timestamp set by server on creation     |

## Endpoints

### POST /api/v1/tasks
Create a new task.

**Request body (JSON):**
```json
{{
  "title": "string (required, max {max_title_len} chars)",
  "description": "string (optional, max {max_desc_len} chars)",
  "priority": "string (required, one of {priorities_str})"
}}
```

**Success response — 201 Created:**
```json
{{
  "id": 1,
  "title": "Fix login bug",
  "description": "Users cannot log in with SSO",
  "priority": "HIGH",
  "status": "TODO",
  "created_at": "2024-06-01T10:00:00Z"
}}
```

**Error responses:**
- **400** `VALIDATION_ERROR` — missing required field (`title` or `priority`),
  title exceeds {max_title_len} chars, description exceeds {max_desc_len} chars,
  or priority not in allowed values
- **409** `DUPLICATE_TITLE` — a task with that exact title already exists

### GET /api/v1/tasks
List all tasks. Optional query params: `?status=TODO` and/or `?priority=HIGH`.

**Success response — 200 OK:**
```json
[
  {{
    "id": 1,
    "title": "Fix login bug",
    "description": "...",
    "priority": "HIGH",
    "status": "TODO",
    "created_at": "2024-06-01T10:00:00Z"
  }}
]
```

### GET /api/v1/tasks/{{task_id}}
Retrieve a single task by ID.

**Success response — 200 OK:** single task object (same schema as above)

**Error response:**
- **404** `TASK_NOT_FOUND` — no task with that ID

### PUT /api/v1/tasks/{{task_id}}
Update a task's title, description, priority, or status.

**Request body (JSON, all fields optional):**
```json
{{
  "title": "Updated title",
  "description": "Updated description",
  "priority": "CRITICAL",
  "status": "IN_PROGRESS"
}}
```

**Success response — 200 OK:** updated task object

**Error responses:**
- **404** `TASK_NOT_FOUND`
- **400** `VALIDATION_ERROR` — same constraints as POST apply to provided fields
- **409** `DUPLICATE_TITLE` — title conflicts with another existing task

### DELETE /api/v1/tasks/{{task_id}}
Delete a task permanently.

**Success response — 200 OK:**
```json
{{
  "id": 1,
  "title": "Fix login bug",
  "description": "...",
  "priority": "HIGH",
  "status": "TODO",
  "created_at": "2024-06-01T10:00:00Z"
}}
```

**Error response:**
- **404** `TASK_NOT_FOUND`

## Validation Rules (EXACT — must be implemented precisely)

1. `title`: required on POST; max {max_title_len} characters; whitespace-only is rejected
2. `description`: optional; if provided, max {max_desc_len} characters
3. `priority`: required on POST; must be exactly one of {priorities_str} (case-sensitive)
4. `status` on PUT: must be one of {statuses_str}; ignored on POST (always starts `TODO`)
5. Duplicate check: `title` uniqueness is case-insensitive (e.g. "Fix Bug" and "fix bug" conflict)

## Error Response Schema

All errors return JSON:
```json
{{
  "error": "ERROR_CODE",
  "message": "Human-readable description"
}}
```

The `error` field must contain the exact code strings listed above.

## Status Codes Summary

| Scenario                  | HTTP Status |
|---------------------------|-------------|
| Resource created          | 201         |
| Resource found / updated  | 200         |
| Validation failed         | 400         |
| Resource not found        | 404         |
| Duplicate resource        | 409         |
"""

        brief_md = """# SPEC2: Task Management REST API (Executor Brief)

Implement the REST API endpoints in `app.py`. The workspace contains:
- `app.py` — Flask app skeleton with route decorators and TODO bodies
- `models.py` — In-memory data store (do not modify the class interface)
- `test_api.py` — Integration tests for basic behavior

The Planner has the full API specification with exact request/response schemas,
status codes, validation rules, and business logic constraints.

Run tests with: `python -m pytest test_api.py -v`

Install dependencies: `pip install flask pytest`

The endpoints to implement:
- `POST /api/v1/tasks` — create a task
- `GET /api/v1/tasks` — list tasks (with optional filters)
- `GET /api/v1/tasks/<id>` — get one task
- `PUT /api/v1/tasks/<id>` — update a task
- `DELETE /api/v1/tasks/<id>` — delete a task
"""

        app_py = f'''\
"""Task Management REST API — implement the TODO endpoints."""
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from models import TaskStore, Task

app = Flask(__name__)
store = TaskStore()


def error_response(code, message, status):
    return jsonify({{"error": code, "message": message}}), status


def task_to_dict(t):
    return {{
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "priority": t.priority,
        "status": t.status,
        "created_at": t.created_at,
    }}


@app.route("/api/v1/tasks", methods=["POST"])
def create_task():
    # TODO: Parse JSON body
    # TODO: Validate required fields (title, priority)
    # TODO: Check title length <= {max_title_len} and description length <= {max_desc_len}
    # TODO: Validate priority is one of the allowed values
    # TODO: Check for duplicate title (case-insensitive)
    # TODO: Create and store the task; return 201 with task JSON
    pass


@app.route("/api/v1/tasks", methods=["GET"])
def list_tasks():
    # TODO: Get optional query params ?status= and ?priority=
    # TODO: Filter tasks accordingly
    # TODO: Return 200 with list of task dicts
    pass


@app.route("/api/v1/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    # TODO: Look up task by ID
    # TODO: Return 404 TASK_NOT_FOUND if not found
    # TODO: Return 200 with task dict
    pass


@app.route("/api/v1/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    # TODO: Look up task; return 404 if not found
    # TODO: Parse JSON body; apply provided fields
    # TODO: Validate any provided fields (same constraints as create)
    # TODO: Check duplicate title if title is being changed
    # TODO: Return 200 with updated task dict
    pass


@app.route("/api/v1/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    # TODO: Look up task; return 404 if not found
    # TODO: Remove from store
    # TODO: Return 200 with deleted task dict
    pass


if __name__ == "__main__":
    app.run(debug=True)
'''

        models_py = '''\
"""In-memory data store for the Task Management API."""
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class Task:
    id: int
    title: str
    description: Optional[str]
    priority: str
    status: str
    created_at: str


class TaskStore:
    def __init__(self):
        self._tasks: dict[int, Task] = {}
        self._next_id: int = 1

    def add(self, task: Task) -> Task:
        task.id = self._next_id
        self._tasks[self._next_id] = task
        self._next_id += 1
        return task

    def get(self, task_id: int) -> Optional[Task]:
        return self._tasks.get(task_id)

    def all(self) -> List[Task]:
        return list(self._tasks.values())

    def delete(self, task_id: int) -> Optional[Task]:
        return self._tasks.pop(task_id, None)

    def exists_title(self, title: str, exclude_id: Optional[int] = None) -> bool:
        for t in self._tasks.values():
            if t.id == exclude_id:
                continue
            if t.title.lower() == title.lower():
                return True
        return False
'''

        test_api_py = f'''\
"""Basic integration tests for the Task Management REST API.

NOTE: These tests check fundamental behavior but do NOT cover all
validation rules, exact error codes, or edge cases. The Planner has
the complete specification.
"""
import pytest
from app import app as flask_app, store as global_store
from models import TaskStore


@pytest.fixture(autouse=True)
def reset_store():
    """Reset the in-memory store before each test."""
    global_store._tasks.clear()
    global_store._next_id = 1
    yield


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def test_create_task_returns_201(client):
    resp = client.post("/api/v1/tasks", json={{
        "title": "My first task",
        "priority": "{allowed_priorities_sorted[0]}"
    }})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["id"] == 1
    assert data["title"] == "My first task"
    assert data["status"] == "TODO"


def test_create_task_missing_title_returns_400(client):
    resp = client.post("/api/v1/tasks", json={{
        "priority": "{allowed_priorities_sorted[0]}"
    }})
    assert resp.status_code == 400


def test_create_task_missing_priority_returns_400(client):
    resp = client.post("/api/v1/tasks", json={{
        "title": "No priority task"
    }})
    assert resp.status_code == 400


def test_list_tasks_empty(client):
    resp = client.get("/api/v1/tasks")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_tasks_returns_created(client):
    client.post("/api/v1/tasks", json={{
        "title": "Task A",
        "priority": "{allowed_priorities_sorted[0]}"
    }})
    resp = client.get("/api/v1/tasks")
    assert resp.status_code == 200
    tasks = resp.get_json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Task A"


def test_get_task_not_found_returns_404(client):
    resp = client.get("/api/v1/tasks/999")
    assert resp.status_code == 404


def test_get_task_returns_200(client):
    client.post("/api/v1/tasks", json={{
        "title": "Find me",
        "priority": "{allowed_priorities_sorted[0]}"
    }})
    resp = client.get("/api/v1/tasks/1")
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "Find me"


def test_update_task_returns_200(client):
    client.post("/api/v1/tasks", json={{
        "title": "Old title",
        "priority": "{allowed_priorities_sorted[0]}"
    }})
    resp = client.put("/api/v1/tasks/1", json={{"title": "New title"}})
    assert resp.status_code == 200
    assert resp.get_json()["title"] == "New title"


def test_delete_task_returns_200(client):
    client.post("/api/v1/tasks", json={{
        "title": "Delete me",
        "priority": "{allowed_priorities_sorted[0]}"
    }})
    resp = client.delete("/api/v1/tasks/1")
    assert resp.status_code == 200
    # Task should be gone
    assert client.get("/api/v1/tasks/1").status_code == 404
'''

        requirements_txt = "flask\npytest\n"

        return GeneratedTask(
            task_id="SPEC2_api_design",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files={
                "app.py": app_py,
                "models.py": models_py,
                "test_api.py": test_api_py,
                "requirements.txt": requirements_txt,
            },
        )

    # -----------------------------------------------------------------------
    # Domain 1: Inventory API
    # -----------------------------------------------------------------------

    def _gen_inventory(self, seed: int, rng: SeededRandom) -> GeneratedTask:
        max_name_len = rng.choice([50, 80, 100])
        max_qty = rng.choice([500, 1000, 9999])
        categories = rng.sample(
            ["electronics", "clothing", "food", "furniture", "tools", "sports", "books", "toys"],
            rng.randint(4, 6),
        )
        categories_sorted = sorted(categories)
        low_stock_threshold = rng.choice([5, 10, 20])

        expected = {
            "domain": "inventory",
            "resource": "product",
            "max_name_len": max_name_len,
            "max_qty": max_qty,
            "categories": categories_sorted,
            "low_stock_threshold": low_stock_threshold,
            "post_status": 201,
            "get_status": 200,
            "delete_status": 200,
            "not_found_code": "PRODUCT_NOT_FOUND",
            "validation_error_code": "VALIDATION_ERROR",
            "duplicate_code": "DUPLICATE_NAME",
            "low_stock_code": "LOW_STOCK",
            "response_fields": ["id", "name", "category", "quantity", "price", "low_stock"],
            "required_post_fields": ["name", "category", "quantity", "price"],
        }

        cats_str = ", ".join(f'`{c}`' for c in categories_sorted)

        spec_md = f"""# SPEC2: Inventory Management REST API — Full OpenAPI Specification

## Overview
Implement a REST API for inventory management. Products have a name, category,
quantity, and price. The API supports CRUD plus low-stock detection.

## Base URL
`/api/v1`

## Data Model: Product

| Field       | Type    | Description                                                |
|-------------|---------|------------------------------------------------------------|
| `id`        | integer | Auto-assigned, starts at 1, increments by 1               |
| `name`      | string  | Required; max {max_name_len} chars; must be unique (case-insensitive) |
| `category`  | string  | Required; must be one of: {cats_str}                      |
| `quantity`  | integer | Required; 0 to {max_qty} inclusive                        |
| `price`     | number  | Required; must be > 0.0; two decimal places               |
| `low_stock` | boolean | Computed: true when quantity <= {low_stock_threshold}      |

## Endpoints

### POST /api/v1/products
Create a new product.

**Request body (JSON):**
```json
{{
  "name": "string (required, max {max_name_len} chars)",
  "category": "string (required, one of: {cats_str})",
  "quantity": "integer (required, 0-{max_qty})",
  "price": "number (required, > 0)"
}}
```

**Success response — 201 Created:**
```json
{{
  "id": 1,
  "name": "Widget Pro",
  "category": "electronics",
  "quantity": 50,
  "price": 29.99,
  "low_stock": false
}}
```

**Error responses:**
- **400** `VALIDATION_ERROR` — missing required field, name too long,
  invalid category, quantity out of range [0, {max_qty}], or price <= 0
- **409** `DUPLICATE_NAME` — a product with that name already exists (case-insensitive)

### GET /api/v1/products
List all products. Optional query params: `?category=electronics` and/or `?low_stock=true`.

**Success response — 200 OK:** list of product objects

### GET /api/v1/products/{{product_id}}
Retrieve a single product.

**Success response — 200 OK:** product object

**Error response:**
- **404** `PRODUCT_NOT_FOUND`

### PUT /api/v1/products/{{product_id}}
Update a product's fields.

**Request body (JSON, all fields optional):**
```json
{{
  "name": "Updated name",
  "category": "clothing",
  "quantity": 100,
  "price": 49.99
}}
```

**Success response — 200 OK:** updated product object

**Error responses:**
- **404** `PRODUCT_NOT_FOUND`
- **400** `VALIDATION_ERROR`
- **409** `DUPLICATE_NAME`

### DELETE /api/v1/products/{{product_id}}
Delete a product.

**Success response — 200 OK:** deleted product object

**Error response:**
- **404** `PRODUCT_NOT_FOUND`

### GET /api/v1/products/low-stock
List all products with quantity <= {low_stock_threshold}.
Results sorted by quantity ascending, then by id ascending.

**Success response — 200 OK:** list of product objects with `low_stock: true`

## Validation Rules (EXACT)

1. `name`: required; max {max_name_len} chars; whitespace-only rejected
2. `category`: required; must be exactly one of {cats_str} (case-sensitive)
3. `quantity`: required; integer in range [0, {max_qty}] inclusive
4. `price`: required; must be a positive number > 0; stored as float rounded to 2 decimals
5. `low_stock`: computed field — `quantity <= {low_stock_threshold}`
6. Duplicate check: name uniqueness is case-insensitive

## Error Response Schema

```json
{{
  "error": "ERROR_CODE",
  "message": "Human-readable description"
}}
```

## Status Codes Summary

| Scenario                  | HTTP Status |
|---------------------------|-------------|
| Resource created          | 201         |
| Resource found / updated  | 200         |
| Validation failed         | 400         |
| Resource not found        | 404         |
| Duplicate resource        | 409         |
"""

        brief_md = """# SPEC2: Inventory Management REST API (Executor Brief)

Implement the REST API endpoints in `app.py`. The workspace contains:
- `app.py` — Flask app skeleton with route decorators and TODO bodies
- `models.py` — In-memory data store (do not modify the class interface)
- `test_api.py` — Integration tests for basic behavior

The Planner has the full API specification with exact schemas, status codes,
validation rules, and computed fields.

Run tests with: `python -m pytest test_api.py -v`

The endpoints to implement:
- `POST /api/v1/products` — create a product
- `GET /api/v1/products` — list products (with optional filters)
- `GET /api/v1/products/<id>` — get one product
- `PUT /api/v1/products/<id>` — update a product
- `DELETE /api/v1/products/<id>` — delete a product
- `GET /api/v1/products/low-stock` — list low-stock products
"""

        app_py = f'''\
"""Inventory Management REST API — implement the TODO endpoints."""
from flask import Flask, request, jsonify
from models import ProductStore, Product

app = Flask(__name__)
store = ProductStore()


def error_response(code, message, status):
    return jsonify({{"error": code, "message": message}}), status


def product_to_dict(p, low_stock_threshold={low_stock_threshold}):
    return {{
        "id": p.id,
        "name": p.name,
        "category": p.category,
        "quantity": p.quantity,
        "price": p.price,
        "low_stock": p.quantity <= low_stock_threshold,
    }}


@app.route("/api/v1/products", methods=["POST"])
def create_product():
    # TODO: Parse JSON body
    # TODO: Validate required fields (name, category, quantity, price)
    # TODO: Check name length <= {max_name_len}; reject whitespace-only
    # TODO: Validate category is one of the allowed values
    # TODO: Validate quantity in [0, {max_qty}]
    # TODO: Validate price > 0; round to 2 decimal places
    # TODO: Check for duplicate name (case-insensitive) -> 409
    # TODO: Create and store product; return 201
    pass


@app.route("/api/v1/products", methods=["GET"])
def list_products():
    # TODO: Get optional query params ?category= and ?low_stock=
    # TODO: Filter and return 200 with list
    pass


@app.route("/api/v1/products/low-stock", methods=["GET"])
def low_stock_products():
    # TODO: Return products with quantity <= {low_stock_threshold}
    # TODO: Sort by quantity asc, then id asc
    pass


@app.route("/api/v1/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    # TODO: Look up product; return 404 PRODUCT_NOT_FOUND if missing
    # TODO: Return 200 with product dict
    pass


@app.route("/api/v1/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    # TODO: Look up product; 404 if missing
    # TODO: Parse and validate provided fields
    # TODO: Check duplicate name if name is being changed
    # TODO: Return 200 with updated product dict
    pass


@app.route("/api/v1/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    # TODO: Look up product; 404 if missing
    # TODO: Remove and return 200 with deleted product dict
    pass


if __name__ == "__main__":
    app.run(debug=True)
'''

        models_py = '''\
"""In-memory data store for the Inventory API."""
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class Product:
    id: int
    name: str
    category: str
    quantity: int
    price: float


class ProductStore:
    def __init__(self):
        self._products: dict[int, Product] = {}
        self._next_id: int = 1

    def add(self, product: Product) -> Product:
        product.id = self._next_id
        self._products[self._next_id] = product
        self._next_id += 1
        return product

    def get(self, product_id: int) -> Optional[Product]:
        return self._products.get(product_id)

    def all(self) -> List[Product]:
        return list(self._products.values())

    def delete(self, product_id: int) -> Optional[Product]:
        return self._products.pop(product_id, None)

    def exists_name(self, name: str, exclude_id: Optional[int] = None) -> bool:
        for p in self._products.values():
            if p.id == exclude_id:
                continue
            if p.name.lower() == name.lower():
                return True
        return False
'''

        first_cat = categories_sorted[0]
        test_api_py = f'''\
"""Basic integration tests for the Inventory REST API."""
import pytest
from app import app as flask_app, store as global_store
from models import ProductStore


@pytest.fixture(autouse=True)
def reset_store():
    global_store._products.clear()
    global_store._next_id = 1
    yield


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def test_create_product_returns_201(client):
    resp = client.post("/api/v1/products", json={{
        "name": "Widget",
        "category": "{first_cat}",
        "quantity": 50,
        "price": 9.99
    }})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["id"] == 1
    assert data["name"] == "Widget"
    assert "low_stock" in data


def test_create_product_missing_field_returns_400(client):
    resp = client.post("/api/v1/products", json={{
        "name": "Widget",
        "category": "{first_cat}"
    }})
    assert resp.status_code == 400


def test_list_products_empty(client):
    resp = client.get("/api/v1/products")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_get_product_not_found_returns_404(client):
    resp = client.get("/api/v1/products/999")
    assert resp.status_code == 404


def test_get_product_returns_200(client):
    client.post("/api/v1/products", json={{
        "name": "Gadget",
        "category": "{first_cat}",
        "quantity": 10,
        "price": 5.0
    }})
    resp = client.get("/api/v1/products/1")
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Gadget"


def test_update_product_returns_200(client):
    client.post("/api/v1/products", json={{
        "name": "Gadget",
        "category": "{first_cat}",
        "quantity": 10,
        "price": 5.0
    }})
    resp = client.put("/api/v1/products/1", json={{"quantity": 20}})
    assert resp.status_code == 200
    assert resp.get_json()["quantity"] == 20


def test_delete_product_returns_200(client):
    client.post("/api/v1/products", json={{
        "name": "Gadget",
        "category": "{first_cat}",
        "quantity": 10,
        "price": 5.0
    }})
    resp = client.delete("/api/v1/products/1")
    assert resp.status_code == 200
    assert client.get("/api/v1/products/1").status_code == 404


def test_low_stock_endpoint(client):
    resp = client.get("/api/v1/products/low-stock")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)
'''

        requirements_txt = "flask\npytest\n"

        return GeneratedTask(
            task_id="SPEC2_api_design",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files={
                "app.py": app_py,
                "models.py": models_py,
                "test_api.py": test_api_py,
                "requirements.txt": requirements_txt,
            },
        )

    # -----------------------------------------------------------------------
    # Domain 2: Booking API
    # -----------------------------------------------------------------------

    def _gen_booking(self, seed: int, rng: SeededRandom) -> GeneratedTask:
        max_capacity = rng.choice([5, 10, 20])
        min_advance_hours = rng.choice([1, 2, 4])
        max_advance_days = rng.choice([7, 14, 30])
        room_types = rng.sample(
            ["conference", "meeting", "lab", "studio", "lounge", "training"],
            rng.randint(3, 4),
        )
        room_types_sorted = sorted(room_types)

        expected = {
            "domain": "booking",
            "resource": "reservation",
            "max_capacity": max_capacity,
            "min_advance_hours": min_advance_hours,
            "max_advance_days": max_advance_days,
            "room_types": room_types_sorted,
            "post_status": 201,
            "get_status": 200,
            "delete_status": 200,
            "not_found_code": "RESERVATION_NOT_FOUND",
            "room_not_found_code": "ROOM_NOT_FOUND",
            "validation_error_code": "VALIDATION_ERROR",
            "conflict_code": "TIME_CONFLICT",
            "capacity_code": "ROOM_AT_CAPACITY",
            "advance_code": "BOOKING_TOO_SOON",
            "too_far_code": "BOOKING_TOO_FAR_AHEAD",
            "response_fields": ["id", "room_id", "user_id", "start_time", "end_time", "status"],
            "required_post_fields": ["room_id", "user_id", "start_time", "end_time"],
        }

        room_types_str = ", ".join(f'`{r}`' for r in room_types_sorted)

        spec_md = f"""# SPEC2: Room Booking REST API — Full OpenAPI Specification

## Overview
Implement a REST API for room reservations. Rooms have a type and capacity.
Reservations link a user to a room for a time slot.

## Base URL
`/api/v1`

## Data Models

### Room

| Field      | Type    | Description                                     |
|------------|---------|-------------------------------------------------|
| `id`       | integer | Auto-assigned                                   |
| `name`     | string  | Required; unique                                |
| `type`     | string  | Required; one of: {room_types_str}             |
| `capacity` | integer | Required; 1 to {max_capacity}                  |

### Reservation

| Field        | Type    | Description                                           |
|--------------|---------|-------------------------------------------------------|
| `id`         | integer | Auto-assigned                                         |
| `room_id`    | integer | Required; must reference an existing room             |
| `user_id`    | string  | Required; identifier for the booking user             |
| `start_time` | string  | Required; ISO 8601 datetime (e.g. `2024-06-01T09:00:00`) |
| `end_time`   | string  | Required; ISO 8601 datetime; must be after start_time |
| `status`     | string  | `CONFIRMED` on creation; `CANCELLED` after cancellation |

## Endpoints

### POST /api/v1/rooms
Create a room.

**Request body:**
```json
{{
  "name": "string (required, unique)",
  "type": "string (required, one of: {room_types_str})",
  "capacity": "integer (required, 1-{max_capacity})"
}}
```

**Success: 201** room object. **Errors:** 400 `VALIDATION_ERROR`, 409 `DUPLICATE_NAME`.

### GET /api/v1/rooms
List all rooms. **Success: 200** list of room objects.

### POST /api/v1/reservations
Create a reservation.

**Request body:**
```json
{{
  "room_id": "integer (required)",
  "user_id": "string (required)",
  "start_time": "ISO 8601 datetime (required)",
  "end_time": "ISO 8601 datetime (required)"
}}
```

**Success response — 201 Created:**
```json
{{
  "id": 1,
  "room_id": 1,
  "user_id": "alice",
  "start_time": "2024-06-01T09:00:00",
  "end_time": "2024-06-01T10:00:00",
  "status": "CONFIRMED"
}}
```

**Error responses:**
- **404** `ROOM_NOT_FOUND` — room_id does not exist
- **400** `VALIDATION_ERROR` — missing field, end_time not after start_time,
  invalid datetime format
- **409** `TIME_CONFLICT` — room already has a CONFIRMED reservation overlapping
  the requested time slot
- **400** `BOOKING_TOO_SOON` — start_time is less than {min_advance_hours} hour(s) from now
- **400** `BOOKING_TOO_FAR_AHEAD` — start_time is more than {max_advance_days} days from now

### GET /api/v1/reservations
List reservations. Optional: `?room_id=1` and/or `?user_id=alice` and/or `?status=CONFIRMED`.

**Success: 200** list of reservation objects.

### GET /api/v1/reservations/{{reservation_id}}
Get one reservation. **Success: 200**. **Error: 404** `RESERVATION_NOT_FOUND`.

### DELETE /api/v1/reservations/{{reservation_id}}
Cancel a reservation (sets status to `CANCELLED`, does not delete the record).

**Success response — 200 OK:** reservation object with `status: CANCELLED`

**Error response: 404** `RESERVATION_NOT_FOUND`

## Validation Rules (EXACT)

1. `room.type`: must be one of {room_types_str} (case-sensitive)
2. `room.capacity`: integer in range [1, {max_capacity}] inclusive
3. `reservation.start_time` and `end_time`: must parse as ISO 8601 datetime
4. `end_time` must be strictly after `start_time`
5. Advance booking window: start_time must be at least {min_advance_hours} hour(s) from "now"
   (where "now" is the server's current UTC time)
6. Far-future limit: start_time must be at most {max_advance_days} days from "now"
7. Conflict check: a new CONFIRMED reservation conflicts if it overlaps any existing
   CONFIRMED reservation for the same room. Overlap: `new.start < existing.end AND new.end > existing.start`

## Error Response Schema

```json
{{
  "error": "ERROR_CODE",
  "message": "Human-readable description"
}}
```

## Status Codes Summary

| Scenario             | HTTP Status |
|----------------------|-------------|
| Resource created     | 201         |
| Resource found       | 200         |
| Validation failed    | 400         |
| Resource not found   | 404         |
| Time conflict        | 409         |
"""

        brief_md = """# SPEC2: Room Booking REST API (Executor Brief)

Implement the REST API endpoints in `app.py`. The workspace contains:
- `app.py` — Flask app skeleton with route decorators and TODO bodies
- `models.py` — In-memory data store (do not modify the class interface)
- `test_api.py` — Integration tests for basic behavior

The Planner has the full API specification with exact schemas, status codes,
validation rules (advance booking windows, conflict detection), and business logic.

Run tests with: `python -m pytest test_api.py -v`

The endpoints to implement:
- `POST /api/v1/rooms` — create a room
- `GET /api/v1/rooms` — list rooms
- `POST /api/v1/reservations` — create a reservation
- `GET /api/v1/reservations` — list reservations (with filters)
- `GET /api/v1/reservations/<id>` — get one reservation
- `DELETE /api/v1/reservations/<id>` — cancel a reservation
"""

        app_py = f'''\
"""Room Booking REST API — implement the TODO endpoints."""
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify
from models import BookingStore, Room, Reservation

app = Flask(__name__)
store = BookingStore()


def error_response(code, message, status):
    return jsonify({{"error": code, "message": message}}), status


def room_to_dict(r):
    return {{"id": r.id, "name": r.name, "type": r.type, "capacity": r.capacity}}


def reservation_to_dict(r):
    return {{
        "id": r.id,
        "room_id": r.room_id,
        "user_id": r.user_id,
        "start_time": r.start_time,
        "end_time": r.end_time,
        "status": r.status,
    }}


@app.route("/api/v1/rooms", methods=["POST"])
def create_room():
    # TODO: Validate required fields (name, type, capacity)
    # TODO: Validate type is one of the allowed values
    # TODO: Validate capacity in [1, {max_capacity}]
    # TODO: Check duplicate name (case-insensitive) -> 409 DUPLICATE_NAME
    # TODO: Return 201 with room dict
    pass


@app.route("/api/v1/rooms", methods=["GET"])
def list_rooms():
    # TODO: Return 200 with list of all room dicts
    pass


@app.route("/api/v1/reservations", methods=["POST"])
def create_reservation():
    # TODO: Validate required fields
    # TODO: Check room_id exists -> 404 ROOM_NOT_FOUND if not
    # TODO: Parse and validate start_time and end_time as ISO 8601
    # TODO: Validate end_time > start_time -> 400 VALIDATION_ERROR
    # TODO: Check advance booking window (min {min_advance_hours}h, max {max_advance_days}d)
    # TODO: Check for time conflicts with existing CONFIRMED reservations -> 409 TIME_CONFLICT
    # TODO: Create reservation with status=CONFIRMED; return 201
    pass


@app.route("/api/v1/reservations", methods=["GET"])
def list_reservations():
    # TODO: Filter by optional query params room_id, user_id, status
    # TODO: Return 200 with list
    pass


@app.route("/api/v1/reservations/<int:reservation_id>", methods=["GET"])
def get_reservation(reservation_id):
    # TODO: Look up; 404 RESERVATION_NOT_FOUND if missing; 200 with dict
    pass


@app.route("/api/v1/reservations/<int:reservation_id>", methods=["DELETE"])
def cancel_reservation(reservation_id):
    # TODO: Look up; 404 if missing
    # TODO: Set status to CANCELLED (do not delete the record)
    # TODO: Return 200 with updated reservation dict
    pass


if __name__ == "__main__":
    app.run(debug=True)
'''

        models_py = '''\
"""In-memory data store for the Room Booking API."""
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class Room:
    id: int
    name: str
    type: str
    capacity: int


@dataclass
class Reservation:
    id: int
    room_id: int
    user_id: str
    start_time: str
    end_time: str
    status: str  # CONFIRMED or CANCELLED


class BookingStore:
    def __init__(self):
        self._rooms: dict[int, Room] = {}
        self._reservations: dict[int, Reservation] = {}
        self._room_next_id: int = 1
        self._res_next_id: int = 1

    def add_room(self, room: Room) -> Room:
        room.id = self._room_next_id
        self._rooms[self._room_next_id] = room
        self._room_next_id += 1
        return room

    def get_room(self, room_id: int) -> Optional[Room]:
        return self._rooms.get(room_id)

    def all_rooms(self) -> List[Room]:
        return list(self._rooms.values())

    def room_name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        for r in self._rooms.values():
            if r.id == exclude_id:
                continue
            if r.name.lower() == name.lower():
                return True
        return False

    def add_reservation(self, res: Reservation) -> Reservation:
        res.id = self._res_next_id
        self._reservations[self._res_next_id] = res
        self._res_next_id += 1
        return res

    def get_reservation(self, res_id: int) -> Optional[Reservation]:
        return self._reservations.get(res_id)

    def all_reservations(self) -> List[Reservation]:
        return list(self._reservations.values())
'''

        first_room_type = room_types_sorted[0]
        test_api_py = f'''\
"""Basic integration tests for the Room Booking REST API."""
import pytest
from datetime import datetime, timezone, timedelta
from app import app as flask_app, store as global_store
from models import BookingStore


@pytest.fixture(autouse=True)
def reset_store():
    global_store._rooms.clear()
    global_store._reservations.clear()
    global_store._room_next_id = 1
    global_store._res_next_id = 1
    yield


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def future_time(hours=24):
    t = datetime.now(timezone.utc) + timedelta(hours=hours)
    return t.strftime("%Y-%m-%dT%H:%M:%S")


def test_create_room_returns_201(client):
    resp = client.post("/api/v1/rooms", json={{
        "name": "Room A",
        "type": "{first_room_type}",
        "capacity": 2
    }})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["id"] == 1
    assert data["name"] == "Room A"


def test_create_room_missing_field_returns_400(client):
    resp = client.post("/api/v1/rooms", json={{"name": "Room A"}})
    assert resp.status_code == 400


def test_list_rooms_empty(client):
    resp = client.get("/api/v1/rooms")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_create_reservation_returns_201(client):
    client.post("/api/v1/rooms", json={{
        "name": "Room A", "type": "{first_room_type}", "capacity": 2
    }})
    start = future_time(hours=4)
    end = future_time(hours=5)
    resp = client.post("/api/v1/reservations", json={{
        "room_id": 1,
        "user_id": "alice",
        "start_time": start,
        "end_time": end
    }})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["status"] == "CONFIRMED"


def test_create_reservation_missing_room_returns_404(client):
    start = future_time(hours=4)
    end = future_time(hours=5)
    resp = client.post("/api/v1/reservations", json={{
        "room_id": 999,
        "user_id": "alice",
        "start_time": start,
        "end_time": end
    }})
    assert resp.status_code == 404


def test_get_reservation_not_found_returns_404(client):
    resp = client.get("/api/v1/reservations/999")
    assert resp.status_code == 404


def test_cancel_reservation_returns_200(client):
    client.post("/api/v1/rooms", json={{
        "name": "Room A", "type": "{first_room_type}", "capacity": 2
    }})
    start = future_time(hours=4)
    end = future_time(hours=5)
    client.post("/api/v1/reservations", json={{
        "room_id": 1, "user_id": "alice",
        "start_time": start, "end_time": end
    }})
    resp = client.delete("/api/v1/reservations/1")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "CANCELLED"
'''

        requirements_txt = "flask\npytest\n"

        return GeneratedTask(
            task_id="SPEC2_api_design",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files={
                "app.py": app_py,
                "models.py": models_py,
                "test_api.py": test_api_py,
                "requirements.txt": requirements_txt,
            },
        )

    # -----------------------------------------------------------------------
    # Domain 3: User Management API
    # -----------------------------------------------------------------------

    def _gen_user_management(self, seed: int, rng: SeededRandom) -> GeneratedTask:
        max_username_len = rng.choice([20, 30, 50])
        max_bio_len = rng.choice([150, 200, 300])
        roles = rng.sample(["admin", "editor", "viewer", "moderator", "analyst", "developer"], rng.randint(3, 4))
        roles_sorted = sorted(roles)
        min_password_len = rng.choice([8, 10, 12])

        expected = {
            "domain": "user_management",
            "resource": "user",
            "max_username_len": max_username_len,
            "max_bio_len": max_bio_len,
            "roles": roles_sorted,
            "min_password_len": min_password_len,
            "post_status": 201,
            "get_status": 200,
            "delete_status": 200,
            "not_found_code": "USER_NOT_FOUND",
            "validation_error_code": "VALIDATION_ERROR",
            "duplicate_code": "USERNAME_TAKEN",
            "invalid_role_code": "INVALID_ROLE",
            "response_fields": ["id", "username", "email", "role", "bio", "active"],
            "required_post_fields": ["username", "email", "password", "role"],
            "password_not_in_response": True,
        }

        roles_str = ", ".join(f'`{r}`' for r in roles_sorted)

        spec_md = f"""# SPEC2: User Management REST API — Full OpenAPI Specification

## Overview
Implement a REST API for user management. Users have a username, email,
role, and optional bio. Passwords are accepted on creation but NEVER
returned in API responses.

## Base URL
`/api/v1`

## Data Model: User

| Field      | Type    | Description                                                   |
|------------|---------|---------------------------------------------------------------|
| `id`       | integer | Auto-assigned                                                 |
| `username` | string  | Required; max {max_username_len} chars; alphanumeric + underscores only; unique |
| `email`    | string  | Required; must contain exactly one `@` and one `.` after `@`; unique |
| `password` | string  | Required on creation; min {min_password_len} chars; NEVER returned in responses |
| `role`     | string  | Required; one of: {roles_str}                                |
| `bio`      | string  | Optional; max {max_bio_len} chars                            |
| `active`   | boolean | Defaults to `true` on creation                               |

## Endpoints

### POST /api/v1/users
Create a new user.

**Request body:**
```json
{{
  "username": "string (required, max {max_username_len} chars, alphanumeric+underscore)",
  "email": "string (required, valid email format)",
  "password": "string (required, min {min_password_len} chars)",
  "role": "string (required, one of: {roles_str})",
  "bio": "string (optional, max {max_bio_len} chars)"
}}
```

**Success response — 201 Created:**
```json
{{
  "id": 1,
  "username": "alice_smith",
  "email": "alice@example.com",
  "role": "editor",
  "bio": null,
  "active": true
}}
```
Note: `password` is NOT included in the response.

**Error responses:**
- **400** `VALIDATION_ERROR` — missing required field, username too long,
  username contains invalid characters (non-alphanumeric and non-underscore),
  email format invalid, password shorter than {min_password_len} chars,
  bio too long, or role not in allowed list
- **409** `USERNAME_TAKEN` — username already exists (case-insensitive)
- **409** `EMAIL_TAKEN` — email already exists (case-insensitive)

### GET /api/v1/users
List users. Optional: `?role=admin` and/or `?active=true`.

**Success: 200** list of user objects (no passwords).

### GET /api/v1/users/{{user_id}}
Get one user. **Success: 200**. **Error: 404** `USER_NOT_FOUND`.

### PUT /api/v1/users/{{user_id}}
Update user fields (except password).

**Request body (all optional):**
```json
{{
  "username": "new_name",
  "email": "new@example.com",
  "role": "admin",
  "bio": "Updated bio",
  "active": false
}}
```

**Success: 200** updated user object (no password). **Errors:** 404, 400, 409.

### DELETE /api/v1/users/{{user_id}}
Delete a user permanently.

**Success: 200** deleted user object. **Error: 404** `USER_NOT_FOUND`.

## Validation Rules (EXACT)

1. `username`: max {max_username_len} chars; must match `^[a-zA-Z0-9_]+$`; whitespace-only rejected; case-insensitive uniqueness
2. `email`: must contain exactly one `@`; the part after `@` must contain at least one `.`; case-insensitive uniqueness
3. `password`: min {min_password_len} characters (on creation only; not accepted on PUT)
4. `role`: must be exactly one of {roles_str} (case-sensitive)
5. `bio`: max {max_bio_len} characters if provided
6. `active`: boolean; defaults to `true` if omitted on POST

## Error Response Schema

```json
{{
  "error": "ERROR_CODE",
  "message": "Human-readable description"
}}
```

## Status Codes Summary

| Scenario             | HTTP Status |
|----------------------|-------------|
| User created         | 201         |
| User found / updated | 200         |
| Validation failed    | 400         |
| User not found       | 404         |
| Duplicate user       | 409         |
"""

        brief_md = """# SPEC2: User Management REST API (Executor Brief)

Implement the REST API endpoints in `app.py`. The workspace contains:
- `app.py` — Flask app skeleton with route decorators and TODO bodies
- `models.py` — In-memory data store (do not modify the class interface)
- `test_api.py` — Integration tests for basic behavior

The Planner has the full API specification including exact validation rules,
password handling constraints, and error codes.

Run tests with: `python -m pytest test_api.py -v`

The endpoints to implement:
- `POST /api/v1/users` — create a user
- `GET /api/v1/users` — list users
- `GET /api/v1/users/<id>` — get one user
- `PUT /api/v1/users/<id>` — update a user
- `DELETE /api/v1/users/<id>` — delete a user
"""

        first_role = roles_sorted[0]
        app_py = f'''\
"""User Management REST API — implement the TODO endpoints."""
import re
from flask import Flask, request, jsonify
from models import UserStore, User

app = Flask(__name__)
store = UserStore()


def error_response(code, message, status):
    return jsonify({{"error": code, "message": message}}), status


def user_to_dict(u):
    # NOTE: password must NEVER be included in responses
    return {{
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "role": u.role,
        "bio": u.bio,
        "active": u.active,
    }}


@app.route("/api/v1/users", methods=["POST"])
def create_user():
    # TODO: Validate required fields (username, email, password, role)
    # TODO: Validate username <= {max_username_len} chars, alphanumeric+underscore only
    # TODO: Validate email format (one @, dot after @)
    # TODO: Validate password >= {min_password_len} chars
    # TODO: Validate role is one of the allowed values
    # TODO: Validate bio <= {max_bio_len} chars if provided
    # TODO: Check USERNAME_TAKEN (case-insensitive) -> 409
    # TODO: Check EMAIL_TAKEN (case-insensitive) -> 409
    # TODO: Set active=True; do NOT return password; return 201
    pass


@app.route("/api/v1/users", methods=["GET"])
def list_users():
    # TODO: Filter by ?role= and/or ?active=
    # TODO: Return 200 with list (no passwords)
    pass


@app.route("/api/v1/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    # TODO: 404 USER_NOT_FOUND if missing; 200 with user dict (no password)
    pass


@app.route("/api/v1/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    # TODO: 404 if missing
    # TODO: Apply provided fields (username, email, role, bio, active)
    # TODO: Validate same rules as create (except password, which is not accepted)
    # TODO: Check uniqueness constraints if username/email change
    # TODO: Return 200 (no password)
    pass


@app.route("/api/v1/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    # TODO: 404 if missing; remove and return 200 with deleted user dict
    pass


if __name__ == "__main__":
    app.run(debug=True)
'''

        models_py = '''\
"""In-memory data store for the User Management API."""
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class User:
    id: int
    username: str
    email: str
    password_hash: str  # store hashed or raw for simplicity
    role: str
    bio: Optional[str]
    active: bool


class UserStore:
    def __init__(self):
        self._users: dict[int, User] = {}
        self._next_id: int = 1

    def add(self, user: User) -> User:
        user.id = self._next_id
        self._users[self._next_id] = user
        self._next_id += 1
        return user

    def get(self, user_id: int) -> Optional[User]:
        return self._users.get(user_id)

    def all(self) -> List[User]:
        return list(self._users.values())

    def delete(self, user_id: int) -> Optional[User]:
        return self._users.pop(user_id, None)

    def username_exists(self, username: str, exclude_id: Optional[int] = None) -> bool:
        for u in self._users.values():
            if u.id == exclude_id:
                continue
            if u.username.lower() == username.lower():
                return True
        return False

    def email_exists(self, email: str, exclude_id: Optional[int] = None) -> bool:
        for u in self._users.values():
            if u.id == exclude_id:
                continue
            if u.email.lower() == email.lower():
                return True
        return False
'''

        test_api_py = f'''\
"""Basic integration tests for the User Management REST API."""
import pytest
from app import app as flask_app, store as global_store
from models import UserStore


@pytest.fixture(autouse=True)
def reset_store():
    global_store._users.clear()
    global_store._next_id = 1
    yield


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def valid_user(**overrides):
    base = {{
        "username": "alice_smith",
        "email": "alice@example.com",
        "password": "secretpass123",
        "role": "{first_role}"
    }}
    base.update(overrides)
    return base


def test_create_user_returns_201(client):
    resp = client.post("/api/v1/users", json=valid_user())
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["id"] == 1
    assert data["username"] == "alice_smith"
    assert "password" not in data


def test_create_user_missing_field_returns_400(client):
    resp = client.post("/api/v1/users", json={{"username": "bob"}})
    assert resp.status_code == 400


def test_list_users_empty(client):
    resp = client.get("/api/v1/users")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_get_user_not_found_returns_404(client):
    resp = client.get("/api/v1/users/999")
    assert resp.status_code == 404


def test_get_user_returns_200(client):
    client.post("/api/v1/users", json=valid_user())
    resp = client.get("/api/v1/users/1")
    assert resp.status_code == 200
    assert resp.get_json()["username"] == "alice_smith"


def test_password_not_in_response(client):
    client.post("/api/v1/users", json=valid_user())
    resp = client.get("/api/v1/users/1")
    assert "password" not in resp.get_json()


def test_update_user_returns_200(client):
    client.post("/api/v1/users", json=valid_user())
    resp = client.put("/api/v1/users/1", json={{"bio": "Hello world"}})
    assert resp.status_code == 200
    assert resp.get_json()["bio"] == "Hello world"


def test_delete_user_returns_200(client):
    client.post("/api/v1/users", json=valid_user())
    resp = client.delete("/api/v1/users/1")
    assert resp.status_code == 200
    assert client.get("/api/v1/users/1").status_code == 404
'''

        requirements_txt = "flask\npytest\n"

        return GeneratedTask(
            task_id="SPEC2_api_design",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files={
                "app.py": app_py,
                "models.py": models_py,
                "test_api.py": test_api_py,
                "requirements.txt": requirements_txt,
            },
        )

    # -----------------------------------------------------------------------
    # Domain 4: Blog API
    # -----------------------------------------------------------------------

    def _gen_blog(self, seed: int, rng: SeededRandom) -> GeneratedTask:
        max_title_len = rng.choice([100, 150, 200])
        max_tag_count = rng.choice([3, 5, 8])
        max_tags_per_post = rng.choice([3, 5, 7])
        statuses = ["draft", "published", "archived"]
        max_content_kb = rng.choice([10, 50, 100])

        expected = {
            "domain": "blog",
            "resource": "post",
            "max_title_len": max_title_len,
            "max_tag_count": max_tag_count,
            "max_tags_per_post": max_tags_per_post,
            "statuses": statuses,
            "max_content_kb": max_content_kb,
            "post_status": 201,
            "get_status": 200,
            "delete_status": 200,
            "not_found_code": "POST_NOT_FOUND",
            "tag_not_found_code": "TAG_NOT_FOUND",
            "validation_error_code": "VALIDATION_ERROR",
            "duplicate_code": "DUPLICATE_SLUG",
            "too_many_tags_code": "TOO_MANY_TAGS",
            "response_fields": ["id", "title", "slug", "content", "author", "status", "tags", "created_at"],
            "required_post_fields": ["title", "content", "author"],
        }

        max_content_bytes = max_content_kb * 1024
        statuses_str = ", ".join(f'`{s}`' for s in statuses)

        spec_md = f"""# SPEC2: Blog REST API — Full OpenAPI Specification

## Overview
Implement a REST API for a blog platform. Posts have a title, slug, content,
author, status, and associated tags. Tags must be created before being
applied to posts.

## Base URL
`/api/v1`

## Data Models

### Tag

| Field  | Type    | Description                                    |
|--------|---------|------------------------------------------------|
| `id`   | integer | Auto-assigned                                  |
| `name` | string  | Required; unique (case-insensitive); lowercase |

### Post

| Field        | Type     | Description                                                         |
|--------------|----------|---------------------------------------------------------------------|
| `id`         | integer  | Auto-assigned                                                       |
| `title`      | string   | Required; max {max_title_len} chars                                |
| `slug`       | string   | Auto-generated from title: lowercase, spaces→hyphens, strip special chars; unique |
| `content`    | string   | Required; max {max_content_kb} KB ({max_content_bytes} bytes)      |
| `author`     | string   | Required; non-empty                                                 |
| `status`     | string   | One of: {statuses_str}; defaults to `draft` on creation           |
| `tags`       | array    | List of tag name strings (max {max_tags_per_post} tags per post)  |
| `created_at` | string   | ISO 8601 timestamp set on creation                                 |

## Slug Generation Rule
Slug is auto-generated from the title:
1. Convert to lowercase
2. Replace spaces with hyphens
3. Remove all characters that are not alphanumeric or hyphens
4. Collapse multiple consecutive hyphens into one
5. Strip leading/trailing hyphens

Example: `"Hello, World! 2024"` → `"hello-world-2024"`

## Endpoints

### POST /api/v1/tags
Create a tag.

**Request body:**
```json
{{"name": "string (required)"}}
```
Tag name is stored lowercase. **Success: 201** tag object `{{"id": 1, "name": "python"}}`.
**Error: 409** `DUPLICATE_SLUG` if tag name already exists.

### GET /api/v1/tags
List all tags. **Success: 200** list of tag objects.

### POST /api/v1/posts
Create a new post.

**Request body:**
```json
{{
  "title": "string (required, max {max_title_len} chars)",
  "content": "string (required, max {max_content_kb} KB)",
  "author": "string (required, non-empty)",
  "status": "string (optional, default: draft)",
  "tags": ["array of tag names (optional, max {max_tags_per_post} tags)"]
}}
```

**Success response — 201 Created:**
```json
{{
  "id": 1,
  "title": "Hello World",
  "slug": "hello-world",
  "content": "My first post content",
  "author": "alice",
  "status": "draft",
  "tags": ["python", "tutorial"],
  "created_at": "2024-06-01T10:00:00Z"
}}
```

**Error responses:**
- **400** `VALIDATION_ERROR` — missing required field, title too long, content too large,
  empty author, invalid status value, or more than {max_tags_per_post} tags
- **404** `TAG_NOT_FOUND` — one or more tag names in the `tags` array do not exist
- **409** `DUPLICATE_SLUG` — auto-generated slug conflicts with an existing post's slug

### GET /api/v1/posts
List posts. Optional: `?status=published` and/or `?author=alice` and/or `?tag=python`.

**Success: 200** list of post objects.

### GET /api/v1/posts/{{post_id}}
Get one post. **Success: 200**. **Error: 404** `POST_NOT_FOUND`.

### PUT /api/v1/posts/{{post_id}}
Update a post's fields.

**Request body (all optional):**
```json
{{
  "title": "Updated title",
  "content": "Updated content",
  "author": "bob",
  "status": "published",
  "tags": ["python"]
}}
```

When `title` is updated, the `slug` is regenerated automatically.
**Success: 200**. **Errors:** 404, 400, 404 TAG_NOT_FOUND, 409 DUPLICATE_SLUG.

### DELETE /api/v1/posts/{{post_id}}
Delete a post permanently.

**Success: 200** deleted post object. **Error: 404** `POST_NOT_FOUND`.

## Validation Rules (EXACT)

1. `title`: max {max_title_len} chars; whitespace-only rejected
2. `content`: max {max_content_kb} KB ({max_content_bytes} bytes, measured in UTF-8 bytes)
3. `author`: non-empty, whitespace-only rejected
4. `status`: must be one of {statuses_str} (case-sensitive)
5. `tags`: max {max_tags_per_post} tag names; each must reference an existing tag
6. Slug uniqueness is checked after auto-generation; if conflict, return 409 DUPLICATE_SLUG

## Error Response Schema

```json
{{
  "error": "ERROR_CODE",
  "message": "Human-readable description"
}}
```

## Status Codes Summary

| Scenario              | HTTP Status |
|-----------------------|-------------|
| Resource created      | 201         |
| Resource found/updated| 200         |
| Validation failed     | 400         |
| Resource not found    | 404         |
| Duplicate slug/tag    | 409         |
"""

        brief_md = """# SPEC2: Blog REST API (Executor Brief)

Implement the REST API endpoints in `app.py`. The workspace contains:
- `app.py` — Flask app skeleton with route decorators and TODO bodies
- `models.py` — In-memory data store (do not modify the class interface)
- `test_api.py` — Integration tests for basic behavior

The Planner has the full API specification with exact slug generation rules,
tag referencing constraints, content size limits, and error codes.

Run tests with: `python -m pytest test_api.py -v`

The endpoints to implement:
- `POST /api/v1/tags` — create a tag
- `GET /api/v1/tags` — list tags
- `POST /api/v1/posts` — create a post
- `GET /api/v1/posts` — list posts (with optional filters)
- `GET /api/v1/posts/<id>` — get one post
- `PUT /api/v1/posts/<id>` — update a post
- `DELETE /api/v1/posts/<id>` — delete a post
"""

        app_py = f'''\
"""Blog REST API — implement the TODO endpoints."""
import re
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from models import BlogStore, Tag, Post

app = Flask(__name__)
store = BlogStore()


def error_response(code, message, status):
    return jsonify({{"error": code, "message": message}}), status


def slugify(title: str) -> str:
    # TODO: Implement slug generation:
    # 1. lowercase, 2. spaces->hyphens, 3. remove non-alphanumeric/hyphen chars,
    # 4. collapse multiple hyphens, 5. strip leading/trailing hyphens
    pass


def tag_to_dict(t):
    return {{"id": t.id, "name": t.name}}


def post_to_dict(p):
    return {{
        "id": p.id,
        "title": p.title,
        "slug": p.slug,
        "content": p.content,
        "author": p.author,
        "status": p.status,
        "tags": p.tags,
        "created_at": p.created_at,
    }}


@app.route("/api/v1/tags", methods=["POST"])
def create_tag():
    # TODO: Validate name field is present
    # TODO: Normalize to lowercase
    # TODO: Check duplicate (case-insensitive) -> 409 DUPLICATE_SLUG
    # TODO: Return 201 with tag dict
    pass


@app.route("/api/v1/tags", methods=["GET"])
def list_tags():
    # TODO: Return 200 with list of all tags
    pass


@app.route("/api/v1/posts", methods=["POST"])
def create_post():
    # TODO: Validate required fields (title, content, author)
    # TODO: Validate title <= {max_title_len} chars; reject whitespace-only
    # TODO: Validate content <= {max_content_kb} KB (in UTF-8 bytes)
    # TODO: Validate author non-empty
    # TODO: Validate status if provided (must be one of draft/published/archived)
    # TODO: Validate tags array <= {max_tags_per_post} items; each tag name must exist -> 404 TAG_NOT_FOUND
    # TODO: Generate slug from title; check slug uniqueness -> 409 DUPLICATE_SLUG
    # TODO: Default status to 'draft' if not provided
    # TODO: Return 201 with post dict
    pass


@app.route("/api/v1/posts", methods=["GET"])
def list_posts():
    # TODO: Filter by ?status=, ?author=, ?tag=
    # TODO: Return 200 with list of post dicts
    pass


@app.route("/api/v1/posts/<int:post_id>", methods=["GET"])
def get_post(post_id):
    # TODO: 404 POST_NOT_FOUND if missing; 200 with post dict
    pass


@app.route("/api/v1/posts/<int:post_id>", methods=["PUT"])
def update_post(post_id):
    # TODO: 404 if missing
    # TODO: Apply provided fields; regenerate slug if title changes
    # TODO: Validate constraints; check tag existence; check slug uniqueness
    # TODO: Return 200 with updated post dict
    pass


@app.route("/api/v1/posts/<int:post_id>", methods=["DELETE"])
def delete_post(post_id):
    # TODO: 404 if missing; remove and return 200
    pass


if __name__ == "__main__":
    app.run(debug=True)
'''

        models_py = '''\
"""In-memory data store for the Blog API."""
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class Tag:
    id: int
    name: str


@dataclass
class Post:
    id: int
    title: str
    slug: str
    content: str
    author: str
    status: str
    tags: List[str]
    created_at: str


class BlogStore:
    def __init__(self):
        self._tags: dict[int, Tag] = {}
        self._posts: dict[int, Post] = {}
        self._tag_next_id: int = 1
        self._post_next_id: int = 1

    def add_tag(self, tag: Tag) -> Tag:
        tag.id = self._tag_next_id
        self._tags[self._tag_next_id] = tag
        self._tag_next_id += 1
        return tag

    def get_tag_by_name(self, name: str) -> Optional[Tag]:
        for t in self._tags.values():
            if t.name == name.lower():
                return t
        return None

    def all_tags(self) -> List[Tag]:
        return list(self._tags.values())

    def add_post(self, post: Post) -> Post:
        post.id = self._post_next_id
        self._posts[self._post_next_id] = post
        self._post_next_id += 1
        return post

    def get_post(self, post_id: int) -> Optional[Post]:
        return self._posts.get(post_id)

    def all_posts(self) -> List[Post]:
        return list(self._posts.values())

    def delete_post(self, post_id: int) -> Optional[Post]:
        return self._posts.pop(post_id, None)

    def slug_exists(self, slug: str, exclude_id: Optional[int] = None) -> bool:
        for p in self._posts.values():
            if p.id == exclude_id:
                continue
            if p.slug == slug:
                return True
        return False
'''

        test_api_py = f'''\
"""Basic integration tests for the Blog REST API."""
import pytest
from app import app as flask_app, store as global_store
from models import BlogStore


@pytest.fixture(autouse=True)
def reset_store():
    global_store._tags.clear()
    global_store._posts.clear()
    global_store._tag_next_id = 1
    global_store._post_next_id = 1
    yield


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def test_create_tag_returns_201(client):
    resp = client.post("/api/v1/tags", json={{"name": "python"}})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["name"] == "python"


def test_list_tags_empty(client):
    resp = client.get("/api/v1/tags")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_create_post_returns_201(client):
    resp = client.post("/api/v1/posts", json={{
        "title": "Hello World",
        "content": "My first post",
        "author": "alice"
    }})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["id"] == 1
    assert data["slug"] == "hello-world"
    assert data["status"] == "draft"


def test_create_post_missing_field_returns_400(client):
    resp = client.post("/api/v1/posts", json={{
        "title": "No content post"
    }})
    assert resp.status_code == 400


def test_list_posts_empty(client):
    resp = client.get("/api/v1/posts")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_get_post_not_found_returns_404(client):
    resp = client.get("/api/v1/posts/999")
    assert resp.status_code == 404


def test_update_post_returns_200(client):
    client.post("/api/v1/posts", json={{
        "title": "Hello World",
        "content": "Content",
        "author": "alice"
    }})
    resp = client.put("/api/v1/posts/1", json={{"status": "published"}})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "published"


def test_delete_post_returns_200(client):
    client.post("/api/v1/posts", json={{
        "title": "Delete me",
        "content": "Content",
        "author": "alice"
    }})
    resp = client.delete("/api/v1/posts/1")
    assert resp.status_code == 200
    assert client.get("/api/v1/posts/1").status_code == 404


def test_post_with_tag_requires_tag_to_exist(client):
    resp = client.post("/api/v1/posts", json={{
        "title": "Tagged post",
        "content": "Content",
        "author": "alice",
        "tags": ["nonexistent_tag"]
    }})
    assert resp.status_code == 404
'''

        requirements_txt = "flask\npytest\n"

        return GeneratedTask(
            task_id="SPEC2_api_design",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files={
                "app.py": app_py,
                "models.py": models_py,
                "test_api.py": test_api_py,
                "requirements.txt": requirements_txt,
            },
        )
