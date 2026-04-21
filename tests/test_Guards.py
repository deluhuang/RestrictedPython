import pytest

from RestrictedPython import compile_restricted_exec
from RestrictedPython.Guards import full_write_guard
from RestrictedPython.Guards import guarded_unpack_sequence
from RestrictedPython.Guards import safe_builtins
from RestrictedPython.Guards import safe_globals
from RestrictedPython.Guards import safer_getattr
from tests.helper import restricted_eval
from tests.helper import restricted_exec


def _write_(x):
    return x


def test_Guards_bytes():
    """It contains bytes"""
    assert restricted_eval('bytes(1)') == bytes(1)


def test_Guards_sorted():
    """It contains sorted"""
    assert restricted_eval('sorted([5, 2, 8, 1])') == sorted([5, 2, 8, 1])


def test_Guards__safe_builtins__1():
    """It contains `slice()`."""
    assert restricted_eval('slice(1)') == slice(1)


def test_Guards__safe_builtins__2():
    """It allows to define new classes by allowing `__build_class__`.
    """

    class_can_be_defined_code = '''
class MyClass:
    value = None
    def display(self):
        return str(self.value)

ob1 = MyClass()
ob1.value = 2411
result = ob1.display()'''

    restricted_globals = dict(
        result=None,
        __name__='restricted_module',
        __metaclass__=type,
        _write_=_write_,
        _getattr_=getattr)

    restricted_exec(class_can_be_defined_code, restricted_globals)
    assert restricted_globals['result'] == '2411'


def test_Guards__guarded_setattr__1():
    """It allows use setattr and delattr when _guarded_writes is True.
    """
    class MyObjectD:
        value = None
        _guarded_writes = 1

    setattr_code = '''
my_object_d = MyObjectD()
setattr(my_object_d, 'value', 9999)'''

    delattr_code = "delattr(my_object_d, 'value')"

    restricted_globals = dict(
        __builtins__=safe_builtins,
        MyObjectD=MyObjectD,
        my_object_d=None,
        __name__='restricted_module',
        __metaclass__=type,
        _write_=_write_,
        _getattr_=getattr,)

    restricted_exec(setattr_code, restricted_globals)
    assert 9999 == restricted_globals['my_object_d'].value

    restricted_exec(delattr_code, restricted_globals)
    assert None is restricted_globals['my_object_d'].value


def test_Guards__write_wrapper__1():
    """It wraps the value attribute when it is not
    marked with _guarded_writes."""
    class ObjWithoutGuardedWrites:
        my_attr = None

    setattr_without_guarded_writes_code = '''
my_ob = ObjWithoutGuardedWrites()
setattr(my_ob, 'my_attr', 'bar')'''

    restricted_globals = dict(
        __builtins__=safe_builtins,
        ObjWithoutGuardedWrites=ObjWithoutGuardedWrites,
        my_attr=None,
        __name__='restricted_module',
        __metaclass__=type,
        _write_=_write_,
        _getattr_=getattr,)

    with pytest.raises(TypeError) as excinfo:
        restricted_exec(
            setattr_without_guarded_writes_code, restricted_globals)
    assert 'attribute-less object (assign or del)' in str(excinfo.value)


def test_Guards__write_wrapper__2():
    """It wraps setattr and it works when guarded_setattr is implemented."""

    class ObjWithGuardedSetattr:
        my_attr = None

        def __guarded_setattr__(self, key, value):
            setattr(self, key, value)

    set_attribute_using_guarded_setattr_code = '''
myobj_with_guarded_setattr = ObjWithGuardedSetattr()
setattr(myobj_with_guarded_setattr, 'my_attr', 'bar')
    '''

    restricted_globals = dict(
        __builtins__=safe_builtins,
        ObjWithGuardedSetattr=ObjWithGuardedSetattr,
        myobj_with_guarded_setattr=None,
        __name__='restricted_module',
        __metaclass__=type,
        _write_=_write_,
        _getattr_=getattr,)

    restricted_exec(
        set_attribute_using_guarded_setattr_code, restricted_globals)
    assert restricted_globals['myobj_with_guarded_setattr'].my_attr == 'bar'


def test_Guards__guarded_unpack_sequence__1(mocker):
    """If the sequence is shorter then expected the interpreter will raise
    'ValueError: need more than X value to unpack' anyway
    => No childs are unpacked => nothing to protect."""
    src = "one, two, three = (1, 2)"

    _getiter_ = mocker.stub()
    _getiter_.side_effect = lambda it: it
    glb = {
        '_getiter_': _getiter_,
        '_unpack_sequence_': guarded_unpack_sequence,
    }

    with pytest.raises(ValueError) as excinfo:
        restricted_exec(src, glb)
    assert 'values to unpack' in str(excinfo.value)
    assert _getiter_.call_count == 1


STRING_DOT_FORMAT_DENIED = """\
a = 'Hello {}'
b = a.format('world')
"""


def test_Guards__safer_getattr__1a():
    """It prevents using the format method of a string.

    format() is considered harmful:
    http://lucumr.pocoo.org/2016/12/29/careful-with-str-format/
    """
    glb = {
        '__builtins__': safe_builtins,
    }
    with pytest.raises(NotImplementedError) as err:
        restricted_exec(STRING_DOT_FORMAT_DENIED, glb)
    assert 'Using the format*() methods of `str` is not safe' == str(err.value)


# contributed by Ward Theunisse
STRING_DOT_FORMAT_MAP_DENIED = """\
a = 'Hello {foo.__dict__}'
b = a.format_map({foo:str})
"""


def test_Guards__safer_getattr__1b():
    """It prevents using the format method of a string.

    format() is considered harmful:
    http://lucumr.pocoo.org/2016/12/29/careful-with-str-format/
    """
    glb = {
        '__builtins__': safe_builtins,
    }
    with pytest.raises(NotImplementedError) as err:
        restricted_exec(STRING_DOT_FORMAT_MAP_DENIED, glb)
    assert 'Using the format*() methods of `str` is not safe' == str(err.value)


# contributed by Abhishek Govindarasu
STR_DOT_FORMAT_DENIED = """\
str.format('{0.__class__.__mro__[1]}', int)
"""


def test_Guards__safer_getattr__1c():
    """It prevents using the format method of a string.

    format() is considered harmful:
    http://lucumr.pocoo.org/2016/12/29/careful-with-str-format/
    """
    glb = {
        '__builtins__': safe_builtins,
    }
    with pytest.raises(NotImplementedError) as err:
        restricted_exec(STR_DOT_FORMAT_DENIED, glb)
    assert 'Using the format*() methods of `str` is not safe' == str(err.value)


STR_DOT_FORMAT_MAP_DENIED = """\
str.format_map('Hello {foo.__dict__}', {'foo':str})
"""


def test_Guards__safer_getattr__1d():
    """It prevents using the format method of a string.

    format() is considered harmful:
    http://lucumr.pocoo.org/2016/12/29/careful-with-str-format/
    """
    glb = {
        '__builtins__': safe_builtins,
    }
    with pytest.raises(NotImplementedError) as err:
        restricted_exec(STR_DOT_FORMAT_MAP_DENIED, glb)
    assert 'Using the format*() methods of `str` is not safe' == str(err.value)


SAFER_GETATTR_ALLOWED = """\
class A:

    def __init__(self, value):
        self.value = value

a = A(2)
result = getattr(a, 'value')
"""


def test_Guards__safer_getattr__3():
    """It allows to use `safer_getattr`."""
    restricted_globals = dict(
        __builtins__=safe_builtins,
        __name__=None,
        __metaclass__=type,
        _write_=_write_,
        getattr=safer_getattr,
        result=None,
    )
    restricted_exec(SAFER_GETATTR_ALLOWED, restricted_globals)
    assert restricted_globals['result'] == 2


SAFER_GETATTR_BREAKOUT = """\
def g(obj, name):
    # create class FakeString which inherits from str
    class FakeString(str):
        # overload startswith() to always return false
        def startswith(self, _):
            return False
    return getattr(obj, FakeString(name))

# call str.__class__.__base__.__subclasses__()
subclasses = g(g(g(str, "__class__"), "__base__"), "__subclasses__")()
# traverse list of subclasses until we reach the BuiltinImporter class
x = "test"
while "BuiltinImporter" not in str(x):
    x = subclasses.pop()
    continue
# use BuiltinImporter to import 'os' and access to a not allowed function
result = x.load_module('os').getgid()
"""


def test_Guards__safer_getattr__4():
    restricted_globals = dict(
        __builtins__=safe_builtins,
        __name__=None,
        __metaclass__=type,
        # _write_=_write_,
        getattr=safer_getattr,
        result=None,
    )

    with pytest.raises(TypeError) as err:
        restricted_exec(SAFER_GETATTR_BREAKOUT, restricted_globals)
    assert 'type(name) must be str' == str(err.value)


SAFER_GETATTR_BREAKOUT2 = """\
g = None
leak = None
def test():
    global g, leak
    leak = getattr(getattr(getattr(g, "gi_frame"), "f_back"), "f_back")
    yield leak
g = test()
g.send(None)
os = getattr(leak, "f_builtins").get('__import__')('os')
result = os.getgid()
"""


def test_Guards__safer_getattr__5():
    restricted_globals = dict(
        __builtins__=safe_builtins,
        __name__=None,
        __metaclass__=type,
        # _write_=_write_,
        getattr=safer_getattr,
        result=None,
    )

    # restricted_exec(SAFER_GETATTR_BREAKOUT2, restricted_globals)
    # assert restricted_globals['result'] == 20
    with pytest.raises(AttributeError) as err:
        restricted_exec(SAFER_GETATTR_BREAKOUT2, restricted_globals)
    assert (
        '"gi_frame" is a restricted name, '
        'that is forbidden to access in RestrictedPython.'
    ) == str(err.value)


def test_Guards__safer_getattr_raise():
    from types import SimpleNamespace

    from RestrictedPython.Guards import safer_getattr_raise

    o = SimpleNamespace(a="a")
    assert safer_getattr_raise(o, "a") == "a"
    assert safer_getattr_raise(o, "b", None) is None
    with pytest.raises(AttributeError):
        safer_getattr_raise(o, "b")


def test_call_py3_builtins():
    """It should not be allowed to access global builtins in Python3."""
    result = compile_restricted_exec('builtins["getattr"]')
    assert result.code is None
    assert result.errors == ('Line 1: "builtins" is a reserved name.',)


GETATTR_UNDERSCORE_NAME = """
getattr([], '__class__')
"""


def test_safer_getattr__underscore_name():
    """It prevents accessing an attribute which starts with an underscore."""
    result = compile_restricted_exec(GETATTR_UNDERSCORE_NAME)
    assert result.errors == ()
    assert result.warnings == []
    glb = safe_globals.copy()
    glb['getattr'] = safer_getattr
    with pytest.raises(AttributeError) as err:
        exec(result.code, glb, {})
    assert (
        '"__class__" is an invalid attribute name because it starts with "_"'
        == str(err.value))


# ---------------------------------------------------------------------------
# Security: full_write_guard wrapper must not leak the original object
# ---------------------------------------------------------------------------
# 安全说明（中文）：
# full_write_guard 的设计意图是作为 _write_ 钩子，在受限代码执行写操作（如
# setattr/delattr/setitem/delitem）时临时包装目标对象，检查其是否声明了
# __guarded_writes__，从而拒绝对未声明保护的对象执行写操作。
#
# Wrapper 实例从未被设计为直接暴露给不可信代码。如果调用者错误地把
#   wrapped = full_write_guard(sensitive_obj)
# 塞入受限脚本的 globals/locals，则受限代码原本可以通过访问 wrapped.ob
# 来恢复原始敏感对象（.ob 不以下划线开头，safer_getattr 不会拦截它）。
#
# 本修复将 Wrapper 内部属性由 `ob` 重命名为 `_ob`（下划线前缀），使得
# safer_getattr 会因 "_ob".startswith("_") 而拒绝访问，从而防止泄漏。
# ---------------------------------------------------------------------------


class _SensitiveObject:
    """Simulates a sensitive host object (e.g. hass, db connection)."""

    secret = "CLASSIFIED"

    def get_secret(self):
        return self.secret


def test_full_write_guard__wrapper_ob_not_accessible_via_safer_getattr():
    """Wrapper._ob is not reachable from restricted code via safer_getattr.

    安全 PoC（无害版）：验证修复后 wrapper 对象内部的 _ob 属性无法被
    safer_getattr 访问，因为属性名以下划线开头会被拦截。
    这确保了即使误将 full_write_guard(sensitive_obj) 的返回值暴露给
    不可信代码，攻击者也无法通过 ._ob 恢复原始敏感对象。
    旧属性名 'ob' 也不再存在于 Wrapper.__dict__ 中，确保无法通过该路径泄漏。
    """
    from RestrictedPython.Guards import safer_getattr_raise

    sensitive = _SensitiveObject()
    wrapped = full_write_guard(sensitive)

    # The internal attribute is now stored as _ob (underscore-prefixed).
    # safer_getattr must block it due to the underscore prefix rule.
    with pytest.raises(AttributeError) as excinfo:
        safer_getattr(wrapped, '_ob')
    assert '"_ob" is an invalid attribute name' in str(excinfo.value)

    # The old attribute name 'ob' no longer exists on the wrapper.
    # safer_getattr_raise (which has no default) must raise AttributeError.
    with pytest.raises(AttributeError):
        safer_getattr_raise(wrapped, 'ob')


def test_full_write_guard__wrapper_ob_not_accessible_from_restricted_code():
    """Restricted code cannot recover the original object from a wrapper.

    安全 PoC：通过受限执行环境验证，即使将 wrapper 实例直接放入受限脚本的
    globals，受限代码也无法通过任何公开属性路径访问到原始敏感对象。

    修复前（ob）：safer_getattr(wrapped, 'ob') 返回原始对象 → 敏感数据泄漏。
    修复后（_ob）：
      - 'ob' 不再存在，safer_getattr 返回 None（内置默认值）。
      - '_ob' 因下划线前缀被 safer_getattr 拦截，抛出 AttributeError。
    两条路径均不会泄漏原始敏感对象。
    """
    sensitive = _SensitiveObject()
    wrapped = full_write_guard(sensitive)

    # Mimic a downstream misuse pattern: wrapper placed directly in globals.
    # After the fix, getattr(wrapped, 'ob') returns None (ob no longer exists).
    # The restricted code detects raw is None and records 'ob_gone'.
    poc_code = """
try:
    raw = getattr(wrapped, 'ob')
    if raw is None:
        result = 'ob_gone'
    else:
        result = 'LEAKED'
except AttributeError:
    result = 'blocked'
"""
    compiled = compile_restricted_exec(poc_code)
    assert compiled.errors == ()

    glb = {
        '__builtins__': safe_builtins,
        'wrapped': wrapped,
        'result': None,
        'getattr': safer_getattr,
    }
    exec(compiled.code, glb)
    # 'ob' is gone from the wrapper — the original object is not accessible.
    assert glb['result'] in ('ob_gone', 'blocked')
    # The secret must not have leaked.
    assert glb['result'] != sensitive.secret
    assert glb['result'] != 'LEAKED'


def test_full_write_guard__wrapper_underscore_ob_blocked_from_restricted_code():
    """Restricted code cannot access ._ob either (underscore guard applies).

    安全 PoC：验证重命名后的 _ob 属性也无法从受限代码中访问。
    """
    sensitive = _SensitiveObject()
    wrapped = full_write_guard(sensitive)

    poc_code = """
try:
    raw = getattr(wrapped, '_ob')
    result = raw.secret
except AttributeError:
    result = 'blocked'
"""
    result = compile_restricted_exec(poc_code)
    assert result.errors == ()

    glb = {
        '__builtins__': safe_builtins,
        'wrapped': wrapped,
        'result': None,
        'getattr': safer_getattr,
    }
    exec(result.code, glb)
    assert glb['result'] == 'blocked'


def test_full_write_guard__wrapper_structure_is_opaque():
    """PoC: documents the wrapper structure for analysis.

    wrapper 结构分析（无害 PoC）：
    - type(wrapped)  → Wrapper（不是原始类型）
    - safetype 检查：dict/list 直接返回，其他类型返回 Wrapper 实例
    - 包装后 Wrapper.__dict__ 仅含 '_ob'（下划线前缀，外部不可访问）
    - 不可信代码无法通过 safer_getattr 读取 _ob 来恢复原始对象
    """
    # dict and list are safeypes — returned as-is, not wrapped
    assert full_write_guard({}) is not None
    assert type(full_write_guard({})) is dict
    assert type(full_write_guard([])) is list

    # Custom objects are wrapped
    sensitive = _SensitiveObject()
    wrapped = full_write_guard(sensitive)
    assert type(wrapped).__name__ == 'Wrapper'

    # Internal storage: only _ob exists, not ob
    assert '_ob' in wrapped.__dict__
    assert 'ob' not in wrapped.__dict__

    # The wrapped._ob is the original object (accessible to trusted Python code)
    assert wrapped.__dict__['_ob'] is sensitive
    assert wrapped.__dict__['_ob'].secret == 'CLASSIFIED'

