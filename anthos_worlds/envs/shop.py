"""Shop world: a WebShop-style catalog with search, cart, and checkout."""

from __future__ import annotations

import random
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
    {"id": "p8", "name": "usb-c hub", "category": "accessory", "price": 45.0, "rating": 4.5},
    {"id": "p9", "name": "desk lamp", "category": "accessory", "price": 32.0, "rating": 4.1},
]


class ShopEnv(Environment):
    name = "shop"
    description = "An online store. Search the catalog, manage a cart, check out."

    def tasks(self) -> List[Task]:
        return [
            self._task("shop.laptop", "laptop", 1, 800.0, 4.5),
            self._task("shop.gifts", "gift", 2, 50.0, 0.0),
        ]

    def generate(self, rng: random.Random) -> Task:
        category = rng.choice(["laptop", "gift", "accessory"])
        pool = [p for p in _CATALOG if p["category"] == category]
        count = rng.randint(1, min(2, len(pool)))
        targets = rng.sample(pool, count)
        min_rating = min(p["rating"] for p in targets)
        max_total = round(sum(p["price"] for p in targets) + rng.choice([5, 15, 30]))
        return self._task(f"shop.gen{rng.randrange(10**6)}",
                          category, count, float(max_total), min_rating)

    def solve(self, task: Task) -> List[str]:
        s = task.spec
        qualifying = sorted(
            (p for p in _CATALOG
             if p["category"] == s["category"] and p["rating"] >= s["min_rating"]),
            key=lambda p: p["price"])
        picks = qualifying[:s["count"]]  # cheapest qualifying set fits any budget
        return ([f"search {s['category']}"]
                + [f"add {p['id']}" for p in picks] + ["checkout"])

    def _task(self, tid: str, category: str, count: int,
              max_total: float, min_rating: float) -> Task:
        rating_clause = (f", each with a rating of at least {min_rating}"
                         if min_rating > 0 else "")
        plural = "different items" if count > 1 else "item"
        instruction = (f"Buy exactly {count} {category} {plural}{rating_clause}, "
                       f"with a combined price under ${max_total:.0f}, then checkout.")
        return Task(tid, instruction, spec={"category": category, "count": count,
                                            "max_total": max_total,
                                            "min_rating": min_rating})

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
        s = self.task.spec
        items = [self._find(i) for i in self.cart]
        ok = (len(items) == s["count"]
              and all(p["category"] == s["category"] for p in items)
              and sum(p["price"] for p in items) < s["max_total"]
              and all(p["rating"] >= s["min_rating"] for p in items))
        return 1.0 if ok else 0.0
