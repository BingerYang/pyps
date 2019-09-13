# -*- coding: utf-8 -*- 
# @Time     : 2019-08-20 09:59
# @Author   : binger
from copy import deepcopy
from PIL import ImageFont, ImageDraw, Image
from pyps.layer import img, position
from pyps.layer import constant as Align
from pyps.replace import AutoAlign, LineAutoAlign
from pyps.layer.multi import having_bind_relationship, load_background_pil, get_alignment_type
from pyps.layer.font_paste import FontPaste
from pyps.layer import constant


class TextBase(object):
    def __init__(self, layer, bg_pil, edge_area, request_same_font=False):
        """

        :param layer:
        :param bg_pil:
        """
        self.bg_pil = bg_pil
        self.layer = layer
        self.rect_info = layer.rect_info
        self._limit_mini_font = 12
        self._edge_area = edge_area
        self._have_overlay = False
        self.request_same_font = request_same_font

    def move_single_y_to_safe_area(self, rect, is_up=True):
        """
        对一个区域，向上下移动，找到安全的区域（区域不突变）
        :param rect:
        :param is_up:
        :return:
        """
        while True:
            is_similar_area = img.judge_similar_area(self.bg_pil, *rect)
            if not is_similar_area:
                if is_up:
                    rect[1] -= 2
                    rect[3] -= 2
                else:
                    rect[1] += 2
                    rect[3] += 2
            else:
                break
        return rect

    def move_double_y_to_safe_area(self, rect, height):
        rect1 = deepcopy(rect)
        rect2 = deepcopy(rect)
        rect1[1], rect1[3] = LineAutoAlign(limit=(self.layer.core.ymin, self.layer.core.ymax)).run(length=height,
                                                                                                   align=0)
        rect2[1], rect2[3] = LineAutoAlign(limit=(self.layer.core.ymin, self.layer.core.ymax)).run(length=height,
                                                                                                   align=1)
        while True:
            is_similar_area1 = img.judge_similar_area(self.bg_pil, *rect1)
            is_similar_area2 = img.judge_similar_area(self.bg_pil, *rect2)
            if not is_similar_area1 and not is_similar_area2:
                rect1[1] += 2
                rect1[3] += 2
                rect2[1] -= 2
                rect2[3] -= 2
            else:
                if is_similar_area1 and is_similar_area2:
                    rect[1] = (rect1[1] + rect2[1]) // 2
                    rect[3] = (rect2[3] + rect2[3]) // 2
                elif is_similar_area1:
                    rect[1] = rect1[1]
                    rect[3] = rect1[3]
                else:
                    rect[1] = rect2[1]
                    rect[3] = rect2[3]
                break
        return rect

    def resize_x_to_largest_area(self, rect, align: int):
        """
        按照对齐方法获取横向最大可扩展区域
        :param rect: rect = [0, 1, 2, 3]
        :param align: 对齐方式：0, 1, 2
        :return:
        """
        while True:
            # 在最大范围（bg_pil的范围）时为 False
            is_similar_area = img.judge_similar_area(self.bg_pil, *rect)
            if is_similar_area:
                if align == Align.ALIGN_LEFT:  # 做对齐
                    xmax = rect[2] + 2
                    if xmax > self.bg_pil.size[0] - 1:
                        break
                    rect[2] = xmax
                elif align == Align.ALIGN_CENTER:
                    xmin, xmax = rect[0] - 2, rect[2] + 2
                    if xmin < 0 or xmax > self.bg_pil.size[0] - 1:
                        break
                    rect[0] = xmin
                    rect[2] = xmax
                else:
                    xmin = rect[0] - 2
                    if xmin < 0:
                        rect[0] = xmin
            else:
                rect[0] = max(rect[0], 0)
                rect[2] = min(rect[2], self.bg_pil.size[0] - 1)
                break
        return rect

    @staticmethod
    def get_front_interval(draw, height, font_type_path, font_size, text, row):
        my_font = ImageFont.truetype(font_type_path, font_size)
        text_size = draw.textsize(text, font=my_font)
        return max((height - row * text_size[1]) / (row * 2), 0), text_size

    def _get_resize_front_by_font(self, draw, rect, text, row, font_type_path, start_front_size, min_fornt_size=12,
                                  align=Align.ALIGN_CENTER,
                                  have_overlay=False, have_in_edge=True):

        l_height = rect[3] - rect[1]
        l_width = rect[2] - rect[0]
        while True:
            # 获取字体信息，宽高，间距
            y_offset, text_size = self.get_front_interval(draw, l_height, font_type_path, start_front_size, text, row)
            # # 防止字体的高比每行框的高大，做字体减小分支判断
            # 防止字体占的行宽度大于主元素所在框的宽，首先合理扩张框的宽度，如果还不满足情况，则缩小字体的大小

            # ratio = y_offset / (y_offset + text_size[1])

            if text_size[1] > l_height / row or text_size[0] > l_width:
                if start_front_size > min_fornt_size:
                    start_front_size -= 1
                    continue

            # 判断字体是否超出安全范围，是否压其他之类的
            rect_limit = [rect[0], rect[1] + y_offset, rect[2], rect[3] + y_offset]
            cur_rect = AutoAlign(area=rect_limit, rect_size=text_size, align=(Align.ALIGN_UP, align)).run()
            if not have_overlay:
                if img.judge_similar_area(self.bg_pil, *cur_rect):
                    break
            if have_in_edge:
                if position.is_inclusion_relation(cur_rect, self._edge_area):
                    break

            if start_front_size > min_fornt_size:
                start_front_size -= 1
                continue

            break
        return y_offset, text_size, start_front_size

    def write_text(self, rect, text_list, font_type_path, font_size, align):
        text_list = [text.strip("\r") for text in text_list]
        temp = Image.new('RGBA', self.bg_pil.size,
                         (self.layer.core.color[1], self.layer.core.color[2], self.layer.core.color[3], 0))
        draw = ImageDraw.Draw(temp)

        if self.request_same_font:
            interval, text_size = self.get_front_interval(draw, rect[3] - rect[1] + 1, font_type_path, font_size,
                                                          text_list[0], len(text_list))
        else:
            from functools import reduce
            from operator import itemgetter

            def get_len(text):
                return reduce(lambda len, v: len + (1 if v.isascii() else 2), text, 0)

            info = {text: get_len(text) for text in text_list}
            max_text = max(info.items(), key=itemgetter(1))[0]

            interval, text_size, font_size = self._get_resize_front_by_font(draw, rect, max_text, len(text_list),
                                                                            font_type_path, font_size,
                                                                            align=align, have_in_edge=True,
                                                                            have_overlay=self._have_overlay)

        y_min = rect[1] + interval
        for i, text in enumerate(text_list):
            font_mode = {
                "size": font_size,  # 字号
                "ttf": font_type_path,  # 字体文件
                "color": (
                    self.layer.core.color[1], self.layer.core.color[2], self.layer.core.color[3],
                    self.layer.core.color[0]),
                "position": (rect[0], y_min),
                "frame": self.bg_pil.size}
            y_min = text_size[1] + 2 * interval
            FontPaste.write_text(temp, font_mode, text)

        rect[2] = rect[0] + text_size[0] - 1
        pil = temp.crop(rect)
        self.layer.replace_pil(pil, is_center_align=True)
        # self.layer.replace_pil_at_rect(pil, xmin=rect[0], ymin=rect[1])
        self.layer.core.fontSize = font_size
        self.layer.core.text = "\r".join(text_list)

        return


class Text(TextBase):
    def __init__(self, layer, psd_cluster, edge_area, request_same_font=False):
        self.layer = layer
        self.psd_cluster = psd_cluster
        self.cluster = psd_cluster.load_cluster_by_layer(name=layer.core.name)
        # self.bg_pil = get_title_background(layer, self.psd_cluster.layers, *self.psd_cluster.size)  # 获取背景画布（带新思路优化）
        self.bg_pil = self.load_background()  # 获取背景画布（带新思路优化）
        super(Text, self).__init__(layer, self.bg_pil, edge_area, request_same_font=request_same_font)

    def load_background(self):
        if self.cluster:
            layers = self.cluster["layers"]
            if self.cluster["type"] == constant.TYPE_RELATION:
                layers.append(self.cluster["layer"])
        else:
            layers = self.psd_cluster.psd_layers
        return load_background_pil(self.layer, layers, self.psd_cluster.size)

    def load_y_align_with_other(self, cluster, row):
        y_one_line = self.layer.height / row  # 原始图层的文字的行高

        align = 1  # 0，1, 2  在y方向上
        if cluster:
            for l in cluster["layers"]:
                # 同一组，文本相近
                if l is not self.layer and l.core.type == 'text' \
                        and having_bind_relationship(self.layer.rect, l.rect, direct=1, iou=0.8):
                    if l.core.ymin < self.layer.core.ymin <= l.core.ymax + 2 * y_one_line:
                        align = 0
                    elif l.core.ymin - 2 * y_one_line < self.layer.core.ymax < l.core.ymax:
                        align = 2
        return align

    def replace(self, replace_element):
        src_text_list = [text for text in self.layer.core.text.split("\r") if not text == ""]  # ps中 \r 换行

        text_list = replace_element.info["text"].split("\n")

        # 获得对齐关系 align
        # 新替换的图层，与原有图层的对齐替换关系
        replace_by_align = self.load_y_align_with_other(self.cluster, row=len(text_list))
        # 根据对齐扩展或者缩小区域
        # align: 0, 1, 2
        new_temp_height = self.layer.height * (len(text_list) / len(src_text_list))
        # cur_rect = AutoAlign(area=rect_limit, rect_size=text_size, align=(Align.ALIGN_UP, align)).run()

        if replace_by_align != Align.ALIGN_CENTER:
            ymin, ymax = LineAutoAlign(limit=(self.layer.core.ymin, self.layer.core.ymax)).run(length=new_temp_height,
                                                                                               align=replace_by_align)
            rect = [self.layer.core.xmin, ymin, self.layer.core.xmax, self.layer.core.ymax]
            rect = self.move_single_y_to_safe_area(rect, is_up=not replace_by_align)
        else:
            rect = deepcopy(self.layer.rect)
            rect = self.move_double_y_to_safe_area(rect, height=new_temp_height)

        if self.cluster:
            align = get_alignment_type(self.cluster["layers"])
        else:
            align = constant.ALIGN_CENTER
        # 通过字体文本，获取安全的区域和字体大小（是否允许字体缩小 self.request_same_font）
        self.resize_x_to_largest_area(rect, align)

        # 替换
        text_list = replace_element.info["text"].split("\n")
        font_type_path = replace_element.path
        font_size = replace_element.info["FontSize"]
        self.write_text(rect, text_list=text_list, font_type_path=font_type_path, font_size=font_size,
                        align=align)


if __name__ == "__main__":
    pass
