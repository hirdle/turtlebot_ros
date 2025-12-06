# Документация main_matching.py

## Назначение
Модуль для **детекции дорожных знаков по цвету** и **сопоставления их с шаблонами** (template matching).

---

## Архитектура (5 блоков)

```
1. ЗАГРУЗКА → 2. ДЕТЕКЦИЯ ЦВЕТА → 3. КОНТУРЫ/ROI → 4. МАТЧИНГ → 5. ВИЗУАЛИЗАЦИЯ
```

---

## Блок 1: ЗАГРУЗКА

| Функция | Что делает |
|---------|------------|
| `load_image(path)` | Загружает изображение через cv2.imread |
| `load_templates(paths, color, padding)` | Загружает шаблоны и сразу извлекает из них ROI |

**Ключевое**: шаблоны обрабатываются ТАК ЖЕ как входное изображение (детекция → ROI).

---

## Блок 2: ДЕТЕКЦИЯ ЦВЕТА (HSV)

### Базовая функция
```python
def detect_color(image, lower_hsv, upper_hsv):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower, upper)
    # + морфология: CLOSE, OPEN с ядром 5x5
    return mask
```

### Цветовые диапазоны (HSV)
| Цвет | H | S | V |
|------|---|---|---|
| **Синий** | 100-130 | 100-255 | 100-255 |
| **Красный** | 0-10 ИЛИ 160-180 | 100-255 | 100-255 |
| **Зеленый** | 40-80 | 100-255 | 100-255 |
| **Желтый** | 20-40 | 100-255 | 100-255 |

**Автоопределение** (`detect_dominant_color`): проверяет все 4 цвета, выбирает с максимальной площадью маски.

---

## Блок 3: КОНТУРЫ И ROI

### Алгоритм извлечения ROI
```
1. Маска цвета → findContours (RETR_EXTERNAL)
2. Фильтрация контуров (area > 100)
3. Берем САМЫЙ БОЛЬШОЙ контур
4. Bounding box + padding (20px)
5. Перспективная трансформация → квадрат 300x300
```

### Ключевые функции
```python
find_largest_contour(mask, min_area=100)  # → контур или None
get_bounding_box(contour, padding=20)      # → (x_min, y_min, x_max, y_max)
extract_roi(image, bbox, output_size=300)  # → квадратное ROI
extract_object_roi(image, color, padding)  # → ROI или None (все в одном)
```

### Перспективная трансформация
```python
pts1 = углы bbox
pts2 = [[0,0], [300,0], [0,300], [300,300]]
M = cv2.getPerspectiveTransform(pts1, pts2)
roi = cv2.warpPerspective(image, M, (300, 300))
```

---

## Блок 4: МАТЧИНГ

### Предобработка
```python
def preprocess_for_matching(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    return blurred
```

### Сравнение
```python
def match_single(roi, template):
    # 1. Предобработка обоих
    # 2. Resize шаблона под размер ROI
    # 3. cv2.matchTemplate(..., cv2.TM_CCOEFF_NORMED)
    # 4. Берем max_val из minMaxLoc
    return confidence  # 0.0 - 1.0
```

### Матчинг со списком шаблонов
```python
def match_templates(roi, templates, threshold=0.7):
    # Проходим по всем шаблонам
    # Выбираем лучший по confidence
    return (is_match, confidence, best_name)
```

**Threshold по умолчанию: 0.7** (в примере используется 0.45)

---

## Блок 5: ВИЗУАЛИЗАЦИЯ

```python
def draw_result(image, contour, bbox, is_match, confidence, template_name):
    # Зеленый если MATCH, красный если NO MATCH
    # Рисует: контур, bbox, текст с результатом
    return result_image
```

---

## Главные функции (точки входа)

### 1. `detect_and_match()` - работа с файлами
```python
detect_and_match(
    image_path='photo.png',
    template_paths=['t1.png', 't2.png'],
    color='auto',      # или 'blue', 'red', 'green', 'yellow'
    threshold=0.7,
    padding=20,
    save_path='result.jpg'  # опционально
)
# → (is_match, confidence, best_template_name)
```

### 2. `detect_and_match_image()` - работа с numpy arrays
```python
detect_and_match_image(
    image=np_array,
    templates=[(name, roi), ...],  # предзагруженные
    color='auto',
    threshold=0.7,
    padding=20
)
# → (is_match, confidence, best_template_name)
```

---

## Пайплайн обработки (схема)

```
ВХОДНОЕ ИЗОБРАЖЕНИЕ           ШАБЛОНЫ
       |                         |
       v                         v
   BGR→HSV                   BGR→HSV
       |                         |
       v                         v
   Маска цвета               Маска цвета
       |                         |
       v                         v
   Контуры                   Контуры
       |                         |
       v                         v
   Bounding Box              Bounding Box
       |                         |
       v                         v
   ROI 300x300               ROI 300x300
       |                         |
       +----------+-------------+
                  |
                  v
           TEMPLATE MATCHING
           (TM_CCOEFF_NORMED)
                  |
                  v
           confidence >= threshold?
                  |
            +-----+-----+
            |           |
          MATCH      NO MATCH
```

---

## Формулы для запоминания

### HSV диапазоны (запомнить H)
- **Синий**: 100-130
- **Красный**: 0-10 + 160-180 (два диапазона!)
- **Зеленый**: 40-80
- **Желтый**: 20-40

### Константы
- **min_area** контура: 100
- **padding**: 20
- **output_size** ROI: 300x300
- **kernel** морфологии: 5x5
- **GaussianBlur**: (5, 5)
- **threshold** матчинга: 0.7 (настраиваемый)

### Методы OpenCV
- `cv2.inRange()` - создание маски
- `cv2.morphologyEx(MORPH_CLOSE/OPEN)` - очистка маски
- `cv2.findContours(RETR_EXTERNAL)` - поиск контуров
- `cv2.getPerspectiveTransform()` - матрица трансформации
- `cv2.warpPerspective()` - применение трансформации
- `cv2.matchTemplate(TM_CCOEFF_NORMED)` - сравнение изображений

---

## Минимальный код для воспроизведения

```python
import cv2
import numpy as np

# 1. Детекция цвета (пример для синего)
hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
mask = cv2.inRange(hsv, (100,100,100), (130,255,255))
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5,5)))

# 2. Контур и bbox
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
contour = max(contours, key=cv2.contourArea)
x,y,w,h = cv2.boundingRect(contour)

# 3. ROI с трансформацией
pts1 = np.float32([[x,y],[x+w,y],[x,y+h],[x+w,y+h]])
pts2 = np.float32([[0,0],[300,0],[0,300],[300,300]])
M = cv2.getPerspectiveTransform(pts1, pts2)
roi = cv2.warpPerspective(image, M, (300,300))

# 4. Матчинг
gray1 = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
gray2 = cv2.cvtColor(template_roi, cv2.COLOR_BGR2GRAY)
result = cv2.matchTemplate(gray1, gray2, cv2.TM_CCOEFF_NORMED)
confidence = cv2.minMaxLoc(result)[1]
```
