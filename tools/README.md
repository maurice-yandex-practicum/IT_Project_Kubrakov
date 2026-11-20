# Инструменты работы с диаграммами draw.io

`drawio.py` — инспектор и минимальный редактор .drawio-файлов (Python 3, без сторонних пакетов). Правки выполняются на уровне строк, остальная разметка сохраняется как есть.

## Команды

| Команда | Что делает |
|---|---|
| `python3 tools/drawio.py pages FILE` | список листов с числом вершин и рёбер |
| `python3 tools/drawio.py cells FILE "Имя листа"` | вершины листа: id, подпись, геометрия |
| `python3 tools/drawio.py edges FILE "Имя листа"` | рёбра: `source -> target : подпись` |
| `python3 tools/drawio.py find FILE "Имя листа" TEXT` | поиск подписи по вершинам и рёбрам |
| `python3 tools/drawio.py stat FILE "Имя листа"` | степень каждой вершины (для проверки баланса DFD) |
| `python3 tools/drawio.py dot FILE "Имя листа" [OUT.dot]` | выгрузка листа в Graphviz DOT |
| `python3 tools/drawio.py check FILE` | проверка XML-валидности файла |
| `python3 tools/drawio.py set-label FILE "Имя листа" SRC TGT TEXT` | заменить подпись ребра |
| `python3 tools/drawio.py set-cell FILE "Имя листа" ID TEXT` | заменить подпись вершины (например, имени связи ER) |
| `python3 tools/drawio.py add-child FILE "Имя листа" PARENT CHILD "Подпись"` | добавить вершину-потомок под родителем и ребро |

## Замечания

- Имена листов передаются так, как в атрибуте `name` `<diagram>` (например, `"DFD level 1"`).
- Перед правкой сохраните файл в Git — `set-label` и `add-child` перезаписывают его.
- `stat` считает входящие/исходящие рёбра; для проверки баланса контекстной диаграммы и DFD уровня 1 сравнивайте степени внешних сущностей.
