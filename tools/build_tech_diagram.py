#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка представлений C4: контекст, контейнеры, компоненты.

Запуск: py -3.14 tools/build_tech_diagram.py
Необязательный просмотр: --preview-dir ПАПКА (требует Pillow).
Схема строится стандартной библиотекой; PNG просмотра в артефакты не включаются.
"""

import argparse
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
from c4_model import build_pages


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "06-tech_project" / "technical_solution.drawio.xml"
BLUE = "#dbeafe"
GREEN = "#dcfce7"
GRAY = "#f1f5f9"
AMBER = "#fef3c7"
INK = "#334155"


class Page:
    def __init__(self, name, width, height, level, scope):
        self.name, self.width, self.height = name, width, height
        self.level, self.scope = level, scope
        self.nodes, self.edges = [], []

    def node(self, ident, text, x, y, w, h, fill=BLUE, font=18,
             align="center", plain=False, metadata=None):
        assert not any(n["id"] == ident for n in self.nodes), ident
        self.nodes.append(dict(id=ident, text=text, x=x, y=y, w=w, h=h,
                               fill=fill, font=font, align=align, plain=plain,
                               metadata=metadata or {}))

    def element(self, ident, name, kind, description, x, y, w, h,
                technology="", scope="", external=False, font=18):
        types = {"Person": "Человек", "SoftwareSystem": "Программная система",
                 "Container": "Контейнер", "Component": "Компонент"}
        typed = types[kind] + (f": {technology}" if technology else "")
        self.node(ident, f"{name}\n[{typed}]\n\n{description}", x, y, w, h,
                  fill=GRAY if external else BLUE, font=font,
                  metadata={"c4Type": kind, "c4Name": name,
                            "c4Description": description, "c4Technology": technology,
                            "c4Scope": scope, "c4External": str(external).lower()})

    def boundary(self, ident, name, kind, x, y, w, h):
        label = "Программная система" if kind == "SoftwareSystem" else "Контейнер"
        self.node(ident, f"{name} [{label}]", x, y, w, h, font=20, align="left",
                  metadata={"c4Type": "Boundary", "c4Name": name,
                            "c4BoundaryType": kind})

    def edge(self, ident, source, target, text, start, end, points=(),
             label=None, label_width=250, font=14, two_way=False, technology=""):
        self.edges.append(dict(id=ident, source=source, target=target,
                               text=text, start=start, end=end,
                               points=list(points), label=label,
                               label_width=label_width, font=font, two_way=two_way,
                               technology=technology))

    def titles(self, title, subtitle):
        self.node("title", title, 40, 25, self.width - 80, 55,
                  font=28, align="left", plain=True)
        self.node("subtitle", subtitle, 40, 85, self.width - 80, 50,
                  font=16, align="left", plain=True)

    def path(self, edge):
        by_id = {n["id"]: n for n in self.nodes}

        def anchor(ident, relative):
            n = by_id[ident]
            return (n["x"] + relative[0] * n["w"],
                    n["y"] + relative[1] * n["h"])

        return [anchor(edge["source"], edge["start"]), *edge["points"],
                anchor(edge["target"], edge["end"])]

    def xml(self):
        diagram = ET.Element("diagram", id=self.name, name=self.name,
                             c4Level=str(self.level), c4Scope=self.scope)
        graph = ET.SubElement(diagram, "mxGraphModel", dx=str(self.width),
                              dy=str(self.height), grid="1", gridSize="10",
                              guides="1", tooltips="1", connect="1", arrows="1",
                              fold="1", page="1", pageScale="1",
                              pageWidth=str(self.width), pageHeight=str(self.height),
                              math="0", shadow="0", background="#ffffff")
        root = ET.SubElement(graph, "root")
        ET.SubElement(root, "mxCell", id="0")
        ET.SubElement(root, "mxCell", id="1", parent="0")
        for n in self.nodes:
            style = ("rounded=0;whiteSpace=wrap;html=1;fontFamily=Arial;"
                     f"fontSize={n['font']};fontColor={INK};"
                     f"align={n['align']};verticalAlign=middle;spacing=14;")
            style += ("strokeColor=none;fillColor=none;" if n["plain"] else
                      f"strokeColor={INK};strokeWidth=1.5;fillColor={n['fill']};")
            if n["metadata"].get("c4Type") == "Boundary":
                style += "fillColor=none;dashed=1;verticalAlign=top;spacingTop=18;"
            c = ET.SubElement(root, "mxCell", id=n["id"],
                              value=n["text"].replace("\n", "<br>"),
                              style=style, vertex="1", parent="1", **n["metadata"])
            ET.SubElement(c, "mxGeometry", x=str(n["x"]), y=str(n["y"]),
                          width=str(n["w"]), height=str(n["h"]), **{"as": "geometry"})
        for e in self.edges:
            sx, sy = e["start"]
            tx, ty = e["end"]
            style = ("noEdgeStyle=1;rounded=0;html=1;endArrow=block;endFill=1;"
                     "strokeWidth=1.5;whiteSpace=wrap;fontFamily=Arial;"
                     f"fontSize={e['font']};strokeColor={INK};fontColor={INK};"
                     "labelBackgroundColor=#ffffff;"
                     f"exitX={sx};exitY={sy};exitDx=0;exitDy=0;"
                     f"entryX={tx};entryY={ty};entryDx=0;entryDy=0;")
            if e["two_way"]:
                style += "startArrow=block;startFill=1;"
            c = ET.SubElement(root, "mxCell", id=e["id"],
                              value=e["text"].replace("\n", "<br>"), style=style,
                              edge="1", parent="1", source=e["source"], target=e["target"],
                              c4Technology=e["technology"])
            geo = ET.SubElement(c, "mxGeometry", x="0", y="0", relative="1",
                                **{"as": "geometry"})
            if e["points"]:
                array = ET.SubElement(geo, "Array", **{"as": "points"})
                for x, y in e["points"]:
                    ET.SubElement(array, "mxPoint", x=str(x), y=str(y))
            if e["label"]:
                mx, my = midpoint(self.path(e))
                ET.SubElement(geo, "mxPoint", x=str(e["label"][0] - mx),
                              y=str(e["label"][1] - my), **{"as": "offset"})
        return diagram


def midpoint(points):
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    remaining = sum(lengths) / 2
    for a, b, length in zip(points, points[1:], lengths):
        if remaining <= length and length:
            ratio = remaining / length
            return a[0] + ratio * (b[0] - a[0]), a[1] + ratio * (b[1] - a[1])
        remaining -= length
    return points[-1]


def preview(page, destination):
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (page.width, page.height), "white")
    draw = ImageDraw.Draw(img)
    font_path = Path("C:/Windows/Fonts/arial.ttf")

    def text_box(text, cx, cy, width, size, align="center", background=False):
        font = ImageFont.truetype(str(font_path), size)
        lines = []
        for paragraph in text.split("\n"):
            line = ""
            for word in paragraph.split():
                trial = (line + " " + word).strip()
                if line and draw.textlength(trial, font=font) > width:
                    lines.append(line)
                    line = word
                else:
                    line = trial
            lines.append(line)
        height = len(lines) * (size + 5)
        top = cy - height / 2
        if background:
            actual_width = max(draw.textlength(line, font=font) for line in lines)
            draw.rectangle((cx - actual_width/2 - 5, top - 3,
                            cx + actual_width/2 + 5, top + height + 3), fill="white")
        for index, line in enumerate(lines):
            x = cx - (width / 2 if align == "left" else draw.textlength(line, font=font)/2)
            draw.text((x, top + index * (size + 5)), line, fill=INK, font=font)
        return height

    for n in page.nodes:
        if n["metadata"].get("c4Type") == "Boundary":
            x, y, w, h = n["x"], n["y"], n["w"], n["h"]
            for offset in range(0, int(w), 18):
                stop = min(offset+10, w)
                draw.line((x+offset, y, x+stop, y), fill=INK, width=2)
                draw.line((x+offset, y+h, x+stop, y+h), fill=INK, width=2)
            for offset in range(0, int(h), 18):
                stop = min(offset+10, h)
                draw.line((x, y+offset, x, y+stop), fill=INK, width=2)
                draw.line((x+w, y+offset, x+w, y+stop), fill=INK, width=2)
            draw.text((n["x"]+18, n["y"]+18), n["text"], fill=INK,
                      font=ImageFont.truetype(str(font_path), n["font"]))
            continue
        if not n["plain"]:
            draw.rectangle((n["x"], n["y"], n["x"]+n["w"], n["y"]+n["h"]),
                           fill=n["fill"], outline=INK, width=2)
        height = text_box(n["text"], n["x"]+n["w"]/2, n["y"]+n["h"]/2,
                          n["w"]-28, n["font"], n["align"])
        if height > n["h"] - (0 if n["plain"] else 20):
            raise ValueError(f"Текст не помещается: {page.name}/{n['id']}")
    for e in page.edges:
        pts = page.path(e)
        draw.line(pts, fill=INK, width=2)
        ends = [(pts[-2], pts[-1])]
        if e["two_way"]:
            ends.append((pts[1], pts[0]))
        for a, b in ends:
            angle = math.atan2(b[1]-a[1], b[0]-a[0])
            triangle = [b, (b[0]-12*math.cos(angle-.4), b[1]-12*math.sin(angle-.4)),
                        (b[0]-12*math.cos(angle+.4), b[1]-12*math.sin(angle+.4))]
            draw.polygon(triangle, fill=INK)
    for e in page.edges:
        cx, cy = e["label"] or midpoint(page.path(e))
        text_box(e["text"], cx, cy, e["label_width"], e["font"], background=True)
    img.save(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-dir", type=Path)
    args = parser.parse_args()
    pages = build_pages(Page)
    mxfile = ET.Element("mxfile", host="app.diagrams.net", type="device")
    for page in pages:
        mxfile.append(page.xml())
    ET.indent(mxfile, space="  ")
    ET.ElementTree(mxfile).write(OUTPUT, encoding="utf-8", xml_declaration=True)
    print(f"Схема: {OUTPUT.relative_to(ROOT)}")
    if args.preview_dir:
        args.preview_dir.mkdir(parents=True, exist_ok=True)
        for number, page in enumerate(pages, 1):
            target = args.preview_dir / f"technical-solution-{number}.png"
            preview(page, target)
            print(f"Просмотр: {target}")


if __name__ == "__main__":
    main()
