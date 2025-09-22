"""
簡易なcoordinatorとgeneratorアプリケーション

統合テスト用の最小限のアプリケーション実装
"""

from fastapi import FastAPI
from quicklook.comm import coordinator, generator

# Coordinator アプリケーション
coordinator_app = FastAPI(lifespan=coordinator.lifespan)
coordinator_app.include_router(coordinator.router)

# Generator アプリケーション  
generator_app = FastAPI(lifespan=generator.lifespan)
generator_app.include_router(generator.router)