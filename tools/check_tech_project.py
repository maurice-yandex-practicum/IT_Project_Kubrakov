#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Статическая сверка ссылок и геометрии технического проекта.

Проверяет основания проверок методики, коды задач BPMN в техническом
проекте, уникальность идентификаторов и маршруты нового исходника draw.io.
Маршруты читаются с учётом exitX/entryX; смещение подписи не является точкой
маршрута. Программные испытания серверного ПО этим инструментом не выполняются.
"""

from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
ERRORS = []
BASIS = r"(?:Н-\d+|R\d+|F\d+)"


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def verify(condition, message):
    if not condition:
        ERRORS.append(message)


def check_references():
    domain = read("01-domain/domain.md")
    functional = read("03-functional/functional.md")
    quality = read("07-quality/quality.md")
    technical = read("06-tech_project/tech_project.md")
    ids = set(re.findall(r"Н-\d+", domain))
    ids.update(re.findall(r"\*\*(R\d+)\.\*\*", domain))
    ids.update(re.findall(r"^### (F\d+)\.", functional, re.M))
    checks = set(re.findall(r"^### (П-\d+)\.", quality, re.M))
    criteria = set(re.findall(r"^- \*\*(КР-\d+):", quality, re.M))
    for item in set(re.findall(r"П-\d+", technical)):
        verify(item in checks, f"Неизвестная проверка в техническом проекте: {item}")
    sections = set(re.findall(r"^#{2,3} (6\.\d+(?:\.\d+)?)\.", technical, re.M))
    for line in quality.splitlines():
        if line.startswith("Критерий:"):
            verify("Основание:" in line, "У проверки отсутствует основание")
            for item in re.findall(BASIS, line):
                verify(item in ids, f"Неизвестное основание в методике: {item}")
            for item in re.findall(r"КР-\d+", line):
                verify(item in criteria, f"Неизвестный критерий: {item}")
            if "технический проект" in line:
                for item in re.findall(r"\b6\.\d+(?:\.\d+)?", line):
                    verify(item in sections, f"Неизвестный раздел технического проекта: {item}")
    obsolete = r"(?:\bF\d+/\d+(?:\.\d+)*|\b(?:У|ФТ|Т|К)-\d+)"
    verify(not re.search(obsolete, quality), "В методике остались идентификаторы удалённого перечня требований")
    blocks = re.split(r"(?=^### П-\d+\.)", quality, flags=re.M)
    for ident, check in [("F1", "П-01"), ("F3", "П-04"),
                         ("F3", "П-07"), ("F5", "П-09"),
                         ("F6", "П-17")]:
        block = next((b for b in blocks if b.startswith(f"### {check}.")), "")
        verify(ident in block, f"Нет обратной ссылки {check} → {ident}")
    bpmn = ET.fromstring(read("04-bpmn/BPMN.drawio.xml"))
    task_ids = {c.get("id") for c in bpmn.iter("mxCell")}
    task_pattern = r"\b(?:RG|AU|RA|RC|RS|RI|ST|MT|FN|CL|CP|FI|OB|CF|PY|JB)\d+[a-z]?\b"
    for item in set(re.findall(task_pattern, technical)):
        verify(item in task_ids, f"Неизвестная задача BPMN в техническом проекте: {item}")
    print(f"Ссылки: {len(ids)} оснований, {len(criteria)} критериев, {len(checks)} проверок")


def style_values(style):
    return dict(part.split("=", 1) for part in style.split(";") if "=" in part)


def segment_crosses(a, b, rect):
    x, y, w, h = rect
    if abs(a[0] - b[0]) < 1e-6:
        return x < a[0] < x+w and max(min(a[1], b[1]), y) < min(max(a[1], b[1]), y+h)
    if abs(a[1] - b[1]) < 1e-6:
        return y < a[1] < y+h and max(min(a[0], b[0]), x) < min(max(a[0], b[0]), x+w)
    raise ValueError(f"Неортогональный участок: {a} → {b}")


def check_diagram():
    tree = ET.fromstring(read("06-tech_project/technical_solution.drawio.xml"))
    pages = tree.findall("diagram")
    verify(len(pages) == 3, "Техническая схема должна содержать три листа")
    for page in pages:
        cells = list(page.iter("mxCell"))
        ids = [c.get("id") for c in cells]
        verify(len(ids) == len(set(ids)), f"Повтор id на листе {page.get('name')}")
        rects = {}
        model = page.find("mxGraphModel")
        for cell in cells:
            if cell.get("vertex") != "1":
                continue
            geo = cell.find("mxGeometry")
            rect = tuple(float(geo.get(key, "0")) for key in ("x", "y", "width", "height"))
            rects[cell.get("id")] = rect
            x, y, w, h = rect
            verify(0 <= x and 0 <= y and x+w <= float(model.get("pageWidth"))
                   and y+h <= float(model.get("pageHeight")), f"Блок за границами: {cell.get('id')}")
        overlaps = 0
        for i, (ident, a) in enumerate(rects.items()):
            for other, b in list(rects.items())[i+1:]:
                if max(a[0], b[0]) < min(a[0]+a[2], b[0]+b[2]) and max(a[1], b[1]) < min(a[1]+a[3], b[1]+b[3]):
                    overlaps += 1
                    verify(False, f"Пересечение блоков {page.get('name')}: {ident}, {other}")
        crossings = 0
        for cell in cells:
            if cell.get("edge") != "1":
                continue
            source, target = cell.get("source"), cell.get("target")
            if source not in rects or target not in rects:
                verify(False, f"Нет конца связи: {cell.get('id')}")
                continue
            style = style_values(cell.get("style", ""))
            sx, sy, sw, sh = rects[source]
            tx, ty, tw, th = rects[target]
            pts = [(sx + sw*float(style.get("exitX", ".5")), sy + sh*float(style.get("exitY", ".5")))]
            pts.extend((float(p.get("x")), float(p.get("y")))
                       for p in cell.findall("mxGeometry/Array[@as='points']/mxPoint"))
            pts.append((tx + tw*float(style.get("entryX", ".5")), ty + th*float(style.get("entryY", ".5"))))
            for ident, rect in rects.items():
                if ident not in (source, target) and any(segment_crosses(a, b, rect) for a, b in zip(pts, pts[1:])):
                    crossings += 1
                    verify(False, f"Связь {page.get('name')}/{cell.get('id')} пересекает {ident}")
        print(f"{page.get('name')}: {len(rects)} блоков; пересечений блоков {overlaps}, связей с блоками {crossings}")


def main():
    check_references()
    check_diagram()
    for error in ERRORS:
        print(f"ОШИБКА: {error}")
    print(f"Статическая проверка: ошибок {len(ERRORS)}")
    return bool(ERRORS)


if __name__ == "__main__":
    sys.exit(main())
