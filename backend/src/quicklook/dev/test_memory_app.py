f"""
テスト用のFastAPIアプリケーション
メモリ使用量やリソース制限の情報を提供するエンドポイントを含む
"""

import os
import psutil
import resource
from fastapi import FastAPI

app = FastAPI(title="Memory Test App")


@app.get("/healthz")
def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "ok"}


@app.get("/memory_info")
def get_memory_info():
    """現在のメモリ使用量とリソース制限情報を返す"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    # リソース制限を取得
    rss_limit = resource.getrlimit(resource.RLIMIT_RSS)
    
    return {
        "pid": os.getpid(),
        "memory_usage": {
            "rss": memory_info.rss,  # Resident Set Size (実際に使用している物理メモリ)
            "vms": memory_info.vms,  # Virtual Memory Size (仮想メモリサイズ)
            "rss_mb": memory_info.rss / (1024 * 1024),
            "vms_mb": memory_info.vms / (1024 * 1024)
        },
        "resource_limits": {
            "rss_soft_limit": rss_limit[0],
            "rss_hard_limit": rss_limit[1],
            "rss_soft_limit_mb": rss_limit[0] / (1024 * 1024) if rss_limit[0] != -1 else -1,
            "rss_hard_limit_mb": rss_limit[1] / (1024 * 1024) if rss_limit[1] != -1 else -1,
        }
    }


@app.get("/allocate_memory/{mb}")
def allocate_memory(mb: int):
    """指定したMB分のメモリを割り当てる（テスト用）"""
    try:
        # メモリを割り当て（注意：これは危険な操作です）
        size = mb * 1024 * 1024
        data = bytearray(size)
        
        # メモリ使用量を確認
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        return {
            "allocated_mb": mb,
            "current_rss_mb": memory_info.rss / (1024 * 1024),
            "success": True
        }
    except MemoryError as e:
        return {
            "allocated_mb": mb,
            "error": str(e),
            "success": False
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)