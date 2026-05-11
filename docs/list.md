# Функции для описания

0. инициализация
- определение топиков и колбэков
- утилиты-функции (нормализация угла, перевод угла)
`_normalize_angle`

1. базовое движение и позиционирование
- остановка
`stop`
- управление моторами раздельно
`move_motors`
- движение по условию
`move_by_condition`
`move_motors_by_condition`
- прямолинейное движение
`move_linear`
`move_forward`
`move_backward`
- повороты
`turn`
`turn_left`
`turn_right`
- определение текущего угла и позиции относительно старта
`get_position`
`get_yaw`
`get_yaw_degrees`
- движение по дуге заданного радиуса
`move_circle_arc`
- работа с odom, imu, cmd_vel
параметры знать

2. лидар
- чтение всех данных
`get_scan_data`
- чтение данных под определенным углом
`get_distance_at_angle`
- чтение данных по сторонам (слева, справа, впереди, сзади)
`get_distance_front`
`get_distance_left`
`get_distance_right`
`get_distance_back`
- чтение данных по секторам (старт_угол, конец_угол)
`get_sector_data`
`get_sector_xy`
- получение всех объектов на заданном максимальном расстоянии от робота, определение его позиции
`get_object_angle_distance`
`get_object_position`
`get_objects_positions`

- движение по стене
- движение до объекта

3. компьютерное зрание
- определение цвета максимального объекта и его позиции
`colors`
`get_mask`
`find_contour`
`find_dominant_color`
- определение знаков по фото
`crop_roi`
`detect_sign`
- определение aruco кодов
`detect_acuro`
- определение светофоров
`detect_traffic_light`

4. карты (slam) - gazebo
- построение карты
- ориентация по ней, нахождение кратчайшего пути