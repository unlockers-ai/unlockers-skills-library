<!-- Generated from docs/accidental-complexity-guide.md by tools/sync-references.py. Edit the source, not this copy. -->

# Accidental Complexity Guide

A reference for detecting and eliminating accidental complexity in code.

> **Language note:** the principles below are language-agnostic. Code examples are written
> in Python for concreteness; the smell, the reasoning, and the refactoring apply equally
> to Java, C#, TypeScript, Go, Kotlin, Ruby, etc. Where a detection pattern is shown as a
> regex, treat it as "search your codebase for the equivalent construct."

## What Is Accidental Complexity?

Fred Brooks distinguished between **essential complexity** (inherent to the problem
domain) and **accidental complexity** (introduced by our solution). Accidental complexity
is code that doesn't serve the business problem — it exists only because of implementation
choices, defensive habits, or premature abstraction.

**Why it matters:**
- Increases cognitive load for readers
- Makes code harder to change safely
- Hides the essential logic under ceremony
- Compounds over time ("complexity attracts complexity")

## Priority Smells

### 1. Null/Optional Complexity (Critical Priority)

The most important smell to eliminate. Every null/`None`/`Optional` check is a design
decision that should be challenged. (`None` in Python, `null` in Java/C#/JS, `nil` in
Go/Ruby, `Option`/`Optional` wrappers — same idea.)

#### 1.1 Null Checks in Domain Logic

**Smell:** `if x is not None:` / `if (x != null)` / `if x:` guards inside domain/service code.

**Why it's bad:** Null checks are defensive programming. In domain logic, they signal that
the contract is unclear — who is responsible for ensuring the value exists?

**Detection:**
- Search for null/None guards at the start of methods, and nested null checks.

**Bad:**
```python
class PriceCalculator:
    def calculate(self, product: Product, discount: Discount | None = None) -> Money:
        base = product.base_price
        if discount is not None:
            if discount.is_valid():
                base = base - discount.amount
        return base
```

**Good — push the decision up:**
```python
class PriceCalculator:
    def calculate(self, product: Product) -> Money:
        return product.base_price

    def calculate_with_discount(self, product: Product, discount: Discount) -> Money:
        if not discount.is_valid():
            raise InvalidDiscountError(discount)
        return product.base_price - discount.amount
```

**When it's OK:**
- Adapter code translating external data (null is the reality of the external world)
- Repository code handling "not found" cases
- Never in domain/service logic

#### 1.2 Optional Arguments Never Used as Null

**Smell:** an optional/nullable parameter that no caller ever passes as null.

**Why it's bad:** The optionality is a lie. It adds complexity (null checks) for a case
that never happens. Often a leftover from "maybe we'll need this" thinking.

**Detection:**
- Find optional/nullable parameters, then search all callers — does anyone pass null or
  omit the argument?

**Bad:**
```python
def send_notification(user: User, channel: Channel | None = None) -> None:
    if channel is None:
        channel = Channel.EMAIL
    # ... rest of logic
```

If every caller passes a channel, remove the optionality:

**Good:**
```python
def send_notification(user: User, channel: Channel) -> None:
    # ... logic without null check
```

**When it's OK:**
- Genuinely optional configuration with sensible defaults
- Builder pattern where partial construction is intentional

#### 1.3 Defensive Null Returns

**Smell:** Methods that return a nullable/`Optional` when null means "something went wrong."

**Why it's bad:** Pushes error handling to every caller. The caller now needs a null
check, spreading complexity.

**Bad:**
```python
def find_user(user_id: UserId) -> User | None:
    # Returns None if not found, None if invalid ID, None if DB error...
    ...
```

**Good — be explicit about failure modes:**
```python
def get_user(user_id: UserId) -> User:
    """Raises UserNotFoundError if user doesn't exist."""
    ...

def find_user(user_id: UserId) -> User | None:
    """Returns None only for 'not found'. Raises on other errors."""
    ...
```

#### 1.4 Guards on Collections

**Principle:** there should be no conditional on a list, set, map, or other collection —
neither to check it is non-empty before operating on it, nor to check it is empty in order
to skip. Collection operations (iteration, filtering, exclusion, merging, summing,
comprehensions, lookup-with-default) should already be correct no-ops for the empty case.
If a caller needs an emptiness guard before calling a collection method, the method itself
has a design hole — fix it there rather than guarding every call site.

**Why this one can't be searched:** emptiness guards take many shapes — `if items:`,
`if not items:`, `if len(items) > 0:`, `if items != []:` — and none of them mention `None`,
so the searches in 1.1 miss this class entirely. Other languages have their own shapes
(`isEmpty()`, `.length`, `.Any()`); the principle is the same everywhere.

Treat this as a **design principle to reason about at every conditional whose subject is a
collection**, not a pattern to search for.

**Detection:** for each such conditional, ask — *if this collection were empty, would the
guarded code still be correct if it simply ran anyway?* If yes, the guard is accidental
complexity. Delete it, and if the empty case needs handling, push it into the collection
method or type itself.

**Bad — every call site pays for the empty case:**
```python
if excluded_ids:
    results = results.excluding(excluded_ids)
```

**Good — the operation is a no-op on empty, so the call is unconditional:**
```python
class SearchResults:
    def excluding(self, excluded_ids: set[ResultId]) -> "SearchResults":
        if not excluded_ids:
            return self
        return SearchResults([r for r in self.results if r.id not in excluded_ids])

# call site:
results = results.excluding(excluded_ids)
```

The single guard inside `excluding` is not the same smell: it is one deliberate
early-return in the type that owns the operation, replacing a guard repeated at every
caller. Often it isn't needed at all — a filter over an empty exclusion set already returns
everything.

**When it's OK:**
- The branches genuinely do different things, rather than one branch skipping a call that
  would have been a no-op — e.g. choosing between two distinct code paths based on
  collection contents.
- Reporting emptiness to a user ("no results found") is a real behaviour, not a guard.

---

### 2. Exception Handling Complexity (Critical Priority)

> **The default strategy is to not catch at all** — let the exception reach the top and be
> turned into an error there. Everything below is about the cases that deviate from it. See
> [`code-design-rules.md`](code-design-rules.md) rule 3.

#### 2.1 Multi-Layer Exception Handling

**Smell:** The same exception is caught at multiple layers (adapter → service → controller).

**Why it's bad:** Each layer adds try/except ceremony. Often the middle layers just
re-raise or wrap without adding value.

**Detection:**
- Multiple try/catch blocks in a call chain.
- `except SomeError: raise` or catch-and-rewrap patterns; count catches per file/module.

**Bad:**
```python
# adapter.py
def fetch_data():
    try:
        return client.get()
    except ClientError as e:
        raise DataFetchError(e)

# service.py
def process():
    try:
        data = fetch_data()
    except DataFetchError:
        raise ProcessingError("Failed to fetch")

# controller.py
def handle():
    try:
        process()
    except ProcessingError as e:
        return error_response(e)
```

**Good — handle at boundaries only:**
```python
# adapter.py — translate external errors to domain errors
def fetch_data():
    try:
        return client.get()
    except ClientError as e:
        raise DataFetchError(e)

# service.py — let errors propagate
def process():
    data = fetch_data()
    return transform(data)

# controller.py — use the framework's error handler
@app.exception_handler(DomainError)
def handle_domain_error(e: DomainError):
    return error_response(e)
```

**When it's OK:**
- Adapter boundaries (translating library errors to domain errors)
- Framework-level error handlers
- Cleanup/resource management (but prefer context managers / try-with-resources / `defer`)

#### 2.2 Catching Broad Exceptions

**Smell:** `except Exception:` / `catch (Exception)` / bare `except:`.

**Why it's bad:** Catches everything, including programming errors. Hides bugs.

**Bad:**
```python
try:
    result = complex_operation()
except Exception:
    logger.error("Something went wrong")
    return None
```

**Good:**
```python
try:
    result = complex_operation()
except SpecificNetworkError as e:
    logger.error("Network failed", exc_info=e)
    raise ServiceUnavailableError() from e
```

#### 2.3 Re-Raising the Same Exception Type

**Smell:** catch `FooError` only to throw a new `FooError`.

**Why it's bad:** Adds a try/catch block that does nothing useful. If you're not
translating or enriching, don't catch.

#### 2.4 A Catch Standing In for a Missing Type

**Smell:** the exception is thrown deep in the domain because an illegal value got that far,
and a `try` is added where it surfaces.

**Why it's bad:** it treats a construction-time problem as a runtime one, at every site that
handles the value rather than the one that creates it.

**Good:** reject the value in its own type instead — see
[`code-design-rules.md`](code-design-rules.md) rules 1 and 3.

---

## General Code Smells

### 3. Boolean Flag Parameters

**Smell:** a boolean parameter that significantly changes behaviour
(`get_users(include_deleted=False)`).

**Why it's bad:** The function does two different things. Callers must understand the flag.
Often leads to internal `if flag:` branches.

**Detection:** parameters named `include_*`, `with_*`, `is_*`, `should_*`, `enable_*`;
boolean parameters generally.

**Bad:**
```python
def get_users(include_inactive: bool = False) -> list[User]:
    query = select(User)
    if not include_inactive:
        query = query.where(User.active == True)
    return session.execute(query).all()
```

**Good — two methods with clear intent:**
```python
def get_active_users() -> list[User]:
    return session.execute(select(User).where(User.active == True)).all()

def get_all_users() -> list[User]:
    return session.execute(select(User)).all()
```

**When it's OK:** configuration flags that don't change core behaviour; feature flags at
system boundaries.

### 4. Long Parameter Lists

**Smell:** functions with more than ~4 parameters.

**Why it's bad:** Hard to remember order, easy to swap arguments, signals the function
does too much.

**Bad:**
```python
def create_order(
    customer_id, product_id, quantity, shipping_address,
    billing_address, discount_code, gift_wrap, delivery_date,
) -> Order:
    ...
```

**Good — introduce a parameter object:**
```python
@dataclass
class OrderRequest:
    customer_id: int
    product_id: int
    quantity: int
    shipping: Address
    billing: Address
    options: OrderOptions

def create_order(request: OrderRequest) -> Order:
    ...
```

### 5. Primitive Obsession

> Minor as a *review finding*, first as a *refactoring move* — see
> [`code-design-rules.md`](code-design-rules.md) rule 1 for why this and §6 are what to
> reach for before anything structural.

**Smell:** Using primitive types (str, int) for domain concepts.

**Why it's bad:** No type safety, no place for behaviour, easy to mix up parameters of the
same type.

**Bad:**
```python
def transfer(from_account: str, to_account: str, amount: int) -> None:
    ...  # Easy to swap from/to; amount could be negative
```

**Good:**
```python
@dataclass(frozen=True)
class AccountId:
    value: str

@dataclass(frozen=True)
class Money:
    cents: int
    def __post_init__(self):
        if self.cents < 0:
            raise ValueError("Money cannot be negative")

def transfer(source: AccountId, destination: AccountId, amount: Money) -> None:
    ...
```

### 6. Data Clumps

> The positive version of this — where the type lives, and why it is immutable — is
> [`code-design-rules.md`](code-design-rules.md) rule 2.

**Smell:** The same group of parameters/fields appears together in multiple places.

**Why it's bad:** Signals a missing abstraction. Changes require updating multiple places.

**Detection:** two shapes hide from a per-function read and need the whole file:
- the same tuple of arguments threaded down a call chain unchanged, from a dispatcher
  through helpers to a builder, even when every signature on the way is short;
- several small dataclasses in one module whose leading fields are identical — the clump
  has been written once per variant and named in none of them.

**Bad:**
```python
def format_address(street, city, postal_code) -> str: ...
def validate_address(street, city, postal_code) -> bool: ...
def ship_to(street, city, postal_code) -> None: ...
```

**Good:** introduce an `Address` value object and pass it around.

### 7. Middle Man / Unnecessary Delegation

**Smell:** A class that only delegates to another class without adding value.

**Why it's bad:** Extra indirection with no benefit. Caller could use the delegate directly.

**Bad:**
```python
class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo
    def get(self, id): return self.repo.get(id)
    def save(self, user): self.repo.save(user)
    def delete(self, id): self.repo.delete(id)
```

**Good:** remove the middle man and let callers use the repository directly, or add actual
business logic to justify the service layer.

### 8. Feature Envy

**Smell:** A method that uses more features of another class than its own.

**Why it's bad:** Logic is in the wrong place. The method should probably live on the
other class.

**Detection:** methods with many `other_object.field` accesses; chained access like
`self.order.customer.address.city`. Also — and this is where it hides best — the
module-level private function whose parameters are all one type we own, or that reads
several fields of one such type: that is a method the type is missing. List a module's
free functions with their parameter types; the ones that take a single domain object
belong on it. A function that receives a value *and* an object already carrying that
value is the same smell with a bug attached.

**Good:** move the behaviour onto the class that owns the data
(`order.customer.format_shipping_label()`).

### 9. Speculative Generality (YAGNI)

**Smell:** Abstractions, parameters, or code paths that aren't used yet.

**Why it's bad:** Complexity for imagined future needs. The future rarely matches predictions.

**Detection:** abstract base classes / interfaces with one implementation; parameters
always passed the same value; code paths never executed.

**Good:** remove the abstraction until you have a second real use case.

### 10. God Objects / Large Classes

**Smell:** Classes with many responsibilities, methods, and fields.

**Detection:** >10 public methods, >5 dependencies, file size >300 lines — as a screen.
Those counts say "look here"; they do not say what is inside. Get the screen from the
tools (`pylint` R0902 counts every `self.x` set in `__init__`, private ones included;
R0904 counts *public* methods only; CodeScene flags a constructor over 5 arguments), then
look inside with the **method × attribute usage matrix**, which no shipped tool computes:

1. `A` = the attributes assigned on `self` in `__init__`; `M` = the methods, `__init__`
   excluded. Members = `|A| + |M|`; past about six, expect the matrix to show blocks.
2. Fill `U[m][a] = 1` when method `m` reads or writes `self.a` directly (AST:
   `Attribute(value=Name("self"), attr=a)`). Direct use only — a method that reaches an
   attribute solely by calling another method is dispatch, and shows up as an empty row.
3. Read off, in this order:
   - **TCC** = share of method pairs that touch at least one common attribute. Below
     about 0.3 the class is several classes. (Do not use LCOM4 / connected components
     alone: one attribute everybody touches, or self-calls, glue the graph into one
     component and hide everything — which is why CodeScene's cohesion check and the
     `cohesion` package can both stay silent on a class the matrix splits in five.)
   - **Sole-touched attributes**: an attribute used by exactly one method is a
     dependency that belongs to that method, not the class.
   - **Empty rows**: methods touching no attribute — pure dispatch or a free function.
   - **Blocks**: remove the plumbing attributes (a clock, a logger, the one repository
     everyone reads) and recompute the components of the "shares an attribute" graph.
     What remains connected is a candidate class, and its column set is that class's
     constructor.

For Python, [`skills/review-complexity/scripts/class_cohesion.py`](../../review-complexity/scripts/class_cohesion.py)
`FILE [CLASS] [--plumbing a,b]` prints the matrix and the four readings, if you would
rather not walk the AST yourself.

The numbers inform the assessment; they do not make it. A class can score badly on TCC
and be the right shape (a façade over ports is one), so say what the split would buy
before proposing it.

**Refactoring:** extract cohesive groups of methods into separate classes — the blocks.

### 11. Unnecessary State

**Smell:** Instance attributes that could be local variables or parameters.

**Why it's bad:** State makes reasoning harder. Stateless functions are easier to test and
compose.

**Bad:**
```python
class Calculator:
    def __init__(self): self.current_value = 0
    def add(self, x): self.current_value += x
    def get_result(self): return self.current_value
```

**Good:**
```python
def add(a: int, b: int) -> int:
    return a + b
```

### 12. Nested Conditionals (Arrow Anti-Pattern)

**Smell:** Deeply nested if/else blocks forming an "arrow" shape.

**Detection:** indentation depth >3 levels; multiple nested `if` statements.

**Bad:**
```python
def process(order):
    if order is not None:
        if order.is_valid():
            if order.customer.is_active():
                if order.has_stock():
                    return fulfill(order)
                else:
                    return out_of_stock()
            else:
                return inactive_customer()
        else:
            return invalid_order()
    else:
        return no_order()
```

**Good — use early returns (guard clauses):**
```python
def process(order):
    if order is None:
        return no_order()
    if not order.is_valid():
        return invalid_order()
    if not order.customer.is_active():
        return inactive_customer()
    if not order.has_stock():
        return out_of_stock()
    return fulfill(order)
```

### 13. Temporary Fields

**Smell:** Instance attributes that are only set in some code paths.

**Why it's bad:** The object's state is unpredictable. Callers don't know which fields are valid.

**Good — return a result object instead of mutating self:**
```python
@dataclass
class ReportResult:
    summary: Summary
    details: Details

class ReportGenerator:
    def generate(self, data: Data) -> ReportResult:
        return ReportResult(summary=summarize(data), details=extract_details(data))
```

### 14. Mutable Default Arguments

**Smell:** a mutable value used as a default argument (Python: `def foo(items=[])`).

**Why it's bad:** the default is shared across calls — a classic Python gotcha; analogous
shared-mutable-default bugs exist in other languages.

**Bad:**
```python
def append_to(item: str, target: list[str] = []) -> list[str]:
    target.append(item)
    return target
```

**Good:**
```python
def append_to(item: str, target: list[str] | None = None) -> list[str]:
    if target is None:
        target = []
    target.append(item)
    return target
```

Or better — avoid the mutation entirely.

### 15. Inappropriate Intimacy

**Smell:** Classes that know too much about each other's internals.

**Detection:** accessing private attributes; long chains of attribute access.

**Refactoring:** add methods to expose needed behaviour without exposing internals.

### 16. Inconsistent Abstraction Levels

**Smell:** A function that mixes high-level operations with low-level details.

**Bad:**
```python
def create_user(name: str, email: str) -> User:
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        raise InvalidEmailError(email)
    user = User(name=name, email=email)
    connection = psycopg2.connect(DATABASE_URL)
    cursor = connection.cursor()
    cursor.execute("INSERT INTO users ...")
    connection.commit()
    return user
```

**Good:**
```python
def create_user(name: str, email: Email) -> User:
    user = User(name=name, email=email)
    user_repository.save(user)
    return user
```

### 17. Dead Code / Unreachable Branches

**Smell:** Code that can never execute (`if False:`, conditions always true/false,
uncalled methods).

**Action:** delete it.

### 18. Anemic Domain Model

**Smell:** Domain objects that are just data containers with no behaviour.

**Why it's bad:** Business logic ends up in services, scattered across the codebase.

**Good — put behaviour on the model:**
```python
@dataclass
class Order:
    items: list[Item]
    status: OrderStatus

    def total(self) -> Money:
        return sum((item.price for item in self.items), Money.zero())

    def can_cancel(self) -> bool:
        return self.status == OrderStatus.PENDING

    def cancel(self) -> None:
        if not self.can_cancel():
            raise CannotCancelError(self)
        self.status = OrderStatus.CANCELLED
```

### 19. Long Functions

**Smell:** a function past ~30 lines, usually doing more than one job.

**Why it's bad:** hard to read as a whole, hard to test in isolation, hard to change
without touching unrelated logic.

**Detection:** distance between one function definition and the next.

**Good:** no single fix — extracting a helper is often enough; on a use case or a service,
separating deciding from applying is the one worth reaching for first. See
[`code-design-rules.md`](code-design-rules.md) rule 4.

---

## Severity Model

| Severity | Indicators |
|----------|------------|
| Critical | Null checks in domain logic, emptiness guards before operations that are already safe on empty, optional params never used as null, exception handling masking design flaws |
| Major | Multi-layer try/catch, boolean flags splitting behaviour, unnecessary delegation, feature envy, god objects, long functions |
| Minor | Long param lists, speculative generality, unnecessary state, primitive obsession, nested conditionals |

## Tools That Measure These

Before writing an AST walker, check this table: a shipped rule is more precise than the
one you would write in the next ten minutes (it already knows that a private attribute
is still an attribute, that a keyword-only argument still counts, that `async def` is a
method). Use its output to *inform* the finding and the trade-off, not to decide it —
and say which tool and which threshold the number came from. CodeScene, where you have it,
is reachable through its MCP server (`code_health_review` on one file). These are dev
tools: installing another one is cheap and always allowed. Hand-rolling what one of them
already does is the expensive option.

The rule codes are Python's, like the examples. Other ecosystems have the same rules under
other names — PMD and Checkstyle, ESLint and SonarJS, detekt, golangci-lint; CodeScene,
`lizard` and `jscpd` are language-agnostic. Find the equivalent before reaching for a
script.

| Smell (§) | Tool and rule | Trap / note |
|---|---|---|
| 1.1–1.2 null checks, optional never null | `pyright` `reportUnnecessaryComparison`; `mypy --warn-unreachable` | Only as good as the annotations: an untyped parameter hides both. |
| 1.3 defensive null returns | `pyright` `reportOptionalMemberAccess` on the callers | Finds the cost (every caller guards), not the cause. |
| 2.1 multi-layer catches | `ruff` TRY201 (re-raise without `from`), `pylint` W0706 (handler that only raises), `pylint.extensions.broad_try_clause` W0717 | Nothing counts catches per call chain; grep `except` per module and read. |
| 2.2 broad except | `ruff` BLE001; `pylint` W0718 | Both accept a broad catch that re-raises; that is still worth a look. |
| 3 boolean flag parameter | `ruff` FBT001 / FBT002 | FBT002 is the default-valued one — the flag that "splits behaviour". |
| 4 long parameter list | `ruff` PLR0913 (5), PLR0917 positional; `pylint` R0913 / R0917; CodeScene `function_max_arguments` 4, `constructor_max_arguments` 5 | A dataclass `__init__` is exempt in ruff, not in CodeScene. |
| 5 primitive obsession | CodeScene `file_primitive_obsession_percentage_for_warning` 30; `ruff` PLR2004 magic values | The percentage is of *arguments* typed as primitives; a `str` slug that is really a credential scores the same as a name. |
| 6 data clumps | none | Read the signatures of a module together; CodeScene's argument-count rules are the nearest proxy. |
| 7 middle man | none | `pylint` R0903 lists classes with few public methods — a starting list, mostly false positives. |
| 8 feature envy | `ruff` PLR6301 (`--preview`) / `pylint.extensions.no_self_use` R6301: a method that never touches `self` | Only catches the extreme case. A module-level `_helper(record)` is not a method at all, so no tool sees it — list the free functions and their parameter types by hand. |
| 9 speculative generality | `vulture --min-confidence 100`; `ruff` ARG001 / ARG002; `pylint` W0613 | Unused *parameters* are the cheap tell; unused *branches* need a reader. |
| 10 god object | `pylint` R0902 (attributes, private included), R0904 (public methods only); CodeScene constructor over-injection; then the matrix above | `wemake` WPS230 and the `cohesion` package count public members / `def` only — both under-count here, where everything is private and async. |
| 11 unnecessary state | `pylint` R0903 inverted: a class with state and one public method | Judgement call; no tool. |
| 12 nested conditionals | `ruff` PLR1702 (`--preview`), SIM102; `pylint` R1702; CodeScene bumpy road, `function_nesting_depth_warning` 4 | CodeScene's "bumpy road" (two nested blocks in one function) fires earlier than the depth rules. |
| 13 temporary field | `pylint` W0201 attribute-defined-outside-init | Catches the attribute set in one method only. The dataclass whose fields are `None` per variant is the same smell and no tool sees it; see §6. |
| 14 mutable default | `ruff` B006; `pylint` W0102 | Solved; no judgement needed. |
| 15 inappropriate intimacy | `pylint` W0212 protected-access | Precise: `other._field` from outside the class. |
| 16 abstraction levels | none | Read. Cognitive complexity (`flake8-cognitive-complexity` CCR001, if installed) is a weak proxy. |
| 17 dead code | `vulture --min-confidence 100` | Never lower the threshold: below 100, vulture guesses, and a deletion made on a guess is the one that breaks a dynamic lookup. |
| 18 anemic model | `pylint` R0903 as a *list* of data holders | Then ask which service methods only read their fields. |
| 19 long function | `ruff` PLR0915, C901 (9); `pylint` R0915, `pylint.extensions.mccabe` R1260; `radon cc -n B`; `lizard` NLOC/CCN; CodeScene `function_lines_of_code_warning` 70, `function_cyclomatic_complexity_warning` 9 | A linear chain of early-return gates scores high on every one of these and may still be the right shape. |
| duplication | `npx jscpd@4`; `pylint` R0801; CodeScene `function_duplication_min_similarity_percentage` 75 | jscpd counts token runs and will match two field lists in the same order. |

What none of them see: the shape of a module (which helpers belong on which type, which
tuple is threaded through a call chain, whether one class is two programs). That is
where an agent hand-rolls a script, and should — after the table has said what it can.

## Detection Cheat Sheet

Searching finds candidates, not findings — and one class (1.4) has no reliable search
at all. Confirm every hit by reading the surrounding code.

| Smell | What to search for |
|-------|--------------------|
| Null checks | `is None` / `is not None` / `!= null` / `== null` guards |
| Collection guards | **not searchable** — reason about every conditional whose subject is a collection (see 1.4) |
| Optional params | nullable params defaulting to null |
| Broad catch | `except Exception` / `catch (Exception)` / bare catch |
| Boolean flags | boolean parameters with defaults |
| Mutable defaults | mutable literals as default arguments |
| Long functions | distance between one function definition and the next |
| Private access | `._field` / `.__field` cross-object access |

## References

- **Refactoring** (Martin Fowler) — the canonical catalogue of code smells and refactorings
- **Clean Code** (Robert C. Martin) — functions, naming, error handling
- **Growing Object-Oriented Software, Guided by Tests** (Freeman & Pryce) — ports and adapters, test design
- **Domain-Driven Design** (Eric Evans) — rich domain models vs anemic models
- **A Philosophy of Software Design** (John Ousterhout) — complexity management, deep vs shallow modules
