"""
#!/usr/bin/env python
# -*- coding:utf-8 -*-
@Project : crawl_ip
@File : test.py
@Author : 帅张张
@Time : 2025/3/22 17:10

"""

import cv2
import os
import numpy as np

def crop_and_save_image(image_path, x, y, width, height, output_path=None):
    """
    简单地截取图片中的矩形区域并保存，不做任何处理
    
    参数:
        image_path: 输入图片路径
        x, y: 左上角坐标
        width, height: 宽度和高度
        output_path: 输出图片路径，如果为None则自动生成
        
    返回:
        输出图片路径
    """
    # 读取原图 (完整读取，包括透明通道)
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"无法加载图片: {image_path}")
        return None
    
    # 检查坐标是否有效
    img_height, img_width = img.shape[:2]
    if x < 0 or y < 0 or x + width > img_width or y + height > img_height:
        print(f"错误: 截取区域超出图片范围! 图片尺寸: {img_width}x{img_height}")
        return None
    
    # 直接截取区域，不做任何处理
    cropped = img[y:y+height, x:x+width].copy()
    
    # 确定输出路径
    if output_path is None:
        dir_name = os.path.dirname(image_path)
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        ext = os.path.splitext(image_path)[1]  # 保持原扩展名
        output_path = os.path.join(dir_name, f"{base_name}_cropped{ext}")
    
    # 保存图片，完全按照原始格式
    cv2.imwrite(output_path, cropped)
    
    print(f"截取的图片已保存到: {output_path}")
    print(f"截取区域: 左上角({x},{y}), 尺寸 {width}x{height}")
    return output_path

def simple_crop_test():
    """简单截图测试"""
    # 提示用户输入图片路径
    image_path = input("请输入图片路径: ")
    
    if not os.path.exists(image_path):
        print(f"文件不存在: {image_path}")
        return
    
    # 加载图片获取尺寸
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"无法加载图片: {image_path}")
        return
    
    img_height, img_width = img.shape[:2]
    print(f"图片尺寸: {img_width}x{img_height} (宽x高)")
    
    # 让用户输入矩形区域
    print("\n请输入要截取的矩形区域坐标:")
    
    try:
        x = float(input("X坐标(左上角): "))
        y = float(input("Y坐标(左上角): "))
        width = float(input("宽度: "))
        height = float(input("高度: "))
    except ValueError:
        print("错误: 请输入有效的整数数值")
        return
    
    # 截取并保存图片
    output_path = crop_and_save_image(image_path, x, y, width, height)
    
    # 验证截图是否成功
    if output_path and os.path.exists(output_path):
        print(f"截取成功! 图片已保存到: {output_path}")
    else:
        print("截取失败")

if __name__ == "__main__":
    print("\n===== 简单图片区域截取工具 =====\n")
    simple_crop_test()

