<!-- Generated from docs/adapter-contract-testing.md by tools/sync-references.py. Edit the source, not this copy. -->

# Adapter Contract Testing — Methodology Notes

Adapter contract testing keeps simulators/fakes aligned with real adapters by running the same contract tests against both implementations.
The contract defines the behavioral specification of a port; real and simulated adapters must both satisfy it.

## Core pattern

1. Define one abstract contract test class per port.
2. Put all shared behavior tests in that contract.
3. Implement exactly two concrete subclasses:
   - one for the real adapter
   - one for the simulator/fake adapter
4. Run both subclasses in CI.

The contract is the port's specification. If the simulator can pass a test the real adapter
cannot, the simulator is lying and every test that depends on it is worth less than it
looks.

## Canonical structure

```python
class FooContract(ABC):
    @abstractmethod
    def create_foo(self) -> Foo:
        ...

    def test_some_behavior(self) -> None:
        foo = self.create_foo()
        ...

class TestRealFoo(FooContract):
    def create_foo(self) -> Foo:
        return RealFoo(...)

class TestSimulatorFoo(FooContract):
    def create_foo(self) -> Foo:
        return SimulatorFoo(...)
```

## Rules

- Keep one abstract factory method in the contract (`create_foo`, `create_gateway`, etc.).
- Keep only two contract subclasses (real + simulator).
- Do not use `pytest.skip` in contract subclasses; pre-seed the simulator so it satisfies all contract tests.
- Put simulator-only behavior checks in standalone `test_` functions, not in an extra contract subclass.
- Treat the contract as the port specification: if pipeline behavior depends on it, it belongs in the contract.

## File placement

Examples here are Python/pytest; the pattern is an abstract test class with a factory
method, which every xUnit-family framework supports.

| Location | Content |
|---|---|
| `tests/contracts/<port>_contract.py` | Abstract contract class with all shared tests |
| `tests/test_<port>.py` | Real + simulator subclasses; optional simulator-specific standalone tests |

## Done criteria

- The contract captures all required shared behavior for the port.
- Real and simulator subclasses both pass the same contract tests.
- Any simulator-specific tests are isolated from the contract.

## References

- Adapter contract testing papers: https://github.com/adapter-contract-testing/adapter-contract-testing-papers
