#!/usr/bin/env python3
"""
图片边界识别 & 像素面积计算工具
=================================
使用 OpenCV 进行精确的边界检测和面积计算（结果确定、可复现）。
可选集成 OCI Generative AI (Gemini) 对区域进行语义标注。

原理:
  - OpenCV 做分割和测量 → 结果每次一致（解决 LLM 波动问题）
  - Gemini 只用来给区域取名/分类（不是核心测量）

前置条件:
  pip install opencv-python numpy
  pip install oci>=2.130.0    (仅 --use-llm 时需要)

用法:
  # 纯 OpenCV 分割（最稳定）
  python oci_image_analysis.py --image photo.jpg

  # 使用 Gemini 辅助标注区域名称
  python oci_image_analysis.py --image photo.jpg --use-llm \
      --compartment-id ocid1.compartment.oc1... \
      --model-id google.gemini-2.5-pro
"""

import cv2
import numpy as np
import argparse
import logging
from dataclasses import dataclass, field
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ── 数据结构 ──────────────────────────────────────────


@dataclass
class Region:
    """单个分割区域的结果。"""
    label: str          # 区域名称（如 "天空", "草地" 或 "Region_1"）
    area_px: int        # 像素面积（像素个数）
    area_pct: float     # 占总面积的百分比
    bbox: tuple         # (x, y, w, h) 边界框
    color_bgr: tuple    # 平均颜色 (B, G, R)

    @property
    def summary(self) -> str:
        return (f"  {self.label:20s}  {self.area_px:>8} px  "
                f"({self.area_pct:>5.1f}%)  "
                f"bbox=({self.bbox[0]},{self.bbox[1]},{self.bbox[2]},{self.bbox[3]})  "
                f"avg_color=BGR{tuple(int(c) for c in self.color_bgr)}")


# ── 核心分割引擎 ──────────────────────────────────────


def segment_by_color_clustering(
    image: np.ndarray,
    n_clusters: int = 4,
    min_area_ratio: float = 0.02,
    blur_kernel: int = 9,
) -> list[Region]:
    """
    基于 K-Means 颜色聚类的分割。
    适合：颜色对比明显的图片（图表、地图、简单物体）。
    优点：稳定、速度快。
    """
    h, w = image.shape[:2]
    total_px = h * w

    # 降噪
    blurred = cv2.medianBlur(image, blur_kernel)

    # 转成 K-Means 需要的形状 (H*W, 3)
    pixels = blurred.reshape(-1, 3).astype(np.float32)

    # K-Means 聚类
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, labels, centers = cv2.kmeans(
        pixels, n_clusters, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS
    )

    # 重组为 mask
    label_map = labels.reshape(h, w)
    regions = []

    for cluster_id in range(n_clusters):
        mask = (label_map == cluster_id).astype(np.uint8) * 255
        area = int(np.sum(label_map == cluster_id))

        # 跳过太小的区域
        if area / total_px < min_area_ratio:
            continue

        # 找轮廓（用于边界框）
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        all_pts = np.vstack(contours)
        x, y, w_box, h_box = cv2.boundingRect(all_pts)

        # 平均颜色
        avg_color = tuple(centers[cluster_id].astype(int))

        regions.append(Region(
            label=f"Cluster_{cluster_id}",
            area_px=area,
            area_pct=area / total_px * 100,
            bbox=(x, y, w_box, h_box),
            color_bgr=avg_color,
        ))

    # 按面积降序排列
    regions.sort(key=lambda r: r.area_px, reverse=True)
    return regions


def segment_by_edge_contour(
    image: np.ndarray,
    min_contour_area_ratio: float = 0.01,
    canny_thresh1: int = 50,
    canny_thresh2: int = 150,
) -> list[Region]:
    """
    基于边缘检测 + 轮廓查找的分割。
    适合：形状边界清晰的图片（机械零件、建筑图纸）。
    注意：可能产生大量小轮廓，需过滤。
    """
    h, w = image.shape[:2]
    total_px = h * w

    # 转灰度
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Canny 边缘检测
    edges = cv2.Canny(blurred, canny_thresh1, canny_thresh2)

    # 形态学闭运算连接边缘
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    # 找轮廓
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    for i, cnt in enumerate(contours):
        area = cv2.contourArea(cnt)
        if area / total_px < min_contour_area_ratio:
            continue

        x, y, w_box, h_box = cv2.boundingRect(cnt)
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.drawContours(mask, [cnt], -1, 255, -1)

        # 平均颜色
        mean_color = cv2.mean(image, mask)[:3]

        regions.append(Region(
            label=f"Contour_{i}",
            area_px=int(area),
            area_pct=area / total_px * 100,
            bbox=(x, y, w_box, h_box),
            color_bgr=tuple(int(c) for c in mean_color),
        ))

    regions.sort(key=lambda r: r.area_px, reverse=True)
    return regions


def segment_by_hsv_threshold(
    image: np.ndarray,
    color_ranges: Optional[list[dict]] = None,
    min_area_ratio: float = 0.01,
) -> list[Region]:
    """
    基于 HSV 颜色阈值的手动分割。
    适合：已知目标颜色的场景（如红色区域、蓝色区域）。
    可通过 --color-ranges 传入自定义颜色范围。
    """
    h, w = image.shape[:2]
    total_px = h * w

    if color_ranges is None:
        # 预设常用颜色范围（HSV 空间）
        color_ranges = [
            {"name": "Red",    "lower": [0, 50, 50],   "upper": [10, 255, 255]},
            {"name": "Red_2",  "lower": [170, 50, 50],  "upper": [180, 255, 255]},
            {"name": "Blue",   "lower": [100, 50, 50],  "upper": [130, 255, 255]},
            {"name": "Green",  "lower": [40, 50, 50],   "upper": [80, 255, 255]},
            {"name": "Yellow", "lower": [20, 50, 50],   "upper": [35, 255, 255]},
            {"name": "White",  "lower": [0, 0, 200],    "upper": [180, 30, 255]},
            {"name": "Black",  "lower": [0, 0, 0],      "upper": [180, 255, 50]},
        ]

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    regions = []

    for cfg in color_ranges:
        lower = np.array(cfg["lower"], dtype=np.uint8)
        upper = np.array(cfg["upper"], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)

        # 形态学清理
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

        area = int(np.sum(mask > 0))
        if area / total_px < min_area_ratio:
            continue

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        all_pts = np.vstack(contours)
        x, y, w_box, h_box = cv2.boundingRect(all_pts)
        avg_color = cv2.mean(image, mask)[:3]

        regions.append(Region(
            label=cfg["name"],
            area_px=area,
            area_pct=area / total_px * 100,
            bbox=(x, y, w_box, h_box),
            color_bgr=tuple(int(c) for c in avg_color),
        ))

    regions.sort(key=lambda r: r.area_px, reverse=True)
    return regions


def segment_by_watershed(image: np.ndarray, min_area_ratio: float = 0.01) -> list[Region]:
    """
    基于分水岭算法的分割。
    适合：物体相互接触/重叠的场景（细胞、颗粒）。
    """
    h, w = image.shape[:2]
    total_px = h * w

    # 转灰度 + 二值化
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # 形态学操作找前景
    kernel = np.ones((3, 3), np.uint8)
    opening = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=2)
    sure_bg = cv2.dilate(opening, kernel, iterations=3)

    dist = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
    _, sure_fg = cv2.threshold(dist, 0.5 * dist.max(), 255, 0)
    sure_fg = sure_fg.astype(np.uint8)

    unknown = cv2.subtract(sure_bg, sure_fg)
    _, markers = cv2.connectedComponents(sure_fg)
    markers = markers + 1
    markers[unknown == 255] = 0

    # 应用分水岭
    markers = cv2.watershed(image, markers)

    regions = []
    for marker_id in range(2, markers.max() + 1):
        mask = (markers == marker_id).astype(np.uint8) * 255
        area = int(np.sum(markers == marker_id))
        if area / total_px < min_area_ratio:
            continue

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        all_pts = np.vstack(contours)
        x, y, w_box, h_box = cv2.boundingRect(all_pts)
        avg_color = cv2.mean(image, mask)[:3]

        regions.append(Region(
            label=f"Object_{marker_id - 1}",
            area_px=area,
            area_pct=area / total_px * 100,
            bbox=(x, y, w_box, h_box),
            color_bgr=tuple(int(c) for c in avg_color),
        ))

    regions.sort(key=lambda r: r.area_px, reverse=True)
    return regions


# ── Gemini 辅助标注 ──────────────────────────────────


def label_regions_with_gemini(
    image_path: str,
    regions: list[Region],
    compartment_id: str,
    model_id: str = "google.gemini-2.5-pro",
    endpoint: str = None,
    config_profile: str = "DEFAULT",
) -> list[Region]:
    """
    使用 Gemini 对 OpenCV 分割出的区域进行语义标注。
    Gemini 只负责"起名字"，不负责测量。
    """
    try:
        import oci
        import base64
    except ImportError:
        logger.warning("oci 未安装，跳过 LLM 标注")
        return regions

    # 构建描述文本
    area_desc = "\n".join(
        f"  Region #{i}: area={r.area_px}px ({r.area_pct:.1f}%), "
        f"position={r.bbox}, avg_color=BGR{r.color_bgr}"
        for i, r in enumerate(regions)
    )

    # 编码图片
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    ext = image_path.rsplit(".", 1)[-1].lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
    data_url = f"data:{mime};base64,{b64}"

    # 准备 prompt
    prompt = (
        "I've segmented this image into regions. For each region number below, "
        "tell me what it likely represents (e.g., 'sky', 'building', 'road', 'tree').\n"
        "Regions:\n" + area_desc + "\n\n"
        "Respond ONLY with a JSON mapping: {\"0\": \"sky\", \"1\": \"building\", ...}"
    )

    # 调用 Gemini
    config = oci.config.from_file("~/.oci/config", config_profile)
    if not endpoint:
        endpoint = f"https://inference.generativeai.{config.get('region', 'us-chicago-1')}.oci.oraclecloud.com"

    client = oci.generative_ai_inference.GenerativeAiInferenceClient(
        config=config,
        service_endpoint=endpoint,
        retry_strategy=oci.retry.NoneRetryStrategy(),
        timeout=(30, 300),
    )

    chat_request = oci.generative_ai_inference.models.GenericChatRequest()
    chat_request.api_format = oci.generative_ai_inference.models.BaseChatRequest.API_FORMAT_GENERIC
    chat_request.messages = [
        oci.generative_ai_inference.models.Message(
            role="USER",
            content=[
                oci.generative_ai_inference.models.TextContent(text=prompt),
                oci.generative_ai_inference.models.ImageContent(
                    image_url=oci.generative_ai_inference.models.ImageUrl(url=data_url)
                ),
            ],
        )
    ]
    chat_request.max_tokens = 1024
    chat_request.temperature = 0.1  # 低温度 → 输出更稳定

    detail = oci.generative_ai_inference.models.ChatDetails()
    detail.compartment_id = compartment_id
    detail.serving_mode = oci.generative_ai_inference.models.OnDemandServingMode(
        model_id=model_id
    )
    detail.chat_request = chat_request

    logger.info("正在请求 Gemini 对区域进行语义标注 ...")
    try:
        response = client.chat(detail)
        text = response.data.chat_response.choices[0].message.content[0].text

        # 解析 JSON
        import json
        # 提取 JSON 部分
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            labels = json.loads(text[start:end])
            for i, region in enumerate(regions):
                label_key = str(i)
                if label_key in labels:
                    region.label = labels[label_key]
    except Exception as e:
        logger.warning(f"LLM 标注失败: {e}, 使用默认标签")

    return regions


# ── 可视化 ────────────────────────────────────────────


def draw_regions(
    image: np.ndarray,
    regions: list[Region],
    show_labels: bool = True,
    save_path: Optional[str] = None,
) -> np.ndarray:
    """在图片上绘制分割区域边界和标签。"""
    result = image.copy()
    colors = [
        (255, 0, 0), (0, 255, 0), (0, 0, 255),
        (255, 255, 0), (255, 0, 255), (0, 255, 255),
        (128, 0, 0), (0, 128, 0), (0, 0, 128),
    ]

    for i, region in enumerate(regions):
        color = colors[i % len(colors)]
        # 绘制边界框
        x, y, w, h = region.bbox
        cv2.rectangle(result, (x, y), (x + w, y + h), color, 2)

        # 标注
        if show_labels:
            label = f"{region.label}: {region.area_px}px ({region.area_pct:.1f}%)"
            # 文字背景
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(result, (x, y - th - 4), (x + tw + 4, y), color, -1)
            cv2.putText(
                result, label, (x + 2, y - 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1,
            )

    if save_path:
        cv2.imwrite(save_path, result)
        logger.info(f"可视化结果已保存: {save_path}")

    return result


# ── 主流程 ────────────────────────────────────────────


SEGMENTERS = {
    "clustering": segment_by_color_clustering,
    "edge":       segment_by_edge_contour,
    "hsv":        segment_by_hsv_threshold,
    "watershed":  segment_by_watershed,
}


def main():
    parser = argparse.ArgumentParser(
        description="图片边界识别 & 像素面积计算",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
分割方法说明:
  clustering  颜色聚类分割 — 适合颜色对比明显的图片 (默认)
  edge        边缘检测+轮廓 — 适合形状边界清晰的图片
  hsv         HSV 颜色阈值  — 适合已知目标颜色的场景
  watershed   分水岭算法     — 适合物体相互接触的场景

示例:
  python oci_image_analysis.py --image chart.jpg --method clustering --clusters 5
  python oci_image_analysis.py --image parts.jpg --method edge --min-area 0.005
  python oci_image_analysis.py --image photo.jpg --method watershed --use-llm \\
      --compartment-id ocid1.compartment.oc1...
        """,
    )
    parser.add_argument("--image", required=True, help="图片文件路径")
    parser.add_argument(
        "--method", choices=list(SEGMENTERS.keys()), default="clustering",
        help="分割方法 (默认 clustering)",
    )
    parser.add_argument(
        "--clusters", type=int, default=4,
        help="颜色聚类数 (仅 clustering 方法, 默认 4)",
    )
    parser.add_argument(
        "--min-area", type=float, default=0.01,
        help="最小区域占比 (默认 0.01 = 1%%, 小于此值的区域被过滤)",
    )
    parser.add_argument(
        "--show", action="store_true",
        help="显示可视化结果窗口",
    )
    parser.add_argument(
        "--save", default=None,
        help="保存可视化结果到文件 (如 result.jpg)",
    )

    # LLM 辅助标注
    parser.add_argument(
        "--use-llm", action="store_true",
        help="使用 Gemini 对分割区域进行语义标注",
    )
    parser.add_argument("--compartment-id", help="OCI Compartment OCID")
    parser.add_argument("--model-id", default="google.gemini-2.5-pro", help="模型 ID")
    parser.add_argument("--profile", default="DEFAULT", help="OCI 配置文件名")

    args = parser.parse_args()

    # 1. 读取图片
    image = cv2.imread(args.image)
    if image is None:
        logger.error(f"无法读取图片: {args.image}")
        return
    h, w = image.shape[:2]
    logger.info(f"图片尺寸: {w}x{h} = {w * h} px")

    # 2. 选择分割方法
    seg_fn = SEGMENTERS[args.method]

    if args.method == "clustering":
        regions = segment_by_color_clustering(
            image, n_clusters=args.clusters, min_area_ratio=args.min_area,
        )
    elif args.method == "edge":
        regions = segment_by_edge_contour(
            image, min_contour_area_ratio=args.min_area,
        )
    elif args.method == "hsv":
        regions = segment_by_hsv_threshold(
            image, min_area_ratio=args.min_area,
        )
    elif args.method == "watershed":
        regions = segment_by_watershed(
            image, min_area_ratio=args.min_area,
        )
    else:
        regions = seg_fn(image, min_area_ratio=args.min_area)

    if not regions:
        logger.warning("未识别到任何区域，请调整参数")
        return

    # 3. 可选：Gemini 语义标注
    if args.use_llm:
        if not args.compartment_id:
            logger.error("--use-llm 需要 --compartment-id")
            return
        regions = label_regions_with_gemini(
            image_path=args.image,
            regions=regions,
            compartment_id=args.compartment_id,
            model_id=args.model_id,
            config_profile=args.profile,
        )

    # 4. 输出结果
    print("\n" + "=" * 70)
    print(f"  分割方法: {args.method}")
    print(f"  图片尺寸: {w}x{h} = {w * h:,} px")
    print("=" * 70)
    print(f"  {'区域名称':20s}  {'像素面积':>10s}  {'占比':>6s}  {'位置':>30s}  {'平均颜色'}")
    print("  " + "-" * 68)
    for r in regions:
        print(r.summary)
    print("=" * 70)
    print(f"  共识别 {len(regions)} 个区域")

    # 5. 可视化
    if args.save or args.show:
        result = draw_regions(image, regions, save_path=args.save)
        if args.show:
            cv2.imshow("Segmentation Result", result)
            logger.info("按任意键关闭窗口 ...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
