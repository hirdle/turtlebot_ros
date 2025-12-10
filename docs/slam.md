С TurtleBot3 всё почти то же самое, просто часть работы за тебя уже делают готовые launch-файлы.

Разделю на две вещи:

1. **Как НА РОБОТЕ (Waffle Pi) “записать” карту на диск (map.pgm + map.yaml).**
2. **Как потом эту карту “читать” – и системой навигации, и твоим кодом.**

---

## 0. Мини-настройка TurtleBot3 Waffle Pi

На **ПК** и **на роботе** в `~/.bashrc` обычно:

```bash
export TURTLEBOT3_MODEL=waffle_pi
```

Потом:

```bash
source ~/.bashrc
```

---

## 1. “Запись” карты (создание и сохранение)

### 1.1. Запуск робота и SLAM

На **роботе** (Raspberry Pi):

```bash
roslaunch turtlebot3_bringup turtlebot3_robot.launch
```

На **ПК** (с графикой):

```bash
# 1. Запускаем SLAM (например, gmapping)
roslaunch turtlebot3_slam turtlebot3_slam.launch slam_methods:=gmapping

# 2. Для управления роботом с клавиатуры
roslaunch turtlebot3_teleop turtlebot3_teleop_key.launch
```

Ты водишь робота по лабиринту → в `rviz` видишь, как растёт карта.
Топик карты – `/map` (тип `nav_msgs/OccupancyGrid`).

### 1.2. Сохранение карты на диск (map_saver)

Когда карта готова:

```bash
# На ПК (там, где запущен SLAM)
rosrun map_server map_saver -f ~/maps/labyrinth
```

После этого появятся файлы:

```text
~/maps/labyrinth.pgm   # картинка карты
~/maps/labyrinth.yaml  # параметры (resolution, origin, threshold и т.д.)
```

Это и есть “запись карты”.

> ⚠️ Важно: `map_saver` просто берёт **последнее сообщение** из `/map` и сохраняет его.
> Поэтому перед командой убедись, что карта полностью появится (SLAM уже дорисовал всё, что нужно).

---

## 2. “Чтение” карты для дальнейшего использования

### 2.1. Чтение картой системой навигации TurtleBot3

Когда ты уже **не строишь карту**, а хочешь по ней ездить (локализация + планирование по готовой карте), запускаешь навигацию:

```bash
roslaunch turtlebot3_navigation turtlebot3_navigation.launch \
  map_file:=$HOME/maps/labyrinth.yaml
```

Внутри этого launch:

* поднимается `map_server`, который **читает** `labyrinth.yaml` и `labyrinth.pgm`;
* публикует `/map` как `nav_msgs/OccupancyGrid`;
* запускается `move_base`, AMCL и т.п.

Итого: “чтение карты” для навигации = запуск `map_server` с твоим `.yaml`.

Можно и вручную:

```bash
rosrun map_server map_server ~/maps/labyrinth.yaml
```

Тогда просто появится топик `/map` с твоей сохранённой картой.

---

### 2.2. Чтение карты в **твоём** коде (движение по лабиринту)

Для своего алгоритма (например, поиск пути по лабиринту) всё очень просто:
пока `map_server` запущен и публикует `/map`, ты делаешь то, что я показывал в предыдущем ответе – подпишись на `/map` и используй карту.

Минималка, адаптированная под TurtleBot3:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import numpy as np
from nav_msgs.msg import OccupancyGrid

class MapReader(object):
    def __init__(self):
        rospy.init_node("map_reader")

        self.map_data = None
        self.resolution = None
        self.origin = None
        self.width = None
        self.height = None

        rospy.Subscriber("/map", OccupancyGrid, self.map_callback)

    def map_callback(self, msg):
        self.resolution = msg.info.resolution
        self.width = msg.info.width
        self.height = msg.info.height
        self.origin = (msg.info.origin.position.x,
                       msg.info.origin.position.y)

        data = np.array(msg.data, dtype=np.int8)
        self.map_data = data.reshape((self.height, self.width))

        rospy.loginfo_once("Карта загружена: %dx%d, res=%.3f" %
                           (self.width, self.height, self.resolution))

    def spin(self):
        rate = rospy.Rate(1)
        while not rospy.is_shutdown():
            if self.map_data is not None:
                rospy.loginfo_throttle(5, "Карта доступна, можно работать")
                # здесь можно запускать свой алгоритм обхода лабиринта
            rate.sleep()

if __name__ == "__main__":
    node = MapReader()
    node.spin()
```

**Важно:** нет разницы, как была получена карта –
через SLAM секунду назад или загружена из `.yaml` через `map_server`.
Для твоего кода это просто `/map` с OccupancyGrid.

---

## 3. Если хочешь “самописную” запись карты из кода

Обычно достаточно `map_saver`, но можно и самому:

1. Подписаться на `/map`.
2. В `map_callback` взять `msg` и сохранить:

   * значения `msg.data` → картинку (например, PGM/PNG через OpenCV / PIL);
   * метаданные `msg.info` → свой YAML/JSON.

Но для TurtleBot3 *штатный путь* такой:

* **запись**: `rosrun map_server map_saver -f ~/maps/labyrinth`
* **чтение**: `roslaunch turtlebot3_navigation turtlebot3_navigation.launch map_file:=...`
  или `rosrun map_server map_server ...`

---

Если хочешь, могу дальше:

* показать пример **поиска пути (BFS/A*) по карте TurtleBot3**
* или пример полного пайплайна: *загружаем карту → ищем путь по клеткам → отправляем цели в `move_base` для перемещения по лабиринту*.
