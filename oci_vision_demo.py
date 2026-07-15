#!/usr/bin/env python3
"""
OCI Generative AI - 图片内容识别 Demo
=======================================
使用 OCI Generative AI 的视觉多模态模型分析图片内容。

前置条件:
  pip install oci
  配置 ~/.oci/config (参考 OCI SDK 文档)

用法:
  python oci_vision_demo.py --image photo.jpg \
      --compartment-id ocid1.compartment.oc1... \
      --model-id ocid1.generativeaimodel.oc1... \
      --prompt "描述这张图片"
"""

import oci
import base64
import json
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ── 工具函数 ──────────────────────────────────────────


def encode_image(image_path: str) -> dict:
    """读取图片文件，返回 base64 数据和 media_type。"""
    with open(image_path, "rb") as f:
        raw = base64.b64encode(f.read()).decode()

    ext = Path(image_path).suffix.lower()
    mime_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    mime = mime_map.get(ext, "image/jpeg")
    return {"data": raw, "media_type": mime}


# ── 不同模型家族的 ChatRequest 构造 ──────────────────


def build_cohere_chat_request(prompt: str, image_data: str, media_type: str):
    """
    Cohere Command R+ (Vision)
    --------------------------
    将图片 data URL 拼入 message 文本中，模型自动识别。
    """
    data_url = f"data:{media_type};base64,{image_data}"
    req = oci.generative_ai_inference.models.CohereChatRequest()
    req.message = f"{prompt}\n\nImage data: {data_url}"
    req.max_tokens = 2000
    req.temperature = 0.7
    req.is_stream = False
    return req


def build_llama_chat_request(prompt: str, image_data: str, media_type: str):
    """
    Meta Llama 3.2 Vision (11B / 90B)
    -----------------------------------
    Llama 使用 messages 列表，content 为 text + image_url 的数组。
    在 OCI 的 Llama 模型中，通常使用 OpenAI 兼容的消息格式。
    """
    data_url = f"data:{media_type};base64,{image_data}"
    req = oci.generative_ai_inference.models.CohereChatRequest()
    req.message = json.dumps([
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    ])
    req.max_tokens = 2000
    req.temperature = 0.7
    req.is_stream = False
    return req


def build_claude_chat_request(prompt: str, image_data: str, media_type: str):
    """
    Anthropic Claude 3.x (若部署在 OCI)
    ------------------------------------
    使用 Anthropic 标准的 content blocks 格式。
    """
    req = oci.generative_ai_inference.models.AnthropicChatRequest()
    req.messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                },
            ],
        }
    ]
    req.max_tokens = 2000
    req.temperature = 0.7
    return req


# ── 主调用逻辑 ────────────────────────────────────────


def analyze_image(
    image_path: str,
    prompt: str,
    compartment_id: str,
    model_id: str,
    model_family: str = "cohere",
    endpoint: str = None,
    config_profile: str = "DEFAULT",
) -> str:
    """
    使用 OCI Generative AI 分析图片内容。

    Args:
        image_path:   图片文件路径
        prompt:       分析提示词（支持中文）
        compartment_id: OCI Compartment OCID
        model_id:      视觉模型 OCID
        model_family:  模型家族 — "cohere" | "llama" | "claude"
        endpoint:      服务端点 URL
        config_profile: OCI 配置文件名

    Returns:
        模型返回的分析文本
    """
    # 1. 加载 OCI 配置
    config = oci.config.from_file("~/.oci/config", config_profile)

    # 2. 服务端点（根据你的区域调整）
    region = "us-chicago-1"
    if not endpoint:
        endpoint = f"https://inference.generativeai.{region}.oci.oraclecloud.com"

    # 3. 创建客户端
    client = oci.generative_ai_inference.GenerativeAiInferenceClient(
        config=config,
        service_endpoint=endpoint,
        retry_strategy=oci.retry.NoneRetryStrategy(),
        timeout=(10, 240),
    )

    # 4. 编码图片
    encoded = encode_image(image_path)
    logger.info(f"图片已编码: {len(encoded['data'])} 字符 ({encoded['media_type']})")

    # 5. 根据模型家族构造 ChatRequest
    builders = {
        "cohere": build_cohere_chat_request,
        "llama":  build_llama_chat_request,
        "claude": build_claude_chat_request,
    }
    builder = builders.get(model_family)
    if not builder:
        raise ValueError(
            f"不支持的模型家族: {model_family}，可选: {list(builders.keys())}"
        )

    chat_request = builder(prompt, encoded["data"], encoded["media_type"])

    # 6. 组装完整请求
    detail = oci.generative_ai_inference.models.ChatDetails()
    detail.compartment_id = compartment_id
    detail.serving_mode = oci.generative_ai_inference.models.OnDemandServingMode(
        model_id=model_id
    )
    detail.chat_request = chat_request

    # 7. 调用 API
    logger.info("正在请求 OCI Generative AI ...")
    response = client.chat(detail)

    # 8. 解析响应
    if model_family == "cohere":
        return response.data.chat_response.text
    elif model_family == "claude":
        blocks = response.data.content
        if isinstance(blocks, list):
            return "".join(
                b.text for b in blocks if hasattr(b, "text") and b.text
            )
        return str(blocks)
    elif model_family == "llama":
        return response.data.chat_response.text

    return str(response.data)


# ── CLI 入口 ──────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="使用 OCI Generative AI 分析图片内容"
    )
    parser.add_argument(
        "--image", required=True,
        help="图片文件路径（支持 jpg/png/webp）",
    )
    parser.add_argument(
        "--prompt", "-p",
        default=(
            "Describe this image in detail. "
            "What objects, people, text, and scene do you see?"
        ),
        help="分析提示词",
    )
    parser.add_argument(
        "--compartment-id", required=True,
        help="OCI Compartment OCID",
    )
    parser.add_argument(
        "--model-id", required=True,
        help="支持视觉的模型 OCID",
    )
    parser.add_argument(
        "--model-family",
        choices=["cohere", "llama", "claude"],
        default="cohere",
        help="模型家族（根据你的模型选择，默认 cohere）",
    )
    parser.add_argument(
        "--endpoint",
        help=(
            "服务端点 URL（默认自动根据 region 生成，"
            "也可手动指定）"
        ),
    )
    parser.add_argument(
        "--region", default="us-chicago-1",
        help="OCI 区域（默认 us-chicago-1）",
    )
    parser.add_argument(
        "--profile", default="DEFAULT",
        help="OCI 配置文件名（~/.oci/config 中的 profile）",
    )

    args = parser.parse_args()

    try:
        result = analyze_image(
            image_path=args.image,
            prompt=args.prompt,
            compartment_id=args.compartment_id,
            model_id=args.model_id,
            model_family=args.model_family,
            endpoint=args.endpoint,
            config_profile=args.profile,
        )
        print("\n" + "=" * 60)
        print("分析结果")
        print("=" * 60)
        print(result)

    except oci.exceptions.ServiceError as e:
        logger.error(f"OCI API 错误: {e.status} — {e.message}")
        logger.error(f"请求 ID: {e.opc_request_id}")
    except Exception as e:
        logger.error(f"出现错误: {e}")
        raise


if __name__ == "__main__":
    main()
