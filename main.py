from magic import rusty, mirror_main

@rusty(py_function=True)
def add(a: int, b: int) -> int:
    """Ok(a + b)"""
    
@rusty(py_class=True)
class Foo:
    a: int
    b: int
    
    @rusty
    def sum(self) -> int:
        """
        println!("summing {} and {}", self.a, self.b);
        Ok(self.a + self.b)
        """
    
mirror_main()

a = add(1, 2)
print(a)
print(Foo(1, 2).sum())