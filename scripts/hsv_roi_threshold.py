import argparse
from pathlib import Path

import cv2
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Выделяет область на изображении и выводит HSV пороги для выбранной зоны."
    )
    parser.add_argument(
        "image",
        type=Path,
        help="Путь до изображения (форматы, поддерживаемые OpenCV).",
    )
    parser.add_argument(
        "--slack",
        type=int,
        default=0,
        help="Запас к вычисленным min/max HSV (расширяет диапазон).",
    )
    parser.add_argument(
        "--rect",
        type=int,
        nargs=4,
        metavar=("X", "Y", "W", "H"),
        help="ROI без GUI: x y w h. Полезно в headless окружении.",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Использовать всё изображение (без выбора ROI).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.image.exists():
        raise FileNotFoundError(args.image)

    bgr = cv2.imread(str(args.image))
    if bgr is None:
        raise ValueError(f"Не удалось открыть изображение: {args.image}")

    h_img, w_img = bgr.shape[:2]

    if args.full:
        x, y, w, h = 0, 0, w_img, h_img
    elif args.rect:
        x, y, w, h = args.rect
    else:
        # Выбор ROI мышью. После выделения нажмите Enter/Space, Esc — отмена.
        window_name = "Выберите область и нажмите Enter/Space"
        try:
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            roi = cv2.selectROI(window_name, bgr, fromCenter=False, showCrosshair=True)
        except cv2.error as err:
            raise RuntimeError(
                "Нет GUI. Укажите ROI через --rect x y w h или используйте --full."
            ) from err
        cv2.destroyAllWindows()
        x, y, w, h = roi

    # Валидация и обрезка в пределах изображения.
    if w < 0 or h < 0:
        print("Некорректный ROI: отрицательные размеры.")
        return
    if w == 0 or h == 0:
        print("Область не выбрана.")
        return
    x = max(0, x)
    y = max(0, y)
    w = min(w, w_img - x)
    h = min(h, h_img - y)
    if w == 0 or h == 0:
        print("Область не выбрана.")
        return

    roi_bgr = bgr[y : y + h, x : x + w]
    roi_hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)

    # Вычисляем минимальные и максимальные значения по всем каналам HSV.
    min_hsv = roi_hsv.reshape(-1, 3).min(axis=0).astype(int)
    max_hsv = roi_hsv.reshape(-1, 3).max(axis=0).astype(int)

    slack = max(args.slack, 0)
    lower = np.array([max(min_hsv[0] - slack, 0), max(min_hsv[1] - slack, 0), max(min_hsv[2] - slack, 0)], dtype=np.uint8)
    upper = np.array(
        [
            min(max_hsv[0] + slack, 179),
            min(max_hsv[1] + slack, 255),
            min(max_hsv[2] + slack, 255),
        ],
        dtype=np.uint8,
    )

    print(f"Min HSV: {min_hsv.tolist()}")
    print(f"Max HSV: {max_hsv.tolist()}")
    if slack:
        print(f"Диапазон с запасом ±{slack}: lower={lower.tolist()}, upper={upper.tolist()}")

    hsv_full = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv_full, lower, upper)
    result = cv2.bitwise_and(bgr, bgr, mask=mask)

    # Отображаем изображение, маску и результат.
    cv2.imshow("Оригинал", bgr)
    cv2.imshow("Маска", mask)
    cv2.imshow("Результат", result)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
