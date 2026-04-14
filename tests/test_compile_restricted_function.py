from types import FunctionType

from RestrictedPython import PrintCollector
from RestrictedPython import compile_restricted_function
from RestrictedPython import safe_builtins
from RestrictedPython._compat import IS_PY310_OR_GREATER


def test_compile_restricted_function():
    p = ''
    body = """
print("Hello World!")
return printed
"""
    name = "hello_world"
    global_symbols = []

    result = compile_restricted_function(
        p,  # parameters
        body,
        name,
        filename='<string>',
        globalize=global_symbols
    )

    assert result.code is not None
    assert result.errors == ()

    safe_globals = {
        '__name__': 'script',
        '_getattr_': getattr,
        '_print_': PrintCollector,
        '__builtins__': safe_builtins,
    }
    safe_locals = {}
    exec(result.code, safe_globals, safe_locals)
    hello_world = safe_locals['hello_world']
    assert type(hello_world) is FunctionType
    assert hello_world() == 'Hello World!\n'


def test_compile_restricted_function_func_wrapped():
    p = ''
    body = """
print("Hello World!")
return printed
"""
    name = "hello_world"
    global_symbols = []

    result = compile_restricted_function(
        p,  # parameters
        body,
        name,
        filename='<string>',
        globalize=global_symbols
    )

    assert result.code is not None
    assert result.errors == ()
    safe_globals = {
        '__name__': 'script',
        '_getattr_': getattr,
        '_print_': PrintCollector,
        '__builtins__': safe_builtins,
    }

    func = FunctionType(result.code, safe_globals)
    func()
    assert 'hello_world' in safe_globals
    hello_world = safe_globals['hello_world']
    assert hello_world() == 'Hello World!\n'


def test_compile_restricted_function_with_arguments():
    p = 'input1, input2'
    body = """
print(input1 + input2)
return printed
"""
    name = "hello_world"
    global_symbols = []

    result = compile_restricted_function(
        p,  # parameters
        body,
        name,
        filename='<string>',
        globalize=global_symbols
    )

    assert result.code is not None
    assert result.errors == ()

    safe_globals = {
        '__name__': 'script',
        '_getattr_': getattr,
        '_print_': PrintCollector,
        '__builtins__': safe_builtins,
    }
    safe_locals = {}
    exec(result.code, safe_globals, safe_locals)
    hello_world = safe_locals['hello_world']
    assert type(hello_world) is FunctionType
    assert hello_world('Hello ', 'World!') == 'Hello World!\n'


def test_compile_restricted_function_can_access_global_variables():
    p = ''
    body = """
print(input)
return printed
"""
    name = "hello_world"
    global_symbols = ['input']

    result = compile_restricted_function(
        p,  # parameters
        body,
        name,
        filename='<string>',
        globalize=global_symbols
    )

    assert result.code is not None
    assert result.errors == ()

    safe_globals = {
        '__name__': 'script',
        '_getattr_': getattr,
        'input': 'Hello World!',
        '_print_': PrintCollector,
        '__builtins__': safe_builtins,
    }
    safe_locals = {}
    exec(result.code, safe_globals, safe_locals)
    hello_world = safe_locals['hello_world']
    assert type(hello_world) is FunctionType
    assert hello_world() == 'Hello World!\n'


def test_compile_restricted_function_pretends_the_code_is_executed_in_a_global_scope():  # NOQA: E501
    p = ''
    body = """output = output + 'bar'"""
    name = "hello_world"
    global_symbols = ['output']

    result = compile_restricted_function(
        p,  # parameters
        body,
        name,
        filename='<string>',
        globalize=global_symbols
    )

    assert result.code is not None
    assert result.errors == ()

    safe_globals = {
        '__name__': 'script',
        'output': 'foo',
        '__builtins__': {},
    }
    safe_locals = {}
    exec(result.code, safe_globals, safe_locals)
    hello_world = safe_locals['hello_world']
    assert type(hello_world) is FunctionType
    hello_world()
    assert safe_globals['output'] == 'foobar'


def test_compile_restricted_function_allows_invalid_python_identifiers_as_function_name():  # NOQA: E501
    p = ''
    body = """output = output + 'bar'"""
    name = "<foo>.bar.__baz__"
    global_symbols = ['output']

    result = compile_restricted_function(
        p,  # parameters
        body,
        name,
        filename='<string>',
        globalize=global_symbols
    )

    assert result.code is not None
    assert result.errors == ()

    safe_globals = {
        '__name__': 'script',
        'output': 'foo',
        '__builtins__': {},
    }
    safe_locals = {}
    exec(result.code, safe_globals, safe_locals)
    generated_function = tuple(safe_locals.values())[0]
    assert type(generated_function) is FunctionType
    generated_function()
    assert safe_globals['output'] == 'foobar'


def test_compile_restricted_function_handle_SyntaxError():
    p = ''
    body = """a("""
    name = "broken"

    result = compile_restricted_function(
        p,  # parameters
        body,
        name,
    )

    assert result.code is None
    if IS_PY310_OR_GREATER:
        assert result.errors == (
            "Line 1: SyntaxError: '(' was never closed at statement: 'a('",
        )
    else:
        assert result.errors == (
            "Line 1: SyntaxError: unexpected EOF while parsing at statement:"
            " 'a('",
        )


def test_compile_restricted_function_invalid_syntax():
    p = ''
    body = '1=1'
    name = 'broken'

    result = compile_restricted_function(
        p,  # parameters
        body,
        name,
    )

    assert result.code is None
    assert len(result.errors) == 1
    error_msg = result.errors[0]

    if IS_PY310_OR_GREATER:
        assert error_msg.startswith(
            "Line 1: SyntaxError: cannot assign to literal here. Maybe "
        )
    else:
        assert error_msg.startswith(
            "Line 1: SyntaxError: cannot assign to literal at statement:"
        )


def test_compile_restricted_function_rejects_newline_in_params():
    """Newlines in parameters must not inject module-level statements."""
    p = '):\n pass\ninjected = "PWNED"\ndef f('
    body = 'return "safe"'
    name = 'my_func'

    result = compile_restricted_function(p, body, name)
    assert result.code is None
    assert result.errors == (
        'Line 1: parameters must not contain line breaks or '
        'inject additional statements.',
    )


def test_compile_restricted_function_rejects_code_injection_via_params():
    """Various code injection attempts via parameter string must be blocked."""
    p = '):\n import os\n os.system("id")\ndef f('
    result = compile_restricted_function(p, 'pass', 'test')
    assert result.code is None
    assert 'inject additional statements' in result.errors[0]


def test_compile_restricted_function_rejects_function_hijack_via_params():
    """Injecting a same-named function via params must be blocked."""
    p = '):\n pass\ndef legit():\n return "HIJACKED"\ndef f('
    result = compile_restricted_function(p, 'return "REAL"', 'legit')
    assert result.code is None
    assert 'inject additional statements' in result.errors[0]


def test_compile_restricted_function_accepts_valid_params():
    """Normal parameter strings still work."""
    for p in ['', 'x', 'x, y', 'x, y=1', '*args', '**kwargs',
              'x, *args, **kwargs', 'x: int = 0']:
        result = compile_restricted_function(p, 'return 1', 'f')
        assert result.errors == (), f"Unexpected error for params {p!r}: {result.errors}"
        assert result.code is not None


def test_compile_restricted_function_syntax_error_in_params():
    """Invalid syntax in parameter string is handled gracefully."""
    result = compile_restricted_function(',,', 'pass', 'f')
    assert result.code is None
    assert len(result.errors) == 1
