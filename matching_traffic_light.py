#!/usr/bin/env python
# -*- coding: utf-8 -*-

import cv2
from common_cv import (
    find_largest_contour,
    color_detectors,
)


# ============ ГЛАВНАЯ ФУНКЦИЯ ============

def detect_and_match(frame=None):

    result_color_list = []

    for color, detector in color_detectors.items():
        mask = detector(frame)
        contour = find_largest_contour(mask)
        if contour is not None:
            result_color_list.append((color, contour, cv2.contourArea(contour)))

    return result_color_list