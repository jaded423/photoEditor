"""Model-free tests for focal_cut's scene cues (no SAM / BiRefNet needed).

Synthesises the photographer's standard shot — red bucket, black glove, one textured bud held up,
a textured pile along the bottom — and checks the cue stage points at the held bud, not the pile
or the glove, and that a frame-filling pile yields no candidate (→ old full-frame path).
Run: python3 -m pytest test_focal_cut.py -q   (or: python3 test_focal_cut.py)
"""
import numpy as np
import focal_cut as fc

RNG = np.random.default_rng(7)


def _textured(shape, base):
    """Bud-like olive noise: mid saturation, busy texture."""
    noise = RNG.integers(-45, 45, size=shape + (3,))
    return np.clip(np.array(base) + noise, 0, 255).astype(np.uint8)


def scene(held=True, pile=True, glove=True, h=1600, w=900):
    img = np.zeros((h, w, 3), np.uint8)
    img[:] = (205, 25, 30)                                     # red bucket
    if glove:
        img[350:900, 0:260] = (28, 30, 45)                     # black nitrile from the left
    if pile:
        img[1000:h, :] = _textured((h - 1000, w), (120, 130, 70))
    if held:
        yy, xx = np.mgrid[0:h, 0:w]
        blob = ((yy - 600) / 190) ** 2 + ((xx - 470) / 260) ** 2 < 1
        img[blob] = _textured((h, w), (125, 135, 75))[blob]
    return img


def test_points_at_held_bud_not_pile_or_glove():
    info = fc.find_focal_bud(scene())
    assert info is not None
    x, y = info["point"]
    assert 200 < x < 740 and 400 < y < 800, (x, y)             # inside the raised blob
    negs = info["negs"]
    assert any(ny > 1000 for _, ny in negs), negs              # a pile negative
    assert any(nx < 260 and 350 < ny < 900 for nx, ny in negs), negs  # a glove negative
    assert not info["from_pile"]


def test_bud_resting_on_pile_is_carved_out():
    img = scene()
    img[900:1000, 300:640] = _textured((100, 340), (125, 135, 75))  # bridge bud into the pile
    info = fc.find_focal_bud(img)
    assert info is not None
    x, y = info["point"]
    assert y < 950, (x, y)                                     # still the raised part, not the pile


def test_full_frame_pile_has_no_held_bud():
    img = _textured((1600, 900), (120, 130, 70))               # smalls / bulk: pile fills the frame
    assert fc.find_focal_bud(img) is None


def test_bucket_only_has_no_bud():
    assert fc.find_focal_bud(scene(held=False, pile=False, glove=False)) is None


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
