# -*- coding: utf-8 -*-
"""A Pythonic subset of OCL for pyuml2.

This module implements the OCL *type* and *classification* operations
(OCL 2.4 §11.5 / UML 2.5.1 semantics) on top of PyEcore's Ecore
metaclass machinery:

    ocl_is_kind_of(obj, T)   -- obj's dynamic type conforms to T
                                (transitive through generalization)
    ocl_is_type_of(obj, T)   -- obj's dynamic type IS exactly T
                                (no inheritance taken into account)
    ocl_as_type(obj, T)      -- retype: obj if it kind-of T else None
    ocl_type(obj)            -- obj's dynamic type (an EClass)
    ocl_is_undefined(obj)    -- obj is the OCL null/undefined value

Design notes
------------
* "Conformance" for UML metaclasses is the Python class inheritance
  chain: pyecoregen generates ``class Component(..., Class)`` whenever
  the metamodel says Component generalizes Class, so plain
  ``isinstance(obj, T)`` realizes OCL conformsTo exactly.  We delegate
  the check to ``EcoreUtils.isinstance`` which also handles EDataType
  targets (e.g. ``ocl_is_kind_of(3, Integer)``) and EProxy semantics.
* ``obj.eClass`` is the *most specific* EClass of an object, so
  identity comparison against the normalized target type realizes
  oclIsTypeOf.
* OCL ``invalid`` and ``null`` are both represented as ``None`` in this
  subset (the Pythonic simplification; PyEcore unset references are
  also None).  Therefore ``ocl_as_type`` failure, ``null.oclAsType(T)``
  and an unset reference are indistinguishable — document this wherever
  a constraint body cares.
* Type arguments may be given as the generated Python metaclass
  (``pyuml2.uml.Class``), as an EClass instance, or as an EDataType
  (``pyuml2.types.Integer``).  Passing an ordinary *object* where a
  *type* is expected is a TypeError — that keeps transcribed OCL
  bodies honest.
* Classification is implemented via ``EcoreUtils.isinstance``
  (pyecore's own oracle), which walks the same inheritance chain
  pyecoregen emitted from the UML generalization graph.  Empirical
  verification for this metamodel: ``Class`` kind-of ``Classifier``/
  ``Namespace``/``Element``; ``Component`` kind-of ``Class``;
  ``Port`` kind-of ``Property`` (UML 2.5.1 has Port specialize
  Property); property end-type of AssociationClass etc.
* Constraint bodies in uml_mixins.py (spec-derived OCL docstrings)
  are the primary consumers: virtually all of them rely on
  oclIsKindOf/oclAsType pairs, e.g.::

      owner.oclIsKindOf(TemplateParameter)
      and owner.oclAsType(TemplateParameter).signature...

  which transcribes to::

      ocl_is_kind_of(owner, TemplateParameter)
      and (ocl_as_type(owner, TemplateParameter).signature ...)
"""

import pyecore.ecore as ecore
from pyecore.valuecontainer import EcoreUtils

__all__ = [
    "ocl_is_kind_of",
    "ocl_is_type_of",
    "ocl_as_type",
    "ocl_type",
    "ocl_is_undefined",
]


def _normalize_type(type_):
    """Return the EClass for a type argument.

    Accepts a generated metaclass (``pyuml2.uml.Class``), an EClass
    instance, or an EDataType (``pyuml2.types.Integer``).  Anything else
    (in particular an *instance* of a metaclass) is a TypeError.
    """
    if type_ is None:
        raise TypeError(
            "OCL type argument is null: expected a metaclass or EClass")
    if isinstance(type_, ecore.EClass):
        return type_
    if isinstance(type_, (ecore.EDataType, ecore.EClassifier)):
        return type_  # e.g. pyuml2.types.Integer is an EDataType instance
    if isinstance(type_, type):  # a Python class: generated metaclass
        eclass = getattr(type_, "eClass", None)
        if isinstance(eclass, ecore.EClass):
            return eclass
        # Python classes outside the metamodel (int, str, ...) — let
        # EcoreUtils decide; used for EDataType eType checks.
        return type_
    raise TypeError(
        "OCL type argument must be a metaclass or EClass, got %r; "
        "for an object's type use ocl_type(obj)" % (type_,))


def ocl_is_kind_of(obj, type_):
    """OCL ``obj.oclIsKindOf(T)``: does obj's type conform to T?

    True when obj is nil? no -- None is not an instance of anything:

    >>> from pyuml2.uml import Class
    >>> ocl_is_kind_of(None, Class)
    False

    Transitive through generalization (UML 2.5.1: Class conforms to
    Classifier conforms to Namespace conforms to Element), and through
    EDataType targets:

    >>> from pyuml2.types import Integer
    >>> ocl_is_kind_of(3, Integer)
    True
    """
    if obj is None:
        return False
    target = _normalize_type(type_)
    return bool(EcoreUtils.isinstance(obj, target))


def ocl_is_type_of(obj, type_):
    """OCL ``obj.oclIsTypeOf(T)``: is obj's dynamic type exactly T?

    No generalization is taken into account, so a Component is *not*
    a type-of Class even though it kind-of one.
    """
    if obj is None:
        return False
    target = _normalize_type(type_)
    if isinstance(target, ecore.EDataType):
        # data types: exact match of the underlying python type
        return obj.__class__ is target.eType
    return obj.eClass is target


def ocl_as_type(obj, type_):
    """OCL ``obj.oclAsType(T)``: retype obj to T.

    Returns obj unchanged when ``ocl_is_kind_of(obj, T)`` holds,
    otherwise None (this subset's representation of OclInvalid).
    None stays None: ``null.oclAsType(T)`` is invalid in OCL.
    """
    if ocl_is_kind_of(obj, type_):
        return obj
    return None


def ocl_type(obj):
    """OCL ``obj.oclType()``: obj's dynamic type as an EClass.

    The result can be fed straight back into the classification
    operations, as the UML 2.5.1 constraint bodies do:

        self.oclIsKindOf(n.oclType())

    For an object this is its most specific EClass.  For an EClass
    (a metaclass object) OCL would return the metatype; in this subset
    the EClass is already the type object, so it is returned unchanged.
    """
    if obj is None:
        raise TypeError("oclType of OCL null is invalid")
    if isinstance(obj, ecore.EClass):
        return obj
    eclass = getattr(obj, "eClass", None)
    if isinstance(eclass, ecore.EClass):
        return eclass
    raise TypeError("oclType: %r has no dynamic EClass" % (obj,))


def ocl_is_undefined(obj):
    """OCL ``obj.oclIsUndefined()``: True for null and invalid.

    Both are None in this subset.
    """
    return obj is None