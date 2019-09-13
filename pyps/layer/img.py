# -*- coding: utf-8 -*- 
# @Time     : 2019-07-30 17:52
# @Author   : binger

"""
实现图层中图像的变换
"""
from PIL import Image
import numpy as np
import cv2
from pyps.algorithm.transfer import get_inner_rect
from pyps.layer.position import resize_by_rate_to_target


def judge_similar_area(im, x1, y1, x2, y2):
    """
    判断区域(x1, y1, x2, y2)是否相似（是否轮廓突变，边界为轮廓突变）
    :param im: 背景图片
    :param x1:  区域起始列
    :param y1:  区域起始行
    :param x2:  区域结束列
    :param y2:  区域结束行
    :return:    True:该区域为空白区域, False:该区域非空白区域
    """

    img = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGBA2BGRA)
    height, width = img.shape[0], img.shape[1]
    if x1 < 0 or y1 < 0 or x2 > width - 1 or y2 > height - 1 or x1 > x2 or y1 > y2:
        # 是否超出im范围
        return False

    crop = img[int(y1):int(y2), int(x1):int(x2)]
    crop = cv2.Canny(crop, 100, 200)  # 检查阈值边缘差距
    contours, _ = cv2.findContours(crop, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours) > 0:
        return False
    return True


def layer_mask(im, up=0.82, down=0.98):
    """
    :param im:
    :param width:
    :param height:
    :return:
    """
    if im.mode != 'RGBA':
        return im
    w, h = im.size
    s_row, e_row = int(h * up), int(h * down)
    theta = np.pi / (e_row - s_row)
    image = np.asarray(im, np.float32)
    for i in range(s_row, e_row):
        for j in range(0, w):
            image[i, j, 3] *= ((np.cos(theta * (i - s_row)) + 1) / 2)

    for i in range(e_row, h):
        for j in range(0, w):
            if image[i, j, 3] > 0:
                image[i, j, 3] = 0

    image = np.asarray(image, np.uint8)
    image = Image.fromarray(image)

    return image


def get_outer_rect(im):
    """
    获取元素内容外接矩形
    :param im: 图形信息
    :return: 外接矩形相对图形的 xmin，ymin 和 长宽
    """
    img = im.copy()
    x, y, w, h = 0, 0, img.size[0], img.size[1]
    if img.mode != "RGBA":
        return x, y, w, h

    img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGBA2BGRA)
    img = cv2.split(img)
    point = np.argwhere(img[3] > 255 * 0.05)
    if point.size > 0:
        y, x, h, w = cv2.boundingRect(point)

    return x, y, w, h


def crop_blank_region(im):
    """
    获取最大内接矩形区域并删除最大内接矩形区域中的孔洞
    :param im: RGBA图片，[height,width,channels] np.ndarray
    :return: 裁剪处理后的图片并返回
    """
    if im.mode != "RGBA":
        return im

    img = np.asarray(im)
    img1 = cv2.split(img)
    ret, dst = cv2.threshold(img1[3], 1, 255, cv2.THRESH_BINARY)
    contours, hierarchy = cv2.findContours(dst, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    rect_area = []

    # 获取最大的轮廓区域用于搜索最大内接矩形
    for contour in contours:
        rect = cv2.boundingRect(contour)
        area = rect[2] * rect[3]
        rect_area.append(area)
    rect_area = np.asarray(rect_area)
    bigindex = np.argmax(rect_area)
    contour = contours[bigindex]
    height, width = np.shape(dst)
    del contours[bigindex]

    # 获取最大内接矩形
    rect = get_inner_rect(contour, width, height)
    left, top, right, bottom = rect

    # 删除最大内接矩形以外的轮廓点
    for ct_index in range(len(contours) - 1, -1, -1):
        contour = contours[ct_index]
        length = np.shape(contour)[0]
        for index in range(length - 1, -1, -1):
            if contour[index, 0, 0] < left or contour[index, 0, 0] > right \
                    or contour[index, 0, 1] < top or contour[index, 0, 1] > bottom:
                contours[ct_index] = np.delete(contours[ct_index], [index], axis=0)

            else:
                contours[ct_index][index, 0, 0] -= left
                contours[ct_index][index, 0, 1] -= top

        if np.shape(contour)[0] == 0:
            del contours[ct_index]

    # 深拷贝内接矩形切片区域
    image_crop = img[int(top):int(bottom + 1), int(left):int(right) + 1]

    left, top, right, bottom = -1, -1, -1, -1
    # 根据外接矩形去删除孔洞
    for contour in contours:
        if left != -1:
            # 判断上一次是删除的是若干个像素列还是像素列
            if right - left < bottom - top:
                # 如果上一次删除的像素点包含了此次等待删除孔洞的轮廓点，则删除该轮廓点
                for index in range(np.shape(contour)[0] - 1, -1, -1):
                    if left < contour[index, 0, 0] < right:
                        contour = np.delete(contour, index, axis=0)
                    elif contour[index, 0, 0] > right:
                        contour[index, 0, 0] -= right - left

            else:
                # 如果上一次删除的像素点包含了此次等待删除孔洞的轮廓点，则删除该轮廓点
                for index in range(np.shape(contour)[0] - 1, -1, -1):
                    if top < contour[index, 0, 1] < bottom:
                        contour = np.delete(contour, index, axis=0)
                    elif contour[index, 0, 1] > right:
                        contour[index, 0, 1] -= right - left

        # 可能与上次删除的行或列恰好重合，那么可能被删除到不剩任何元素
        if np.shape(contour)[0] == 0:
            continue
        rect = cv2.boundingRect(contour)

        left = rect[0]
        top = rect[1]
        right = rect[0] + rect[2]
        bottom = rect[1] + rect[3]
        # 矩形的宽大于高，就删除矩形高所在行的像素行，反之删除矩形宽所在列的像素列
        if rect[2] > rect[3]:
            delete_list = [i for i in range(right, left - 1, -1)]
            image_crop = np.delete(image_crop, delete_list, axis=1)
        else:
            delete_list = [i for i in range(bottom, top - 1, -1)]
            image_crop = np.delete(image_crop, delete_list, axis=0)

    image_crop = Image.fromarray(image_crop)
    return image_crop


def cut_nonzero(im):
    """
    处理图层图像，裁剪空白区域，保留最小凸包
    :param im:
    :return:
    """
    if im.mode != 'RGBA':
        return im, (0, 0, im.width - 1, im.height - 1)
    crop = np.asarray(im)
    x = np.nonzero(crop[:, :, 3])
    c_min = min(x[1])
    c_max = max(x[1])
    r_min = min(x[0])
    r_max = max(x[0])
    crop = im.crop((c_min, r_min, c_max + 1, r_max + 1))
    return crop, (c_min, r_min, c_max, r_max)


def layer_paste(im, template, xmin=0, ymin=0):
    """
    背景图或者切片
    :param im: 待处理的 image
    :param template: 从 template 拷贝
    :param xmin: 从 template 所在图层的横坐标开始拷贝
    :param ymin: 从 template 所在图层的纵坐标开始拷贝
    :return:
    """
    width, height = im.size
    w, h = template.size
    xmin, ymin = int(xmin), int(ymin)

    cut_x = max(0, -xmin)
    cut_y = max(0, -ymin)
    cut_w = min(w, width - xmin)
    cut_h = min(h, height - ymin)  # 针对 src大的时候，

    crop = template.crop((cut_x, cut_y, cut_w, cut_h))
    # 必须将透明层覆盖到不透明层才会显示上面图层透明
    dst = Image.new('RGBA', im.size, (255, 255, 255, 0))
    dst.paste(crop, (max(0, xmin), max(0, ymin)))
    dst = Image.alpha_composite(im, dst)
    return dst


def resize_by_target(im, target_size: tuple, use_small=True):
    """
    定宽或者定高
    :param im:
    :param target_size:
    :param use_small:
    :return:
    """
    dim = resize_by_rate_to_target(im.size, target_size, use_small)
    return im.resize(dim, Image.BICUBIC)


def resize_to_width_or_height(img, to_width=None, to_height=None):
    """
    扩展到定宽或者定高
    :param img:
    :param to_width:
    :param to_height:
    :return:
    """
    if to_width is None and to_height is None:
        return img

    w, h = img.size
    if to_width is None:
        r = to_height / float(h)
        dim = (max(int(w * r), 1), max(int(to_height), 1))
    else:
        r = to_width / float(w)
        dim = (max(int(to_width), 1), max(int(h * r), 1))
    return img.resize(dim, Image.BICUBIC)


if __name__ == "__main__":
    pass
