"""focal_cut — scene-aware cutout of the ONE held bud in a product photo.

Pipeline (all ONNX / numpy / cv2, PyInstaller-friendly, no torch):
  1. cheap cues at ~600px: colour classes (red bucket / dark glove / bud-coloured) + sharpness
     → pick the focal bud component: bud-coloured, compact, NOT touching the bottom edge (that's the pile),
       sharpest.  Also locate pile / glove / red for negative prompts.
  2. crop around the candidate (margin) and run SAM (rembg's sam_vit_b ONNX) with +bud / -glove / -pile / -red
     point prompts → object-level region mask that EXCLUDES the glove and the pile.
  3. run BiRefNet on the same crop (1024² on a tight crop ≈ 3-4× the edge resolution of the old full-frame
     pass) → fine matte.  final alpha = BiRefNet matte gated by the (soft-dilated) SAM region.  Both models
     must agree on ONE solid blob, else we decline (→ caller's full-frame path).
  4. defringe: 1px erode + feather, then colour-decontaminate edge pixels against a local background
     estimate so red bucket bleed doesn't ride along.
Returns an RGBA crop (subject only) or None when no held bud is found (→ caller treats as pile/bulk).
"""
import numpy as np, cv2
from PIL import Image, ImageOps
from scipy import ndimage

WORK = 640  # long side for heuristics

# ---------------------------------------------------------------- cues ----
def colour_classes(rgb):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    h, s, v = [hsv[..., i].astype(np.int16) for i in range(3)]
    red = ((h < 10) | (h > 168)) & (s > 90) & (v > 60)
    blue = (h >= 95) & (h <= 128) & (s > 40)           # nitrile glove sheen reads dark navy
    glove = ((v < 95) & (s < 140)) | blue              # black / dark-blue nitrile, shadows
    specular = (s < 45) & (v > 190)                    # bucket rim highlights (pink-white)
    bud = (~red) & (~glove) & (~specular) & (v > 55) & (s > 20)
    return red, glove, bud

def sharpness(rgb, sigma=6):
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    lap = np.abs(cv2.Laplacian(g, cv2.CV_32F, ksize=3))
    sh = cv2.GaussianBlur(lap, (0, 0), sigma)
    return sh / max(np.percentile(sh, 99.5), 1e-6)

def texture(rgb, k=5):
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    mu = cv2.blur(g, (k, k)); var = cv2.blur(g * g, (k, k)) - mu * mu
    return np.sqrt(np.clip(var, 0, None))

def interior_point(mask):
    """A point well inside a mask (max of distance transform) as (x, y)."""
    dt = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5)
    y, x = np.unravel_index(np.argmax(dt), dt.shape)
    return int(x), int(y)

def find_focal_bud(rgb_full):
    """Return dict(point, negs, bbox, comp) in FULL-image coords, or None (no held bud → pile/bulk shot)."""
    H, W = rgb_full.shape[:2]
    sc = WORK / max(H, W)
    rgb = cv2.resize(rgb_full, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    h, w = rgb.shape[:2]
    red, glove, bud = colour_classes(rgb)
    sh = sharpness(rgb)
    tx = texture(rgb)
    yy = np.linspace(1.0, 0.0, h, dtype=np.float32)[:, None]      # raised-bud prior: higher in frame = better

    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    budm = cv2.morphologyEx(bud.astype(np.uint8), cv2.MORPH_CLOSE, k)
    budm = cv2.morphologyEx(budm, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    lab, n = ndimage.label(budm)
    if n == 0:
        return None
    sizes = ndimage.sum(budm, lab, range(1, n + 1))

    def describe(m, area):
        ys, xs = np.where(m)
        bh, bw = ys.max() - ys.min() + 1, xs.max() - xs.min() + 1
        return dict(area=area, bbox=(xs.min(), ys.min(), xs.max(), ys.max()),
                    touches_bottom=bool(ys.max() >= h - 3), touches_side=bool(xs.min() <= 2 or xs.max() >= w - 3),
                    touches_top=bool(ys.min() <= 2),
                    fill=area / (bh * bw), sharp=float(sh[m].mean()), tex=float(tx[m].mean()),
                    aspect=max(bh, bw) / max(1, min(bh, bw)))

    cands, piles = [], []
    for i in range(1, n + 1):
        area = sizes[i - 1]
        if area < 0.004 * h * w:
            continue
        m = lab == i
        d = describe(m, area)
        if d["touches_bottom"] and area > 0.12 * h * w:
            # A pile (or bud merged INTO the pile). Carve the raised, sharp top part out as its own candidate.
            piles.append(m)
            if area > 0.6 * h * w:
                continue                              # full-frame pile (smalls / bulk) — nothing is raised above it
            heat = cv2.GaussianBlur((sh * (0.3 + yy)).astype(np.float32), (0, 0), 5) * m
            peak = float(heat.max())
            if peak <= 0:
                continue
            sub = heat > 0.55 * peak
            sl, sn = ndimage.label(sub)
            py, px = np.unravel_index(np.argmax(heat), heat.shape)
            sub = sl == sl[py, px]
            if sub.sum() < 0.004 * h * w:
                continue
            ds = describe(sub, sub.sum())
            rest = m & ~sub
            if ds["touches_bottom"] or ds["tex"] < 6 or ds["aspect"] > 4 or ds["bbox"][1] > 0.6 * h:
                continue
            if rest.sum() > 0 and ds["sharp"] < 1.25 * float(sh[rest].mean()):
                continue                              # not in front of the pile, just part of it
            ds["mask"] = sub; ds["from_pile"] = True
            ds["score"] = ds["sharp"] * np.sqrt(ds["area"]) * (0.35 + ds["fill"]) * 0.8
            cands.append(ds)
            continue
        if d["tex"] < 6 or d["aspect"] > 4:        # smooth or a thin arc → bucket rim / glare, not a bud
            continue
        if d["bbox"][1] > 0.7 * h:                  # lives entirely in the bottom 30% → table / pile edge
            continue
        d["mask"] = m; d["from_pile"] = False
        d["score"] = d["sharp"] * np.sqrt(area) * (0.35 + d["fill"])
        if d["touches_bottom"]:
            d["score"] *= 0.15
        if d["touches_top"]:
            d["score"] *= 0.3
        if d["touches_side"] and area > 0.25 * h * w:
            d["score"] *= 0.3
        cands.append(d)
    if not cands:
        return None
    cands.sort(key=lambda c: -c["score"])
    best = cands[0]
    comp = best["mask"]
    px, py = interior_point(comp)

    negs = []
    # pile: interior of each pile region minus the chosen bud (lower part)
    for pm in piles:
        rest = pm & ~cv2.dilate(comp.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
        rest[: int(best["bbox"][3])] = False        # only below the bud
        if rest.sum() > 0.01 * h * w:
            negs.append(interior_point(rest))
    # glove: up to two dark blobs near the bud bbox
    gl, gn = ndimage.label(cv2.morphologyEx(glove.astype(np.uint8), cv2.MORPH_OPEN, k))
    if gn:
        x0, y0, x1, y1 = best["bbox"]; mx, my = int(0.6 * (x1 - x0)) + 20, int(0.6 * (y1 - y0)) + 20
        gsizes = ndimage.sum(glove, gl, range(1, gn + 1))
        near = []
        for j in range(1, gn + 1):
            if gsizes[j - 1] < 0.003 * h * w: continue
            gy, gx = np.where(gl == j)
            if gx.max() >= x0 - mx and gx.min() <= x1 + mx and gy.max() >= y0 - my and gy.min() <= y1 + my:
                near.append((gsizes[j - 1], j))
        bud_dt = cv2.distanceTransform((~comp).astype(np.uint8), cv2.DIST_L2, 5)   # distance to the bud
        for _, j in sorted(near, reverse=True)[:2]:
            gm = gl == j
            negs.append(interior_point(gm))
            # fingertip: the glove pixel nearest the bud, pulled 6px back into the glove so it is unambiguous
            gy, gx = np.where(gm)
            k_ = np.argmin(bud_dt[gy, gx])
            ty, tx = gy[k_], gx[k_]
            iy, ix = interior_point(gm)[1], interior_point(gm)[0]
            vx, vy = ix - tx, iy - ty; nrm = max(1.0, float(np.hypot(vx, vy)))
            negs.append((int(tx + 6 * vx / nrm), int(ty + 6 * vy / nrm)))
    # red: a point in the biggest red area
    if red.sum() > 0.02 * h * w:
        rl, rn = ndimage.label(red)
        rs = ndimage.sum(red, rl, range(1, rn + 1))
        negs.append(interior_point(rl == (np.argmax(rs) + 1)))

    inv = 1 / sc
    x0, y0, x1, y1 = best["bbox"]
    return dict(point=(px * inv, py * inv), negs=[(x * inv, y * inv) for x, y in negs],
                bbox=(x0 * inv, y0 * inv, (x1 + 1) * inv, (y1 + 1) * inv), from_pile=best["from_pile"],
                comp=cv2.resize(comp.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST).astype(bool),
                cands=cands, scale=sc)

# ----------------------------------------------------------------- SAM ----
SAM_FRAME = (684, 1024)  # rembg's sam_vit_b ONNX export bakes this landscape frame into the decoder

def sam_masks(sam_session, rgb, pos, neg):
    """Run rembg's SAM ONNX pair on rgb (uint8 HxWx3). Returns (masks[n,H,W] bool, iou[n]) in rgb's pixel grid.
    The exported decoder assumes the encoder saw a 684x1024 frame, so anything else comes back warped;
    we aspect-fit the image into that frame, pad, and map the mask back."""
    enc, dec = sam_session.encoder, sam_session.decoder
    H, W = rgb.shape[:2]
    fh, fw = SAM_FRAME
    sc = min(fw / W, fh / H)
    rh, rw = max(1, round(H * sc)), max(1, round(W * sc))
    frame = np.zeros((fh, fw, 3), np.uint8)
    frame[:rh, :rw] = cv2.resize(rgb, (rw, rh), interpolation=cv2.INTER_AREA)
    emb = enc.run(None, {enc.get_inputs()[0].name: frame.astype(np.float32)})[0]
    pts = np.array([[x * sc, y * sc] for x, y in list(pos) + list(neg)] + [[0, 0]], dtype=np.float32)[None]
    lbl = np.array([1] * len(pos) + [0] * len(neg) + [-1], dtype=np.float32)[None]
    masks, iou, _ = dec.run(None, {
        "image_embeddings": emb, "point_coords": pts, "point_labels": lbl,
        "mask_input": np.zeros((1, 1, 256, 256), np.float32), "has_mask_input": np.zeros(1, np.float32),
        "orig_im_size": np.array([fh, fw], np.float32)})
    out = []
    for m in masks[0]:
        m = m[:rh, :rw]
        out.append(cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR) > 0)
    return np.array(out), iou[0]

def pick_sam_mask(masks, iou, ref, negs_xy):
    """Choose the SAM granularity that best matches the colour-cue component and contains no negative point."""
    best, bs = None, -1
    for m, q in zip(masks, iou):
        if m.sum() == 0: continue
        inter = (m & ref).sum(); union = (m | ref).sum()
        j = inter / union
        bad = any(m[int(y), int(x)] for x, y in negs_xy if 0 <= int(y) < m.shape[0] and 0 <= int(x) < m.shape[1])
        s = j * (0.2 if bad else 1.0) + 0.1 * float(q)
        if s > bs: best, bs = m, s
    return best

# ------------------------------------------------------------ BiRefNet ----
def birefnet_alpha(bire_session, rgb):
    from rembg import remove
    out = remove(Image.fromarray(rgb), session=bire_session, only_mask=True)
    return np.asarray(out.convert("L")).astype(np.float32) / 255.0

# ------------------------------------------------------------- compose ----
def peel_foreign(rgb, alpha, band=10):
    """Drop glove fingertips and bucket-red slivers that SAM/BiRefNet let ride along the subject's rim.
    Only pixels near the alpha boundary are eligible, so dark shadows / rust pistils inside the bud are safe."""
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    h, s, v = [hsv[..., i].astype(np.int16) for i in range(3)]
    fg = (alpha > 0.5).astype(np.uint8)
    rim = cv2.dilate(fg, np.ones((3, 3), np.uint8)) - cv2.erode(fg, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * band + 1,) * 2))
    bucket_red = ((h < 6) | (h > 172)) & (s > 110) & (v > 70)
    glove = (((v < 80) & (s < 120)) | ((h >= 95) & (h <= 125) & (s > 25))
             | ((h >= 100) & (h <= 150) & (s < 45) & (v > 90)))      # pale fingertip sheen
    foreign = ((bucket_red | glove) & (rim > 0)).astype(np.uint8)
    foreign = cv2.morphologyEx(foreign, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    # grow glove blobs a touch so their anti-aliased halo goes too
    foreign = cv2.dilate(foreign, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    out = alpha * (1 - foreign.astype(np.float32))
    lab, n = ndimage.label(out > 0.5)
    if n > 1:
        sizes = ndimage.sum(out > 0.5, lab, range(1, n + 1)); out = out * (lab == (int(np.argmax(sizes)) + 1))
    return out

def defringe(rgb, alpha, erode_px=1, feather=1.2):
    """Erode/feather the alpha and pull background colour out of edge pixels."""
    a = (alpha > 0.5).astype(np.uint8)
    if erode_px:
        a = cv2.erode(a, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * erode_px + 1,) * 2))
    a = cv2.GaussianBlur(a.astype(np.float32), (0, 0), feather)
    a = np.clip(a, 0, 1)
    # background estimate under the edge: colour of pixels OUTSIDE the (dilated) subject, diffused inward
    outside = (cv2.dilate((alpha > 0.5).astype(np.uint8), np.ones((9, 9), np.uint8)) == 0).astype(np.float32)
    num = cv2.GaussianBlur(rgb.astype(np.float32) * outside[..., None], (0, 0), 25)
    den = cv2.GaussianBlur(outside, (0, 0), 25)[..., None] + 1e-4
    B = num / den
    C = rgb.astype(np.float32)
    edge = (a > 0.02) & (a < 0.98)
    F = C.copy()
    aa = a[..., None]
    F[edge] = ((C - (1 - aa) * B) / np.maximum(aa, 0.05))[edge]
    return np.clip(F, 0, 255).astype(np.uint8), a

def _sam_region(sam_session, crop, info, X0, Y0, X1, Y1):
    ch, cw = crop.shape[:2]
    s = 1024 / max(ch, cw)
    small = cv2.resize(crop, (round(cw * s), round(ch * s)), interpolation=cv2.INTER_AREA)
    to_s = lambda p: [(p[0] - X0) * s, (p[1] - Y0) * s]
    pos = [to_s(info["point"])]
    neg = [to_s(p) for p in info["negs"] if X0 <= p[0] < X1 and Y0 <= p[1] < Y1]
    ref = cv2.resize(info["comp"][Y0:Y1, X0:X1].astype(np.uint8), (small.shape[1], small.shape[0]),
                     interpolation=cv2.INTER_NEAREST).astype(bool)
    m = None
    for attempt in range(3):
        masks, iou = sam_masks(sam_session, small, pos, neg)
        m = pick_sam_mask(masks, iou, ref, neg)
        if m is None or m.sum() == 0:
            return None, small, pos, neg, iou, s
        lab, n = ndimage.label(m)
        lid = lab[int(pos[0][1]), int(pos[0][0])]
        if lid == 0:
            sizes = ndimage.sum(m, lab, range(1, n + 1)); lid = int(np.argmax(sizes)) + 1
        m = lab == lid
        ys, xs = np.where(m)
        leaks_down = ys.max() >= small.shape[0] - 2 and (Y1 < info["comp"].shape[0])  # hits crop bottom, not image bottom
        too_big = m.sum() > 3.0 * max(ref.sum(), 1)
        if not (leaks_down or too_big):
            break
        # push SAM off the pile: negatives along the lowest rows of the leaked mask
        band = m.copy(); band[: int(ys.min() + 0.75 * (ys.max() - ys.min()))] = False
        if band.sum() > 50:
            by, bx = np.where(band)
            for q in (0.2, 0.5, 0.8):
                idx = int(q * (len(bx) - 1)); order = np.argsort(bx)
                neg.append([float(bx[order[idx]]), float(by[order[idx]])])
    return m, small, pos, neg, iou, s

def cut(path, sam_session, bire_session, margin=0.22, debug=None):
    """Path convenience wrapper around cut_array (EXIF-oriented)."""
    rgb_full = np.asarray(ImageOps.exif_transpose(Image.open(path)).convert("RGB"))
    return cut_array(rgb_full, sam_session, bire_session, margin=margin, debug=debug)

def cut_array(rgb_full, sam_session, bire_session, margin=0.22, debug=None):
    """rgb_full: uint8 HxWx3, already upright. Returns (rgba_crop uint8 HxWx4, meta) or (None, meta)."""
    rgb_full = np.ascontiguousarray(rgb_full)
    H, W = rgb_full.shape[:2]
    info = find_focal_bud(rgb_full)
    if info is None:
        return None, dict(reason="no held bud found")
    if info.get("from_pile"):
        margin = max(margin, 0.5)
    x0, y0, x1, y1 = info["bbox"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    side = max(x1 - x0, y1 - y0) * (1 + 2 * margin)
    for grow in range(3):
        X0, Y0 = int(max(0, cx - side / 2)), int(max(0, cy - side / 2))
        X1, Y1 = int(min(W, cx + side / 2)), int(min(H, cy + side / 2))
        crop = rgb_full[Y0:Y1, X0:X1]
        ch, cw = crop.shape[:2]
        m, small, pos, neg, iou, s = _sam_region(sam_session, crop, info, X0, Y0, X1, Y1)
        if m is None or m.sum() < 0.002 * m.size:
            return None, dict(reason="sam empty")
        ys, xs = np.where(m)
        hits = ((xs.min() <= 1 and X0 > 0) or (ys.min() <= 1 and Y0 > 0) or
                (xs.max() >= small.shape[1] - 2 and X1 < W) or (ys.max() >= small.shape[0] - 2 and Y1 < H))
        if not hits:
            break
        side *= 1.4                                   # subject ran into the crop border → widen and redo
    gate = cv2.resize(m.astype(np.uint8), (cw, ch), interpolation=cv2.INTER_LINEAR).astype(np.float32)
    d = max(3, int(0.012 * max(ch, cw)))
    gate = cv2.dilate(gate, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * d + 1, 2 * d + 1)))
    gate = cv2.GaussianBlur(gate, (0, 0), d / 2)
    # BiRefNet fine matte on the crop, gated by the SAM region. Both models must agree that there is
    # one solid object here; otherwise decline and let the full-frame path have it.
    ba = birefnet_alpha(bire_session, crop)
    alpha = ba * gate
    fg = alpha > 0.5
    sam_area = m.sum() / (s * s)
    if fg.sum() < 0.5 * sam_area:
        return None, dict(reason="birefnet does not see the object SAM picked")
    region = cv2.resize(m.astype(np.uint8), (cw, ch), interpolation=cv2.INTER_NEAREST).astype(bool)
    if region.any() and float(ba[region].mean()) < 0.7:
        return None, dict(reason="birefnet unsure inside the SAM region (uniform matte)")
    lab, n = ndimage.label(fg)
    sizes = ndimage.sum(fg, lab, range(1, n + 1))
    if sizes.max() < 0.7 * fg.sum():
        return None, dict(reason="fragmented matte (texture, not a bud)")
    keep = lab == (int(np.argmax(sizes)) + 1)
    alpha = alpha * keep
    ys, xs = np.where(keep)
    if keep.sum() < 0.3 * (np.ptp(ys) + 1) * (np.ptp(xs) + 1):
        return None, dict(reason="not a solid blob")
    used = "birefnet*sam"
    alpha = peel_foreign(crop, alpha)
    if (alpha > 0.5).mean() < 0.04:
        return None, dict(reason="subject too small for its crop (pile nug?)")
    rgb_df, a = defringe(crop, alpha, erode_px=2, feather=1.5)
    rgba = np.dstack([rgb_df, (a * 255).astype(np.uint8)])
    meta = dict(reason="ok", used=used, bbox=(X0, Y0, X1, Y1), pos=pos, neg=neg, iou=iou.tolist(),
                cover=float((a > 0.5).mean()))
    if debug is not None:
        vis = small.copy()
        for (x, y) in pos: cv2.circle(vis, (int(x), int(y)), 14, (0, 255, 0), -1)
        for (x, y) in neg: cv2.circle(vis, (int(x), int(y)), 14, (255, 0, 255), -1)
        edge = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
        vis[edge] = (255, 255, 0)
        debug["prompt"] = vis
        debug["birefnet"] = (cv2.resize(ba, (small.shape[1], small.shape[0])) * 255).astype(np.uint8)
    return rgba, meta
