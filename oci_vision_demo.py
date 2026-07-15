#!/usr/bin/env python3
"""
OCI Generative AI - 图片内容识别 Demo
=======================================
使用 OCI Generative AI 的视觉多模态模型分析图片内容。

前置条件:
  pip install oci>=2.130.0
  配置 ~/.oci/config (参考 OCI SDK 文档)
  开通 OCI Generative AI 服务并获取模型访问权限

用法:
  python oci_vision_demo.py --image photo.jpg \
      --compartment-id ocid1.compartment.oc1... \
      --model-id google.gemini-2.5-pro \
      --model-family gemini \
      --prompt "描述这张图片"

支持的模型家族:
  gemini  — Google Gemini 2.5 Pro/Flash (推荐, 图片识别能力强)
  cohere  — Cohere Command R+ Vision
  claude  — Claude 3.x (若部署在 OCI)
  llama   — Meta Llama 3.2/4 Vision
"""

import oci
import base64
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ── 工具函数 ──────────────────────────────────────────


def encode_image(image_path: str) -> dict:
    """读取图片文件, 返回 base64 数据和 media_type。"""
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
# 每种模型家族使用不同的 OCI SDK 请求类


def build_generic_chat_request(prompt: str, image_data: str, media_type: str):
    """
    Generic 格式 (Gemini / Meta Llama / xAI Grok)
    ----------------------------------------------
    使用 GenericChatRequest, content 为 TextContent + ImageContent 数组。
    """
    data_url = f"data:{media_type};base64,{image_data}"

    models = oci.generative_ai_inference.models
    chat_request = models.GenericChatRequest()
    chat_request.api_format = models.BaseChatRequest.API_FORMAT_GENERIC
    chat_request.messages = [
        models.Message(
            role="USER",
            content=[
                models.TextContent(text=prompt),
                models.ImageContent(
                    image_url=models.ImageUrl(url=data_url)
                ),
            ],
        )
    ]
    chat_request.max_tokens = 4096
    chat_request.temperature = 0.7
    return chat_request


def build_cohere_chat_request(prompt: str, image_data: str, media_type: str):
    """
    Cohere Command R+ / Command A Vision
    ------------------------------------
    Cohere 将图片 data URL 嵌入 message 文本中.
    """
    data_url = f"data:{media_type};base64,{image_data}"
    req = oci.generative_ai_inference.models.CohereChatRequest()
    req.message = f"{prompt}\n\nImage: {data_url}"
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


# ── 响应解析 ──────────────────────────────────────────


def parse_cohere_response(response) -> str:
    return response.data.chat_response.text


def parse_claude_response(response) -> str:
    blocks = response.data.content
    if isinstance(blocks, list):
        return "".join(b.text for b in blocks if hasattr(b, "text") and b.text)
    return str(blocks)


def parse_generic_response(response) -> str:
    """解析 GenericChatRequest (Gemini/Llama/Grok) 的响应。"""
    try:
        choice = response.data.chat_response.choices[0]
        # content 可能是一个文本字符串或 content block 列表
        if isinstance(choice.message.content, list):
            return "".join(
                c.text for c in choice.message.content
                if hasattr(c, "text") and c.text
            )
        return str(choice.message.content)
    except (AttributeError, IndexError) as e:
        logger.warning(f"解析响应时出错: {e}, 返回原始数据")
        return str(response.data)


# ── 主调用逻辑 ────────────────────────────────────────


# 模型家族配置: (builder_fn, parser_fn)
FAMILY_CONFIG = {
    "gemini": (build_generic_chat_request, parse_generic_response),
    "llama":  (build_generic_chat_request, parse_generic_response),
    "cohere": (build_cohere_chat_request,  parse_cohere_response),
    "claude": (build_claude_chat_request,  parse_claude_response),
}


def analyze_image(
    image_path: str,
    prompt: str,
    compartment_id: str,
    model_id: str,
    model_family: str = "gemini",
    endpoint: str = None,
    config_profile: str = "DEFAULT",
) -> str:
    """
    使用 OCI Generative AI 分析图片内容。

    Args:
        image_path:    图片文件路径
        prompt:        分析提示词 (中英文均可)
        compartment_id: OCI Compartment OCID
        model_id:      模型 ID (如 "google.gemini-2.5-pro")
        model_family:  模型家族 — "gemini" | "llama" | "cohere" | "claude"
        endpoint:      服务端点 URL
        config_profile: OCI 配置文件名

    Returns:
        模型返回的分析文本
    """
    # 1. 加载 OCI 配置
    config = oci.config.from_file("~/.oci/config", config_profile)

    # 2. 服务端点
    if not endpoint:
        region = config.get("region", "us-chicago-1")
        endpoint = f"https://inference.generativeai.{region}.oci.oraclecloud.com"

    # 3. 创建客户端
    client = oci.generative_ai_inference.GenerativeAiInferenceClient(
        config=config,
        service_endpoint=endpoint,
        retry_strategy=oci.retry.NoneRetryStrategy(),
        timeout=(30, 300),
    )

    # 4. 编码图片
    encoded = encode_image(image_path)
    logger.info(f"图片已编码: {len(encoded['data'])} 字符 ({encoded['media_type']})")

    # 5. 获取构造器和解析器
    family_cfg = FAMILY_CONFIG.get(model_family)
    if not family_cfg:
        raise ValueError(
            f"不支持的模型家族: {model_family}, "
            f"可选: {list(FAMILY_CONFIG.keys())}"
        )
    builder, parser = family_cfg

    # 6. 构建 ChatRequest
    chat_request = builder(prompt, encoded["data"], encoded["media_type"])

    # 7. 组装完整请求
    detail = oci.generative_ai_inference.models.ChatDetails()
    detail.compartment_id = compartment_id
    detail.serving_mode = oci.generative_ai_inference.models.OnDemandServingMode(
        model_id=model_id
    )
    detail.chat_request = chat_request

    # 8. 调用 API
    logger.info(f"正在请求 OCI Generative AI ({model_id}) ...")
    response = client.chat(detail)

    # 9. 解析响应
    return parser(response)


# ── CLI 入口 ──────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="使用 OCI Generative AI 分析图片内容"
    )
    parser.add_argument(
        "--image", required=True,
        help="图片文件路径 (支持 jpg/png/webp)",
    )
    parser.add_argument(
        "--prompt", "-p",
        default=(
            "Describe this image in detail. "
            "What objects, people, text, and scene do you see?"
        ),
        help="分析提示词 (中英文均可)",
    )
    parser.add_argument(
        "--compartment-id", required=True,
        help="OCI Compartment OCID",
    )
    parser.add_argument(
        "--model-id",
        default="google.gemini-2.5-pro",
        help=(
            "模型 ID (默认 google.gemini-2.5-pro)。"
            "其他示例: google.gemini-2.5-flash, "
            "meta.llama-3.2-90b-vision-instruct"
        ),
    )
    parser.add_argument(
        "--model-family",
        choices=list(FAMILY_CONFIG.keys()),
        default="gemini",
        help="模型家族 (根据 --model-id 选择, 默认 gemini)",
    )
    parser.add_argument(
        "--endpoint",
        help="服务端点 URL (默认根据 region 自动生成)",
    )
    parser.add_argument(
        "--profile", default="DEFAULT",
        help="OCI 配置文件名 (~/.oci/config 中的 profile)",
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
