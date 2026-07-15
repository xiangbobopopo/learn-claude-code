#!/usr/bin/env python3
"""
oci_image_analysis_lib 的测试用例
===============================
使用合成图片测试 4 种分割算法（不包含 Gemini 标注）。
"""

import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from oci_image_analysis_lib import (
    Region,
    segment_by_color_clustering,
    segment_by_edge_contour,
    segment_by_hsv_threshold,
    segment_by_watershed,
    analyze_image,
    draw_regions,
)


# ── 辅助函数：创建合成测试图片 ──────────────────────


def make_solid_color_image(size: int, color_bgr: tuple) -> np.ndarray:
    """创建纯色图片。"""
    img = np.zeros((size, size, 3), dtype=np.uint8)
    img[:] = color_bgr
    return img


def make_two_color_image(size: int = 200) -> np.ndarray:
    """创建左右两半不同颜色的图片：左蓝(0) 右绿(0,255,0)。"""
    img = np.zeros((size, size, 3), dtype=np.uint8)
    img[:, :size//2] = (255, 0, 0)    # 左半：蓝色 BGR
    img[:, size//2:] = (0, 255, 0)    # 右半：绿色 BGR
    return img


def make_three_rectangle_image(size: int = 300) -> np.ndarray:
    """创建包含三个彩色矩形的图片。"""
    img = np.zeros((size, size, 3), dtype=np.uint8)
    img[:] = (200, 200, 200)  # 灰色背景

    # 红色矩形 (左上)
    cv2.rectangle(img, (20, 20), (120, 120), (0, 0, 255), -1)
    # 蓝色矩形 (右上)
    cv2.rectangle(img, (180, 20), (280, 120), (255, 0, 0), -1)
    # 绿色矩形 (底部)
    cv2.rectangle(img, (80, 180), (220, 280), (0, 255, 0), -1)

    return img


def save_temp_image(img: np.ndarray, suffix: str = ".png") -> str:
    """将 numpy 图片保存为临时文件，返回路径。"""
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    cv2.imwrite(tmp.name, img)
    return tmp.name


# ── 测试 Region 数据结构 ────────────────────────────


class TestRegion:
    def test_region_creation(self):
        r = Region(
            label="test",
            area_px=1000,
            area_pct=50.0,
            bbox=(10, 20, 100, 200),
            color_bgr=(128, 64, 32),
        )
        assert r.label == "test"
        assert r.area_px == 1000
        assert r.area_pct == 50.0
        assert r.bbox == (10, 20, 100, 200)

    def test_region_summary(self):
        r = Region("sky", 5000, 25.5, (0, 0, 100, 50), (120, 200, 80))
        summary = r.summary
        assert "sky" in summary
        assert "5000" in summary
        assert "25.5" in summary


# ── 测试 clustering 分割 ─────────────────────────────


class TestColorClustering:
    def test_two_colors(self):
        img = make_two_color_image(200)
        regions = segment_by_color_clustering(img, n_clusters=2, min_area_ratio=0.1)

        assert len(regions) == 2, f"期望 2 个区域，实际 {len(regions)}"
        a1, a2 = regions[0].area_px, regions[1].area_px
        total = 200 * 200
        # 两个区域面积应该大致相等（各约一半）
        assert abs(a1 - total // 2) < total * 0.05
        assert abs(a2 - total // 2) < total * 0.05
        assert abs(a1 + a2 - total) < 100

    def test_single_color(self):
        img = make_solid_color_image(100, (128, 64, 32))
        regions = segment_by_color_clustering(img, n_clusters=3, min_area_ratio=0.05)

        assert len(regions) >= 1
        # 纯色图，K-Means 可能分 1 个主要区域
        assert regions[0].area_px == 10000

    def test_three_rectangles(self):
        img = make_three_rectangle_image(300)
        regions = segment_by_color_clustering(img, n_clusters=4, min_area_ratio=0.02)

        # 3 个矩形 + 背景，至少 3 个区域
        assert len(regions) >= 3
        total = sum(r.area_px for r in regions)
        assert 25000 < total <= 90000  # 应该有合理的总像素

    def test_min_area_filter(self):
        img = make_two_color_image(200)
        # 高阈值 → 可能只保留 1 个区域
        regions = segment_by_color_clustering(img, n_clusters=2, min_area_ratio=0.6)
        assert len(regions) <= 1


# ── 测试 edge 分割 ──────────────────────────────────


class TestEdgeContour:
    def test_three_rectangles(self):
        img = make_three_rectangle_image(300)
        regions = segment_by_edge_contour(img, min_contour_area_ratio=0.02)

        assert len(regions) >= 2, f"期望至少 2 个轮廓，实际 {len(regions)}"
        for r in regions:
            assert r.area_px > 0
            assert 0 <= r.area_pct <= 100

    def test_empty_for_solid_color(self):
        """纯色图片 → Canny 边缘检测几乎找不到边缘。"""
        img = make_solid_color_image(200, (100, 150, 200))
        regions = segment_by_edge_contour(img)
        # 纯色图边缘极少，可能没有足够大的轮廓
        assert isinstance(regions, list)

    def test_canny_params_affect_result(self):
        img = make_three_rectangle_image(300)
        # 低阈值 → 更多边缘
        r_low = segment_by_edge_contour(img, canny_thresh1=10, canny_thresh2=50)
        # 高阈值 → 更少边缘
        r_high = segment_by_edge_contour(img, canny_thresh1=200, canny_thresh2=255)
        assert len(r_low) >= len(r_high)


# ── 测试 HSV 分割 ───────────────────────────────────


class TestHSVThreshold:
    def test_detect_red(self):
        """红色矩形图片应被 hsv 检测到。"""
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        cv2.rectangle(img, (50, 50), (150, 150), (0, 0, 255), -1)  # BGR red

        red_range = [{"name": "Red", "lower": [0, 50, 50], "upper": [10, 255, 255]}]
        regions = segment_by_hsv_threshold(img, color_ranges=red_range, min_area_ratio=0.01)

        assert len(regions) >= 1
        assert "Red" in [r.label for r in regions]
        # 红色方块 100x100 = 10000 px
        red = [r for r in regions if r.label == "Red"][0]
        assert 8000 <= red.area_px <= 12000

    def test_detect_blue(self):
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        cv2.rectangle(img, (30, 30), (170, 170), (255, 0, 0), -1)  # BGR blue

        blue_range = [{"name": "Blue", "lower": [100, 50, 50], "upper": [130, 255, 255]}]
        regions = segment_by_hsv_threshold(img, color_ranges=blue_range)

        assert len(regions) >= 1
        blue = [r for r in regions if r.label == "Blue"][0]
        assert blue.area_px > 10000

    def test_default_ranges(self):
        """使用默认颜色范围应返回结果（不乱报错）。"""
        img = make_three_rectangle_image(300)
        regions = segment_by_hsv_threshold(img)
        assert isinstance(regions, list)
        # 默认范围可能匹配也可能不匹配，但只要不抛异常就行


# ── 测试 watershed 分割 ─────────────────────────────


class TestWatershed:
    def test_disjoint_rectangles(self):
        """三个分离的矩形应被分水岭识别为不同物体。"""
        img = make_three_rectangle_image(300)
        regions = segment_by_watershed(img, min_area_ratio=0.01)

        assert len(regions) >= 2, f"期望至少 2 个物体，实际 {len(regions)}"
        for r in regions:
            assert r.area_px > 0


# ── 测试 analyze_image 主函数 ───────────────────────


class TestAnalyzeImage:
    def test_clustering_method(self):
        img = make_two_color_image(200)
        path = save_temp_image(img)

        try:
            regions = analyze_image(image_path=path, method="clustering", clusters=2)
            assert len(regions) == 2
        finally:
            Path(path).unlink(missing_ok=True)

    def test_edge_method(self):
        img = make_three_rectangle_image(300)
        path = save_temp_image(img)

        try:
            regions = analyze_image(image_path=path, method="edge")
            assert len(regions) >= 1
        finally:
            Path(path).unlink(missing_ok=True)

    def test_hsv_method(self):
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        cv2.rectangle(img, (50, 50), (150, 150), (0, 0, 255), -1)  # red
        path = save_temp_image(img)

        try:
            regions = analyze_image(image_path=path, method="hsv")
            assert len(regions) >= 1
        finally:
            Path(path).unlink(missing_ok=True)

    def test_watershed_method(self):
        img = make_three_rectangle_image(300)
        path = save_temp_image(img)

        try:
            regions = analyze_image(image_path=path, method="watershed")
            assert len(regions) >= 1
        finally:
            Path(path).unlink(missing_ok=True)

    def test_save_output(self):
        img = make_two_color_image(200)
        path = save_temp_image(img)
        out_path = tempfile.mktemp(suffix=".jpg")

        try:
            regions = analyze_image(image_path=path, method="clustering", clusters=2, save=out_path)
            assert Path(out_path).exists()
            assert len(regions) == 2
        finally:
            Path(path).unlink(missing_ok=True)
            Path(out_path).unlink(missing_ok=True)

    def test_invalid_image_path(self):
        with pytest.raises(FileNotFoundError):
            analyze_image(image_path="/nonexistent/path.jpg")

    def test_invalid_method(self):
        img = make_two_color_image(200)
        path = save_temp_image(img)
        try:
            with pytest.raises(ValueError, match="未知分割方法"):
                analyze_image(image_path=path, method="invalid_method")
        finally:
            Path(path).unlink(missing_ok=True)


# ── 测试可视化 ──────────────────────────────────────


class TestDrawRegions:
    def test_draw_and_save(self):
        img = make_three_rectangle_image(300)
        regions = segment_by_color_clustering(img, n_clusters=4)
        out_path = tempfile.mktemp(suffix=".jpg")

        try:
            result = draw_regions(img, regions, save_path=out_path)
            assert result.shape == img.shape
            assert Path(out_path).exists()
        finally:
            Path(out_path).unlink(missing_ok=True)

    def test_draw_no_labels(self):
        img = make_two_color_image(200)
        regions = segment_by_color_clustering(img, n_clusters=2)
        result = draw_regions(img, regions, show_labels=False)
        assert result.shape == img.shape


# ── 运行入口 ────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
