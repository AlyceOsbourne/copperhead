# `Copperhead` README

## Overview

Copperhead is a Python library in early development that integrates Rust code into Python projects. It uses a decorator-based approach to generate Rust implementations from Python functions and classes, allowing Python developers to use Rust's performance and type safety. The library is a work in progress.

## Usage

Use the `@rusty` decorator to generate Rust code from Python functions and classes. Example:

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

Copperhead is in active development. The library automatically generates Rust code from Python functions and classes decorated with `@rusty`, and handles type conversion between Python and Rust types.

## Contributing

Contributions are welcome. Submit pull requests or open issues on the project repository.

## License

Copperhead is distributed under the [MIT License](https://opensource.org/licenses/MIT).
