from app.api.summ import Summ
from app.api.html import Html
from fastapi import APIRouter

# 创建 APIRouter 实例
router = APIRouter()


html = Html()
summ = Summ()


router.get("/api/get/models")(summ.get_models)
router.post("/api/get/content")(summ.extract_content)
router.post("/api/summ")(summ.chat)
router.get("/")(html.index)
