#!/usr/bin/python
# -*- coding: UTF-8 -*-
# Author:Cash
# 功能包： 替换字体
# Date:2019-01-03


from PIL import ImageDraw, ImageFont


class FontPaste:

    @classmethod
    def write_line(cls, image, font_mode, text, cnt):
        '''
        图片写字
        :param img:
        :param text:
        :param cnt:
        :return:
        '''

        my_font = ImageFont.truetype(font_mode["ttf"], font_mode["size"])
        draw = ImageDraw.Draw(image)
        # 文本长度
        tend = len(text)
        x_pos = font_mode["position"][0]
        y_pos = font_mode["position"][1] + cnt * font_mode["size"]
        while True:
            # 文本图层的尺寸
            text_size = draw.textsize(text[:tend], font=my_font)
            if text_size[0] < font_mode["frame"][0] - x_pos or text_size[0] == 0:
                break
            else:
                # 文本太长，调整文本长度
                tend -= 1

        txt = text[:tend]
        draw.text((x_pos, y_pos), txt, font=my_font, fill=font_mode['color'])

        return image, tend

    @classmethod
    def write_text(cls, image, font_mode, text):
        '''
        写文本
        :param text:
        :return:
        '''

        txt_list = text.split("\n")
        t_begin = 0
        cnt = 0

        for t in txt_list:
            while True:
                img, t_end = FontPaste.write_line(image, font_mode, t, cnt)
                if t_end == 0:
                    break
                else:
                    t = t[t_end:]
                    t_begin = t_begin + t_end
                    cnt += 1

        return img


