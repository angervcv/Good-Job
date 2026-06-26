"""
LLM API 客户端封装 (兼容 OpenAI 协议)
支持 DeepSeek / OpenAI / 阿里云百炼等
"""

import json
from openai import OpenAI
import config


class LLMClient:
    """统一的 LLM 调用客户端"""

    def __init__(self):
        self.client = OpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
        )
        self.model = config.LLM_MODEL

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = None,
        max_tokens: int = None,
        response_format: dict = None,
    ) -> str:
        """发送聊天请求

        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            temperature: 温度参数 (默认使用 config 设置)
            max_tokens: 最大 token 数
            response_format: 响应格式 (如 {"type": "json_object"})

        Returns:
            模型回复文本
        """
        if temperature is None:
            temperature = config.LLM_TEMPERATURE
        if max_tokens is None:
            max_tokens = config.LLM_MAX_TOKENS

        kwargs = {
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }

        if response_format:
            kwargs["response_format"] = response_format

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def chat_json(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
    ) -> dict:
        """发送聊天请求，返回 JSON 对象"""
        response = self.chat(
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        # 尝试清理 markdown 代码块包装
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:]) if len(lines) > 1 else response
            if response.endswith("```"):
                response = response[:-3]
        return json.loads(response)

    def batch_chat(
        self,
        items: list[dict],
        system_prompt: str,
        temperature: float = None,
    ) -> list[str]:
        """批量调用 (顺序执行)

        Args:
            items: [{"user_message": str}, ...]
            system_prompt: 系统提示词（对所有 item 相同）

        Returns:
            回复文本列表
        """
        results = []
        for i, item in enumerate(items):
            try:
                result = self.chat(
                    system_prompt=system_prompt,
                    user_message=item["user_message"],
                    temperature=temperature,
                )
                results.append(result)
            except Exception as e:
                print(f"  [批量调用] 第 {i + 1} 项失败: {e}")
                results.append(None)
        return results


# 全局单例
_client: LLMClient | None = None


def get_client() -> LLMClient:
    """获取 LLM 客户端单例"""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def check_connection() -> bool:
    """检查 LLM API 连接是否正常"""
    try:
        client = get_client()
        response = client.chat(
            system_prompt="你是一个有用的助手。",
            user_message="请回复'连接正常'这四个字。",
            max_tokens=20,
        )
        return "连接正常" in response
    except Exception as e:
        print(f"LLM 连接检查失败: {e}")
        return False


if __name__ == "__main__":
    if check_connection():
        print("LLM API 连接正常！")
    else:
        print("LLM API 连接失败，请检查 API Key 和网络配置。")