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

## Движение по прямой
1. запись в start_x и start_y изначального положения
2. начало цикла
- запись curr_x и curr_y текущего положения
- проверяем, если по формуле Пифагора расстояние больше, чем заданное, прерываем цикл
- публикуем в cmd_vel Twist с скоростью в linear.x
- rate.sleep
3. остановка