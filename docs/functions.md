# Список функций BotController

## Инициализация
- `__init__(node_name, init_node)` - инициализация контроллера
- `wait_for_hardware(timeout)` - ожидание готовности сенсоров
- `wait(sec)` - пауза

## Движение
- `stop()` - остановка робота
- `move_forward(distance, speed)` - движение вперёд
- `move_backward(distance, speed)` - движение назад
- `turn(angle_deg, speed)` - поворот на угол
- `turn_left(angle_deg, speed)` - поворот влево
- `turn_right(angle_deg, speed)` - поворот вправо
- `move_speed(left_speed, right_speed, wheel_base)` - управление скоростью моторов
- `move_circle(radius, speed, clockwise)` - движение по окружности
- `move_circle_arc(radius, angle_deg, speed, clockwise)` - движение по дуге
- `move_by_condition(linear_speed, angular_speed, condition_func)` - движение до условия
- `move_motors_by_condition(left_speed, right_speed, condition_func)` - моторы до условия

## Лидар
- `get_scan_ranges()` - весь массив расстояний (360 значений)
- `get_distance_at_angle(angle_deg)` - расстояние под углом
- `get_distance_front()` - расстояние спереди
- `get_distance_left()` - расстояние слева
- `get_distance_right()` - расстояние справа
- `get_distance_back()` - расстояние сзади
- `get_min_distance()` - минимальное расстояние
- `get_object_angle_distance()` - угол и расстояние до ближайшего объекта
- `get_object_position()` - позиция ближайшего объекта (x, y, dist, angle)
- `get_objects_positions(distance_threshold, min_cluster_size, max_distance)` - позиции всех объектов
- `get_object_width(distance_threshold)` - ширина ближайшего объекта

## Объезд препятствий
- `avoid_obstacle(target_distance, side, speed, extra_distance)` - объезд препятствия
- `follow_wall(target_distance, side, speed, duration, stop_condition)` - следование вдоль стены

## Одометрия/IMU
- `get_yaw()` - угол поворота (радианы)
- `get_yaw_degrees()` - угол поворота (градусы)
- `get_position()` - позиция (x, y)

## Камера
- `get_image()` - текущий кадр с камеры
