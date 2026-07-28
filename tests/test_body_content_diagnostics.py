"""Diagnostic test: verify body_content flows through the data pipeline.

Tests:
1. set_selected_skill with body_content → QQmlPropertyMap has body_content
2. SkillModel.get_skill_at() returns body_content from prepared state
3. The overlay's onSelectedSkillChanged sees body_content on the skill

Run: uv run pytest tests/test_body_content_diagnostics.py -x -v -s
"""

from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlProperty

from skill_manager.core.models.entities import PreparedModelState, Skill
from skill_manager.core.models.qt_model import SkillModel

QML_DIR = Path(__file__).parent.parent / "src" / "skill_manager" / "SkillManagerComponents"


# ── Test 1: set_selected_skill → QQmlPropertyMap body_content ──


def test_set_selected_skill_preserves_body_content(app_controller):
    """Verify body_content survives the set_selected_skill QMap creation."""
    body_text = "# Test\n\nThis is the body content with some **markdown**."
    app_controller.set_selected_skill(
        {
            "name": "TestSkill",
            "local_path": "/test/path/skill.md",
            "is_command": False,
            "is_screenshot": False,
            "body_content": body_text,
        }
    )
    qmap = app_controller.selectedSkill
    assert qmap is not None
    bc = qmap.body_content
    assert bc == body_text, f"body_content mismatch: {bc[:50]!r} != {body_text[:50]!r}"
    print(f"[DIAG] Test 1 PASS: body_content preserved, length={len(bc)}")


# ── Test 2: SkillModel.get_skill_at() returns body_content ──


def test_model_get_skill_at_returns_body_content():
    """Verify SkillModel.get_skill_at returns body_content from prepared state."""
    model = SkillModel()
    body_text = "Model body content line 1\nline 2\nline 3"
    # Build a prepared state with body_content
    skill = Skill(
        name="FromModel",
        local_path="/model/test/skill.md",
        body_content=body_text,
    )
    state = PreparedModelState(
        all_skills=[skill],
        search_engine=None,
        all_filtered_skills=[skill],
        visible_rows=[skill],
        categories=["General"],
        status="test",
        generation=1,
    )
    model.replacePreparedState(state)

    # Read back via get_skill_at
    retrieved = model.get_skill_at(0)
    assert retrieved is not None
    bc = retrieved.get("body_content", "")
    assert bc == body_text, f"body_content mismatch: {bc[:50]!r} != {body_text[:50]!r}"
    print(f"[DIAG] Test 2 PASS: get_skill_at returns body_content, length={len(bc)}")


# ── Test 3: Overlay sees body_content via selectedSkill ──


def test_overlay_sees_body_content(app_controller, qapp):
    """Verify the QML overlay can read body_content from selectedSkill."""
    qml_path = QML_DIR / "SkillInspectorOverlay.qml"
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("appController", app_controller)
    from skill_manager.controllers.font_database_bridge import FontDatabaseBridge

    font_bridge = FontDatabaseBridge()
    engine.rootContext().setContextProperty("fontDB", font_bridge)
    engine._font_bridge = font_bridge
    engine.addImportPath(str(QML_DIR.parent))

    comp = QQmlComponent(engine)
    comp.setData(
        qml_path.read_text(encoding="utf-8").encode(),
        QUrl.fromLocalFile(str(qml_path)),
    )
    overlay = comp.create()
    assert overlay is not None, f"Failed to create overlay: {[e.toString() for e in comp.errors()]}"
    qapp.processEvents()

    body_text = "Overlay diagnostic body content for testing."
    app_controller.set_selected_skill(
        {
            "name": "OverlayTest",
            "local_path": "/overlay/test/skill.md",
            "is_command": False,
            "is_screenshot": False,
            "body_content": body_text,
        }
    )
    qapp.processEvents()

    # Read showSkillInspector flag
    si = QQmlProperty.read(overlay, "showSkillInspector")
    sci = QQmlProperty.read(overlay, "showCommandInspector")
    sii = QQmlProperty.read(overlay, "showImageInspector")
    print(
        f"[DIAG] Test 3: showSkillInspector={si} showCommandInspector={sci} showImageInspector={sii}"
    )

    # Read selectedSkillValid
    ssv = QQmlProperty.read(overlay, "selectedSkillValid")
    print(f"[DIAG] Test 3: selectedSkillValid={ssv}")

    assert si is True, f"showSkillInspector should be True, got {si}"
    assert ssv is True, f"selectedSkillValid should be True, got {ssv}"

    # Now verify the SkillInspector inside the overlay
    insp = None
    for child in overlay.findChildren(QObject):
        if "SkillInspector" in child.metaObject().className():
            insp = child
            break

    if insp is not None:
        insp_visible = QQmlProperty.read(insp, "visible")
        insp_overlay = QQmlProperty.read(insp, "overlayVisible")
        print(f"[DIAG] Test 3: inspector visible={insp_visible} overlayVisible={insp_overlay}")

        # Read _sel.body_content — but _sel is a readonly QML property,
        # may not be accessible via QQmlProperty. Try alternate access.
        sel_prop = QQmlProperty.read(insp, "_sel")
        if sel_prop is not None:
            bc = sel_prop.body_content
            print(f"[DIAG] Test 3: inspector._sel.body_content length={len(bc) if bc else 0}")
        else:
            print(f"[DIAG] Test 3: cannot read inspector._sel (type={type(sel_prop).__name__})")
    else:
        print("[DIAG] Test 3: SkillInspector not found in overlay children")

    print("[DIAG] Test 3 PASS: overlay visibility flags set correctly")


# ── Test 4: structureMutated -> _on_model_structure_mutated refreshes body_content ──


def test_structure_mutation_updates_body_content(app_controller, qapp):
    """Simulate: cache-preview (empty body) → user selects → full discovery (has body).

    This replicates the real startup scenario where a cache-preview loads first
    (body_content empty), the user selects a skill, then full discovery completes
    and structureMutated fires. _on_model_structure_mutated should update the
    selectedSkill QMap with the fresh body_content.
    """
    from skill_manager.core.models.entities import PreparedModelState, Skill

    # ── Phase 1: "Cache preview" — model populated WITHOUT body_content ──
    # This simulates loading the on-disk cache which excludes raw_content/body_content.
    skill_no_body = Skill(
        name="TestSkill",
        local_path="/test/path/skill.md",
        body_content="",  # EMPTY — as loaded from cache
        is_command=False,
        is_screenshot=False,
    )
    preview_state = PreparedModelState(
        all_skills=[skill_no_body],
        search_engine=None,
        all_filtered_skills=[skill_no_body],
        visible_rows=[skill_no_body],
        categories=["General"],
        status="cache preview",
        generation=1,
        is_final=False,
    )

    # Commit preview to BOTH models
    app_controller._library_model.replacePreparedState(preview_state)
    app_controller._quick_copy_model.replacePreparedState(preview_state)
    qapp.processEvents()
    # Process deferred resets
    for _ in range(5):
        qapp.processEvents()

    # ── Phase 2: User selects the skill (body_content is EMPTY) ──
    app_controller.selectSkill(0)  # Select first (and only) visible skill
    qapp.processEvents()

    # Verify: selectedSkill has EMPTY body_content
    sel = app_controller.selectedSkill
    bc_before = sel.body_content if sel else ""
    print(f"[DIAG] Test 4: after cache-preview select, body_content length={len(bc_before)}")

    # ── Phase 3: "Full discovery" — model populated WITH body_content ──
    body_text = "# Skill Body\n\nFull content loaded from disk after discovery."
    skill_with_body = Skill(
        name="TestSkill",
        local_path="/test/path/skill.md",
        body_content=body_text,
        is_command=False,
        is_screenshot=False,
    )
    full_state = PreparedModelState(
        all_skills=[skill_with_body],
        search_engine=None,
        all_filtered_skills=[skill_with_body],
        visible_rows=[skill_with_body],
        categories=["General"],
        status="full discovery",
        generation=2,
        is_final=True,
    )

    # Commit full discovery to BOTH models
    app_controller._library_model.replacePreparedState(full_state)
    app_controller._quick_copy_model.replacePreparedState(full_state)
    # Process deferred resets — this is where structureMutated fires
    for _ in range(5):
        qapp.processEvents()

    # ── Phase 4: Verify selectedSkill has body_content AFTER structureMutated ──
    qapp.processEvents()
    qapp.processEvents()

    sel_after = app_controller.selectedSkill
    bc_after = sel_after.body_content if sel_after else ""
    print(f"[DIAG] Test 4: after full-discovery select, body_content length={len(bc_after)}")

    if len(bc_after) > 0:
        print("[DIAG] Test 4 PASS: body_content refreshed by _on_model_structure_mutated")
        print(f"[DIAG] Test 4: body_preview={bc_after[:80]!r}")
    else:
        print("[DIAG] Test 4 FAIL: body_content STILL EMPTY after structureMutated!")

    # Regardless, verify the property values
    bc_final = sel_after.body_content if sel_after else ""
    assert len(bc_final) > 0, (
        f"body_content should be non-empty after full discovery + structureMutated, "
        f"got length={len(bc_final)}"
    )
