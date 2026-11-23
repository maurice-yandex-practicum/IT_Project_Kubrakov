#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Приведение 04-bpmn/BPMN.drawio.xml к атомарным задачам:
- из подписей задач убраны условия («либо», «или», «при …»);
- выборы вынесены в шлюзы и отдельные задачи;
- end-события с альтернативами разделены на отдельные исходы;
- добавлены недостающие задачи, шлюзы и ветви.

Использует helpers из tools/drawio.py. Перед запуском сохранить файл в Git.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drawio import (  # noqa: E402
    DIAGRAM_RE,
    read_xml,
    find_page,
    xml_escape,
)

FILE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "04-bpmn", "BPMN.drawio.xml"))

# ---- Полные новые подписи вершин (без экранирования) ----
VERTEX_RENAMES = {
    "Регистрация": {
        "RG3": "RG3. Проверить паспорт с ожиданием до 3 с<br><b>[docs_adapter]</b>",
        "RG4": "RG4. Проверить ВУ с ожиданием до 3 с<br><b>[docs_adapter]</b>",
        "RG9": "RG9. Вернуть отказ без создания пользователя<br><b>[gateway]</b>",
    },
    "Арендовать автомобиль": {
        "RA3": "RA3. Вернуть существующую попытку<br><b>[gateway]</b>",
        "RAE1": "Существующая попытка возвращена",
        "RA7": "RA7. Проверить допуск и задолженность<br><b>[rental]</b>",
        "RA14": "RA14. Сверить попытку, поколение и срок<br><b>[rental]</b>",
        "RA15": "RA15. Зафиксировать неуспешное начало с блокировкой автомобиля и заданием согласующего закрытия<br><b>[rental]</b>",
        "RC0": "Возобновление по позднему ответу, повтору задания или после остановки",
        "RC3": "RC3. Запросить статус команды закрытия<br><b>[telemetry_adapter]</b>",
        "RC4": "RC4. Сохранить подтверждённое закрытие<br><b>[rental]</b>",
        "RCE1": "Автомобиль снова доступен",
        "RC5": "RC5. Оставить автомобиль заблокированным<br><b>[rental]</b>",
        "RCE2": "Назначен повтор задания",
        "RS3": "RS3. Сформировать перечень доступных ТС по радиусу и расстоянию<br><b>[rental]</b>",
        "RS4": "RS4. Вернуть перечень<br><b>[gateway]</b>",
        "RI2": "RI2. Проверить владельца<br><b>[rental]</b>",
        "RI3": "RI3. Определить статус и стоимость по сохранённым условиям<br><b>[rental]</b>",
        "RI4": "RI4. Вернуть сведения<br><b>[gateway]</b>",
        "ST4": "ST4. Вернуть квитанцию с сохранённым исходом<br><b>[gateway]</b>",
        "MT3": "MT3. Определить основания и возраст состояния по порогам и интервалам<br><b>[maintenance]</b>",
    },
    "Завершить поездку": {
        "FN5": "FN5. Вернуть отказ без фиксации окончания<br><b>[gateway]</b>",
        "FN6": "FN6. Зафиксировать окончание, итог, стоимость и задания закрытия и оплаты<br><b>[rental]</b>",
        "CL0": "Задание закрытия или восстановление",
        "CL6": "CL6. Сохранить согласованное закрытие<br><b>[rental]</b>",
        "CLE1": "Закрытие согласовано; автомобиль доступен",
        "CL7": "CL7. Оставить автомобиль заблокированным<br><b>[rental]</b>",
        "CLE2": "Назначен повтор задания",
        "CP0": "Задание оплаты или восстановление",
        "CP2": "CP2. Создать платёж с идентификатором операции и назначением<br><b>[payment_adapter]</b>",
        "CP5": "CP5. Сохранить задание для повтора без объявления финансового отказа<br><b>[payment_adapter]</b>",
        "CPE1": "Проверенный результат передан в обработку",
    },
    "Начислить штраф": {
        "FIE1": "Штраф создан",
        "FIE3": "Ожидание; задание повтора сохранено",
        "FI3": "FI3. Вернуть созданный штраф<br><b>[gateway]</b>",
        "PY0": "Уведомление о платеже или результат проверочного запроса",
        "PY2": "PY2. Проверить принадлежность, назначение, сумму и валюту платежа<br><b>[finance]</b>",
        "PY5": "PY5. Зафиксировать проверенный финансовый результат<br><b>[finance]</b>",
        "PY8": "PY8. Создать платёж с новым идентификатором операции<br><b>[payment_adapter]</b>",
        "PY12": "PY12. Передать на сверку с уведомлением администратора<br><b>[finance]</b>",
        "PY13": "PY13. Определить целевое обязательство<br><b>[finance]</b>",
        "JBE": "Результат зафиксирован без нового списания",
        "CF2": "CF2. Проверить параметры запроса<br><b>[admin]</b>",
        "CF3": "CF3. Прочитать справочные данные<br><b>[admin]</b>",
        "CF4": "CF4. Вернуть результат без изменения условий действующих аренд<br><b>[gateway]</b>",
        "JB0": "Таймер или перезапуск",
        "JB3": "JB3. Применить правила обработки платежа с сохранением результата<br><b>[finance]</b>",
    },
}

# ---- Переподписка существующих рёбер: {лист: {(src, tgt): новая подпись}} ----
EDGE_LABELS = {
    "Регистрация": {
        ("RGG4", "RG9"): "нет",
    },
    "Арендовать автомобиль": {
        ("RAG1", "RA3"): "повтор",
        ("RAG7", "RA15"): "отказ в открытии",
        ("RCG2", "RC5"): "нет",
    },
    "Завершить поездку": {
        ("CPG1", "CP5"): "нет",
    },
    "Начислить штраф": {
        ("FIG2", "FI7"): "нет",
    },
}

# ---- Удаляемые рёбра ----
EDGE_REMOVES = {
    "Арендовать автомобиль": [
        ("RAG4", "RAG5"),
        ("RAG7", "RAE4"),
        ("RC4", "RCE1"),
        ("RC5", "RCE2"),
        ("RI2", "RI3"),
    ],
    "Завершить поездку": [
        ("CP1", "CP2"),
        ("CL6", "CLE1"),
        ("CL7", "CLE2"),
    ],
    "Начислить штраф": [
        ("PY13", "PY8"),
        ("CF2", "CF3"),
    ],
}

# ---- Новые вершины: {лист: [(id, label, kind, x, y, w, h)]}, kind: task|gateway|end ----
NEW_VERTICES = {
    "Арендовать автомобиль": [
        ("RA16", "RA16. Сохранить оформляемую попытку, условия и задание открытия<br><b>[rental]</b>", "task", 1800, 350, 270, 100),
        ("RA17", "RA17. Применить подтверждённое открытие<br><b>[rental]</b>", "task", 3040, 40, 240, 90),
        ("RCG3", "Возврат автомобиля в доступ возможен?", "gateway", 1620, 175, 54, 54),
        ("RCE4", "Автомобиль остаётся заблокированным по техническому признаку", "end", 1780, 185, 48, 48),
        ("RCG4", "Допустим повтор?", "gateway", 1600, 320, 54, 54),
        ("RCE5", "Передано на сверку администратору", "end", 1720, 335, 48, 48),
        ("RIG1", "Владелец подтверждён?", "gateway", 560, 105, 54, 54),
        ("RI5", "RI5. Вернуть отказ<br><b>[gateway]</b>", "task", 560, 175, 220, 70),
    ],
    "Завершить поездку": [
        ("CPG0", "Платёж уже создан?", "gateway", 470, 190, 54, 54),
        ("CP6", "CP6. Проверить состояние известного платежа<br><b>[payment_adapter]</b>", "task", 470, 280, 280, 90),
        ("CLG3", "Возврат автомобиля в доступ возможен?", "gateway", 1790, 120, 54, 54),
        ("CLE3", "Автомобиль остаётся заблокированным по техническому признаку", "end", 1900, 160, 48, 48),
        ("CLG4", "Допустим повтор?", "gateway", 1780, 330, 54, 54),
        ("CLE4", "Передано на сверку администратору", "end", 1900, 360, 48, 48),
    ],
    "Начислить штраф": [
        ("PYG4", "Исходная оплата аренды?", "gateway", 2810, 330, 54, 54),
        ("PY14", "PY14. Создать задолженность аренды<br><b>[finance]</b>", "task", 2480, 250, 250, 90),
        ("CFG1", "Операция?", "gateway", 560, 100, 54, 54),
        ("CF5", "CF5. Сохранить справочные данные<br><b>[admin]</b>", "task", 560, 160, 220, 70),
    ],
}

# ---- Новые рёбра: {лист: [(src, tgt, подпись или None)]} ----
NEW_EDGES = {
    "Регистрация": [
        ("RGG4", "RG9", "истёк срок ожидания"),
    ],
    "Арендовать автомобиль": [
        ("RAG1", "RA8", "конфликт параметров"),
        ("RAG4", "RA16", "да"),
        ("RA16", "RAG5", None),
        ("RAG7", "RA17", "открыто вовремя"),
        ("RA17", "RAE4", None),
        ("RAG7", "RA15", "подтверждение после срока"),
        ("RCG2", "RC5", "истёк срок ожидания"),
        ("RC4", "RCG3", None),
        ("RCG3", "RCE1", "да"),
        ("RCG3", "RCE4", "нет"),
        ("RC5", "RCG4", None),
        ("RCG4", "RCE2", "да"),
        ("RCG4", "RCE5", "нет"),
        ("RI2", "RIG1", None),
        ("RIG1", "RI3", "да"),
        ("RIG1", "RI5", "нет"),
        ("RI5", "RIE", None),
    ],
    "Завершить поездку": [
        ("CPG1", "CP5", "истёк срок ожидания"),
        ("CP1", "CPG0", None),
        ("CPG0", "CP2", "платёж не создан"),
        ("CPG0", "CP6", "платёж создан ранее"),
        ("CP6", "CPG1", None),
        ("CL6", "CLG3", None),
        ("CLG3", "CLE1", "да"),
        ("CLG3", "CLE3", "нет"),
        ("CL7", "CLG4", None),
        ("CLG4", "CLE2", "да"),
        ("CLG4", "CLE4", "нет"),
    ],
    "Начислить штраф": [
        ("FIG2", "FI7", "истёк срок ожидания"),
        ("PY13", "PYG4", None),
        ("PYG4", "PY14", "да"),
        ("PYG4", "PY8", "нет"),
        ("PY14", "PY8", None),
        ("CF2", "CFG1", None),
        ("CFG1", "CF3", "чтение"),
        ("CFG1", "CF5", "изменение"),
        ("CF5", "CF4", None),
    ],
}


def get_style(xml, cid):
    m = re.search(r'<mxCell\b[^>]*\bid="' + re.escape(cid) + r'"[^>]*\bstyle="([^"]*)"', xml)
    if m:
        return m.group(1)
    raise SystemExit(f"не найден стиль клетки {cid}")


def set_vertex(body, cid, label):
    pattern = re.compile(r'(<mxCell\b[^>]*\bid="' + re.escape(cid) + r'"[^>]*\bvalue=")[^"]*(")')
    new_body, n = pattern.subn(lambda m: m.group(1) + xml_escape(label) + m.group(2), body)
    return new_body, bool(n)


def set_edge_label(body, src, tgt, label):
    pattern = re.compile(
        r'(<mxCell\b[^>]*\bedge="1"[^>]*\bsource="' + re.escape(src) + r'"[^>]*\btarget="' + re.escape(tgt) + r'"[^>]*>)'
    )
    m = pattern.search(body)
    if not m:
        print(f"  ! ребро {src} -> {tgt} не найдено")
        return body, False
    tag = m.group(1)
    value_m = re.search(r'\bvalue="([^"]*)"', tag)
    if value_m:
        new_tag = tag.replace(f'value="{value_m.group(1)}"', f'value="{xml_escape(label)}"', 1)
    else:
        new_tag = tag[:-1] + f' value="{xml_escape(label)}">'
    return body.replace(tag, new_tag, 1), True


def remove_edge(body, src, tgt):
    pattern = re.compile(
        r'<mxCell\b[^>]*\bedge="1"[^>]*\bsource="' + re.escape(src) + r'"[^>]*\btarget="' + re.escape(tgt) + r'"[^>]*'
        r'(?:/>|>.*?</mxCell>)',
        re.S,
    )
    new_body, n = pattern.subn("", body)
    if not n:
        print(f"  ! ребро для удаления {src} -> {tgt} не найдено")
        return body, False
    return new_body, True


def add_vertex(body, cid, label, style, x, y, w, h):
    cell = (
        f'<mxCell id="{cid}" value="{xml_escape(label)}" style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )
    if "</root>" in body:
        return body.replace("</root>", cell + "</root>", 1)
    return body.rstrip() + "\n" + cell


def add_edge(body, src, tgt, label, style, eid):
    value = f' value="{xml_escape(label)}"' if label else ""
    edge = (
        f'<mxCell id="{eid}"{value} style="{style}" edge="1" source="{src}" target="{tgt}" parent="1">'
        '<mxGeometry relative="1" as="geometry"/></mxCell>'
    )
    if "</root>" in body:
        return body.replace("</root>", edge + "</root>", 1)
    return body.rstrip() + "\n" + edge


def main():
    xml = read_xml(FILE)
    seq_style = get_style(xml, "RA7")
    task_style = get_style(xml, "RA7")
    gw_style = get_style(xml, "RAG4")
    end_style = get_style(xml, "RAE1")
    # стиль потока управления — с существующего ребра
    m = re.search(r'<mxCell\b[^>]*\bsource="RA7"[^>]*\btarget="RAG4"[^>]*\bstyle="([^"]*)"', xml)
    flow_style = m.group(1) if m else "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;endFill=1;"

    c_ren = c_el = c_rm = c_nv = c_ne = 0

    for page, renames in VERTEX_RENAMES.items():
        body = find_page(xml, page)
        nb = body
        for cid, label in renames.items():
            nb, ok = set_vertex(nb, cid, label)
            c_ren += ok
        if nb != body:
            xml = xml.replace(body, nb, 1)

    for page, renames in EDGE_LABELS.items():
        body = find_page(xml, page)
        nb = body
        for (src, tgt), label in renames.items():
            nb, ok = set_edge_label(nb, src, tgt, label)
            c_el += ok
        if nb != body:
            xml = xml.replace(body, nb, 1)

    for page, edges in EDGE_REMOVES.items():
        body = find_page(xml, page)
        nb = body
        for src, tgt in edges:
            nb, ok = remove_edge(nb, src, tgt)
            c_rm += ok
        if nb != body:
            xml = xml.replace(body, nb, 1)

    style_map = {"task": task_style, "gateway": gw_style, "end": end_style}
    for page, vertices in NEW_VERTICES.items():
        body = find_page(xml, page)
        nb = body
        for cid, label, kind, x, y, w, h in vertices:
            nb = add_vertex(nb, cid, label, style_map[kind], x, y, w, h)
            c_nv += 1
        if nb != body:
            xml = xml.replace(body, nb, 1)

    for page, edges in NEW_EDGES.items():
        body = find_page(xml, page)
        nb = body
        for i, (src, tgt, label) in enumerate(edges, start=1):
            eid = f"e-atomic-{page}-{i}"
            nb = add_edge(nb, src, tgt, label, flow_style, eid)
            c_ne += 1
        if nb != body:
            xml = xml.replace(body, nb, 1)

    with open(FILE, "w", encoding="utf-8") as f:
        f.write(xml)

    print(f"переименовано вершин: {c_ren}")
    print(f"переименовано рёбер: {c_el}")
    print(f"удалено рёбер: {c_rm}")
    print(f"добавлено вершин: {c_nv}")
    print(f"добавлено рёбер: {c_ne}")


if __name__ == "__main__":
    main()
