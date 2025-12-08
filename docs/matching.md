# Matching Module - Документация

Упрощённый модуль для детекции ArUco маркеров, дорожных знаков и светофора.

## Установка

```python
import cv2
import numpy as np
from matching import detect_aruco, detect_sign, detect_traffic_light
```

## Функции

### 1. detect_aruco(frame)

Детекция ArUco маркеров 7x7.

```python
results = detect_aruco(frame)
# results = [(marker_id, corners, area), ...]

for marker_id, corners, area in results:
    print(f"Найден маркер ID={marker_id}, площадь={area}")
```

### 2. detect_sign(frame, template_paths, color='auto', threshold=0.7)

Детекция и матчинг знака с шаблонами.

```python
templates = [
    'template/forward.png',
    'template/left.png',
    'template/right.png',
    'template/stop.png',
]

is_match, confidence, name = detect_sign(frame, templates, color='blue')

if is_match:
    print(f"Найден знак: {name} (уверенность: {confidence:.2f})")
```

**Параметры:**
- `frame` - изображение с камеры
- `template_paths` - список путей к шаблонам
- `color` - цвет знака: `'blue'`, `'red'`, `'green'`, `'yellow'` или `'auto'`
- `threshold` - порог совпадения (0.0-1.0), по умолчанию 0.7

### 3. detect_traffic_light(frame)

Детекция цветов светофора.

```python
results = detect_traffic_light(frame)
# results = [(color, contour, area), ...] - отсортировано по площади

if results:
    color, contour, area = results[0]  # самый яркий цвет
    print(f"Светофор: {color}")
```

## HSV Диапазоны цветов

| Цвет   | H (min-max) | S (min-max) | V (min-max) |
|--------|-------------|-------------|-------------|
| blue   | 100-130     | 100-255     | 100-255     |
| green  | 40-80       | 90-255      | 70-255      |
| yellow | 20-40       | 100-255     | 100-255     |
| red    | 0-10, 160-180 | 100-255   | 100-255     |

## Пример полного использования

```python
import cv2
from matching import detect_aruco, detect_sign, detect_traffic_light

cap = cv2.VideoCapture(0)
templates = ['template/forward.png', 'template/stop.png']

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # ArUco
    for marker_id, corners, area in detect_aruco(frame):
        print(f"ArUco: {marker_id}")
    
    # Знак
    is_match, conf, name = detect_sign(frame, templates)
    if is_match:
        print(f"Знак: {name}")
    
    # Светофор
    lights = detect_traffic_light(frame)
    if lights:
        print(f"Светофор: {lights[0][0]}")

cap.release()
```

## Как добавить шаблон знака

1. Сфотографируйте знак на однотонном фоне
2. Сохраните в папку `template/`
3. Добавьте путь в список `template_paths`

```python
templates = [
    'template/forward.png',
    'template/new_sign.png',  # новый шаблон
]
```

## Структура файла

```
matching.py (~120 строк)
├── COLORS - HSV диапазоны
├── _get_mask() - маска по цвету
├── _find_contour() - поиск контура
├── _dominant_color() - автоопределение цвета
├── _crop_roi() - вырезание ROI
├── detect_aruco() - ArUco маркеры
├── detect_sign() - знаки
└── detect_traffic_light() - светофор
```
