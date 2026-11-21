#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка трёх листов технического решения draw.io.

Запуск: py -3.14 tools/build_tech_diagram.py
Необязательный просмотр: --preview-dir ПАПКА (требует Pillow).
Схема строится стандартной библиотекой; PNG просмотра в артефакты не включаются.
"""

import argparse
import math
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "06-tech_project" / "technical_solution.drawio.xml"
BLUE = "#dbeafe"
GREEN = "#dcfce7"
GRAY = "#f1f5f9"
AMBER = "#fef3c7"
INK = "#334155"


class Page:
    def __init__(self, name, width, height):
        self.name, self.width, self.height = name, width, height
        self.nodes, self.edges = [], []

    def node(self, ident, text, x, y, w, h, fill=BLUE, font=18,
             align="center", plain=False):
        assert not any(n["id"] == ident for n in self.nodes), ident
        self.nodes.append(dict(id=ident, text=text, x=x, y=y, w=w, h=h,
                               fill=fill, font=font, align=align, plain=plain))

    def edge(self, ident, source, target, text, start, end, points=(),
             label=None, label_width=250, font=14, two_way=False):
        self.edges.append(dict(id=ident, source=source, target=target,
                               text=text, start=start, end=end,
                               points=list(points), label=label,
                               label_width=label_width, font=font, two_way=two_way))

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
        diagram = ET.Element("diagram", id=self.name, name=self.name)
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
            c = ET.SubElement(root, "mxCell", id=n["id"],
                              value=n["text"].replace("\n", "<br>"),
                              style=style, vertex="1", parent="1")
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
                              edge="1", parent="1", source=e["source"], target=e["target"])
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


def deployment():
    p = Page("Размещение и обмены", 1600, 1120)
    p.titles("Техническое решение АС «Каршеринг»",
             "Состав и физические способы обмена • контрольный стенд Docker Compose / Linux")
    p.node("roles", "Арендатор\nАдминистратор\nТехническая служба\nСредство обращения к API", 40, 210, 280, 140)
    p.node("app", "FastAPI / Uvicorn\nСерверное приложение • один процесс\n\ngateway • auth\nregistration • docs_adapter\nrental • state\nfinance • payment_adapter\nmaintenance • admin\ntelemetry_adapter • notifier\n\nВходы API и обработчики заданий\nВызовы модулей Python\n\nДетализация: листы rental и state",
           590, 170, 470, 520)
    p.node("db", "PostgreSQL\nD1–D9: предметные данные, состояние,\nквитанции, команды и исходящие задания\nТранзакции и ограничения целостности", 590, 820, 470, 150, GREEN)
    p.node("passport", "Имитатор проверки паспорта\nЗапрос и результат проверки", 1270, 175, 290, 100, GRAY, 17)
    p.node("license", "Имитатор проверки ВУ\nЗапрос и результат проверки", 1270, 310, 290, 100, GRAY, 17)
    p.node("telematics", "Имитатор телематики\nКоманды с поколением\nСостояние и подтверждения", 1270, 480, 290, 125, GRAY, 17)
    p.node("payments", "Тестовый магазин ЮKassa\nСоздание и проверка платежа\nУведомления о результате", 1270, 690, 290, 120, GRAY, 17)
    p.node("smtp", "Сервер электронной почты\nРезультат передачи письма", 1270, 880, 290, 100, GRAY, 17)
    p.node("environment", "Условия стенда\n4 vCPU • 8 ГиБ RAM • локальная сеть\n\nПриложение и PostgreSQL запускаются\nв контейнерах Docker Compose.\n\nПулы соединений и исполнители:\nтелеметрия 8 • пользователи 8 • фон 2.\nВнешние вызовы — вне транзакций.",
           40, 430, 400, 300, AMBER, 17, "left")
    p.edge("api", "roles", "app", "HTTPS / JSON • JWT\nзапрос / ответ", (1, .5), (0, 110/520), label=(455, 265), label_width=250)
    p.edge("passport-call", "app", "passport", "HTTP / JSON\nrequest_id, серия, номер\nvalid, reason", (1, 55/520), (0, .5), label=(1165, 220), label_width=200, font=13)
    p.edge("license-call", "app", "license", "HTTP / JSON\nrequest_id, серия, номер\nvalid, reason", (1, 190/520), (0, .5), label=(1165, 355), label_width=200, font=13)
    p.edge("telematics-call", "app", "telematics", "HTTP / JSON • токен\nкоманды / состояния\nподтверждения / квитанции", (1, 370/520), (0, .48), label=(1165, 535), label_width=200, font=13)
    p.edge("payment-call", "app", "payments", "HTTPS / JSON\nплатёж / GET\nуведомление", (1, 465/520), (0, .5), points=[(1170, 635), (1170, 750)], label=(1170, 690), label_width=165, font=13)
    p.edge("mail-call", "app", "smtp", "SMTP\nписьмо / результат", (1, 495/520), (0, .5), points=[(1120, 665), (1120, 930)], label=(1180, 855), label_width=190, font=13)
    p.edge("sql", "app", "db", "SQLAlchemy / psycopg\nSQL • транзакции • пулы 8/8/2", (.5, 1), (.5, 0), label=(825, 750), label_width=420)
    for edge in p.edges:
        edge["two_way"] = True
    p.node("legend", "Двусторонние стрелки показывают направления обмена. Входящие состояния, подтверждения команд и уведомления платежей принимаются отдельными маршрутами API (раздел 6.4).",
           40, 1010, 1520, 75, font=16, align="left", plain=True)
    return p


def rental():
    p = Page("Устройство rental", 1760, 1260)
    p.titles("Техническое устройство компонента rental",
             "F3–F5 • приём параметров, предметное решение, транзакция, исполнение сохранённой команды")
    p.node("gateway", "gateway / auth\nМаршрутизация\nJWT, роль и контекст", 40, 240, 230, 120, GRAY, 17)
    p.node("rental-api", "rental.api\nПараметры F3 / F4 / F5\nКорреляция результата команды\nRA2, RI2–RI3, FN3, RA14", 370, 230, 270, 150, font=17)
    p.node("rental-service", "rental.service\nДопуск, снимок, переходы\nНачало и окончание аренды\nRA7, RA16–RA17, RA15, FN6\nRC / CL: согласование", 760, 220, 330, 180, font=17)
    p.node("rental-repository", "rental.repository\nЧтение и изменение данных\nБлокировки ТС → аренда\nФиксация транзакции", 1220, 230, 270, 150, font=17)
    p.node("docs-adapter", "docs_adapter • RA4 / RA5\nПроверки паспорта и ВУ\nrequest_id, valid, reason\nОжидание каждого ответа ≤3 с", 370, 500, 270, 130, GRAY, 16)
    p.node("state", "state • RA6 / FN2\nАктуальное состояние ТС\nmeasured_at, technical_status,\nкоординаты и возраст данных", 760, 500, 330, 130, GRAY, 17)
    p.node("db", "PostgreSQL • ресурсы\nD2: ТС, модель • D4: rentals\nD1 / D5 / D6 / D8: чтение\nD9: outbox, command_results\nПредметная запись и задание атомарны", 1220, 560, 460, 200, GREEN, 18)
    p.node("worker", "telemetry_adapter\nОбработчик задания D9\nRA10 / RC1 / CL2\nТот же command_id при повторе", 40, 715, 270, 150, GRAY, 17)
    p.node("telematics", "Имитатор телематики\nПоколение и результаты команд\nПовтор command_id безопасен", 40, 1040, 270, 130, GRAY, 17)
    p.node("once", "Применение opened • RA13 → RA14 → RA17\nСлужебный доступ проверяет auth.\nstarting + актуальное поколение + своевременный ответ\n→ active; started_at = время первого приёма.\nЗапись command_results и переход — одна транзакция.\nПовтор → 200; время, стоимость и задания сохраняются.\nТаймер меняет только starting; active не отменяется.", 370, 820, 700, 225, AMBER, 17, "left")
    p.node("fields", "Преобразование данных\nF3: vehicle_id + пользователь\n→ аренда, снимок условий, задание.\nF5: rental_id + состояние + parking\n→ ended_at, finish_parking_id, сумма;\nfinished и задания закрытия/оплаты.\nПовтор F5 возвращает сохранённый итог.\nОплату выполняют finance / payment_adapter.", 1130, 850, 550, 250, AMBER, 17, "left")
    p.edge("request", "gateway", "rental-api", "Python\nконтекст, параметры", (1, .5), (0, 70/150), label=(320, 290), label_width=125, font=12)
    p.edge("application", "rental-api", "rental-service", "Python\nпараметры / результат", (1, .5), (0, 85/180), label=(700, 295), label_width=145, font=12)
    p.edge("repository", "rental-service", "rental-repository", "Python\nрешение / записи", (1, 85/180), (0, .5), label=(1155, 295), label_width=140, font=12)
    p.edge("sql", "rental-repository", "db", "SQLAlchemy / psycopg\nSQL • ограничения • COMMIT", (.5, 1), (135/460, 0), label=(1370, 465), label_width=310)
    p.edge("documents", "rental-service", "docs-adapter", "Python: RA4 / RA5\nрезультаты проверки", (100/330, 1), (.5, 0), points=[(860, 445), (505, 445)], label=(650, 435), label_width=250)
    p.edge("state-read", "rental-service", "state", "Python\nсостояние / возраст", (240/330, 1), (240/330, 0), label=(1000, 450), label_width=195, font=13)
    p.edge("job", "worker", "db", "SQLAlchemy / psycopg • D9\nзадание и прежний command_id", (1, .5), (0, .5), points=[(1120, 790), (1120, 660)], label=(720, 775), label_width=400)
    p.edge("command", "worker", "telematics", "HTTP / JSON\nPOST /commands\ncommand_id, attempt_id,\nlease_version, command_seq", (.5, 1), (.5, 0), label=(175, 950), label_width=280)
    p.edge("callback", "telematics", "rental-api", "HTTP / JSON → gateway / auth\ncommands/result • RA13", (0, .5), (.5, 0), points=[(20, 1105), (20, 165), (505, 165)], label=(260, 165), label_width=420)
    p.node("legend", "Связи между модулями передают вызов и результат. Детальные условия допуска, подтверждения и завершения установлены в разделах 6.5–6.6; физические таблицы — в разделе 6.3.1.",
           370, 1135, 1310, 80, font=16, align="left", plain=True)
    return p


def state():
    p = Page("Устройство state", 1760, 1140)
    p.titles("Техническое устройство компонента state",
             "F6 • первое состояние, порядок отметок, защита повторов и подтверждение после фиксации")
    p.node("gateway-auth", "gateway / auth • ST1\nPOST состояния телематики\nСлужебный Bearer-токен\nДопуск к обработке", 40, 230, 230, 160, GRAY, 17)
    p.node("telemetry-adapter", "telemetry_adapter • ST6\nschema_version 1.0 / 1.1\nНормализация JSON\nДаты RFC3339 → UTC", 365, 230, 250, 160, GRAY, 17)
    p.node("state-api", "state.api • ST2\nНормализованное сообщение\nВнутренний вызов Python\nПередача результата gateway", 715, 230, 230, 160, font=17)
    p.node("state-service", "state.service • ST2 / ST3\nТС, значения и время\nПовтор / новая отметка\nРешение о сохранении", 1050, 230, 250, 160, font=17)
    p.node("state-repository", "state.repository • ST3\nКвитанция и состояние\nОдна транзакция PostgreSQL\nЧтение состояния для RA6,\nRS2 и FN2", 1410, 230, 300, 160, font=17)
    p.node("response", "gateway • ST4 / ST5\nПосле COMMIT: HTTP 200\nmessage_id, outcome, applied,\ncurrent_measured_at\nПри ошибке — причина;\nподтверждение не выдаётся", 40, 620, 360, 220, GRAY, 18)
    p.node("rules", "Проверки и исходы\nБудущее measured_at → 400; неизвестное ТС → 404.\nПервое допустимое сообщение → applied.\nНовая отметка больше сохранённой → applied.\nРанняя или равная отметка → ignored.\nТот же message_id и тело → duplicate, applied=false.\nТот же message_id с другим телом → 409.\nОперационный статус ТС сохраняется.\nОшибка хранения → откат состояния и квитанции.", 460, 590, 580, 320, AMBER, 17, "left")
    p.node("db", "PostgreSQL\nD2: vehicles — проверка ТС\nD3: vehicle_states — PK(vehicle_id)\nD3: telemetry_receipts — PK(message_id)\nОдна строка состояния на ТС", 1130, 620, 580, 200, GREEN, 18)
    p.node("transaction", "Транзакция state.repository\n1. Закрепить message_id и сравнить отпечаток повтора.\n2. INSERT … ON CONFLICT (vehicle_id) DO UPDATE\n   при большей measured_at.\n3. Записать исход квитанции; COMMIT.", 1130, 875, 580, 180, AMBER, 17, "left")
    p.node("capacity", "Приём F6: 8 мест обработки; при исчерпании — 429. Пулы и исполнители 8 / 8 / 2 разделены между телеметрией, пользовательскими запросами и фоновыми действиями. Нагрузочные показатели устанавливаются проверкой П-20.",
           40, 960, 1000, 110, font=16, align="left", plain=True)
    p.edge("json", "gateway-auth", "telemetry-adapter", "JSON\nтело сообщения", (1, .5), (0, .5), label=(317, 300), label_width=110, font=12)
    p.edge("normalized", "telemetry-adapter", "state-api", "Python\nнормализованные\nполя", (1, .5), (0, .5), label=(665, 300), label_width=115, font=12)
    p.edge("application", "state-api", "state-service", "Python\nпараметры\nсообщения", (1, .5), (0, .5), label=(997, 300), label_width=115, font=12)
    p.edge("repository", "state-service", "state-repository", "Python\nрешение / запись", (1, .5), (0, .5), label=(1355, 300), label_width=120, font=12)
    p.edge("sql", "state-repository", "db", "SQLAlchemy / psycopg\nINSERT / UPDATE • COMMIT", (.5, 1), (430/580, 0), label=(1510, 500), label_width=350)
    p.edge("response-call", "state-api", "response", "Python: исход после COMMIT\nлибо контролируемая ошибка", (.5, 1), (.5, 0), points=[(830, 465), (220, 465)], label=(505, 450), label_width=420)
    return p


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
    pages = [deployment(), rental(), state()]
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
