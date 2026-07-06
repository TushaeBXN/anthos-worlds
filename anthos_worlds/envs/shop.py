"""Shop world: a WebShop-style catalog with search, cart, and checkout."""

from __future__ import annotations

from typing import List

from ..core import Environment, StepResult, Task

_CATALOG = [
    {"id": "p1", "name": "aurora laptop 14", "category": "laptop", "price": 749.0, "rating": 4.6},
    {"id": "p2", "name": "titan laptop pro", "category": "laptop", "price": 1299.0, "rating": 4.8},
    {"id": "p3", "name": "budget laptop go", "category": "laptop", "price": 499.0, "rating": 3.9},
    {"id": "p4", "name": "ceramic mug set", "category": "gift", "price": 18.0, "rating": 4.7},
    {"id": "p5", "name": "scented candle", "category": "gift", "price": 12.0, "rating": 4.4},
    {"id": "p6", "name": "leather notebook", "category": "gift", "price": 29.0, "rating": 4.9},
    {"id": "p7", "name": "wireless mouse", "category": "accessory", "price": 25.0, "rating": 4.2},
]


class ShopEnv(Environment):
    name = "shop"
    description = "An online store. Search the catalog, manage a cart, check out."

    def tasks(self) -> List[Task]:
        return [
            Task("shop.laptop",
                 "Buy exactly one laptop that costs under $800 and has a rating "
                 "of at least 4.5, then checkout."),
            Task("shop.gifts",
                 "Buy exactly two different gift items with a combined price "
                 "under $50, then checkout."),
        ]

    def actions_help(self) -> str:
        return "search <query> | view <id> | add <id> | remove <id> | cart | checkout"

    def reset(self, task: Task) -> str:
        self.task = task
        self.cart: List[str] = []
        return ("Welcome to AnthosShop. The catalog has laptops, gifts, and "
                "accessories. Try: search laptop")

    def step(self, action: str) -> StepResult:
        verb, rest = self.parse(action)
        if verb == "search":
            q = rest.lower()
            hits = [p for p in _CATALOG if q in p["name"] or q in p["category"]]
            if not hits:
                return StepResult("no results.")
            return StepResult("\n".join(
                f"[{p['id']}] {p['name']} — ${p['price']:.2f}, rating {p['rating']}"
                for p in hits))
        if verb == "view":
            p = self._find(rest)
            if not p:
                return StepResult(f"no product {rest!r}")
            return StepResult(f"{p['name']} | category: {p['category']} | "
                              f"price: ${p['price']:.2f} | rating: {p['rating']}")
        if verb == "add":
            p = self._find(rest)
            if not p:
                return StepResult(f"no product {rest!r}")
            if p["id"] in self.cart:
                return StepResult("already in cart.")
            self.cart.append(p["id"])
            return StepResult(f"added {p['name']} to cart.")
        if verb == "remove":
            if rest.strip() in self.cart:
                self.cart.remove(rest.strip())
                return StepResult("removed.")
            return StepResult("not in cart.")
        if verb == "cart":
            items = [self._find(i) for i in self.cart]
            total = sum(p["price"] for p in items)
            listing = ", ".join(p["name"] for p in items) or "(empty)"
            return StepResult(f"cart: {listing} — total ${total:.2f}")
        if verb == "checkout":
            return StepResult("order placed.", self._score(), True)
        return StepResult(f"unknown command: {action!r}. Commands: {self.actions_help()}")

    def _find(self, pid: str):
        pid = pid.strip()
        return next((p for p in _CATALOG if p["id"] == pid), None)

    def _score(self) -> float:
        items = [self._find(i) for i in self.cart]
        if self.task.id == "shop.laptop":
            return 1.0 if (len(items) == 1 and items[0]["category"] == "laptop"
                           and items[0]["price"] < 800 and items[0]["rating"] >= 4.5) else 0.0
        if self.task.id == "shop.gifts":
            gifts = [p for p in items if p["category"] == "gift"]
            ok = (len(items) == 2 and len(gifts) == 2
                  and sum(p["price"] for p in gifts) < 50)
            return 1.0 if ok else 0.0
        return 0.0
