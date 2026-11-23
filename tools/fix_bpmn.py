#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пакетная правка 04-bpmn/BPMN.drawio.xml:
- замена технических деталей (JWT, ЮKassa, HTTP-коды, хеш, токен, operation_id, message_id, metadata, статусы API) на бизнес-язык;
- содержательные подписи потоков сообщений;
- недостающие потоки сообщений (результат ВУ, RC, JB, PY8);
- коды ошибок заменены исходами, привязанными к ветвям шлюзов.

Использует helpers из tools/drawio.py. Перед запуском сохранить файл в Git.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drawio import (  # noqa: E402
    DIAGRAM_RE,
    MXCELL_RE,
    read_xml,
    find_page,
    xml_escape,
)

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "04-bpmn", "BPMN.drawio.xml")
FILE = os.path.normpath(FILE)

# Новые подписи вершин: {лист: {id: полная новая подпись (без экранирования)}}
VERTEX_RENAMES = {
    "Регистрация": {
        "RGE1": "Пользователь создан",
        "RGE2": "Отказ с причиной",
        "RG2": "RG2. Проверить принятие оферты и уникальность телефона и адреса почты<br><b>[registration]</b>",
        "RG6": "RG6. Подготовить пароль к защищённому хранению<br><b>[auth]</b>",
        "RG7": "RG7. Создать пользователя, документы и принятие оферты<br><b>[registration]</b>",
        "AU1": "AU1. Сверить пароль с сохранёнными данными<br><b>[auth]</b>",
        "AU2": "AU2. Сформировать подтверждение входа с пользователем и ролью<br><b>[auth]</b>",
        "AU3": "AU3. Вернуть подтверждение входа<br><b>[gateway]</b>",
        "AUE1": "Вход подтверждён",
        "AUE2": "Отказ во входе",
    },
    "Арендовать автомобиль": {
        "RA1": "RA1. Проверить учётные данные и роль<br><b>[auth]</b>",
        "RA7": "RA7. Проверить допуск; сохранить оформляемую попытку, условия и задание открытия<br><b>[rental]</b>",
        "RA9": "RA9. Вернуть принятие запроса и адрес получения результата<br><b>[gateway]</b>",
        "RAE1": "Существующая попытка либо отказ",
        "RAE2": "Отказ с причиной",
        "RAE3": "Запрос принят; ожидается открытие",
        "RAE4": "Аренда действует; время начала зафиксировано",
        "RAE6": "Устаревший ответ: только запись",
        "RA15": "RA15. Зафиксировать неуспешное начало; автомобиль заблокирован; задание согласующего закрытия<br><b>[rental]</b>",
        "RC5": "RC5. Оставить автомобиль заблокированным; назначить повтор либо сверку администратором<br><b>[rental]</b>",
        "RCE1": "Автомобиль снова доступен либо остаётся заблокированным по техническому признаку",
        "ST1": "ST1. Проверить служебные данные отправителя<br><b>[auth]</b>",
        "ST2": "ST2. Проверить форму, автомобиль, признак повтора и готовность приёма<br><b>[state]</b>",
        "ST3": "ST3. Сравнить отметку, обновить состояние и сохранить квитанцию<br><b>[state]</b>",
        "ST4": "ST4. Вернуть исход: применено, устарело либо повтор<br><b>[gateway]</b>",
        "STE1": "Квитанция после сохранения",
        "STE2": "Отказ с причиной; обработка не подтверждена",
        "ST6": "ST6. Привести сообщение к принятой форме<br><b>[telemetry_adapter]</b>",
        "MTE1": "Перечень с основаниями",
        "MTE2": "Ошибка неполных данных; нормы не подставляются",
    },
    "Завершить поездку": {
        "FN1": "FN1. Проверить учётные данные<br><b>[auth]</b>",
        "FN3": "FN3. Проверить владельца, состояние, свежесть сведений и парковку<br><b>[rental]</b>",
        "FN5": "FN5. Вернуть отказ; окончание не фиксируется<br><b>[gateway]</b>",
        "FN6": "FN6. Зафиксировать окончание, итог и стоимость; задания закрытия и оплаты<br><b>[rental]</b>",
        "FN7": "FN7. Вернуть окончание, стоимость, ожидаемый финансовый результат и результат команды<br><b>[gateway]</b>",
        "FNE1": "Сохранённый результат без новых заданий",
        "FNE2": "Отказ с причиной",
        "FNE3": "Аренда завершена",
        "CL6": "CL6. Сохранить согласованное закрытие; вернуть автомобиль в доступ при выполненных условиях<br><b>[rental]</b>",
        "CL7": "CL7. Оставить автомобиль заблокированным; повторить задание либо передать на сверку<br><b>[rental]</b>",
        "CP1": "CP1. Взять задание оплаты с идентификатором операции<br><b>[payment_adapter]</b>",
        "CP2": "CP2. Создать платёж с тем же идентификатором операции и назначением либо проверить известный платёж<br><b>[payment_adapter]</b>",
        "CP3": "CP3. Связать сведения платежа и ссылку с обязательством<br><b>[finance]</b>",
        "CPG1": "Проверенные сведения получены?",
        "CPE1": "Ожидание либо проверенный результат для обработки",
        "CPE2": "Ожидание; повтор с тем же идентификатором операции",
        "CP-X-PAY": "Платёжный шлюз",
    },
    "Начислить штраф": {
        "FI-X-PAY": "Платёжный шлюз",
        "PY-X-PAY": "Платёжный шлюз",
        "FI2": "FI2. Проверить аренду и сумму; сохранить штраф, идентификатор операции и задание<br><b>[finance]</b>",
        "FI3": "FI3. Вернуть созданный штраф; оплата в работе<br><b>[gateway]</b>",
        "FI5": "FI5. Сохранить сведения платежа и ссылку<br><b>[finance]</b>",
        "FIE1": "Штраф создан; оплата в работе",
        "FIE2": "Ссылка на оплату доступна арендатору",
        "FIE3": "Ожидание; при недоступности — сверка администратором",
        "FIG2": "Сведения о платеже получены?",
        "OB1": "OB1. Проверить учётные данные и роль<br><b>[auth]</b>",
        "CF4": "CF4. Вернуть результат; условия действующих аренд сохранены<br><b>[gateway]</b>",
        "PY0": "Уведомление платёжного шлюза / результат проверочного запроса",
        "PYG0": "Сведения получены?",
        "PY1": "PY1. Получить текущее состояние платежа через проверенный запрос<br><b>[payment_adapter]</b>",
        "PY2": "PY2. Проверить принадлежность, назначение, сумму и валюту платежа; закрепить обязательство<br><b>[finance]</b>",
        "PY5": "PY5. Применить подтверждённую оплату или подтверждённый отказ; при неясности сохранить ожидание<br><b>[finance]</b>",
        "PY8": "PY8. Создать платёж задолженности с новым идентификатором операции<br><b>[payment_adapter]</b>",
        "PY9": "PY9. Сохранить ссылку для оплаты<br><b>[finance]</b>",
        "PY12": "PY12. Передать на сверку администратору; уведомить<br><b>[finance]</b>",
        "PYE1": "Записано для сверки администратором",
        "PYE2": "Повтор без финансового эффекта",
        "PYE3": "Ожидается подтверждение",
        "PYE4": "Результат зафиксирован",
        "PYE5": "Отказ без применения результата",
        "JB1": "JB1. Получить незавершённое платёжное задание с тем же идентификатором операции<br><b>[payment_adapter]</b>",
        "JB2": "JB2. Повторить запрос либо получить состояние платежа<br><b>[payment_adapter]</b>",
        "JB3": "JB3. Применить правила обработки платежа; сохранить результат<br><b>[finance]</b>",
    },
}

# Новые подписи рёбер: {лист: {(source, target): новая подпись}}
EDGE_RENAMES = {
    "Регистрация": {
        ("RG-X-USER", "RG0"): "запрос регистрации",
        ("RG-X-PASS", "RG3"): "результат проверки паспорта",
        ("RG3", "RG-X-PASS"): "запрос проверки паспорта",
        ("RG-X-VU", "RG4"): "результат проверки ВУ",
        ("RG4", "RG-X-VU"): "запрос проверки ВУ",
        ("AU-X-USER", "AU0"): "телефон и пароль",
    },
    "Арендовать автомобиль": {
        ("RA-X-USER", "RA0"): "запрос начала аренды",
        ("RA-X-DOC", "RA4"): "результат проверки паспорта",
        ("RA4", "RA-X-DOC"): "запрос проверки паспорта",
        ("RA5", "RA-X-DOC"): "запрос проверки ВУ",
        ("RA-X-TEL", "RA10"): "квитанция приёма команды",
        ("RA10", "RA-X-TEL"): "команда открытия",
        ("RA-X-TEL", "RA11"): "подтверждение открытия с идентификаторами команды, попытки и поколения",
        ("RSX", "RS0"): "запрос поиска",
        ("RIX", "RI0"): "запрос сведений",
        ("ST-X-TEL", "ST0"): "сообщение состояния",
        ("MT-X-USER", "MT0"): "запрос перечня",
    },
    "Завершить поездку": {
        ("FN-X-USER", "FN0"): "запрос завершения",
        ("CL-X-TEL", "CL2"): "квитанция приёма команды",
        ("CL2", "CL-X-TEL"): "команда закрытия",
        ("CP-X-PAY", "CP2"): "сведения о платеже и ссылка",
        ("CP2", "CP-X-PAY"): "создание платежа; проверка состояния",
        ("FN6", "FN-D9"): "задания закрытия и оплаты",
    },
    "Начислить штраф": {
        ("FI-X-ADMIN", "FI0"): "запрос начисления штрафа",
        ("FI-X-PAY", "FI4"): "сведения о платеже и ссылка",
        ("FI4", "FI-X-PAY"): "создание платежа",
        ("OBX", "OB0"): "запрос обязательств",
        ("CFX", "CF0"): "запрос справочника",
        ("PY-X-PAY", "PY0"): "уведомление о платеже",
        ("PY1", "PY-X-PAY"): "запрос состояния платежа",
    },
}

# Новые рёбра: {лист: [(source, target, подпись)]}
EDGE_ADDS = {
    "Арендовать автомобиль": [
        ("RA-X-DOC", "RA5", "результат проверки ВУ"),
        ("RC3", "RA-X-TEL", "запрос статуса; команда закрытия"),
        ("RA-X-TEL", "RC3", "статус и подтверждение"),
    ],
    "Начислить штраф": [
        ("JB2", "PY-X-PAY", "повтор запроса; проверка платежа"),
        ("PY-X-PAY", "JB2", "состояние платежа"),
        ("PY8", "PY-X-PAY", "создание платежа"),
        ("PY-X-PAY", "PY9", "сведения о платеже и ссылка"),
    ],
}

MESSAGE_STYLE = (
    "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=blockThin;endFill=1;"
    "strokeColor=#334155;fontSize=12;labelBackgroundColor=#ffffff;"
    "dashed=1;endArrow=open;endFill=0;startArrow=oval;startFill=0;"
)


def set_vertex(body, cid, label):
    pattern = re.compile(
        r'(<mxCell\b[^>]*\bid="' + re.escape(cid) + r'"[^>]*\bvalue=")[^"]*(")'
    )
    new_body, n = pattern.subn(lambda m: m.group(1) + xml_escape(label) + m.group(2), body)
    if not n:
        print(f"  ! вершина {cid} не найдена")
        return body, False
    return new_body, True


def set_edge(body, src, tgt, label):
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


def add_edge(body, src, tgt, label, eid):
    edge = (
        f'<mxCell id="{eid}" value="{xml_escape(label)}" style="{MESSAGE_STYLE}" '
        f'edge="1" source="{src}" target="{tgt}" parent="1">'
        '<mxGeometry relative="1" as="geometry"/></mxCell>'
    )
    if "</root>" in body:
        return body.replace("</root>", edge + "</root>", 1), True
    return body.rstrip() + "\n" + edge, True


def main():
    xml = read_xml(FILE)
    changed_v = changed_e = added = 0

    for page, renames in VERTEX_RENAMES.items():
        body = find_page(xml, page)
        new_body = body
        for cid, label in renames.items():
            new_body, ok = set_vertex(new_body, cid, label)
            if ok:
                changed_v += 1
        if new_body != body:
            xml = xml.replace(body, new_body, 1)

    for page, renames in EDGE_RENAMES.items():
        body = find_page(xml, page)
        new_body = body
        for (src, tgt), label in renames.items():
            new_body, ok = set_edge(new_body, src, tgt, label)
            if ok:
                changed_e += 1
        if new_body != body:
            xml = xml.replace(body, new_body, 1)

    for page, edges in EDGE_ADDS.items():
        body = find_page(xml, page)
        new_body = body
        for i, (src, tgt, label) in enumerate(edges, start=1):
            eid = f"e-msg-{page}-{i}"
            new_body, ok = add_edge(new_body, src, tgt, label, eid)
            if ok:
                added += 1
        if new_body != body:
            xml = xml.replace(body, new_body, 1)

    with open(FILE, "w", encoding="utf-8") as f:
        f.write(xml)

    print(f"изменено подписей вершин: {changed_v}")
    print(f"изменено подписей рёбер: {changed_e}")
    print(f"добавлено рёбер: {added}")


if __name__ == "__main__":
    main()
