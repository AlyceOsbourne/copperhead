"""
Welcome to Copperhead, a tool to inline Rust code into Python.
"""
import builtins
import contextlib
import dataclasses
import inspect
import os
import pathlib
import types
import typing

import jinja2
import rustimport
import rustimport.import_hook

__version__ = "0.0.1"

old_import = builtins.__import__
builtins.__import__ = lambda name, *args, **kwargs: mirror(old_import(name, *args, **kwargs))

env = jinja2.Environment()
TYPE_MAP = {int         : "i32", str: "String", bool: "bool", float: "f32", typing.List: "Vec<{}>", list: "Vec<{}>",
            typing.Dict : 'HashMap<{}, {}>', dict: 'HashMap<{}, {}>', typing.Set: 'HashSet<{}>', set: 'HashSet<{}>',
            typing.Tuple: '({})', tuple: '({})', typing.Self: 'Self', None: '()', }
UNLINK = False


# noinspection PyArgumentList,PyTypeChecker
def rusty(func = None, /, **kwargs):
    if func is None:
        return lambda func: rusty(func, **kwargs)
    func.__rusty__ = True
    for key, value in kwargs.items():
        setattr(func, key, value)
    return func


# noinspection PyTypeChecker
@dataclasses.dataclass
class PyClass:
    cls: type

    def __post_init__(self):
        for name, value in self.cls.__dict__.items():
            if name.startswith('_'):
                continue
            if callable(value) and not getattr(value, '__rusty__', False):
                setattr(self.cls, name, rusty(value))

    @property
    def attrs(self) -> typing.List[typing.Tuple[str, str]]:
        attrs = []
        for name, value in self.cls.__annotations__.items():
            if name.startswith('_'):
                continue
            if hasattr(value, '__origin__'):
                formatted = TYPE_MAP[value.__origin__]
                value = formatted.format(*[TYPE_MAP[arg] for arg in value.__args__])
            else:
                value = TYPE_MAP[value]
            attrs.append((name, value))
        return attrs

    @property
    def name(self) -> str:
        return self.cls.__name__

    @property
    def methods(self) -> typing.List[typing.Tuple[str, typing.List[str], str, str]]:
        methods = []
        for name, value in self.cls.__dict__.items():
            if name.startswith('_'):
                continue
            if callable(value) and getattr(value, '__rusty__', False):
                args = inspect.getfullargspec(value)
                mapped_arg = []
                return_type = TYPE_MAP[args.annotations['return']]
                for arg in args.args:
                    if arg == 'self':
                        mapped_arg.append('&mut self')
                    else:
                        if hasattr(args.annotations[arg], '__origin__'):
                            formatted = TYPE_MAP[args.annotations[arg].__origin__]
                            mapped_arg.append(formatted.format(*[
                                    f"{name}: {TYPE_MAP[arg].format(*[TYPE_MAP[arg] for arg in args.annotations[arg].__args__])}"
                                    for arg in args.annotations[arg].__args__]))
                        else:
                            # mapped_arg.append(TYPE_MAP[args.annotations[arg]])
                            mapped_arg.append(f"{arg}: {TYPE_MAP[args.annotations[arg]]}")
                methods.append((name, mapped_arg, return_type, inspect.getdoc(value)))
        return methods

    @property
    def template(self) -> str:
        template = """
#[pyclass(get_all, set_all)]
#[derive(Debug)]
pub struct {{ cls.name }} {
    {%- for name, value in cls.attrs %}
    pub {{ name }}: {{ value }}{%- if not loop.last -%},{%- endif -%}
    {% endfor %}
}

#[pymethods] impl {{ cls.name }} { #[new] pub fn new({%- for name, value in cls.attrs %}{{ name }}: {{ value }}{%- if 
not loop.last -%},{%- endif -%}{%- endfor -%}) -> Self { {{ cls.name }} { {%- for name, value in cls.attrs -%} {{ 
name }}{%- if not loop.last -%},{%- endif -%} {%- endfor -%} } }

    {% for name, args, return_type, doc in cls.methods -%}
    pub fn {{ name }}({{ args|join(', ') }}) -> PyResult<{{ return_type }}> {
        {{ doc }}
    }
    {%- endfor %}
    
    fn __repr__(&self) -> PyResult<String> {
        Ok(format!("{:?}", self))
    }
}
        """
        return env.from_string(template, globals = {'cls': self}).render()


# noinspection PyTypeChecker
@dataclasses.dataclass
class RustClass:
    cls: type

    def __post_init__(self):
        for name, value in self.cls.__dict__.items():
            if name.startswith('_'):
                continue
            if callable(value) and not getattr(value, '__rusty__', False):
                setattr(self.cls, name, rusty(value))

    @property
    def attrs(self) -> typing.List[typing.Tuple[str, str]]:
        attrs = []
        for name, value in self.cls.__annotations__.items():
            if name.startswith('_'):
                continue
            if hasattr(value, '__origin__'):
                formatted = TYPE_MAP[value.__origin__]
                value = formatted.format(*[TYPE_MAP[arg] for arg in value.__args__])
            else:
                value = TYPE_MAP[value]
            attrs.append((name, value))
        return attrs

    @property
    def name(self) -> str:
        return self.cls.__name__

    @property
    def methods(self) -> typing.List[typing.Tuple[str, typing.List[str], str, str]]:
        methods = []
        for name, value in self.cls.__dict__.items():
            if name.startswith('_'):
                continue
            if callable(value) and getattr(value, '__rusty__', False):
                args = inspect.getfullargspec(value)
                mapped_arg = []
                return_type = TYPE_MAP[args.annotations['return']]
                for arg in args.args:
                    if arg == 'self':
                        mapped_arg.append('&self')
                    else:
                        if hasattr(args.annotations[arg], '__origin__'):
                            formatted = TYPE_MAP[args.annotations[arg].__origin__]
                            mapped_arg.append(
                                    formatted.format(*[TYPE_MAP[arg] for arg in args.annotations[arg].__args__]))
                        else:
                            mapped_arg.append(TYPE_MAP[args.annotations[arg]])
                methods.append((name, mapped_arg, return_type, inspect.getdoc(value)))
        return methods

    @property
    def template(self) -> str:
        template = """
#[derive(Debug)]
pub struct {{ cls.name }} {
    {%- for name, value in cls.attrs %}
    pub {{ name }}: {{ value }}{%- if not loop.last -%},{%- endif -%}
    {% endfor %}
}

impl {{ cls.name }} {
    pub fn new({%- for name, value in cls.attrs %}{{ name }}: {{ value }}{%- if not loop.last -%},
    {%- endif -%}{%- endfor -%}) -> Self {
        {{ cls.name }} {
            {%- for name, value in cls.attrs -%}
            {{ name }}{%- if not loop.last -%},{%- endif -%}
            {%- endfor -%}
        }
    }
    
    {% for name, args, return_type, doc in cls.methods -%}
    pub fn {{ name }}({{ args|join(', ') }}) -> {{ return_type }} {
        {{ doc }}
    }
    {%- endfor %}
    
}
        """
        return env.from_string(template, globals = {'cls': self}).render()


# noinspection PyTypeChecker
@dataclasses.dataclass
class PyFunction:
    func: types.FunctionType

    @property
    def name(self) -> str:
        return self.func.__name__

    @property
    def args(self) -> typing.List[str]:
        args = inspect.getfullargspec(self.func)
        mapped_arg = []
        for name, _type in args.annotations.items():
            if name == "return":
                continue
            if name == 'self':
                mapped_arg.append('&self: Self')
            else:
                if hasattr(_type, '__origin__'):
                    formatted = TYPE_MAP[_type.__origin__]
                    mapped_arg.append(f"{name}: {formatted.format(*[TYPE_MAP[arg] for arg in _type.__args__])}")
                else:
                    mapped_arg.append(f"{name}: {TYPE_MAP[_type]}")
        return mapped_arg

    @property
    def return_type(self) -> str:
        ret = inspect.getfullargspec(self.func).annotations['return']
        if hasattr(ret, '__origin__'):
            formatted = TYPE_MAP[ret.__origin__]
            return formatted.format(*[TYPE_MAP[arg] for arg in ret.__args__])
        else:
            return TYPE_MAP[ret]

    @property
    def body(self) -> str:
        return inspect.getdoc(self.func)

    @property
    def template(self) -> str:
        template = """
#[pyfunction]
pub fn {{ func.name }}({{ func.args|join(', ') }}) -> PyResult<{{ func.return_type }}> {
    {{ func.body }}
}
        """
        return env.from_string(template, globals = {'func': self}).render()


# noinspection PyTypeChecker
@dataclasses.dataclass
class RustFunction:
    func: types.FunctionType

    @property
    def name(self) -> str:
        return self.func.__name__

    @property
    def args(self) -> typing.List[str]:
        args = inspect.getfullargspec(self.func)
        mapped_arg = []
        for name, _type in args.annotations.items():
            if name == "return":
                continue
            if name == 'self':
                mapped_arg.append('&self: Self')
            else:
                if hasattr(_type, '__origin__'):
                    formatted = TYPE_MAP[_type.__origin__]
                    mapped_arg.append(f"{name}: {formatted.format(*[TYPE_MAP[arg] for arg in _type.__args__])}")
                else:
                    mapped_arg.append(f"{name}: {TYPE_MAP[_type]}")
        return mapped_arg

    @property
    def return_type(self) -> str:
        return TYPE_MAP[inspect.getfullargspec(self.func).annotations['return']]

    @property
    def body(self) -> str:
        return inspect.getdoc(self.func)

    @property
    def template(self):
        template = """
fn {{ func.name }}({{ func.args|join(', ') }}) -> {{ func.return_type }} {
    {{ func.body }}
}
        """
        return env.from_string(template, globals = {'func': self}).render()


@dataclasses.dataclass
class RustyModule:
    module: types.ModuleType

    @property
    def name(self):
        # return self.module.__name__
        return f"rust_{self.module.__name__.strip('_')}"

    @property
    def classes(self):
        classes = []
        for name, cls in inspect.getmembers(self.module, inspect.isclass):
            if getattr(cls, '__rusty__', False):
                if getattr(cls, 'py_class', False):
                    classes.append(PyClass(cls))
                else:
                    classes.append(RustClass(cls))
        return classes

    @property
    def functions(self):
        functions = []
        for name, func in inspect.getmembers(self.module, inspect.isfunction):
            if getattr(func, '__rusty__', False):
                if not getattr(func, 'py_function', False):
                    functions.append(RustFunction(func))
        return functions

    @property
    def py_functions(self):
        functions = []
        for name, func in inspect.getmembers(self.module, inspect.isfunction):
            if getattr(func, '__rusty__', False):
                if getattr(func, 'py_function', False):
                    functions.append(PyFunction(func))
        return functions

    @property
    def template(self):
        template = """
// rustimport:pyo3
use pyo3::prelude::*;

{% for cls in module.classes -%}
{{ cls.template}}
{%- endfor -%}

{%- for func in module.functions -%}
{{ func.template }}
{%- endfor %}

{%- for func in module.py_functions -%}
{{ func.template }}
{%- endfor %}

#[pymodule]
fn {{ module.name }}(_py: Python, m: &PyModule) -> PyResult<()> {
    {% for cls in module.classes -%}
    m.add_class::<{{ cls.name }}>()?;
    {%- endfor %}
    {% for func in module.py_functions -%}
    m.add_function(wrap_pyfunction!({{ func.name }}, m)?)?;
    {% endfor -%}
    Ok(())
}
""".strip()
        return env.from_string(template, globals = {'module': self}).render()


def should_mirror(module: types.ModuleType):
    if hasattr(module, '__rust_module__'):
        return False
    for name, value in inspect.getmembers(module):
        if getattr(value, '__rusty__', False):
            return True
    return False


def mirror(module: types.ModuleType):
    if not should_mirror(module):
        return module
    rust_module = RustyModule(module)
    if (not pathlib.Path(f"{rust_module.name}.rs").exists() or open(f'{rust_module.name}.rs',
                                                                   'r').read() != rust_module.template):
        with open(f'{rust_module.name}.rs', 'w') as f:
            f.write(rust_module.template)
        with contextlib.redirect_stdout(None):
            rustimport.build_filepath(f'{rust_module.name}.rs')
    module.__rust_module__ = rustimport.imp_from_path(f'{rust_module.name}.rs', f'{rust_module.name}')
    for name, value in inspect.getmembers(module):
        if getattr(value, '__rusty__', False):
            setattr(module, name, getattr(module.__rust_module__, name))
    if UNLINK:
        pathlib.Path(f'{rust_module.name}.rs').unlink()
    else:
        os.utime(f'{rust_module.name}.rs')
    return module
