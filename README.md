# `Copperhead` README

## Overview

Copperhead is an innovative Python library currently in its early stages of development. Its goal is to facilitate the integration of Rust code into Python projects, offering an intuitive approach for Python developers to leverage Rust's performance and type safety. The library is a work in progress (WIP), and we're actively developing its features and capabilities.

## Usage

Copperhead simplifies the process of integrating Rust with Python. Use the `@rusty` decorator to automatically mirror Python functions and classes in Rust. Here's a preliminary example:

```python
import copperhead
from copperhead import rusty

@rusty(py_function = True)
def add(a: int, b: int) -> int:
    """Ok(a + b)"""

@rusty(py_class = True)
class Foo:
    a: int
    b: int

    @rusty
    def sum(self) -> int:
        """
        println!("summing {} and {}", self.a, self.b);
        Ok(self.a + self.b)
        """

def main():
    copperhead.mirror_main()
    print(add(1, 2))
    print(Foo(1, 2).sum())
    
main()
```

## Current Status and Key Features

- **WIP State**: Copperhead is in a developmental phase, and users should expect frequent updates and changes.
- **Automatic Rust Code Generation**: Generates Rust code for Python functions and classes.
- **Type Mapping**: Automatic type conversion from Python to Rust.

## Contributing

As a work in progress, Copperhead welcomes contributions from the developer community. Your input and pull requests are valuable for its growth and stability.

## License

Copperhead is distributed under the [MIT License](https://opensource.org/licenses/MIT).

---

**Disclaimer**: This README reflects the current state of Copperhead as a work-in-progress project. Users should be prepared for potential changes and updates as the project evolves. Further documentation, including more detailed examples and a comprehensive API reference, will be provided as the project matures.
