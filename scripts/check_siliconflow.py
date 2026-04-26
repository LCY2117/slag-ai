from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_config
from app.llm import siliconflow_chat

if __name__ == "__main__":
    cfg = load_config("config.yaml")
    result = siliconflow_chat([
        {"role": "system", "content": "你是一个简洁的 API 连通性测试助手。"},
        {"role": "user", "content": "请回复：MSPC-GreenAI API 连接成功。"},
    ], cfg, fallback="未配置 API Key 或 API 调用失败，当前处于离线模式。")
    print("mode:", result.get("mode"))
    if result.get("error"):
        print("error:", result.get("error"))
    print("content:", result.get("content"))
