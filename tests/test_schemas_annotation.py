"""Tests for the annotation Pydantic discriminated-union contract.

Background
----------
The annotation models live in ``skill_manager.core.schemas``. The
discriminator field is named ``type`` and lives on each subclass as a
``Literal[...]`` (e.g. ``"rect"``, ``"arrow"``). The base class
``BaseAnnotation`` deliberately does *not* declare ``type`` — that keeps
each subclass' ``type`` field independent of a mutable class attribute
on the base, which is what was tripping pyright's
``reportIncompatibleVariableOverride`` check.

The ``Annotation`` type is a Pydantic v2 discriminated union:

    Annotation = Annotated[
        RectAnnotation | ArrowAnnotation | ...,
        Field(discriminator="type"),
    ]

These tests pin down the runtime contract that pyright can no longer
check statically:

1. Each subclass carries the expected ``Literal`` discriminator value.
2. ``BaseAnnotation`` no longer exposes a ``type`` field — the
   discriminator lives only on the union members.
3. The ``RedactAnnotation`` alias still resolves to the same class as
   ``FilledRectAnnotation``.
4. ``Annotation`` (a ``TypeAdapter``-validated discriminated union)
   correctly dispatches to the right subclass based on the
   discriminator and rejects unknown types.
5. The discriminator survives a JSON round-trip (this is what
   ``image_inspector_controller.saveAnnotations`` actually does at
   runtime when it persists annotations to disk).
"""

from __future__ import annotations

import json

import pytest
from pydantic import TypeAdapter, ValidationError

from skill_manager.core.schemas import (
    Annotation,
    AnnotationPoint,
    ArrowAnnotation,
    BaseAnnotation,
    EllipseAnnotation,
    FilledEllipseAnnotation,
    FilledRectAnnotation,
    FreehandAnnotation,
    HighlightAnnotation,
    RectAnnotation,
    RedactAnnotation,
    TextAnnotation,
)

# ``Annotation`` is an ``Annotated[Union[...], Field(discriminator=...)]``
# type alias — at runtime it is a ``typing._AnnotatedAlias`` with no
# ``model_validate`` of its own. The accepted Pydantic v2 entry point
# for arbitrary (and discriminated-union) types is ``TypeAdapter``;
# ``image_inspector_controller.saveAnnotations`` uses the same path
# with ``TypeAdapter(list[Annotation])``.
_ANNOTATION_ADAPTER = TypeAdapter(Annotation)


# (subclass, expected discriminator literal) — the source of truth for
# what the discriminator contract looks like.
_DISCRIMINATOR_CASES = [
    (RectAnnotation, "rect"),
    (ArrowAnnotation, "arrow"),
    (FilledRectAnnotation, "filledRect"),
    (FreehandAnnotation, "freehand"),
    (TextAnnotation, "text"),
    (HighlightAnnotation, "highlight"),
    (EllipseAnnotation, "ellipse"),
    (FilledEllipseAnnotation, "filledEllipse"),
]

# A minimal valid payload for each subclass — used to construct
# instances for discriminator assertions.
_VALID_PAYLOADS: dict[type, dict] = {
    RectAnnotation: {"x": 0.0, "y": 0.0, "width": 10.0, "height": 10.0},
    ArrowAnnotation: {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 10.0},
    FilledRectAnnotation: {"x": 0.0, "y": 0.0, "width": 10.0, "height": 10.0},
    FreehandAnnotation: {
        "points": [AnnotationPoint(x=0, y=0), AnnotationPoint(x=5, y=5)],
    },
    TextAnnotation: {"x": 0.0, "y": 0.0, "text": "hello"},
    HighlightAnnotation: {"x": 0.0, "y": 0.0, "width": 10.0, "height": 10.0},
    EllipseAnnotation: {"x": 0.0, "y": 0.0, "width": 10.0, "height": 10.0},
    FilledEllipseAnnotation: {"x": 0.0, "y": 0.0, "width": 10.0, "height": 10.0},
}


@pytest.mark.parametrize(("annotation_cls", "expected_type"), _DISCRIMINATOR_CASES)
def test_each_subclass_has_correct_type_literal(annotation_cls, expected_type):
    """Each subclass' ``type`` field pins the discriminator literal.

    This is the contract pyright can no longer enforce statically now
    that ``type`` is removed from ``BaseAnnotation``.
    """
    payload = _VALID_PAYLOADS[annotation_cls]
    instance = annotation_cls(**payload)
    assert instance.type == expected_type


@pytest.mark.parametrize("annotation_cls", [cls for cls, _ in _DISCRIMINATOR_CASES])
def test_subclass_type_field_is_in_model_fields(annotation_cls):
    """The discriminator must be a real Pydantic field on each subclass."""
    assert "type" in annotation_cls.model_fields
    assert annotation_cls.model_fields["type"].annotation is not None


def test_base_annotation_does_not_expose_type_field():
    """``BaseAnnotation`` intentionally omits ``type``.

    The discriminator lives only on the union members. If a future
    refactor accidentally reintroduces ``type`` on the base, the
    subclasses' ``type: Literal[...]`` declarations would become
    ``reportIncompatibleVariableOverride`` violations again and the
    discriminated union would silently double-validate the field.
    """
    assert "type" not in BaseAnnotation.model_fields


def test_redact_alias_still_resolves_to_filled_rect():
    """The historical ``RedactAnnotation`` alias must stay a class alias.

    Callers (and older annotation files on disk) may still import
    ``RedactAnnotation``. The class identity must match
    ``FilledRectAnnotation`` so Pydantic's discriminated-union dispatch
    continues to route the alias to the same validator.
    """
    assert RedactAnnotation is FilledRectAnnotation


def test_filled_rect_accepts_redact_discriminator_value():
    """``FilledRectAnnotation`` accepts ``type='redact'`` as a valid literal.

    ``FilledRectAnnotation`` declares its ``type`` as
    ``Literal["filledRect", "redact"]`` so existing persisted data
    that uses the historical ``"redact"`` discriminator keeps
    validating.
    """
    payload = {"type": "redact", "x": 0.0, "y": 0.0, "width": 10.0, "height": 10.0}
    instance = FilledRectAnnotation.model_validate(payload)
    assert instance.type == "redact"
    assert isinstance(instance, FilledRectAnnotation)


def test_redact_discriminator_round_trips_to_filled_rect_subclass():
    """Validating ``{"type": "redact", ...}`` against the union
    resolves to ``FilledRectAnnotation`` (not some other subclass)."""
    payload = {"type": "redact", "x": 0.0, "y": 0.0, "width": 10.0, "height": 10.0}
    instance = _ANNOTATION_ADAPTER.validate_python(payload)
    assert isinstance(instance, FilledRectAnnotation)


def test_annotation_union_dispatches_by_discriminator():
    """The ``Annotation`` union routes each ``type`` to the right subclass.

    A single Pydantic ``model_validate`` call must produce an
    instance of the subclass whose ``Literal[...]`` matches the
    discriminator — that's the whole point of
    ``Field(discriminator="type")``.
    """
    samples = [
        (RectAnnotation, {"type": "rect", "x": 0, "y": 0, "width": 1, "height": 1}),
        (
            ArrowAnnotation,
            {"type": "arrow", "x1": 0, "y1": 0, "x2": 1, "y2": 1},
        ),
        (
            FilledRectAnnotation,
            {"type": "filledRect", "x": 0, "y": 0, "width": 1, "height": 1},
        ),
        (
            FreehandAnnotation,
            {
                "type": "freehand",
                "points": [{"x": 0, "y": 0}, {"x": 1, "y": 1}],
            },
        ),
        (TextAnnotation, {"type": "text", "x": 0, "y": 0, "text": "x"}),
        (
            HighlightAnnotation,
            {"type": "highlight", "x": 0, "y": 0, "width": 1, "height": 1},
        ),
        (
            EllipseAnnotation,
            {"type": "ellipse", "x": 0, "y": 0, "width": 1, "height": 1},
        ),
        (
            FilledEllipseAnnotation,
            {"type": "filledEllipse", "x": 0, "y": 0, "width": 1, "height": 1},
        ),
    ]
    for expected_cls, payload in samples:
        instance = _ANNOTATION_ADAPTER.validate_python(payload)
        assert type(instance) is expected_cls, (
            f"discriminator {payload['type']!r} routed to "
            f"{type(instance).__name__}, expected {expected_cls.__name__}"
        )


def test_annotation_union_rejects_unknown_discriminator():
    """An unknown ``type`` value must raise ``ValidationError``.

    Without ``Field(discriminator=...)``, Pydantic would have to
    trial-validate each union member. With the discriminator, a
    missing or unknown ``type`` fails fast.
    """
    with pytest.raises(ValidationError):
        _ANNOTATION_ADAPTER.validate_python(
            {"type": "circle", "x": 0, "y": 0, "width": 1, "height": 1}
        )


def test_annotation_union_rejects_missing_discriminator():
    """A payload with no ``type`` field must raise ``ValidationError``."""
    with pytest.raises(ValidationError):
        _ANNOTATION_ADAPTER.validate_python({"x": 0, "y": 0, "width": 1, "height": 1})


def test_serialize_roundtrip_preserves_type():
    """A round-trip through JSON must preserve the discriminator value.

    This mirrors the runtime path used by
    ``image_inspector_controller.saveAnnotations`` (Pydantic
    ``model_dump_json`` followed by ``model_validate_json`` on the
    next session). The discriminator must survive the round-trip
    so the discriminated union can re-dispatch to the right
    subclass.
    """
    original = RectAnnotation(x=1.0, y=2.0, width=3.0, height=4.0)
    payload = json.loads(original.model_dump_json())
    assert payload["type"] == "rect"
    restored = _ANNOTATION_ADAPTER.validate_python(payload)
    assert isinstance(restored, RectAnnotation)
    assert restored.type == "rect"
    assert restored.x == 1.0
    assert restored.width == 3.0
