#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Tests for _find_graphical_markers in build_map_from_tfl_pdf."""
import sys
sys.path.insert(0, '.')
from build_map_from_tfl_pdf import _find_graphical_markers


def _circle_drawing(cx, cy, r, fill=(1.0, 1.0, 1.0)):
    """Fake drawing dict matching what PyMuPDF returns for a filled white circle."""
    return {
        'fill': fill,
        'items': [('c', None, None, None), ('c', None, None, None), ('c', None, None, None)],
        'rect': (cx - r, cy - r, cx + r, cy + r),
        'type': 'f',
    }


def _rect_drawing(cx, cy, w, h, fill):
    """Fake drawing dict for a filled rectangle."""
    return {
        'fill': fill,
        'items': [('l', None, None), ('l', None, None), ('l', None, None), ('l', None, None)],
        'rect': (cx - w/2, cy - h/2, cx + w/2, cy + h/2),
        'type': 'f',
    }


def test_finds_white_station_circle():
    drawings = [_circle_drawing(100.0, 200.0, 2.8)]  # 5.6×5.6, white
    result = _find_graphical_markers(drawings)
    assert len(result) == 1
    assert abs(result[0][0] - 100.0) < 0.01
    assert abs(result[0][1] - 200.0) < 0.01


def test_ignores_white_circle_too_small():
    drawings = [_circle_drawing(100.0, 200.0, 1.0)]  # 2×2 — border circle, ignore
    result = _find_graphical_markers(drawings)
    assert len(result) == 0


def test_ignores_white_circle_too_large():
    drawings = [_circle_drawing(100.0, 200.0, 6.0)]  # 12×12 — interchange blob, ignore
    result = _find_graphical_markers(drawings)
    assert len(result) == 0


def test_finds_step_free_marker():
    sf_fill = (0.15, 0.70, 0.91)
    drawings = [_rect_drawing(50.0, 80.0, 8.2, 8.8, sf_fill)]
    result = _find_graphical_markers(drawings)
    assert len(result) == 1
    assert abs(result[0][0] - 50.0) < 0.01
    assert abs(result[0][1] - 80.0) < 0.01


def test_ignores_non_white_filled_circle():
    red_fill = (1.0, 0.0, 0.0)
    drawings = [_circle_drawing(100.0, 200.0, 2.8, fill=red_fill)]
    result = _find_graphical_markers(drawings)
    assert len(result) == 0


def test_ignores_drawings_with_no_curves():
    d = {
        'fill': (1.0, 1.0, 1.0),
        'items': [('l', None, None), ('l', None, None)],
        'rect': (97.2, 197.2, 102.8, 202.8),
        'type': 'f',
    }
    result = _find_graphical_markers([d])
    assert len(result) == 0


def test_returns_multiple_markers():
    drawings = [
        _circle_drawing(100.0, 200.0, 2.8),
        _circle_drawing(300.0, 400.0, 2.8),
        _rect_drawing(500.0, 600.0, 8.2, 8.8, (0.15, 0.70, 0.91)),
    ]
    result = _find_graphical_markers(drawings)
    assert len(result) == 3


if __name__ == '__main__':
    tests = [v for k, v in list(globals().items()) if k.startswith('test_')]
    passed = 0
    for t in tests:
        try:
            t()
            print(f'  PASS  {t.__name__}')
            passed += 1
        except Exception as e:
            print(f'  FAIL  {t.__name__}: {e}')
    print(f'\n{passed}/{len(tests)} passed')
    raise SystemExit(0 if passed == len(tests) else 1)
