# Документация bot_camera.py

## Назначение
Модуль для работы с камерой TurtleBot3 через ROS. Получает изображения, детектирует цвета, находит контуры и сопоставляет с шаблонами.

---

## Архитектура (что запомнить)

```
BotCameraController
├── Инициализация (ROS node + subscriber)
├── Получение кадров (BGR, RGB, HSV, Gray)
├── Детекция цветов (HSV маски + морфология)
├── Работа с контурами (поиск, центр, площадь)
└── Матчинг шаблонов (через main_matching)
```

---

## Зависимости

```python
import rospy                          # ROS Python API
import cv2                            # OpenCV
import numpy as np                    # Массивы
from sensor_msgs.msg import Image     # ROS Image сообщение
from cv_bridge import CvBridge        # Конвертер ROS <-> OpenCV
import main_matching                  # Модуль матчинга шаблонов
```

---

## Класс BotCameraController

### Инициализация

```python
def __init__(self, node_name='bot_camera_controller', init_node=True):
    if init_node:
        rospy.init_node(node_name, anonymous=True)
    
    self.bridge = CvBridge()           # Конвертер ROS -> OpenCV
    self.current_frame = None          # Текущий кадр
    
    # Подписка на топик камеры
    rospy.Subscriber('/front_camera/image_raw', Image, self._image_callback)
    
    self.rate = rospy.Rate(30)         # 30 Hz
```

**Ключевые моменты:**
- `CvBridge` - мост между ROS Image и OpenCV numpy array
- Топик: `/front_camera/image_raw`
- `init_node=False` - если нода уже создана в другом модуле

### Callback камеры

```python
def _image_callback(self, msg):
    try:
        self.current_frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
    except CvBridgeError as e:
        rospy.logerr("CvBridge Error: %s" % e)
```

**Запомнить:** `imgmsg_to_cv2(msg, "bgr8")` - конвертация в BGR формат OpenCV

---

## Методы получения изображений

| Метод | Возвращает | Конвертация |
|-------|-----------|-------------|
| `get_image()` | BGR (оригинал) | `.copy()` |
| `get_image_rgb()` | RGB | `COLOR_BGR2RGB` |
| `get_hsv_image()` | HSV | `COLOR_BGR2HSV` |
| `get_gray_image()` | Grayscale | `COLOR_BGR2GRAY` |
| `get_image_size()` | `(height, width)` | `shape[:2]` |

---

## Детекция цветов (главное!)

### HSV диапазоны цветов

| Цвет | H min | H max | S | V |
|------|-------|-------|---|---|
| Красный | 0-10 ИЛИ 160-180 | | 100-255 | 100-255 |
| Зеленый | 40 | 80 | 100-255 | 100-255 |
| Синий | 100 | 130 | 100-255 | 100-255 |
| Желтый | 20 | 40 | 100-255 | 100-255 |

### Базовый метод детекции

```python
def _detect_color_hsv(self, lower_hsv, upper_hsv):
    hsv = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2HSV)
    lower = np.array(lower_hsv, dtype=np.uint8)
    upper = np.array(upper_hsv, dtype=np.uint8)
    mask = cv2.inRange(hsv, lower, upper)
    
    # Морфология для очистки маски
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)  # Закрыть дыры
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)   # Убрать шум
    return mask
```

### Особенность красного цвета

Красный в HSV "разрывается" на 0 и 180, нужно 2 маски:

```python
def _detect_red(self):
    hsv = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
    mask2 = cv2.inRange(hsv, np.array([160, 100, 100]), np.array([180, 255, 255]))
    mask = cv2.bitwise_or(mask1, mask2)  # Объединяем маски
    # ... морфология
```

### Автодетекция доминирующего цвета

```python
def detect_dominant_color(self):
    color_detectors = {'blue': ..., 'red': ..., 'green': ..., 'yellow': ...}
    best_color, best_area, best_mask = 'blue', 0, None
    
    for color_name, detector in color_detectors.items():
        mask = detector()
        area = cv2.countNonZero(mask)  # Считаем белые пиксели
        if area > best_area:
            best_area, best_color, best_mask = area, color_name, mask
    
    return best_mask, best_color
```

---

## Работа с контурами

### Поиск контуров

```python
def find_contours(self, mask):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return contours
```

**Параметры:**
- `RETR_EXTERNAL` - только внешние контуры
- `CHAIN_APPROX_SIMPLE` - сжатие контура (экономия памяти)

### Центр контура через моменты

```python
def get_contour_center(self, contour):
    M = cv2.moments(contour)
    if M["m00"] == 0:
        return None
    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    return (cx, cy)
```

**Формулы:**
- `m00` - площадь
- `cx = m10 / m00`
- `cy = m01 / m00`

---

## Матчинг шаблонов

```python
def match_template(self, template_paths, color='auto', threshold=0.7, padding=20):
    templates = main_matching.load_templates(template_paths, color, padding)
    return main_matching.detect_and_match_image(
        self.current_frame, templates, color, threshold, padding
    )
```

**Возвращает:** `(is_match: bool, confidence: float, best_template: str or None)`

---

## Пример использования

```python
if __name__ == '__main__':
    cam = BotCameraController()
    
    if cam.wait_for_camera():
        # Получить кадр
        frame = cam.get_image()
        
        # Детекция синего
        mask = cam.detect_blue()
        
        # Найти объект
        contour = cam.find_largest_contour(mask)
        center = cam.get_contour_center(contour)
        
        # Матчинг
        is_match, conf, name = cam.match_template(['template/stop.png'])
```

---

## Шпаргалка для написания с нуля

### Минимальный скелет

```python
import rospy, cv2, numpy as np
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

class BotCameraController:
    def __init__(self):
        rospy.init_node('cam')
        self.bridge = CvBridge()
        self.frame = None
        rospy.Subscriber('/front_camera/image_raw', Image, self._cb)
    
    def _cb(self, msg):
        self.frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
    
    def detect_blue(self):
        hsv = cv2.cvtColor(self.frame, cv2.COLOR_BGR2HSV)
        return cv2.inRange(hsv, np.array([100,100,100]), np.array([130,255,255]))
```

### Чек-лист при написании

1. [ ] rospy.init_node
2. [ ] CvBridge для конвертации
3. [ ] Subscriber на топик камеры
4. [ ] Callback сохраняет frame
5. [ ] HSV конвертация для цвета
6. [ ] cv2.inRange для маски
7. [ ] Морфология (CLOSE + OPEN) для очистки
8. [ ] findContours с RETR_EXTERNAL
9. [ ] moments для центра контура

---

## HSV диапазоны (выучить!)

```
Синий:   H=100-130, S=100-255, V=100-255
Зеленый: H=40-80,   S=100-255, V=100-255
Желтый:  H=20-40,   S=100-255, V=100-255
Красный: H=0-10 OR H=160-180, S=100-255, V=100-255
```

## Ключевые OpenCV функции

```python
cv2.cvtColor(img, cv2.COLOR_BGR2HSV)           # Конвертация цвета
cv2.inRange(hsv, lower, upper)                  # Создание маски
cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel) # Закрыть дыры
cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)  # Убрать шум
cv2.findContours(mask, RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)
cv2.contourArea(contour)                        # Площадь
cv2.moments(contour)                            # Моменты для центра
cv2.countNonZero(mask)                          # Кол-во белых пикселей
```
