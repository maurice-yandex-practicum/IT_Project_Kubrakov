#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Инспектор и минимальный редактор диаграмм draw.io (.drawio / .xml).

Работает со структурой:
    <mxfile><diagram name="..."><mxGraphModel><root><mxCell .../></root></mxGraphModel></diagram>...</mxfile>

Не требует сторонних пакетов (только стандартная библиотека).
Правки выполняются на уровне строк: остальная разметка файла сохраняется байт-в-байт.

Команды:
    pages                              — список листов (диаграмм) с числом вершин и рёбер
    cells  PAGE                        — вершины листа: id, подпись, геометрия (x, y, w, h)
    cells  PAGE --all                  — то же, включая клетки без подписей
    edges  PAGE                        — рёбра листа: source -> target : подпись
    edges  PAGE --all                  — включая рёбра без подписей
    find   PAGE TEXT                   — вершины и рёбра, в подписи которых есть TEXT
    stat   PAGE                        — степень каждой вершины (число входящих/исходящих рёбер)
    dot    PAGE [OUT.dot]              — выгрузить лист в формат Graphviz DOT
    set-label PAGE SOURCE TARGET TEXT  — заменить подпись ребра source->target на TEXT
    add-child PAGE PARENT_ID CHILD_ID LABEL [--x X --y Y]
                                       — добавить вершину-потомка под PARENT_ID и ребро от родителя;
                                         без --x/--y потомки укладываются столбцом под родителем
Примеры:
    python3 tools/drawio.py pages
    python3 tools/drawio.py cells "DFD level 1"
    python3 tools/drawio.py edges "DFD level 1"
    python3 tools/drawio.py set-label "Контекстная модель" renter F0 "Регистрация; поиск; ..."
"""

import argparse
import os
import re
import sys

MXCELL_RE = re.compile(r"<mxCell\b[^>]*/?>")
DIAGRAM_RE = re.compile(r"<diagram\b[^>]*name=\"([^\"]*)\"[^>]*>(.*?)</diagram>", re.S)
ATTR_RE = re.compile(r'(\w+)="([^"]*)"')


def read_xml(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def pages(xml):
    return [(name, body) for name, body in DIAGRAM_RE.findall(xml)]


def cells(body, only_labeled=True):
    """Вернуть список вершин: (id, value, geometry dict)."""
    out = []
    for m in MXCELL_RE.finditer(body):
        tag = m.group(0)
        attrs = dict(ATTR_RE.findall(tag))
        if attrs.get("edge") == "1":
            continue
        if not tag.endswith("/>"):
            after = body[m.end():m.end() + 400]
            gm = re.match(r'\s*(<mxGeometry\b[^>]*>)', after)
            if gm:
                attrs.update(dict(ATTR_RE.findall(gm.group(1))))
        value = attrs.get("value", "")
        if only_labeled and not value:
            continue
        geo = {k: attrs.get(k) for k in ("x", "y", "width", "height") if k in attrs}
        out.append((attrs.get("id", ""), value, geo))
    return out


def edges(body, only_labeled=True):
    out = []
    for m in MXCELL_RE.finditer(body):
        tag = m.group(0)
        attrs = dict(ATTR_RE.findall(tag))
        if attrs.get("edge") != "1":
            continue
        value = attrs.get("value", "")
        if only_labeled and not value:
            continue
        out.append((attrs.get("source", ""), attrs.get("target", ""), value))
    return out


def find_page(xml, name):
    for n, body in pages(xml):
        if n == name:
            return body
    raise SystemExit(f"лист не найден: {name}")


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def cmd_pages(args):
    for name, body in pages(read_xml(args.file)):
        vs = cells(body, only_labeled=False)
        es = edges(body, only_labeled=False)
        print(f"{name}: вершин {len(vs)}, рёбер {len(es)}")


def cmd_cells(args):
    body = find_page(read_xml(args.file), args.page)
    for vid, value, geo in cells(body, only_labeled=not args.all):
        g = " ".join(f"{k}={geo[k]}" for k in ("x", "y", "width", "height") if k in geo)
        print(f"{vid}\t{value}\t{g}")


def cmd_edges(args):
    body = find_page(read_xml(args.file), args.page)
    for src, tgt, value in edges(body, only_labeled=not args.all):
        print(f"{src} -> {tgt} : {value}")


def cmd_find(args):
    body = find_page(read_xml(args.file), args.page)
    text = args.text.lower()
    for vid, value, geo in cells(body, only_labeled=False):
        if text in value.lower():
            print(f"[v] {vid}\t{value}")
    for src, tgt, value in edges(body, only_labeled=False):
        if text in value.lower():
            print(f"[e] {src} -> {tgt} : {value}")


def cmd_stat(args):
    body = find_page(read_xml(args.file), args.page)
    ins, outs = {}, {}
    labels = {vid: value for vid, value, _ in cells(body, only_labeled=False)}
    for src, tgt, _ in edges(body, only_labeled=False):
        ins[tgt] = ins.get(tgt, 0) + 1
        outs[src] = outs.get(src, 0) + 1
    ids = sorted(set(ins) | set(outs) | set(labels))
    for i in ids:
        print(f"{i}\t{labels.get(i, '')}\tin={ins.get(i, 0)} out={outs.get(i, 0)}")


def cmd_dot(args):
    body = find_page(read_xml(args.file), args.page)
    out = [f"digraph {re.sub(r'\\W', '_', args.page)} {{", '  node [shape=box];']
    seen = set()
    for vid, value, _ in cells(body, only_labeled=False):
        label = value.replace('"', "'").replace("\n", " ")
        out.append(f'  "{vid}" [label="{label}"];')
        seen.add(vid)
    for src, tgt, value in edges(body, only_labeled=False):
        label = value.replace('"', "'")
        attr = f' [label="{label}"]' if value else ""
        out.append(f'  "{src}" -> "{tgt}"{attr};')
        seen.add(src)
        seen.add(tgt)
    out.append("}")
    text = "\n".join(out)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"записано: {args.out}")
    else:
        print(text)


def replace_cell_value(body, cid, new_value):
    """Заменить value клетки с id=cid (вершины или ребра). Возвращает (new_body, changed)."""
    pattern = re.compile(r'(<mxCell\b[^>]*\bid="' + re.escape(cid) + r'"[^>]*\bvalue=")[^"]*(")')
    new_body, n = pattern.subn(lambda m: m.group(1) + new_value.replace("&", "&amp;").replace('"', "&quot;") + m.group(2), body)
    return new_body, bool(n)


def insert_cells(body, cells_xml):
    """Вставить клетки перед закрывающим </root> (или в конец тела листа)."""
    if "</root>" in body:
        return body.replace("</root>", cells_xml + "</root>", 1)
    return body.rstrip() + "\n" + cells_xml


def xml_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def cmd_set_label(args):
    xml = read_xml(args.file)
    body = find_page(xml, args.page)
    pattern = re.compile(
        r'(<mxCell\b[^>]*\bedge="1"[^>]*\bsource="' + re.escape(args.source) + r'"[^>]*\btarget="' + re.escape(args.target) + r'"[^>]*>)'
    )
    m = pattern.search(body)
    if not m:
        raise SystemExit(f"ребро {args.source} -> {args.target} не найдено на листе {args.page}")
    tag = m.group(1)
    value_m = re.search(r'\bvalue="([^"]*)"', tag)
    if value_m:
        new_tag = tag.replace(f'value="{value_m.group(1)}"', f'value="{xml_escape(args.text)}"', 1)
    else:
        new_tag = tag[:-1] + f' value="{xml_escape(args.text)}">'
    new_body = body.replace(tag, new_tag, 1)
    xml = xml.replace(body, new_body, 1)
    with open(args.file, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"подпись заменена: {args.source} -> {args.target} : {args.text}")


def cmd_set_cell(args):
    xml = read_xml(args.file)
    body = find_page(xml, args.page)
    pattern = re.compile(
        r'(<mxCell\b[^>]*\bid="' + re.escape(args.cell) + r'"[^>]*\bvalue=")[^"]*(")'
    )
    new_body, n = pattern.subn(lambda m: m.group(1) + xml_escape(args.text) + m.group(2), body)
    if not n:
        raise SystemExit(f"вершина {args.cell} на листе {args.page} не найдена или без подписи")
    xml = xml.replace(body, new_body, 1)
    with open(args.file, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"подпись заменена: {args.cell} = {args.text}")


def cmd_check(args):
    import xml.etree.ElementTree as ET
    try:
        ET.parse(args.file)
        print("XML валиден:", args.file)
    except ET.ParseError as e:
        print("ОШИБКА:", e)
        sys.exit(1)


def cmd_add_edge(args):
    xml = read_xml(args.file)
    body = find_page(xml, args.page)
    style = args.style or (
        "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=blockThin;endFill=1;"
        "strokeColor=#334155;fontSize=12;labelBackgroundColor=#ffffff;"
        "dashed=1;endArrow=open;endFill=0;startArrow=oval;startFill=0;"
    )
    eid = args.edge_id or ("e-" + args.source + "-" + args.target)
    edge = (
        f'<mxCell id="{eid}" value="{xml_escape(args.label)}" style="{style}" '
        f'edge="1" source="{args.source}" target="{args.target}" parent="1">'
        '<mxGeometry relative="1" as="geometry"/></mxCell>'
    )
    new_body = insert_cells(body, edge)
    xml = xml.replace(body, new_body, 1)
    with open(args.file, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"добавлено ребро: {args.source} -> {args.target} : {args.label}")


def cmd_remove_edge(args):
    xml = read_xml(args.file)
    body = find_page(xml, args.page)
    pattern = re.compile(
        r'<mxCell\b[^>]*\bedge="1"[^>]*\bsource="' + re.escape(args.source) + r'"[^>]*\btarget="' + re.escape(args.target) + r'"[^>]*'
        r'(?:/>|>.*?</mxCell>)',
        re.S,
    )
    new_body, n = pattern.subn("", body)
    if not n:
        raise SystemExit(f"ребро {args.source} -> {args.target} не найдено")
    xml = xml.replace(body, new_body, 1)
    with open(args.file, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"ребро удалено: {args.source} -> {args.target}")


def cmd_add_vertex(args):
    xml = read_xml(args.file)
    body = find_page(xml, args.page)
    style = args.style or "whiteSpace=wrap;html=1;align=center;verticalAlign=middle;rounded=0;"
    cell = (
        f'<mxCell id="{args.cell}" value="{xml_escape(args.label)}" style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{args.x}" y="{args.y}" width="{args.width}" height="{args.height}" as="geometry"/></mxCell>'
    )
    new_body = insert_cells(body, cell)
    xml = xml.replace(body, new_body, 1)
    with open(args.file, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"добавлена вершина: {args.cell} = {args.label}")


def cmd_add_child(args):
    xml = read_xml(args.file)
    body = find_page(xml, args.page)
    parents = {vid: (value, geo) for vid, value, geo in cells(body, only_labeled=False)}
    if args.parent not in parents:
        raise SystemExit(f"вершина {args.parent} не найдена")
    _, pgeo = parents[args.parent]
    px, py = fnum(pgeo.get("x")), fnum(pgeo.get("y"))
    pw, ph = fnum(pgeo.get("width")), fnum(pgeo.get("height"))
    if args.x is not None:
        cx, cy = float(args.x), float(args.y)
    else:
        # под родителем, столбцом с шагом 44
        existing = [g for vid, _, g in cells(body, only_labeled=False)
                    if vid.startswith(args.parent + "-") or vid.startswith(args.parent + ".")]
        cx = px + pw / 2 - 60
        cy = py + ph + 24 + 44 * len(existing)
    style = "whiteSpace=wrap;html=1;align=center;verticalAlign=middle;rounded=0;"
    child = (f'<mxCell id="{args.child}" value="{xml_escape(args.label)}" style="{style}" vertex="1" parent="1">'
             f'<mxGeometry x="{cx:.0f}" y="{cy:.0f}" width="120" height="40" as="geometry"/></mxCell>')
    edge = (f'<mxCell id="e-{args.child}" edge="1" parent="1" source="{args.parent}" target="{args.child}" '
            'style="edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=none;">'
            '<mxGeometry relative="1" as="geometry"/></mxCell>')
    new_body = insert_cells(body, child + edge)
    xml = xml.replace(body, new_body, 1)
    with open(args.file, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"добавлено: {args.parent} -> {args.child} : {args.label}")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("pages"); sp.add_argument("file"); sp.set_defaults(func=cmd_pages)

    sp = sub.add_parser("cells"); sp.add_argument("file"); sp.add_argument("page"); sp.add_argument("--all", action="store_true"); sp.set_defaults(func=cmd_cells)
    sp = sub.add_parser("edges"); sp.add_argument("file"); sp.add_argument("page"); sp.add_argument("--all", action="store_true"); sp.set_defaults(func=cmd_edges)
    sp = sub.add_parser("find"); sp.add_argument("file"); sp.add_argument("page"); sp.add_argument("text"); sp.set_defaults(func=cmd_find)
    sp = sub.add_parser("stat"); sp.add_argument("file"); sp.add_argument("page"); sp.set_defaults(func=cmd_stat)
    sp = sub.add_parser("dot"); sp.add_argument("file"); sp.add_argument("page"); sp.add_argument("out", nargs="?"); sp.set_defaults(func=cmd_dot)
    sp = sub.add_parser("check"); sp.add_argument("file"); sp.set_defaults(func=cmd_check)

    sp = sub.add_parser("set-label"); sp.add_argument("file"); sp.add_argument("page"); sp.add_argument("source"); sp.add_argument("target"); sp.add_argument("text"); sp.set_defaults(func=cmd_set_label)
    sp = sub.add_parser("set-cell"); sp.add_argument("file"); sp.add_argument("page"); sp.add_argument("cell"); sp.add_argument("text"); sp.set_defaults(func=cmd_set_cell)
    sp = sub.add_parser("add-child"); sp.add_argument("file"); sp.add_argument("page"); sp.add_argument("parent"); sp.add_argument("child"); sp.add_argument("label"); sp.add_argument("--x"); sp.add_argument("--y"); sp.set_defaults(func=cmd_add_child)
    sp = sub.add_parser("add-edge"); sp.add_argument("file"); sp.add_argument("page"); sp.add_argument("source"); sp.add_argument("target"); sp.add_argument("label"); sp.add_argument("--style"); sp.add_argument("--edge-id"); sp.set_defaults(func=cmd_add_edge)
    sp = sub.add_parser("remove-edge"); sp.add_argument("file"); sp.add_argument("page"); sp.add_argument("source"); sp.add_argument("target"); sp.set_defaults(func=cmd_remove_edge)
    sp = sub.add_parser("add-vertex"); sp.add_argument("file"); sp.add_argument("page"); sp.add_argument("cell"); sp.add_argument("label"); sp.add_argument("--style"); sp.add_argument("--x"); sp.add_argument("--y"); sp.add_argument("--width"); sp.add_argument("--height"); sp.set_defaults(func=cmd_add_vertex)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
