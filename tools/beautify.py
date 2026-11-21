#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Делает диаграммы draw.io (.drawio / .xml) более читаемыми.

Что делает (для каждого листа диаграммы):
  1. Раздвигает пересекающиеся блоки, чтобы подписи не накладывались друг на друга.
     Перемещает только «листовые» фигуры (задачи, сущности, атрибуты и т. п.),
     а не плавательные дорожки/пулы (swimlane); фигуры остаются внутри родителя.
  2. Перекладывает каждое ребро ортогонально (по сетке) и огибает все блоки
     (A* с обходом препятствий), поэтому линии не пересекают блоки.
  3. Разводит рёбра, проходящие по одним и тем же коридорам, чтобы они не наслаивались
     (стоимость повторного использования клеток + смещение совпавших маршрутов).
  4. Гарантирует белый фон подписей рёбер (labelBackgroundColor) и сдвигает подпись,
     если её центр попадает на блок.

Не меняет подписи, стили заливки/цвета и шрифты. Правки выполняются на уровне строк —
остальная разметка файла сохраняется байт-в-байт.

Зависимости: только стандартная библиотека Python 3.

Команды:
    python3 tools/beautify.py check ФАЙЛ [ЛИСТ...]     — диагностика без изменений
    python3 tools/beautify.py fix   ФАЙЛ [ЛИСТ...]     — применить правки (перезаписывает файл)

Опции команды fix:
    --no-layout          не раздвигать блоки (только перекладывать рёбра)
    --margin N           отступ рёбер от блоков, px (по умолчанию 12)
    --grid N             шаг сетки маршрутизации, px (по умолчанию 10)
    --dry-run            показать, что изменится, без записи в файл
"""

import argparse
import heapq
import re

MXCELL_RE = re.compile(r"<mxCell\b.*?</mxCell>|<mxCell\b[^>]*/>", re.S)
DIAGRAM_RE = re.compile(r"<diagram\b[^>]*name=\"([^\"]*)\"[^>]*>(.*?)</diagram>", re.S)
ATTR_RE = re.compile(r"([A-Za-z_][\w-]*)=\"([^\"]*)\"")
EXIT_RE = re.compile(r"(?:^|;)\s*(?:exitX|exitY|entryX|entryY|exitDx|exitDy|entryDx|entryDy)\s*=\s*[^;]*", re.I)
EDGESTYLE_RE = re.compile(r"(?:^|;)\s*edgeStyle\s*=\s*[^;]*", re.I)


# --------------------------------------------------------------------------- #
# Чтение и разбор
# --------------------------------------------------------------------------- #

def read_xml(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def pages(xml):
    return [(name, body) for name, body in DIAGRAM_RE.findall(xml)]


def is_swimlane(style):
    return "swimlane" in (style or "")


def fmt(v):
    """Целое — без дроби, иначе один знак после запятой."""
    v = float(v)
    if abs(v - round(v)) < 1e-6:
        return str(int(round(v)))
    return f"{v:.1f}"


def parse_cells(body):
    """Вернуть список клеток листа с их смещениями в теле."""
    cells = []
    for m in MXCELL_RE.finditer(body):
        raw = m.group(0)
        attrs = dict(ATTR_RE.findall(raw))
        c = {
            "raw": raw,
            "start": m.start(),
            "end": m.end(),
            "id": attrs.get("id", ""),
            "value": attrs.get("value", ""),
            "style": attrs.get("style", ""),
            "parent": attrs.get("parent", "1"),
            "vertex": attrs.get("vertex") == "1",
            "edge": attrs.get("edge") == "1",
            "source": attrs.get("source", ""),
            "target": attrs.get("target", ""),
            "x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0,
            "points": [],
            "label_x": None, "label_y": None,
        }
        gm = re.search(r"<mxGeometry\b[^>]*>", raw)
        if gm:
            geo = gm.group(0)
            gattrs = dict(ATTR_RE.findall(geo))
            if "x" in gattrs:
                c["x"] = float(gattrs["x"])
            if "y" in gattrs:
                c["y"] = float(gattrs["y"])
            if "width" in gattrs:
                c["w"] = float(gattrs["width"])
            if "height" in gattrs:
                c["h"] = float(gattrs["height"])
            if c["edge"]:
                # у рёбер x/y в geometry — это смещение подписи
                if "x" in gattrs:
                    c["label_x"] = float(gattrs["x"])
                if "y" in gattrs:
                    c["label_y"] = float(gattrs["y"])
            c["points"] = [
                (float(a), float(b))
                for a, b in re.findall(
                    r"<mxPoint\b[^>]*\bx=\"([^\"]*)\"[^>]*\by=\"([^\"]*)\"", raw
                )
            ]
        cells.append(c)
    return cells


def abs_rect(c, by_id):
    """Абсолютный прямоугольник клетки (с учётом цепочки родителей)."""
    x, y = c["x"], c["y"]
    p = c["parent"]
    while p and p not in ("0", "1"):
        pc = by_id.get(p)
        if not pc:
            break
        x += pc["x"]
        y += pc["y"]
        p = pc["parent"]
    return x, y, c["w"], c["h"]


def parent_offset(c, by_id):
    """Суммарное смещение предков клетки (для перевода абсолютных координат в локальные)."""
    ox = oy = 0.0
    p = c["parent"]
    while p and p not in ("0", "1"):
        pc = by_id.get(p)
        if not pc:
            break
        ox += pc["x"]
        oy += pc["y"]
        p = pc["parent"]
    return ox, oy


# --------------------------------------------------------------------------- #
# Раздвижение пересекающихся блоков
# --------------------------------------------------------------------------- #

def overlap(a, b, eps=1.0):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ox = min(ax + aw, bx + bw) - max(ax, bx)
    oy = min(ay + ah, by + bh) - max(ay, by)
    return ox > eps and oy > eps


# дополнительный зазор, на который раздвигаются пересекающиеся блоки
SEP_MARGIN = 8.0


def _separate_pair(a, b, bounds, margin=SEP_MARGIN):
    """Вычислить новую позицию b (x, y), чтобы она не пересекала a.
    Возвращает (nx, ny) или None, если двигать не требуется."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ox = min(ax + aw, bx + bw) - max(ax, bx)
    oy = min(ay + ah, by + bh) - max(ay, by)
    if ox <= 0 or oy <= 0:
        return None

    cax, cay = ax + aw / 2, ay + ah / 2
    cbx, cby = bx + bw / 2, by + bh / 2
    if ox <= oy:
        dx = ox + margin if cbx >= cax else -(ox + margin)
        dy = 0.0
    else:
        dx = 0.0
        dy = oy + margin if cby >= cay else -(oy + margin)

    nx, ny = bx + dx, by + dy
    if bounds is not None:
        minx, miny, maxx, maxy = bounds
        nx = max(minx, min(nx, maxx - bw))
        ny = max(miny, min(ny, maxy - bh))
        if abs(nx - bx) < 0.5 and abs(ny - by) < 0.5:
            # некуда двигать — пробуем противоположное направление
            if dx:
                nx = max(minx, min(bx - dx, maxx - bw))
            if dy:
                ny = max(miny, min(by - dy, maxy - bh))

    return (nx, ny)


def resolve_overlaps(cells, by_id, max_iter=400, margin=SEP_MARGIN):
    """Вернуть {id: (abs_x, abs_y)} для вершин, которые пришлось сдвинуть.

    Раздвигает все пересекающиеся листовые фигуры глобально; фигура, у которой есть
    родитель-контейнер (swimlane), удерживается в его границах."""
    rects = []
    for c in cells:
        if c["vertex"] and not is_swimlane(c["style"]) and c["w"] > 0 and c["h"] > 0:
            bounds = None
            if c["parent"] not in ("0", "1"):
                pc = by_id.get(c["parent"])
                if pc:
                    px, py, pw, ph = abs_rect(pc, by_id)
                    bounds = (px, py, px + pw, py + ph)
            rects.append([c, *abs_rect(c, by_id), bounds])  # [cell, x, y, w, h, bounds]

    for _ in range(max_iter):
        moved = False
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                a = rects[i][1:5]
                b = rects[j][1:5]
                if overlap(a, b):
                    new = _separate_pair(a, b, rects[j][5], margin)
                    if new is not None:
                        rects[j][1], rects[j][2] = new
                        moved = True
        if not moved:
            break

    return {c["id"]: (x, y) for c, x, y, _w, _h, _b in rects}


# --------------------------------------------------------------------------- #
# Ортогональная маршрутизация рёбер (A* с обходом препятствий)
# --------------------------------------------------------------------------- #

class Router:
    def __init__(self, obstacles, grid=10, pad=200):
        self.grid = grid
        if not obstacles:
            obstacles = [(0, 0, 100, 100)]
        xs = [r[0] for r in obstacles]
        ys = [r[1] for r in obstacles]
        xe = [r[0] + r[2] for r in obstacles]
        ye = [r[1] + r[3] for r in obstacles]
        self.minx = int(min(xs) - pad)
        self.miny = int(min(ys) - pad)
        maxx = int(max(xe) + pad)
        maxy = int(max(ye) + pad)
        self.w = (maxx - self.minx) // grid + 2
        self.h = (maxy - self.miny) // grid + 2
        self.blocked = self._build(obstacles)

    def _build(self, obstacles):
        g = self.grid
        blocked = [[False] * self.h for _ in range(self.w)]
        for (x, y, w, h) in obstacles:
            i0 = int((x - self.minx) / g)
            i1 = int((x + w - self.minx) / g) + 1
            j0 = int((y - self.miny) / g)
            j1 = int((y + h - self.miny) / g) + 1
            for i in range(max(0, i0), min(self.w, i1)):
                for j in range(max(0, j0), min(self.h, j1)):
                    # блокируем только клетки, чей центр внутри препятствия,
                    # иначе стены получаются на полклетки толще и закрывают проходы
                    cx = self.minx + (i + 0.5) * g
                    cy = self.miny + (j + 0.5) * g
                    if x <= cx <= x + w and y <= cy <= y + h:
                        blocked[i][j] = True
        return blocked

    def _cell(self, x, y):
        return int((x - self.minx) / self.grid), int((y - self.miny) / self.grid)

    def _center(self, i, j):
        return self.minx + (i + 0.5) * self.grid, self.miny + (j + 0.5) * self.grid

    def _inside(self, rect, x, y):
        rx, ry, rw, rh = rect
        return rx <= x <= rx + rw and ry <= y <= ry + rh

    def _free(self, i, j, src, tgt):
        if not (0 <= i < self.w and 0 <= j < self.h):
            return False
        if not self.blocked[i][j]:
            return True
        # клетка занята — разрешаем проход только через прямоугольники источника/цели
        cx, cy = self._center(i, j)
        return self._inside(src, cx, cy) or self._inside(tgt, cx, cy)

    def route(self, src_rect, tgt_rect, usage, margin):
        sx, sy = src_rect[0] + src_rect[2] / 2, src_rect[1] + src_rect[3] / 2
        tx, ty = tgt_rect[0] + tgt_rect[2] / 2, tgt_rect[1] + tgt_rect[3] / 2
        # область, через которую ребру разрешено проходить у своих концов,
        # включает зазор (margin) вокруг фигуры — иначе ребро заперто в фигуре
        src_free = (src_rect[0] - margin, src_rect[1] - margin,
                    src_rect[2] + 2 * margin, src_rect[3] + 2 * margin)
        tgt_free = (tgt_rect[0] - margin, tgt_rect[1] - margin,
                    tgt_rect[2] + 2 * margin, tgt_rect[3] + 2 * margin)
        start = self._cell(sx, sy)
        goal = self._cell(tx, ty)

        def h(i, j):
            return abs(i - goal[0]) + abs(j - goal[1])

        g = {start: 0.0}
        came = {}
        open_set = [(h(*start), 0.0, start)]
        heapq.heapify(open_set)
        closed = set()
        found = None

        while open_set:
            _f, _g, cur = heapq.heappop(open_set)
            if cur in closed:
                continue
            closed.add(cur)
            if cur == goal:
                found = cur
                break
            i, j = cur
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ni, nj = i + di, j + dj
                nxt = (ni, nj)
                if not self._free(ni, nj, src_free, tgt_free):
                    continue
                extra = usage.get(nxt, 0) * 2.0
                ng = g[cur] + 1.0 + extra
                if ng < g.get(nxt, float("inf")):
                    g[nxt] = ng
                    came[nxt] = cur
                    heapq.heappush(open_set, (ng + h(ni, nj), ng, nxt))

        if found is None:
            return None

        # восстановить путь в клетках
        path = [found]
        while path[-1] in came:
            path.append(came[path[-1]])
        path.reverse()
        pts = [self._center(i, j) for i, j in path]
        return pts


def _simplify(pts):
    if len(pts) <= 2:
        return pts
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        x0, y0 = out[-1]
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        colinear = (x1 == x0 == x2) or (y1 == y0 == y2)
        if not colinear:
            out.append(pts[i])
    out.append(pts[-1])
    return out


def _border_crossing(inside, outside, rect):
    x, y, w, h = rect
    x0, y0 = inside
    x1, y1 = outside
    ts = []
    if x1 < x and x1 != x0:
        ts.append((x - x0) / (x1 - x0))
    elif x1 > x + w and x1 != x0:
        ts.append((x + w - x0) / (x1 - x0))
    if y1 < y and y1 != y0:
        ts.append((y - y0) / (y1 - y0))
    elif y1 > y + h and y1 != y0:
        ts.append((y + h - y0) / (y1 - y0))
    if not ts:
        return inside
    t = min(v for v in ts if 0 <= v <= 1)
    return (x0 + t * (x1 - x0), y0 + t * (y1 - y0))


def _trim_path(pts, src_rect, tgt_rect):
    """Обрезать маршрут от центра до центра — до границ фигур."""
    if len(pts) < 2:
        return pts
    # от источника
    a = 0
    while a < len(pts) and _point_in(pts[a], src_rect):
        a += 1
    if a == 0:
        a = 1
    if a >= len(pts):
        a = len(pts) - 1
    start_cross = _border_crossing(pts[a - 1], pts[a], src_rect)

    b = len(pts) - 1
    while b >= 0 and _point_in(pts[b], tgt_rect):
        b -= 1
    if b == len(pts) - 1:
        b = len(pts) - 2
    if b < 0:
        b = 0
    end_cross = _border_crossing(pts[b + 1], pts[b], tgt_rect)

    mid = pts[a:b + 1]
    return [start_cross] + mid + [end_cross]


def _point_in(p, rect):
    x, y, w, h = rect
    return x <= p[0] <= x + w and y <= p[1] <= y + h


def polyline_midpoint(pts):
    if not pts:
        return (0, 0)
    if len(pts) == 1:
        return pts[0]
    total = 0.0
    segs = []
    for i in range(1, len(pts)):
        d = abs(pts[i][0] - pts[i - 1][0]) + abs(pts[i][1] - pts[i - 1][1])
        segs.append(d)
        total += d
    half = total / 2.0
    acc = 0.0
    for i, d in enumerate(segs):
        if acc + d >= half:
            t = (half - acc) / d if d else 0.0
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            return (x0 + t * (x1 - x0), y0 + t * (y1 - y0))
        acc += d
    return pts[-1]


def route_edges(cells, by_id, margin, grid):
    """Вернуть {edge_id: (points, label_offset)} для рёбер, которые удалось переложить."""
    obstacles = []
    for c in cells:
        if c["vertex"] and not is_swimlane(c["style"]) and c["w"] > 0 and c["h"] > 0:
            x, y, w, h = abs_rect(c, by_id)
            obstacles.append((x - margin, y - margin, w + 2 * margin, h + 2 * margin))

    router = Router(obstacles, grid=grid)
    usage = {}
    result = {}
    placed_labels = []

    for c in cells:
        if not c["edge"]:
            continue
        src = by_id.get(c["source"])
        tgt = by_id.get(c["target"])
        if not src or not tgt or c["source"] == c["target"]:
            continue
        src_rect = abs_rect(src, by_id)
        tgt_rect = abs_rect(tgt, by_id)
        pts = router.route(src_rect, tgt_rect, usage, margin)
        if pts is None:
            continue
        pts = _trim_path(pts, src_rect, tgt_rect)
        pts = _simplify(pts)
        if len(pts) < 2:
            continue
        # учесть занятость клеток, чтобы следующие рёбра шли по другим коридорам
        for p in pts[1:-1]:
            usage[router._cell(*p)] = usage.get(router._cell(*p), 0) + 1

        # подпись: белый фон, сдвиг, если центр попал на блок
        lx = ly = 0.0
        if c["value"]:
            mx, my = polyline_midpoint(pts)
            for ob in obstacles:
                if ob[0] <= mx <= ob[0] + ob[2] and ob[1] <= my <= ob[1] + ob[3]:
                    ly = (ob[1] + ob[3]) - my + 6
                    break
            for (px, py) in placed_labels:
                if abs(px - (mx + lx)) < 40 and abs(py - (my + ly)) < 20:
                    ly += 16
            placed_labels.append((mx + lx, my + ly))

        result[c["id"]] = (pts, (round(lx), round(ly)))
    return result


# --------------------------------------------------------------------------- #
# Перезапись XML
# --------------------------------------------------------------------------- #

def clean_edge_style(style):
    s = EXIT_RE.sub("", style or "")
    s = EDGESTYLE_RE.sub("", s)
    s = "edgeStyle=orthogonalEdgeStyle;" + s.lstrip(";")
    return s


def ensure_label_bg(style):
    if "labelBackgroundColor" not in style:
        return style.rstrip(";") + ";labelBackgroundColor=#ffffff;"
    return style


def set_vertex_pos(raw, nx, ny):
    m = re.search(r"<mxGeometry\b[^>]*>", raw)
    if not m:
        return raw
    geo = m.group(0)
    new_geo = geo
    for attr, val in (("x", fmt(nx)), ("y", fmt(ny))):
        if re.search(r"\b" + attr + r"=\"[^\"]*\"", new_geo):
            new_geo = re.sub(r"\b" + attr + r"=\"[^\"]*\"", attr + '="' + val + '"', new_geo)
        else:
            new_geo = new_geo[:-2] + ' ' + attr + '="' + val + '">'
    return raw[:m.start()] + new_geo + raw[m.end():]


def set_edge_geometry(raw, points, label_off):
    m = re.search(r"<mxGeometry\b[^>]*>", raw)
    if not m:
        return raw
    start = m.start()
    if m.group(0).rstrip().endswith("/>"):
        end = m.end()
    else:
        close = raw.find("</mxGeometry>", m.end())
        end = close + len("</mxGeometry>") if close != -1 else m.end()

    lx, ly = label_off
    s = '<mxGeometry relative="1" as="geometry" x="%d" y="%d">' % (lx, ly)
    s += "<Array as=\"points\">"
    for x, y in points:
        s += '<mxPoint x="%s" y="%s" />' % (fmt(x), fmt(y))
    s += "</Array></mxGeometry>"
    return raw[:start] + s + raw[end:]


def set_edge_style(raw, new_style):
    m = re.search(r"<mxCell\b[^>]*>", raw)
    if not m:
        return raw
    tag = m.group(0)
    if re.search(r"\bstyle=\"[^\"]*\"", tag):
        new_tag = re.sub(r"\bstyle=\"[^\"]*\"", 'style="' + new_style.replace('"', "&quot;") + '"', tag)
    else:
        new_tag = tag[:-1] + ' style="' + new_style.replace('"', "&quot;") + '">'
    return raw[:m.start()] + new_tag + raw[m.end():]


def apply_changes(body, cells, new_pos, edge_routes):
    edits = []  # (start, end, new_raw)
    for c in cells:
        raw = c["raw"]
        if c["id"] in new_pos:
            nx, ny = new_pos[c["id"]]
            raw = set_vertex_pos(raw, nx, ny)
        if c["edge"] and c["id"] in edge_routes:
            points, label_off = edge_routes[c["id"]]
            style = ensure_label_bg(clean_edge_style(c["style"]))
            raw = set_edge_style(raw, style)
            raw = set_edge_geometry(raw, points, label_off)
        if raw != c["raw"]:
            edits.append((c["start"], c["end"], raw))

    # применяем с конца, чтобы смещения остались корректными
    edits.sort(reverse=True)
    for start, end, raw in edits:
        body = body[:start] + raw + body[end:]
    return body


# --------------------------------------------------------------------------- #
# Диагностика
# --------------------------------------------------------------------------- #

def report(body):
    cells = parse_cells(body)
    by_id = {c["id"]: c for c in cells}
    nodes = [abs_rect(c, by_id) for c in cells
             if c["vertex"] and not is_swimlane(c["style"]) and c["w"] > 0 and c["h"] > 0]

    n_overlap = 0
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if overlap(nodes[i], nodes[j]):
                n_overlap += 1

    n_cross = 0
    for c in cells:
        if not c["edge"]:
            continue
        src = by_id.get(c["source"])
        tgt = by_id.get(c["target"])
        if not src or not tgt:
            continue
        sx, sy, sw, sh = abs_rect(src, by_id)
        tx, ty, tw, th = abs_rect(tgt, by_id)
        # прямая (или имеющийся маршрут) от центра к центру
        cx0, cy0 = sx + sw / 2, sy + sh / 2
        cx1, cy1 = tx + tw / 2, ty + th / 2
        if c["points"]:
            pts = [(cx0, cy0)] + list(c["points"]) + [(cx1, cy1)]
        else:
            pts = [(cx0, cy0), (cx1, cy1)]
        crosses = False
        for k in range(len(pts) - 1):
            x0, y0 = pts[k]
            x1, y1 = pts[k + 1]
            steps = 24
            for s in range(steps + 1):
                x = x0 + (x1 - x0) * s / steps
                y = y0 + (y1 - y0) * s / steps
                for rx, ry, rw, rh in nodes:
                    if (rx, ry, rw, rh) == (sx, sy, sw, sh) or (rx, ry, rw, rh) == (tx, ty, tw, th):
                        continue
                    if rx < x < rx + rw and ry < y < ry + rh:
                        crosses = True
                        break
                if crosses:
                    break
            if crosses:
                break
        if crosses:
            n_cross += 1

    return {"nodes": len(nodes), "overlaps": n_overlap, "crossings": n_cross}


# --------------------------------------------------------------------------- #
# Команды
# --------------------------------------------------------------------------- #

def cmd_check(args):
    xml = read_xml(args.file)
    shown = False
    for name, body in pages(xml):
        if args.pages and name not in args.pages:
            continue
        r = report(body)
        print(f"{name}: блоков {r['nodes']}, пересечений блоков {r['overlaps']}, "
              f"пересечений рёбер с блоками {r['crossings']}")
        shown = True
    if not shown:
        raise SystemExit("не найдено ни одного указанного листа")


def cmd_fix(args):
    xml = read_xml(args.file)
    total = {"vertices": 0, "edges": 0}
    for name, body in pages(xml):
        if args.pages and name not in args.pages:
            continue
        cells = parse_cells(body)
        by_id = {c["id"]: c for c in cells}

        new_pos = {}
        if not args.no_layout:
            abs_pos = resolve_overlaps(cells, by_id)
            for cid, (ax, ay) in abs_pos.items():
                c = by_id[cid]
                ox, oy = parent_offset(c, by_id)
                nx, ny = ax - ox, ay - oy
                if abs(nx - c["x"]) > 0.5 or abs(ny - c["y"]) > 0.5:
                    new_pos[cid] = (nx, ny)

        edge_routes = route_edges(cells, by_id, args.margin, args.grid)

        new_body = apply_changes(body, cells, new_pos, edge_routes)
        total["vertices"] += len(new_pos)
        total["edges"] += len(edge_routes)
        if new_body != body:
            xml = xml.replace(body, new_body, 1)
        print(f"{name}: сдвинуто блоков {len(new_pos)}, переложено рёбер {len(edge_routes)}")

    if not args.dry_run:
        with open(args.file, "w", encoding="utf-8") as f:
            f.write(xml)
        print(f"записано: {args.file}")
    else:
        print("(dry-run: файл не изменён)")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("check", help="диагностика без изменений")
    sp.add_argument("file")
    sp.add_argument("pages", nargs="*")
    sp.set_defaults(func=cmd_check)

    sp = sub.add_parser("fix", help="применить правки")
    sp.add_argument("file")
    sp.add_argument("pages", nargs="*")
    sp.add_argument("--no-layout", action="store_true")
    sp.add_argument("--margin", type=float, default=12.0)
    sp.add_argument("--grid", type=int, default=10)
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_fix)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
