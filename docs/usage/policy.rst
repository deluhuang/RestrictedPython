.. _policy_builtins:

Policies & builtins
-------------------

RestrictedPython provides a way to define policies, by redefining restricted versions of ``print``, ``getattr``, ``setattr``, ``import``, etc..
As shortcuts it offers three stripped down versions of Python's ``__builtins__``:

.. _predefined_builtins:

Predefined builtins
...................

``safe_builtins``
    a safe set of builtin modules and functions
``limited_builtins``
    restricted sequence types (e. g. ``range``, ``list`` and ``tuple``)
``utility_builtins``
    access to standard modules like math, random, string and set.

``safe_globals`` is a shortcut for ``{'__builtins__': safe_builtins}`` as this
is the way globals have to be provided to the `exec` function to actually
restrict the access to the builtins provided by Python.

Guards
......

RestrictedPython predefines several guarded access and manipulation methods:

* ``safer_getattr``
* ``guarded_setattr``
* ``guarded_delattr``
* ``guarded_iter_unpack_sequence``
* ``guarded_unpack_sequence``

Those and additional methods rely on a helper construct ``full_write_guard``,
which is intended to be used **as the value of** ``_write_`` in restricted
execution globals.  See the `Guards`_ section under *Examples* below for
correct usage and important security caveats.

Implementing a policy
---------------------

RestrictedPython only provides the raw material for restricted execution.
To actually enforce any restrictions, you need to supply a policy
implementation by providing restricted versions of ``print``,
``getattr``, ``setattr``, ``import``, etc.  These restricted
implementations are hooked up by providing a set of specially named
objects in the global dict that you use for execution of code.
Specifically:

1. ``_print_`` is a callable object that returns a handler for print
   statements.  This handler must have a ``write()`` method that
   accepts a single string argument, and must return a string when
   called. ``RestrictedPython.PrintCollector.PrintCollector`` is a
   suitable implementation.

2. ``_write_`` is a guard function taking a single argument.  If the
   object passed to it may be written to, it should be returned,
   otherwise the guard function should raise an exception.  ``_write_``
   is typically called on an object before a ``setattr`` operation.

3. ``_getattr_`` and ``_getitem_`` are guard functions, each of which
   takes two arguments.  The first is the base object to be accessed,
   while the second is the attribute name or item index that will be
   read.  The guard function should return the attribute or subitem,
   or raise an exception.
   RestrictedPython ships with a default implementation
   for ``_getattr_`` which prevents the following actions:

   * accessing an attribute whose name start with an underscore
   * accessing the format method of strings as this is considered harmful.

4. ``__import__`` is the normal Python import hook, and should be used
   to control access to Python packages and modules.

5. ``__builtins__`` is the normal Python builtins dictionary, which
   should be weeded down to a set that cannot be used to get around
   your restrictions.  A usable "safe" set is
   ``RestrictedPython.Guards.safe_builtins``.

To help illustrate how this works under the covers, here's an example
function:

.. code-block:: python

    def f(x):
        x.foo = x.foo + x[0]
        print x
        return printed

and (sort of) how it looks after restricted compilation:

.. code-block:: python

    def f(x):
        # Make local variables from globals.
        _print = _print_()
        _write = _write_
        _getattr = _getattr_
        _getitem = _getitem_

        # Translation of f(x) above
        _write(x).foo = _getattr(x, 'foo') + _getitem(x, 0)
        print >>_print, x
        return _print()

Examples
--------

``print``
.........

To support the ``print`` statement in restricted code, we supply a
``_print_`` object (note that it's a *factory*, e.g. a class or a
callable, from which the restricted machinery will create the object):

.. code-block:: pycon

    >>> from RestrictedPython.PrintCollector import PrintCollector
    >>> _print_ = PrintCollector
    >>> _getattr_ = getattr

    >>> src = '''
    ... print("Hello World!")
    ... '''
    >>> code = compile_restricted(src, '<string>', 'exec')
    >>> exec(code)

As you can see, the text doesn't appear on stdout.  The print
collector collects it.  We can have access to the text using the
``printed`` variable, though:

.. code-block:: pycon

    >>> src = '''
    ... print("Hello World!")
    ... result = printed
    ... '''
    >>> code = compile_restricted(src, '<string>', 'exec')
    >>> exec(code)

    >>> result
    'Hello World!\n'

Built-ins
.........

By supplying a different ``__builtins__`` dictionary, we can rule out
unsafe operations, such as opening files:

.. code-block:: pycon

    >>> from RestrictedPython.Guards import safe_builtins
    >>> restricted_globals = dict(__builtins__=safe_builtins)

    >>> src = '''
    ... open('/etc/passwd')
    ... '''
    >>> code = compile_restricted(src, '<string>', 'exec')
    >>> exec(code, restricted_globals)
    Traceback (most recent call last):
      ...
    NameError: name 'open' is not defined

Guards
......

``full_write_guard`` is a callable that is intended to be used **only** as
the value of ``_write_`` in the restricted execution globals.  It is **not**
an object-capability wrapper and must not be used to pre-wrap objects before
placing them into the restricted globals or locals.

The restricted compiler rewrites every write operation to call ``_write_``:

.. code-block:: python

    # Original restricted source:
    x.attr = value

    # Compiled form (approximately):
    _write_(x).attr = value

``_write_`` receives the target object, checks whether mutations are
permitted (based on ``type(obj)`` being a safe type or ``obj._guarded_writes``
being set), and either returns the object or a transient ``Wrapper`` that
raises ``TypeError`` if a write is attempted.  The ``Wrapper`` is discarded
immediately after the operation.

.. warning::

   **Wrapper instances must never be exposed to untrusted code.**

   Calling ``full_write_guard(obj)`` and passing the returned ``Wrapper``
   directly to restricted code allows the untrusted script to observe the
   internal structure of the wrapper and, before this fix was applied,
   to recover the original wrapped object via the ``.ob`` attribute.
   The internal reference is now stored under the underscore-prefixed name
   ``_ob``, which ``safer_getattr`` refuses to expose, but the fundamental
   rule remains: do not expose wrappers to untrusted code.

   Correct usage::

       restricted_globals = {
           '__builtins__': safe_builtins,
           '_write_': full_write_guard,   # ← assign the guard, not a wrapper
           '_getattr_': safer_getattr,
       }
       exec(compiled_code, restricted_globals, {'my_obj': my_obj})

   Incorrect usage (do not do this)::

       wrapped = full_write_guard(my_obj)          # creates a Wrapper instance
       restricted_globals['my_obj'] = wrapped      # ← exposes Wrapper to untrusted code

