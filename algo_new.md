## Используемые библиотеки

Базовые
```
rospy
geometry_msgs.msg (Twist)
nav_msgs.msg (Odometry)
sensor_msgs.msg (LaserScan, Image, Imu)
numpy
math
```

Зрение
```
cv2
cv_bridge (CvBridge)
```

Навигация
```
move_base_msgs.msg (MoveBaseAction, MoveBaseGoal)
actionlib
```

## Инициализация класса
1. инициализация ноды (init_node)
2. создание паблишера /cmd_vel с Twist и очередью 10
3. создание подписчиков на /odom и /scan с колбэками на записывающие функции в переменную из класса
4. создание подписчика на камеру / с Image и колбэком на функцию set_image из класса
5. инициалиация actionlib.SimpleActionClient с /move_base, MoveBaseAction
6. ожидание сервера в клиенте навигации
7. инициализация Rate c 100 герц
8. указание скоростей по умолчанию
9. создание переменных для одометрии, изображения (current_image), данных с лидара
10. инициализация словаря цветов (colors) в rgb формате
11. указание действия при выключении (on_shutdown) - функция stop

## Функция wait 
1. метод sleep из rospy с переводом в секунды

## Функция stop
1. публикуем в cmd_vel пустой Twist

## Функция get_image
1. возвращаем копию current_image из класса

## Функция set_image
1. задаем current_image из класса значение, переведенное с помощью метода imgmsg_to_cv2 из CvBridge со вторым аргументом `bgr8`

## Функция get_position
1. задаем переменным x и y значения из odom_data.pose.pose.position.?
2. возвращаем их

## Функция get_angle
1. возвращаем 2 * math.degrees(math.asin(self.odom_data.pose.pose.orientation.z) * math.copysign(1, self.odom_data.pose.pose.orientation.w))
Это есть в learn.turtlebro.ru

## Функция normilize_angle
1. перевод исходного угла в радианы
2. получение результата от atan2(sin(x), cos(x))
3. возвращение результата, переведенного в градусы

## Движение move_linear
1. если скорость не передана, берем base_speed
2. запись в start_x и start_y изначального положения
3. запускаем цикл до shutdown
- запись curr_x и curr_y текущего положения
- проверяем, если по формуле Пифагора расстояние больше, чем заданное, прерываем цикл
- публикуем в cmd_vel Twist с скоростью в linear.x
- rate.sleep
4. остановка

## Функция turn
1. если скорость не передана, берем turn_speed
2. вычисляем target_angle как normilize_angle(текущий угол - заданный)
3. запускаем цикл до shutdown
- если модуль разницы между target_angle и текущим углом меньше 2 градусов, выходим
- формируем Twist с angular.z = -speed * (angle/abs(angle)) и публикуем в cmd_vel
- rate.sleep
4. остановка

## Функция move_motors_speed
1. считаем linear = (right_speed + left_speed) / 2.0
2. считаем angular = (right_speed - left_speed) / wheel_base
3. формируем Twist с linear.x = linear и angular.z = angular
4. публикуем в cmd_vel

## Функция move_circle_arc
1. считаем angular_speed = speed / radius
2. считаем linear_component = angular_speed * (wheel_base / 2)
3. если clockwise: left = speed + linear_component, right = speed - linear_component
- иначе: left = speed - linear_component, right = speed + linear_component
4. запоминаем current_angle = get_angle(), target_angle_deg = abs(angle_deg), accumulated = 0
5. цикл до shutdown:
- previous = current_angle, current_angle = get_angle()
- delta = normilize_angle(current_angle - previous)
- accumulated += abs(delta)
- если accumulated >= target_angle_deg, выходим из цикла (break)
- вызываем move_motors_speed(left, right)
- rate.sleep
6. остановка

## Функция get_distance_at_angle
1. пересчитываем угол по формуле 360 - abs(-angle - 180)
2. если итог 360, заменяем на 0
3. возвращаем scan_data.ranges[angle]

## Функция get_min_distance
1. если scan_data пуст, возвращаем бесконечность
2. фильтруем ranges: убираем inf, NaN и значения <= 0
3. если есть валидные расстояния, берем минимум, иначе бесконечность

## Функция get_sector_data
1. если scan_data пуст, возвращаем []
2. берем число лучей и шаг угла в градусах
3. нормализуем start_angle и end_angle по модулю 360
4. идем по всем измерениям, считаем angle_deg = 360 - abs(raw_angle + 180), angle_deg % 360
5. проверяем попадание в сектор (учет перехода через 0); если внутри и расстояние валидно, кладем (angle_deg, distance) в список
6. сортируем по углу и возвращаем

## Функция get_sector_xy
1. если scan_data пуст, возвращаем []
2. берем шаг угла в градусах, нормализуем start/end
3. идем по лучам, считаем angle_deg как 360 - abs(raw_angle + 180) с модулем 360
4. проверяем попадание в сектор; для валидных расстояний считаем x = r*cos(rad), y = r*sin(rad), добавляем в списки
5. возвращаем xs, ys

## Функция get_object_angle_distance
1. если scan_data пуст, возвращаем (None, бесконечность)
2. проходим ranges, ищем минимальное валидное расстояние (>0, не inf/NaN), запоминаем индекс
3. если ничего не нашли, возвращаем (None, бесконечность)
4. считаем angle_deg = idx * angle_increment в градусах, затем 360 - abs(angle_deg + 180)
5. возвращаем (angle_deg, min_distance)

## Функция get_object_position
1. берем angle_deg, distance из get_object_angle_distance; если angle_deg None, возвращаем (None, None, None, None)
2. получаем позицию робота (x, y) и yaw в радианах
3. считаем глобальный угол до объекта: yaw + radians(angle_deg)
4. объект: x + distance * cos(угол), y + distance * sin(угол)
5. возвращаем (object_x, object_y, distance, angle_deg)

## Функция get_objects_positions
1. если scan_data пуст, возвращаем []
2. собираем points = (index, distance) для валидных измерений (0 < r < max_distance)
3. если points пуст, возвращаем []
4. кластеризуем по разрыву индексов > 5 или по скачку расстояния > distance_threshold; сохраняем кластеры длиной >= min_cluster_size
5. берем позицию и yaw робота, готовим список объектов
6. для каждого кластера: берем точку с минимальной дистанцией, переводим индекс в angle_deg (360 - abs(angle_deg + 180)), считаем глобальный угол yaw + radians(angle_deg) и координаты объекта
7. добавляем (x, y, distance, angle_deg) в список, сортируем объекты по расстоянию и возвращаем

## Функция get_mask
1. создаем kernel 5x5 из единиц с типом np.uint8
2. берем нижнюю и верхнюю границы цвета из colors
3. переводим кадр из BGR в RGB через cvtColor с cv2.COLOR_BGR2RGB
4. строим маску cv2.inRange по выбранному цвету (frame, low, high)
5. применяем morphologyEx: MORPH_OPEN, затем MORPH_CLOSE с тем же kernel
6. возвращаем маску

## Функция find_contours
1. ищем внешние контуры (RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)
- contours, _ = cv2.findContours
2. фильтруем контуры по площади (countourArea) > min_area
3. возвращаем итоговый список

## Функция track_object
1. цикл до shutdown
- получаем маску get_mask от текущего кадра get_image
- ищем контуры через find_contours
- если контуры есть:
-- берем первый контур
-- делаем reshape с параметрами -1, 2 (pts = c.reshape)
-- находим x1, y1 через pts.min(axis=0)
-- находим x2, y2 через pts.max(axis=0)
-- получаем h, w кадра через .shape[:2]
-- diff = половина ширины кадра минус центр объекта (x1+x2) / 2
-- формируем Twist с angular.z = diff * 0.001, публикуем
-- rate.sleep

## Функция send_goal
1. переводим yaw_deg в радианы (math.radians)
2. собираем кватернион через quaternion_from_euler(0,0,yaw)
3. создаем goal от MoveBaseGoal с frame_id "map" и stamp = rospy.Time.now()
```
goal.target_pose.header.frame_id = "map"
goal.target_pose.header.stamp = rospy.Time.now()
```
4. записываем позицию x, y, z=0 (goal.target_pose.pose.position.?)
5. записываем ориентацию из кватерниона
```
goal.target_pose.pose.orientation.x = q[0]
goal.target_pose.pose.orientation.y = q[1]
goal.target_pose.pose.orientation.z = q[2]
goal.target_pose.pose.orientation.w = q[3]
```
6. отправляем goal через client.send_goal из класса
