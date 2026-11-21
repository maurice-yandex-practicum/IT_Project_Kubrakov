#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Элементы и связи трёх представлений C4 АС «Каршеринг»."""


PEOPLE = [
    ("renter", "Арендатор", "Получает ТС в аренду и сведения о своих обязательствах"),
    ("administrator", "Администратор", "Ведёт справочники, штрафы и обязательства"),
    ("technician", "Техническая служба", "Получает перечень ТС для обслуживания"),
]
EXTERNAL = [
    ("passport", "Имитатор проверки паспорта", "Проверяет паспорт и сообщает результат"),
    ("license", "Имитатор проверки ВУ", "Проверяет ВУ и сообщает результат"),
    ("telematics", "Имитатор телематики", "Исполняет команды и передаёт состояние ТС"),
    ("payments", "ЮKassa", "Проводит оплату и сообщает её результат; тестовый магазин"),
    ("mail", "Сервер электронной почты", "Принимает письма участникам сервиса"),
]
COMPONENTS = {
    "gateway": "Принимает запросы, маршрутизирует их и формирует ответы",
    "auth": "Проверяет учётные данные, роли и служебный доступ",
    "registration": "Регистрирует пользователя, документы и принятие оферты",
    "rental": "Выполняет поиск и операции аренды; сохраняет условия и стоимость",
    "finance": "Ведёт обязательства, попытки оплаты и финансовые результаты",
    "maintenance": "Формирует перечень ТО и основания включения ТС",
    "admin": "Ведёт тарифы и парковки",
    "state": "Принимает и предоставляет актуальное состояние ТС и квитанции",
    "docs_adapter": "Выполняет проверки паспорта и ВУ через имитаторы",
    "telemetry_adapter": "Обменивается командами, подтверждениями и состоянием ТС",
    "payment_adapter": "Создаёт платежи и получает проверенные объекты платежей",
    "notifier": "Исполняет сохранённые задания отправки писем",
}


def relation(p, ident, source, target, action, a, b, points=(), label=None,
             technology="", width=260, font=14):
    by_id = {n["id"]: n for n in p.nodes}

    def port(node_id, point):
        n = by_id[node_id]
        return ((point[0]-n["x"])/n["w"], (point[1]-n["y"])/n["h"])

    text = action + (f"\n[{technology}]" if technology else "")
    p.edge(ident, source, target, text, port(source, a), port(target, b),
           points=points, label=label, label_width=width, font=font,
           technology=technology)


def scope_page(Page, level):
    name = "C1 — Контекст системы" if level == 1 else "C2 — Контейнеры"
    p = Page(name, 1900, 1400, level, "system")
    p.titles(name, "АС «Каршеринг» • область представления: одна программная система")
    if level == 2:
        p.boundary("system", "АС «Каршеринг»", "SoftwareSystem", 600, 250, 620, 940)
    for index, (ident, name, description) in enumerate(PEOPLE):
        p.element(ident, name, "Person", description, 40, 260+index*310,
                  330, 170, external=True)
    for index, (ident, name, description) in enumerate(EXTERNAL):
        p.element(ident, name, "SoftwareSystem", description, 1470,
                  150+index*230, 370, 170, external=True)
    y = 490 if level == 1 else 420
    central = "system" if level == 1 else "app"
    p.element(central, "АС «Каршеринг»" if level == 1 else "Серверное приложение",
              "SoftwareSystem" if level == 1 else "Container",
              "Предоставляет аренду ТС, ведёт расчёты и состояние парка",
              650, y, 520, 300, scope="" if level == 1 else "system",
              technology="" if level == 1 else "Python / FastAPI / Uvicorn", font=21)
    if level == 2:
        p.element("database", "База данных", "Container",
                  "Хранит D1–D9: предметные данные, состояние, квитанции и задания",
                  650, 900, 520, 180, technology="PostgreSQL", scope="system", font=19)
    technology = "" if level == 1 else "HTTPS/JSON"
    for ident, sy, ty, action, label in [
        ("renter", 345, y+50, "Использует операции аренды\nи просмотра обязательств", (500, 410)),
        ("administrator", 655, y+140, "Ведёт справочники\nи обязательства", (500, 620)),
        ("technician", 965, y+230, "Запрашивает перечень ТО", (500, 845)),
    ]:
        relation(p, f"{ident}-uses", ident, central, action,
                 (370, sy), (650, ty), [(500, sy), (500, ty)], label,
                 technology=technology, width=250)
    relation(p, "passport-check", central, "passport", "Проверяет паспорт",
             (1170, y+40), (1470, 235), [(1320, y+40), (1320, 235)], (1345, 300),
             technology="" if level == 1 else "HTTP/JSON", width=230)
    relation(p, "license-check", central, "license", "Проверяет ВУ",
             (1170, y+90), (1470, 465), [(1270, y+90), (1270, 465)], (1350, 445),
             technology="" if level == 1 else "HTTP/JSON", width=220)
    relation(p, "command", central, "telematics", "Передаёт команды\nоткрытия и закрытия",
             (1170, y+140), (1470, 650), [(1320, y+140), (1320, 650)], (1330, 610),
             technology="" if level == 1 else "HTTP/JSON", width=230)
    relation(p, "state-result", "telematics", central, "Передаёт состояние\nи подтверждения команд",
             (1470, 705), (1170, y+190), [(1380, 705), (1380, y+190)], (1340, 720),
             technology="" if level == 1 else "HTTP/JSON", width=240)
    relation(p, "payment", central, "payments", "Создаёт платежи\nи проверяет их состояние",
             (1170, y+240), (1470, 890), [(1270, y+240), (1270, 890)], (1310, 835),
             technology=technology, width=250)
    relation(p, "payment-result", "payments", central, "Уведомляет об изменении\nсостояния платежа",
             (1470, 965), (1170, y+280), [(1380, 965), (1380, y+280)], (1380, 960),
             technology=technology, width=260)
    relation(p, "notification", central, "mail", "Передаёт письма\nдля доставки участникам",
             (1170, y+295), (1470, 1155), [(1240, y+295), (1240, 1155)], (1330, 1155),
             technology="" if level == 1 else "SMTP", width=240)
    if level == 2:
        relation(p, "storage", "app", "database", "Читает и сохраняет данные",
                 (910, 720), (910, 900), label=(900, 810),
                 technology="SQL/TCP; SQLAlchemy / psycopg", width=500)
    legend = ("Тип элемента указан в квадратных скобках. Синий — система проекта, серый — участники и внешние системы. "
              "Каждая стрелка задаёт направленное взаимодействие; подпись описывает действие.")
    if level == 2:
        legend += " Пунктир — граница АС. Контейнер C4 обозначает приложение или хранилище данных."
    p.node("legend", legend, 40, 1280, 1800, 90, font=16, align="left", plain=True)
    return p


def components(Page):
    p = Page("C3 — Компоненты сервера", 3300, 2620, 3, "app")
    p.titles("C3 — Компоненты серверного приложения",
             "Область представления: один контейнер «Серверное приложение» • 12 компонентов Python модульного монолита")
    p.boundary("app", "Серверное приложение", "Container", 470, 150, 2110, 1930)
    for i, (ident, name, description) in enumerate(PEOPLE):
        p.element(ident, name, "Person", description, 40, 230+i*260, 330, 180, external=True)
    for i, (ident, name, description) in enumerate(EXTERNAL):
        p.element(ident, name, "SoftwareSystem", description, 2890, 200+i*280, 360, 180, external=True)
    positions = {"gateway": (520, 240, 350, 1450), "auth": (520, 1780, 350, 170)}
    for ident, y in [("registration", 240), ("rental", 500), ("finance", 760),
                     ("maintenance", 1020), ("admin", 1280), ("state", 1540)]:
        positions[ident] = (1200, y, 400, 160)
    for ident, y in [("docs_adapter", 240), ("telemetry_adapter", 500),
                     ("payment_adapter", 760), ("notifier", 1020)]:
        positions[ident] = (2050, y, 430, 160)
    for ident, position in positions.items():
        p.element(ident, ident, "Component", COMPONENTS[ident], *position,
                  technology="Python", scope="app", font=19)
    p.element("database", "База данных", "Container",
              "D1–D9: предметные данные, состояние ТС, квитанции, задания и история интеграций",
              1200, 2240, 900, 180, technology="PostgreSQL", scope="system", font=21)
    for i, (ident, _, _) in enumerate(PEOPLE):
        y = 320+i*260
        relation(p, f"{ident}-uses", ident, "gateway", "Вызывает операции\nсвоей роли",
                 (370, y), (520, y), label=(445, y), technology="HTTPS/JSON", width=145, font=12)
    for ident, y, action in [("registration", 320, "Передаёт регистрацию"),
                             ("rental", 580, "Передаёт операции аренды"),
                             ("finance", 840, "Передаёт операции обязательств"),
                             ("maintenance", 1100, "Запрашивает перечень ТО"),
                             ("admin", 1360, "Передаёт операции справочников")]:
        relation(p, f"gateway-{ident}", "gateway", ident, action, (870, y), (1200, y),
                 label=(1035, y-15), technology="Python", width=315)
    relation(p, "access", "gateway", "auth", "Проверяет доступ", (695, 1690), (695, 1780),
             label=(695, 1730), technology="Python", width=270)
    relation(p, "registration-documents", "registration", "docs_adapter", "Проверяет паспорт и ВУ",
             (1600, 320), (2050, 320), label=(1825, 305), technology="Python", width=360)
    relation(p, "rental-documents", "rental", "docs_adapter", "Повторно проверяет документы",
             (1600, 530), (2050, 270), [(1940, 530), (1940, 270)], (1820, 460), technology="Python", width=340)
    relation(p, "rental-command", "rental", "telemetry_adapter", "Исполняет сохранённую команду",
             (1600, 580), (2050, 580), label=(1825, 575), technology="Python", width=380)
    relation(p, "rental-state", "rental", "state", "Получает состояние и возраст",
             (1600, 630), (1600, 1660), [(1820, 630), (1820, 1660)], (1830, 1510), technology="Python", width=350)
    relation(p, "rental-finance", "rental", "finance", "Передаёт обязательство аренды",
             (1400, 660), (1400, 760), label=(1400, 710), technology="Python", width=380)
    relation(p, "maintenance-state", "maintenance", "state", "Получает состояние парка",
             (1600, 1100), (1600, 1590), [(1770, 1100), (1770, 1590)], (1780, 1310), technology="Python", width=320)
    relation(p, "finance-payment", "finance", "payment_adapter", "Создаёт и проверяет платежи",
             (1600, 800), (2050, 800), label=(1820, 790), technology="Python", width=350)
    relation(p, "payment-finance", "payment_adapter", "finance", "Передаёт проверенный результат",
             (2050, 885), (1600, 885), label=(1820, 895), technology="Python", width=370)
    relation(p, "finance-notification", "finance", "notifier", "Передаёт финансовое уведомление",
             (1500, 920), (2250, 1020), [(1500, 975), (2250, 975)], (2250, 970), technology="Python", width=420)
    relation(p, "rental-notification", "rental", "notifier", "Передаёт результат аренды",
             (1600, 650), (2050, 1140), [(1900, 650), (1900, 1140)], (1910, 1220), technology="Python", width=330)
    relation(p, "normalized-state", "telemetry_adapter", "state", "Передаёт нормализованное состояние",
             (2480, 640), (1510, 1700), [(2520, 640), (2520, 1740), (1510, 1740)], (2350, 1650), technology="Python", width=400)
    relation(p, "passport-check", "docs_adapter", "passport", "Запрашивает проверку паспорта",
             (2480, 280), (2890, 280), label=(2680, 265), technology="HTTP/JSON", width=380)
    relation(p, "license-check", "docs_adapter", "license", "Запрашивает проверку ВУ",
             (2480, 360), (2890, 560), [(2660, 360), (2660, 560)], (2710, 450), technology="HTTP/JSON", width=330)
    relation(p, "telematics-command", "telemetry_adapter", "telematics", "Передаёт команды открытия и закрытия",
             (2480, 560), (2890, 800), [(2700, 560), (2700, 800)], (2695, 660), technology="HTTP/JSON", width=380)
    relation(p, "telematics-state", "telematics", "telemetry_adapter", "Передаёт состояние и подтверждения",
             (2890, 880), (2350, 660), [(2800, 880), (2800, 690), (2350, 690)], (2660, 700), technology="HTTP/JSON", width=400)
    relation(p, "payment-request", "payment_adapter", "payments", "Создаёт платёж и запрашивает его объект",
             (2480, 800), (2890, 1100), [(2730, 800), (2730, 1100)], (2700, 1005), technology="HTTPS/JSON", width=380)
    relation(p, "payment-event", "payments", "payment_adapter", "Сообщает изменение состояния платежа",
             (2890, 1180), (2350, 920), [(2830, 1180), (2830, 950), (2350, 950)], (2680, 950), technology="HTTPS/JSON", width=420)
    relation(p, "mail-send", "notifier", "mail", "Передаёт письмо участнику",
             (2480, 1100), (2890, 1400), [(2640, 1100), (2640, 1400)], (2700, 1340), technology="SMTP", width=350)
    relation(p, "rental-storage", "rental", "database", "Читает D1/D5/D6/D8; изменяет D2/D4/D9",
             (1560, 660), (1450, 2240), [(1560, 690), (1700, 690), (1700, 2160), (1450, 2160)],
             (1730, 1920), technology="SQL/TCP; SQLAlchemy / psycopg", width=440)
    relation(p, "finance-storage", "finance", "database", "Читает D1; изменяет D4/D7/D8/D9",
             (1550, 920), (1850, 2240), [(1550, 940), (1740, 940), (1740, 2130), (1850, 2130)],
             (1920, 2040), technology="SQL/TCP; SQLAlchemy / psycopg", width=410)
    relation(p, "state-storage", "state", "database", "Читает D2; сохраняет состояние и квитанции D3",
             (1360, 1700), (1360, 2240), label=(1350, 2110),
             technology="SQL/TCP; SQLAlchemy / psycopg", width=460)
    p.node("legend", "C4: тип, технология и ответственность указаны в каждом элементе; пунктир — граница контейнера. Серые элементы находятся вне этого контейнера. Стрелки показывают направление взаимодействия. Связи PostgreSQL раскрывают выбранные цепочки rental/state и финансовый результат; полный состав доступа установлен архитектурой. Внешние связи обозначают компоненты обмена; приём запросов и проверка доступа обеспечиваются gateway/auth.",
           40, 2460, 3200, 120, font=18, align="left", plain=True)
    return p


def build_pages(Page):
    return [scope_page(Page, 1), scope_page(Page, 2), components(Page)]
