# -*- coding: utf-8 -*-
"""Tests for the pyuml2 OCL subset (pyuml2.ocl).

Every expected value below is transcribed from OCL 2.4 §11.5
classification operations / UML 2.5.1 generalization semantics, and
from the constraint bodies embedded in uml_mixins.py that use them.
"""
import pytest

import pyecore.ecore as ecore
from pyecore.valuecontainer import EcoreUtils  # noqa: F401  (used in doctest-ish asserts)

from pyuml2.uml import (
    Class, Classifier, Namespace, Element, Component, Port, Property,
    Package, BehavioredClassifier, Activity, NamedElement, Association,
)
from pyuml2.types import String, Integer, Boolean
from pyuml2.ocl import (
    ocl_is_kind_of, ocl_is_type_of, ocl_as_type, ocl_type,
    ocl_is_undefined,
)


# ---------------------------------------------------------------------
# oclIsKindOf — conformance is transitive through generalization


def test_kind_of_exact():
    c = Class(name="C")
    assert ocl_is_kind_of(c, Class) is True


def test_kind_of_transitive():
    c = Class(name="C")
    assert ocl_is_kind_of(c, Classifier) is True
    assert ocl_is_kind_of(c, Namespace) is True
    assert ocl_is_kind_of(c, Element) is True


def test_kind_of_subclass_instance():
    comp = Component(name="K")
    # Component generalizes Class in UML 2.5.1 (its metaclass chain:
    # Component -> Class -> Classifier -> ...)
    assert ocl_is_kind_of(comp, Class) is True
    assert ocl_is_kind_of(comp, Classifier) is True


def test_kind_of_negative():
    p = Port(name="P")
    assert ocl_is_kind_of(p, Class) is False
    assert ocl_is_kind_of(p, Package) is False


def test_kind_of_sibling_not_conforming():
    # Port specializes Property (so kind-of Property), but Property is
    # NOT kind-of Port (downward is not conformance)
    p = Port(name="P")
    assert ocl_is_kind_of(p, Property) is True
    prop = Property(name="prop")
    assert ocl_is_kind_of(prop, Port) is False


def test_kind_of_none():
    assert ocl_is_kind_of(None, Class) is False


def test_kind_of_datatype():
    assert ocl_is_kind_of(3, Integer) is True
    assert ocl_is_kind_of("x", String) is True
    assert ocl_is_kind_of(3, String) is False


def test_kind_of_accepts_eclass_target():
    c = Class(name="C")
    assert ocl_is_kind_of(c, Class.eClass) is True


def test_kind_of_rejects_instance_as_type():
    c = Class(name="C")
    with pytest.raises(TypeError):
        ocl_is_kind_of(c, c)  # instance passed where type expected


# ---------------------------------------------------------------------
# oclIsTypeOf — exact dynamic type, no generalization


def test_type_of_exact():
    c = Class(name="C")
    assert ocl_is_type_of(c, Class) is True
    assert ocl_is_type_of(c, Classifier) is False  # transitivity ignored


def test_type_of_subclass():
    comp = Component(name="K")
    assert ocl_is_type_of(comp, Component) is True
    assert ocl_is_type_of(comp, Class) is False
    assert ocl_is_kind_of(comp, Class) is True  # contrast with kind-of


def test_type_of_none():
    assert ocl_is_type_of(None, Class) is False


def test_type_of_datatype():
    assert ocl_is_type_of(3, Integer) is True
    assert ocl_is_type_of(True, Integer) is False
    assert ocl_is_type_of(True, Boolean) is True


# ---------------------------------------------------------------------
# oclAsType — retype


def test_as_type_success_keeps_identity():
    comp = Component(name="K")
    r = ocl_as_type(comp, Class)
    assert r is comp


def test_as_type_failure_returns_none():
    p = Port(name="P")
    assert ocl_as_type(p, Class) is None


def test_as_type_none_stays_none():
    assert ocl_as_type(None, Class) is None


def test_as_type_upcast_downcast_roundtrip():
    # the pervasive OCL idiom from uml_mixins constraint bodies:
    #   n.oclIsKindOf(X) and n.oclAsType(X).member->includes(...)
    ns = Package(name="ns")
    obj = Class(name="C")
    ns.packagedElement.append(obj)
    member = obj.member  # inherited from Namespace
    # the retyped object really has the Namespace feature
    assert ocl_as_type(obj, Namespace).member is member


def test_as_type_idiom_from_spec_body():
    # mirrors: owner.oclIsKindOf(TemplateParameter) and
    #          owner.oclAsType(TemplateParameter).signature...
    c = Class(name="C")
    prop = Property(name="p")
    c.ownedAttribute.append(prop)
    owner = prop.owner  # owner property resolves to c
    if ocl_is_kind_of(owner, Class):
        assert ocl_as_type(owner, Class).ownedAttribute[0] is prop
    else:
        pytest.fail("owner of owned attribute must kind-of Class")


# ---------------------------------------------------------------------
# oclType — dynamic type


def test_type_roundtrip():
    comp = Component(name="K")
    t = ocl_type(comp)
    assert isinstance(t, ecore.EClass)
    assert t.name == "Component"
    # the UML 2.5.1 idiom: oclIsKindOf(x.oclType())
    assert ocl_is_kind_of(comp, t) is True
    other = Class(name="C")
    assert ocl_is_kind_of(other, t) is False


def test_type_of_eclass_is_itself():
    # metalevel: an EClass is already a type object
    assert ocl_type(Class.eClass) is Class.eClass


def test_type_none_invalid():
    with pytest.raises(TypeError):
        ocl_type(None)


# ---------------------------------------------------------------------
# oclIsUndefined


def test_undefined():
    assert ocl_is_undefined(None) is True
    assert ocl_is_undefined(Class(name="C")) is False
    # unset reference reads as None -> undefined
    prop = Property(name="p")
    assert ocl_is_undefined(prop.type) is True

# ---------------------------------------------------------------------
# Spec-spelling methods on every UML element (via ElementMixin)


def test_method_spellings():
    comp = Component(name="K")
    assert comp.oclIsKindOf(Class) is True
    assert comp.oclIsTypeOf(Component) is True
    assert comp.oclIsTypeOf(Class) is False
    assert comp.oclAsType(Class) is comp
    assert comp.oclType().name == "Component"
    assert comp.oclIsUndefined() is False


def test_method_reach_all_metaclasses():
    # Element is the root: Property, Package, Activity all get the API
    p = Property(name="p")
    pk = Package(name="pk")
    a = Activity(name="a")
    for obj in (p, pk, a):
        assert obj.oclIsKindOf(Element) is True
        assert obj.oclIsUndefined() is False


def test_method_as_type_mismatch_none():
    prop = Property(name="p")
    assert prop.oclAsType(Class) is None
