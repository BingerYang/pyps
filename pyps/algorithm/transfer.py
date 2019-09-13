# -*- coding: utf-8 -*- 
# @Time     : 2019-09-12 16:01
# @Author   : binger
import numpy as np
import cv2
import math
from scipy.spatial import Delaunay


def layer_distance(layer1, layer2):
    """
    计算两个图层在水平X和垂直Y方向的距离与两图层长度之和的占比：
    :param layer1: 图层1
    :param layer2: 图层2
    :return: distx, disty
    """
    distx = max(layer1['xmin'] - layer2['xmax'], layer2['xmin'] - layer1['xmax'])
    disty = max(layer1['ymin'] - layer2['ymax'], layer2['ymin'] - layer1['ymax'])

    return distx, disty


def layer_compare(layer1, layer2, direct=0, iou=0.8, dist=None):
    """
    比较两个图层在水平或垂直方向是否存在绑定关系：
    :param layer1: 图层1
    :param layer2: 图层2
    :param direct: 水平为0，垂直为1
    :param iou: 重叠度百分比
    :param dist: 两图层中心距相对于两图层宽度/高度之和的比例
    :return: True 绑定, False 非绑定
    """

    if direct == 0:
        intersect = min(layer1['ymax'], layer2['ymax']) - max(layer1['ymin'], layer2['ymin']) + 1
        union = min(layer1['ymax'] - layer1['ymin'] + 1, layer2['ymax'] - layer2['ymin'] + 1)
        distance, _ = layer_distance(layer1, layer2)

    else:
        intersect = min(layer1['xmax'], layer2['xmax']) - max(layer1['xmin'], layer2['xmin']) + 1
        union = min(layer1['xmax'] - layer1['xmin'] + 1, layer2['xmax'] - layer2['xmin'] + 1)
        _, distance = layer_distance(layer1, layer2)

    if dist is None:
        return True if intersect / union >= iou else False
    else:

        return True if intersect / union >= iou and abs(distance) <= dist else False


def coordinate_transfer(rect, source_size, target_size):
    """
    延展坐标换算公式
    :param rect: [x1, y1, x2, y2]
    :param source_size: 延展前画面尺寸
    :param target_size: 延展目标尺寸
    :return:
    """

    def get_center(rect, width, height):
        """
        获取元素在画布内的中心坐标（最小外接矩形的中心）：
        :param rect: [x1, y1, x2, y2]
        :param width: 画面宽
        :param height: 画面高
        :return:
        """
        # 获取元素在画布内的实际区域
        xmin = max(0, rect[0])
        ymin = max(0, rect[1])
        xmax = min(xmin + rect[2] - rect[0], width - 1)
        ymax = min(ymin + rect[3] - rect[1], height - 1)
        return (ymin + ymax) / 2, (xmin + xmax) / 2

    width_scale = target_size[0] / source_size[0]
    height_scale = target_size[1] / source_size[1]
    min_scale = min(width_scale, height_scale)

    # 元素外接矩形中心
    src_center_row, src_center_col = (rect[1] + rect[3]) / 2, (rect[0] + rect[2]) / 2
    src_row, src_col = get_center(rect, source_size[0], source_size[1])  # 元素在画布内的中心
    new_row = src_row * height_scale
    new_col = src_col * width_scale
    # 通过画布内切片中心点计算完整切片的中心点
    new_row = new_row - (src_row - src_center_row) * min_scale
    new_col = new_col - (src_col - src_center_col) * min_scale

    width, height = (rect[2] - rect[0] + 1) * min_scale, (rect[3] - rect[1] + 1) * min_scale
    xmin = new_col - (width - 1) / 2
    ymin = new_row - (height - 1) / 2
    xmax = xmin + width - 1
    ymax = ymin + height - 1

    return [xmin, ymin, xmax, ymax]


def relative_transfer(input_rect, from_rect, to_rect):
    """
    相对坐标变换公式
    :param input_rect: [x1, y1, x2, y2]
    :param from_rect: [x1, y1, x2, y2]
    :param to_rect: [x1, y1, x2, y2]
    :return: [x1, y1, x2, y2]
    """
    width_scale = (to_rect[2] - to_rect[0] + 1) / (from_rect[2] - from_rect[0] + 1)
    height_scale = (to_rect[3] - to_rect[1] + 1) / (from_rect[3] - from_rect[1] + 1)
    width = (input_rect[2] - input_rect[0] + 1) * width_scale
    height = (input_rect[3] - input_rect[1] + 1) * height_scale

    from_rect_row = (from_rect[1] + from_rect[3]) / 2
    from_rect_col = (from_rect[0] + from_rect[2]) / 2

    to_rect_row = (to_rect[1] + to_rect[3]) / 2
    to_rect_col = (to_rect[0] + to_rect[2]) / 2

    row = (input_rect[1] + input_rect[3]) / 2
    col = (input_rect[0] + input_rect[2]) / 2
    new_row = to_rect_row + (row - from_rect_row) * height_scale
    new_col = to_rect_col + (col - from_rect_col) * width_scale

    xmin = new_col - (width - 1) / 2
    ymin = new_row - (height - 1) / 2
    xmax = xmin + width - 1
    ymax = ymin + height - 1

    return [xmin, ymin, xmax, ymax]


def get_inner_rect(contour, width, height):
    """
    获取最大内接矩形，根据输入的轮廓
    :param contour:多边形的轮廓，只能是一维列表，也就是代表一个轮廓，
    cv2.findContours(dst, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE),一定要是cv2.CHAIN_APPROX_NONE
    :param width: 原始图像的宽
    :param height: 原始图像的高
    :return: 返回最大内接矩形
    """

    rect_frist = cv2.boundingRect(contour)
    rect = [
        rect_frist[0],
        rect_frist[1],
        rect_frist[0] + rect_frist[2],
        rect_frist[1] + rect_frist[3]
    ]
    x_sets = []
    y_sets = []
    for point in contour:
        x_sets.append(point[0, 0])
        y_sets.append(point[0, 1])

    def inside_point(rect, x_sets, y_sets, width, height):
        """
        递归函数，不断的优化最内点去获取最大内接矩形
        :param rect:
        :param x_sets:
        :param y_sets:
        :param width:
        :param height:
        :return:
        """

        left, top, right, bottom = rect
        inside_x_sets = []
        inside_y_sets = []
        weight = []

        for idx in range(len(x_sets)):
            if left < x_sets[idx] < right and top < y_sets[idx] < bottom:
                inside_x_sets.append(x_sets[idx])
                inside_y_sets.append(y_sets[idx])
                weight.append((x_sets[idx] / width - left / width) * (y_sets[idx] / height - top / height)
                              * (right / width - x_sets[idx] / width) * (bottom / height - y_sets[idx] / height))

        weight = np.asarray(weight)
        weight_index = np.argsort(weight)
        # 递归
        if len(inside_x_sets) != 0:
            point = [inside_x_sets[weight_index[-1]], inside_y_sets[weight_index[-1]]]
            rect = next_rect(rect, point)
            rect = inside_point(rect, inside_x_sets, inside_y_sets, width, height)
            return rect

        else:
            return rect

    def next_rect(rect, point):
        """
        根据内点去移动矩形的边获取下一个矩形
        :param rect:
        :param point:
        :return:
        """

        left, top, right, bottom = rect
        pts = np.array([[left, top], [right, top], [left, bottom], [right, bottom]], np.float32)
        point = np.asarray(point, dtype=np.float32)
        p_num = np.shape(pts)[0]
        dist = []

        for i in range(p_num):
            dist.append(np.linalg.norm(point - pts[i, :]))
        dist = np.asarray(dist, dtype=np.float32)
        dist_idx = np.argmin(dist)

        if dist_idx == 0:
            if (point[1] - top) * (right - left) < (point[0] - left) * (bottom - top):
                top = point[1]
            else:
                left = point[0]
        elif dist_idx == 1:
            if (point[1] - top) * (right - left) < (right - point[0]) * (bottom - top):
                top = point[1]
            else:
                right = point[0]
        elif dist_idx == 2:
            if (bottom - point[1]) * (right - left) < (point[0] - left) * (bottom - top):
                bottom = point[1]
            else:
                left = point[0]
        else:
            if (bottom - point[1]) * (right - left) < (right - point[0]) * (bottom - top):
                bottom = point[1]
            else:
                right = point[0]
        return [left, top, right, bottom]

    rect = inside_point(rect, x_sets, y_sets, width, height)
    return rect  # It's a list like->[left, top, right, bottom]


def find_similar_layout(templates_size, target_size):
    """
    寻找相似框架
    :param templates_size:
    :param target_size:
    :return:
    """

    def get_nearest_line(points, pt):
        """
        计算输入点集points与点pt最近的线段
        :param points: 已知输入点集
        :param pt: 目标点
        :return: 与点pt最近线段的索引
        """
        lines = {}
        for i in range(len(points) - 1):
            for j in range(i + 1, len(points)):
                a = np.array([points[j][0] - pt[0], points[j][1] - pt[1]])
                b = np.array([points[j][0] - points[i][0], points[j][1] - points[i][1]])
                if b.dot(b) == 0:
                    continue
                temp = float(a.dot(b)) / b.dot(b)
                c = b.dot(temp)

                distance = np.sqrt((a - c).dot((a - c)))
                lines[distance] = (i, j)

        d = min(lines.keys())
        i, j = lines[d]

        return i, j

    def get_distance(points, pt):
        """
        计算点pt与输入点集的距离
        :param points: 已知输入点集
        :param pt: 目标点
        :return: 目标点与输入点集的距离（复数）
        """
        distances = []
        for x, y in points:
            distances.append(((x - pt[0]) ** 2 + (y - pt[1]) ** 2) ** 0.5)

        return distances

    select_indexes = []
    print("输入框架个数：", len(templates_size))
    if len(templates_size) >= 4:
        points = np.array(templates_size)
        triangulation = Delaunay(points)
        tri = triangulation.simplices  # 每个三角面所包含的坐标点

        # 画图
        # plt.scatter(points[:, 0], points[:, 1], color='g')
        # plt.triplot(points[:, 0], points[:, 1], tri, linewidth=1.5)
        # plt.scatter(target_size[0], target_size[1], color='r')
        # plt.show()

        p = triangulation.find_simplex(target_size)
        indexes = tri[p]
        if p != -1:
            for i in indexes:
                distance_x = abs(templates_size[i][0] - target_size[0])
                distance_y = abs(templates_size[i][1] - target_size[1])
                alpha = math.atan2(distance_y, distance_x) * 180 / math.pi
                if alpha > 45:
                    continue
                select_indexes.append(i)

    if len(select_indexes) == 0:
        if len(templates_size) > 1:
            m, n = get_nearest_line(templates_size, target_size)
            if (target_size[0] - templates_size[m][0]) * (target_size[0] - templates_size[n][0]) < 0:
                select_indexes.append(m)
                select_indexes.append(n)
            else:
                distances = get_distance(templates_size, target_size)
                min_index = distances.index(min(distances))
                select_indexes.append(min_index)
        elif len(templates_size) == 1:
            select_indexes.append(0)

    return select_indexes


if __name__ == "__main__":
    pass
